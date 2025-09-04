from celery import Task
from celery.exceptions import Reject
from src.celery_app import celery_app
from src.enrichment_pipeline import enrich_ad
from src.models import AdKnowledgeObject
from src.logger import logger
from src.dependencies import get_supabase_client, get_gemini_flash, get_gemini_pro, get_embedding_model

# Import necessary classes for client types
from supabase import Client as SupabaseClient
from google.generativeai.client import Client as GeminiClient
from langchain_google_genai import GoogleGenerativeAIEmbeddings

class BaseTaskWithClients(Task):
    _supabase_client: SupabaseClient = None
    _gemini_flash_client: GeminiClient = None
    _gemini_pro_client: GeminiClient = None
    _embedding_model_instance: GoogleGenerativeAIEmbeddings = None

    @property
    def supabase_client(self) -> SupabaseClient:
        if self._supabase_client is None:
            self._supabase_client = get_supabase_client()
        return self._supabase_client

    @property
    def gemini_flash_client(self) -> GeminiClient:
        if self._gemini_flash_client is None:
            self._gemini_flash_client = get_gemini_flash()
        return self._gemini_flash_client

    @property
    def gemini_pro_client(self) -> GeminiClient:
        if self._gemini_pro_client is None:
            self._gemini_pro_client = get_gemini_pro()
        return self._gemini_pro_client

    @property
    def embedding_model_instance(self) -> GoogleGenerativeAIEmbeddings:
        if self._embedding_model_instance is None:
            self._embedding_model_instance = get_embedding_model()
        return self._embedding_model_instance

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True, base=BaseTaskWithClients)
def enrichment_task(self, ad_id: str):
    """
    Celery task to enrich an ad, fetching data from the DB.
    Handles retries and dead-lettering.
    """
    try:
        logger.info(f"Starting enrichment for ad ID: {ad_id}")

        # Access clients from the task instance
        supabase = self.supabase_client
        gemini_flash = self.gemini_flash_client
        gemini_pro = self.gemini_pro_client
        embedding_model = self.embedding_model_instance

        # Fetch the ad data from Supabase
        response = supabase.from_("ads").select("*").eq("id", ad_id).single().execute()
        
        if not response.data:
            logger.error(f"Ad with ID {ad_id} not found in the database. Rejecting task.")
            raise Reject("Ad not found", requeue=False)

        ad_data = AdKnowledgeObject(**response.data)

        # Idempotency Check
        if ad_data.status in ['ENRICHED', 'ENRICHING']:
            logger.warning(f"Ad {ad_id} is already {ad_data.status}. Skipping task.")
            return
        
        # Set status to ENRICHING
        supabase.from_("ads").update({"status": "ENRICHING"}).eq("id", ad_id).execute()

        # Run the enrichment pipeline using clients from the task instance
        enriched_ad = enrich_ad(
            ad_data=ad_data,
            gemini_flash=gemini_flash,
            gemini_pro=gemini_pro,
            embedding_model=embedding_model,
            supabase=supabase
        )

        # Update the database with the result
        update_data = enriched_ad.model_dump(exclude_unset=True)
        supabase.from_("ads").update(update_data).eq("id", ad_id).execute()

        logger.info(f"Successfully enriched ad {ad_id}")
        return enriched_ad.model_dump_json()

    except Exception as e:
        logger.error(f"Enrichment task failed for ad {ad_id}: {e}")
        try:
            # Retry for transient errors
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # Move to dead-letter queue for persistent errors
            logger.error(f"Max retries exceeded for ad {ad_id}. Moving to DLQ.")
            # Update status to FAILED in DB
            supabase.from_("ads").update({
                "status": "FAILED",
                "error_log": f"Max retries exceeded: {e}"
            }).eq("id", ad_id).execute()
            raise Reject(e, requeue=False)
