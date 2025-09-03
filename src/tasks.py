from celery.exceptions import Reject
from src.celery_app import celery_app
from src.enrichment_pipeline import enrich_ad
from src.models import AdKnowledgeObject
from src.logger import logger

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def enrichment_task(self, ad_id: str):
    """
    Celery task to enrich an ad, fetching data from the DB.
    Handles retries and dead-lettering.
    """
    try:
        logger.info(f"Starting enrichment for ad ID: {ad_id}")

        # Fetch the ad data from Supabase
        response = self.supabase.from_("ads").select("*").eq("id", ad_id).single().execute()
        
        if not response.data:
            logger.error(f"Ad with ID {ad_id} not found in the database. Rejecting task.")
            raise Reject("Ad not found", requeue=False)

        ad_data = AdKnowledgeObject(**response.data)

        # Idempotency Check
        if ad_data.status in ['ENRICHED', 'ENRICHING']:
            logger.warning(f"Ad {ad_id} is already {ad_data.status}. Skipping task.")
            return
        
        # Set status to ENRICHING
        self.supabase.from_("ads").update({"status": "ENRICHING"}).eq("id", ad_id).execute()
        if response.data:
            current_status = response.data[0]['status']
            if current_status in ['ENRICHED', 'ENRICHING']:
                logger.warning(f"Ad {ad_data.ad_id} is already {current_status}. Skipping task.")
                return
        
        # Set status to ENRICHING
        self.supabase.from_("ads").update({"status": "ENRICHING"}).eq("id", str(ad_data.id)).execute()

        # Run the enrichment pipeline using clients from the task instance
        enriched_ad = enrich_ad(
            ad_data=ad_data,
            gemini_flash=self.gemini_flash,
            gemini_pro=self.gemini_pro,
            embedding_model=self.embedding_model,
            supabase=self.supabase
        )

        # Update the database with the result
        update_data = enriched_ad.model_dump(exclude_unset=True)
        self.supabase.from_("ads").update(update_data).eq("id", ad_id).execute()

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
            self.supabase.from_("ads").update({
                "status": "FAILED",
                "error_log": f"Max retries exceeded: {e}"
            }).eq("id", ad_id).execute()
            raise Reject(e, requeue=False)
