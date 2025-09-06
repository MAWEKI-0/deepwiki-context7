from celery.exceptions import Reject
from src.celery_app import celery_app
from src.enrichment_pipeline import enrich_ad
from src.models import AdKnowledgeObject
from src.logger import logger
from src.celery_base import BaseTaskWithClients

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

        # Atomic Idempotency Check and Status Update
        # Attempt to set status to ENRICHING only if it's currently PENDING
        update_response = supabase.from_("ads").update({"status": "ENRICHING"}).eq("id", ad_id).eq("status", "PENDING").execute()

        if update_response.count == 0:
            # If no rows were updated, it means the ad was not in PENDING status,
            # or it was already ENRICHED/ENRICHING by another process.
            response = supabase.from_("ads").select("status").eq("id", ad_id).single().execute()
            current_status = response.data["status"] if response.data else "UNKNOWN"
            logger.warning(f"Ad {ad_id} is already {current_status} or not found. Skipping task.")
            return

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
