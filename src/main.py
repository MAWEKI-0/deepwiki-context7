import asyncio
import traceback
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import Client
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from src.models import AdKnowledgeObject
from src.query_engine import synthesize_answer
from src.dependencies import get_supabase, get_settings, create_gemini_pro_client, create_embedding_model_client
from src.logger import logger
from src.tasks import enrichment_task
from src.config import Settings

app = FastAPI(
    title="AdGenesis Intelligence Engine",
    description="API for ingesting, enriching, and querying competitor ad intelligence.",
    version="1.0.0",
)

@app.middleware("http")
async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Unhandled exception: {e}\n{error_traceback}")
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error", "detail": str(e)},
        )

class IngestAdRequest(BaseModel):
    ad_id: int
    raw_data_snapshot: dict
    ad_creative_url: str

class IngestAdResponse(BaseModel):
    message: str
    ad_id: str

class QueryRequest(BaseModel):
    query: str
    filter_criteria: Optional[dict] = None
    k: int = 5

@app.post("/ingest-ad", response_model=IngestAdResponse, status_code=202)
async def ingest_and_enrich_ad(
    request: IngestAdRequest,
    supabase: Client = Depends(get_supabase),
):
    """
    Ingests a new raw ad and schedules it for background enrichment using Celery.
    """
    request.raw_data_snapshot["ad_creative_url"] = request.ad_creative_url

    ad_to_ingest = AdKnowledgeObject(
        ad_id=request.ad_id,
        raw_data_snapshot=request.raw_data_snapshot,
        status="PENDING"
    )

    response = supabase.from_("ads").insert(ad_to_ingest.model_dump(exclude_none=True)).execute()
    
    if not response.data:
        raise HTTPException(status_code=500, detail=f"Failed to ingest ad: {response.error}")

    inserted_ad = AdKnowledgeObject(**response.data[0])
    
    # Dispatch the enrichment task to Celery with only the ad's ID
    enrichment_task.delay(ad_id=str(inserted_ad.id))

    return IngestAdResponse(
        message="Ad accepted for enrichment.",
        ad_id=str(inserted_ad.id)
    )

@app.post("/query-ads")
async def query_ad_intelligence(
    request: QueryRequest,
    supabase: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    gemini_pro: ChatGoogleGenerativeAI = create_gemini_pro_client(settings)
    embedding_model: GoogleGenerativeAIEmbeddings = create_embedding_model_client(settings)
    """
    Queries the enriched ad data and synthesizes an answer based on the user's natural language query.
    """
    answer = await synthesize_answer(
        query=request.query,
        supabase=supabase,
        gemini_pro=gemini_pro,
        embedding_model=embedding_model,
        filter_criteria=request.filter_criteria,
        k=request.k,
    )
    return {"query": request.query, "answer": answer}

@app.get("/ads/{ad_id}/status")
async def get_ad_status(ad_id: str, supabase: Client = Depends(get_supabase)):
    """
    Retrieves the current status of an ad enrichment task.
    """
    response = supabase.from_("ads").select("status, error_log").eq("id", ad_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Ad not found")
    return response.data[0]

@app.get("/health")
async def health_check():
    """
    Health check endpoint to ensure the API is running.
    """
    return {"status": "ok"}

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Shutting down logger.")
    logger.remove()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
