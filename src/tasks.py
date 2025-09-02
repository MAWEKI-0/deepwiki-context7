from celery.exceptions import Reject
from src.celery_app import celery_app
from src.enrichment_pipeline import enrich_ad
from src.models import AdKnowledgeObject
from src.logger import logger
from src.dependencies import get_supabase_client, get_gemini_flash, get_gemini_pro, get_embedding_model

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def enrichment_task(self, ad_data_dict: dict):
    """
    Celery task to enrich an ad.
    Handles retries and dead-lettering.
    """
    try:
        ad_data = AdKnowledgeObject(**ad_data_dict)
        logger.info(f"Starting enrichment for ad {ad_data.ad_id}")

        # Get dependencies
        supabase = get_supabase_client()

        # Idempotency Check
        response = supabase.from_("ads").select("status").eq("id", str(ad_data.id)).execute()
        if response.data:
            current_status = response.data[0]['status']
            if current_status in ['ENRICHED', 'ENRICHING']:
                logger.warning(f"Ad {ad_data.ad_id} is already {current_status}. Skipping task.")
                return
        
        # Set status to ENRICHING
        supabase.from_("ads").update({"status": "ENRICHING"}).eq("id", str(ad_data.id)).execute()
        gemini_flash = get_gemini_flash()
        gemini_pro = get_gemini_pro()
        embedding_model = get_embedding_model()

        # Run the enrichment pipeline
        enriched_ad = enrich_ad(
            ad_data=ad_data,
            gemini_flash=gemini_flash,
            gemini_pro=gemini_pro,
            embedding_model=embedding_model,
            supabase=supabase
        )

        # Update the database with the result
        update_data = enriched_ad.model_dump(exclude_unset=True)
        supabase.from_("ads").update(update_data).eq("id", str(enriched_ad.id)).execute()

        logger.info(f"Successfully enriched ad {enriched_ad.ad_id}")
        return enriched_ad.model_dump_json()

    except Exception as e:
        logger.error(f"Enrichment task failed for ad {ad_data_dict.get('ad_id')}: {e}")
        try:
            # Retry for transient errors
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # Move to dead-letter queue for persistent errors
            logger.error(f"Max retries exceeded for ad {ad_data_dict.get('ad_id')}. Moving to DLQ.")
            # Update status to FAILED in DB
            supabase = get_supabase_client()
            supabase.from_("ads").update({
                "status": "FAILED",
                "error_log": f"Max retries exceeded: {e}"
            }).eq("id", ad_data_dict.get("id")).execute()
            raise Reject(e, requeue=False)
