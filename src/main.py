import asyncio
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from supabase import Client
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from src.enrichment_pipeline import enrich_ad
from src.models import AdKnowledgeObject
from src.query_engine import hybrid_retrieve_ads, synthesize_answer
from src.dependencies import get_supabase, get_gemini_flash, get_gemini_pro, get_embedding_model
from src.logger import logger

from src.config import settings

app = FastAPI(
    title="AdGenesis Intelligence Engine",
    description="API for ingesting, enriching, and querying competitor ad intelligence.",
    version="1.0.0",
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
    background_tasks: BackgroundTasks,
    supabase: Client = Depends(get_supabase),
    gemini_flash: ChatGoogleGenerativeAI = Depends(get_gemini_flash),
    gemini_pro: ChatGoogleGenerativeAI = Depends(get_gemini_pro),
    embedding_model: GoogleGenerativeAIEmbeddings = Depends(get_embedding_model),
):
    """
    Ingests a new raw ad and schedules it for background enrichment.
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
    
    background_tasks.add_task(
        enrich_ad_and_update, inserted_ad, supabase, gemini_flash, gemini_pro, embedding_model
    )

    return IngestAdResponse(
        message="Ad accepted for enrichment.",
        ad_id=str(inserted_ad.id)
    )

async def enrich_ad_and_update(
    ad: AdKnowledgeObject,
    supabase: Client,
    gemini_flash: ChatGoogleGenerativeAI,
    gemini_pro: ChatGoogleGenerativeAI,
    embedding_model: GoogleGenerativeAIEmbeddings,
):
    """
    Task to enrich an ad and update its status in Supabase.
    """
    try:
        logger.info(f"Starting enrichment for ad: {ad.id}")
        enriched_ad = await enrich_ad(ad, gemini_flash, gemini_pro, embedding_model, supabase)
        supabase.from_("ads").update(enriched_ad.model_dump(exclude_none=True)).eq("id", enriched_ad.id).execute()
        logger.info(f"Enrichment complete for ad: {ad.id}")
    except Exception as e:
        error_message = f"Enrichment failed for ad {ad.id}: {str(e)}"
        logger.error(error_message)
        supabase.from_("ads").update({
            "status": "FAILED",
            "error_log": error_message
        }).eq("id", ad.id).execute()

@app.post("/query-ads")
async def query_ad_intelligence(
    request: QueryRequest,
    supabase: Client = Depends(get_supabase),
    gemini_pro: ChatGoogleGenerativeAI = Depends(get_gemini_pro),
    embedding_model: GoogleGenerativeAIEmbeddings = Depends(get_embedding_model),
):
    """
    Queries the enriched ad data and synthesizes an answer based on the user's natural language query.
    """
    retrieved_ads = await hybrid_retrieve_ads(
        request.query, embedding_model, supabase, request.filter_criteria, request.k
    )
    answer = await synthesize_answer(request.query, retrieved_ads, gemini_pro, embedding_model)
    return {"query": request.query, "answer": answer, "retrieved_ads_count": len(retrieved_ads)}

@app.get("/health")
async def health_check():
    """
    Health check endpoint to ensure the API is running.
    """
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
