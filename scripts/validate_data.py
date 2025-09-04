import os
import random
from typing import List, Dict, Any

from pydantic import ValidationError
from supabase import create_client, Client

from src.models import AdKnowledgeObject
from src.logger import logger

# --- Configuration ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
TABLE_NAME = "ads"
SAMPLE_SIZE = 20  # Number of ads to sample for validation

def get_supabase_client() -> Client:
    """Initializes and returns a Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be set in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_random_ads(client: Client, table_name: str, sample_size: int) -> List[Dict[str, Any]]:
    """Fetches a random sample of ads from the database."""
    # This is a simplified approach to get a random sample.
    # For larger datasets, a more efficient method might be needed.
    response = client.from_(table_name).select("id, enriched_at").execute()
    if not response.data:
        return []
    
    all_ids = [item['id'] for item in response.data]
    sample_ids = random.sample(all_ids, min(len(all_ids), sample_size))
    
    response = client.from_(table_name).select("*").in_("id", sample_ids).execute()
    return response.data

def validate_ads_data(ads_data: List[Dict[str, Any]]) -> None:
    """Validates a list of ad data against the AdKnowledgeObject model."""
    valid_count = 0
    invalid_count = 0

    for ad in ads_data:
        try:
            AdKnowledgeObject.model_validate(ad)
            valid_count += 1
            logger.info(f"Ad with ID {ad.get('id')} is valid.")
        except ValidationError as e:
            invalid_count += 1
            logger.error(f"Ad with ID {ad.get('id')} is invalid. Errors: {e.errors()}")

    logger.info("--- Validation Summary ---")
    logger.info(f"Total ads checked: {len(ads_data)}")
    logger.info(f"Valid ads: {valid_count}")
    logger.info(f"Invalid ads: {invalid_count}")

def main():
    """Main function to run the data validation process."""
    logger.info("Starting data validation process...")
    try:
        supabase_client = get_supabase_client()
        ads_to_validate = fetch_random_ads(supabase_client, TABLE_NAME, SAMPLE_SIZE)
        
        if not ads_to_validate:
            logger.info("No ads found to validate.")
            return
            
        validate_ads_data(ads_to_validate)
        
    except Exception as e:
        logger.error(f"An error occurred during the validation process: {e}")
    finally:
        logger.info("Data validation process finished.")

if __name__ == "__main__":
    main()
