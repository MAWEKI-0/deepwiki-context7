import asyncio
import json
import httpx
import time
from celery.result import AsyncResult

# Configuration
BASE_URL = "http://localhost:8000"
INGEST_ENDPOINT = f"{BASE_URL}/ingest-ad"
QUERY_ENDPOINT = f"{BASE_URL}/query-ads"
TEST_DATA_PATH = "test_dataset.json"
HEADERS = {"Content-Type": "application/json"}

async def run_test():
    """
    Reads a test dataset, ingests each ad, and then queries for related ads.
    """
    try:
        with open(TEST_DATA_PATH, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Test data file not found at {TEST_DATA_PATH}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {TEST_DATA_PATH}")
        return

    async with httpx.AsyncClient(timeout=120.0) as client: # Increased timeout for potentially longer enrichment
        for i, ad_data in enumerate(test_data):
            print(f"--- Processing Ad {i+1}/{len(test_data)} (ID: {ad_data.get('ad_id')}) ---")

            # 1. Ingest the Ad
            try:
                # Ensure required fields are present
                ad_id = ad_data.get("ad_id")
                creatives = ad_data.get("creatives")
                
                if not ad_id or not creatives or not isinstance(creatives, list) or not creatives[0].get("original_url"):
                    print(f"Skipping ad due to missing 'ad_id' or 'creatives' data.")
                    continue

                ingest_payload = {
                    "ad_id": ad_id,
                    "raw_data_snapshot": ad_data,
                    "ad_creative_url": creatives[0]["original_url"]
                }

                print(f"Attempting to ingest ad ID: {ad_id}")
                response = await client.post(INGEST_ENDPOINT, json=ingest_payload, headers=HEADERS)
                response.raise_for_status()
                ingest_result = response.json()
                internal_ad_id = ingest_result.get("ad_id") # Get the internal UUID
                celery_task_id = ingest_result.get("task_id") # Get the Celery task ID
                print(f"Ingestion successful: {ingest_result}")

            except httpx.HTTPStatusError as e:
                print(f"Error during ingestion for ad ID {ad_id}: {e.response.status_code} - {e.response.text}")
                continue # Skip to next ad if ingestion fails
            except Exception as e:
                print(f"An unexpected error occurred during ingestion for ad ID {ad_id}: {e}")
                continue

            # Wait for the background enrichment task to complete using Celery's AsyncResult
            if celery_task_id:
                print(f"Waiting for Celery enrichment task {celery_task_id} to complete...")
                task_result = AsyncResult(celery_task_id)
                timeout_seconds = 120 # Maximum wait time for enrichment
                start_time = time.time()
                while not task_result.ready() and (time.time() - start_time) < timeout_seconds:
                    print(f"Task {celery_task_id} status: {task_result.status}. Waiting...")
                    await asyncio.sleep(5) # Poll every 5 seconds

                if task_result.ready():
                    print(f"Celery task {celery_task_id} completed with status: {task_result.status}")
                    if task_result.successful():
                        print("Enrichment task successful.")
                    else:
                        print(f"Enrichment task failed: {task_result.traceback}")
                else:
                    print(f"Warning: Celery task {celery_task_id} timed out after {timeout_seconds} seconds.")
            else:
                print("No Celery task ID received, skipping explicit wait for enrichment.")

            # Check ad enrichment status (this can remain as a secondary check)
            try:
                if not internal_ad_id:
                    print("Skipping status check because internal ad_id was not retrieved.")
                    continue

                status_endpoint = f"{BASE_URL}/ads/{internal_ad_id}/status"
                print(f"Checking status for ad ID: {internal_ad_id}")
                status_response = await client.get(status_endpoint)
                status_response.raise_for_status()
                status_result = status_response.json()
                print(f"Ad status: {status_result.get('status')}")
                if status_result.get('status') != 'enriched':
                    print("Warning: Ad is not fully enriched. Query may yield no results.")
            except httpx.HTTPStatusError as e:
                print(f"Error checking status for ad ID {ad_id}: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                print(f"An unexpected error occurred during status check for ad ID {ad_id}: {e}")

            # 2. Query for Related Ads
            try:
                query_text = ad_data.get("ad_body_text")
                if not query_text:
                    print("No 'ad_body_text' found, using page name as fallback query.")
                    query_text = ad_data.get("page_name", "default query")

                query_payload = {
                    "query": query_text,
                    "k": 3
                }

                print(f"Querying with text: '{query_text[:80]}...'")
                response = await client.post(QUERY_ENDPOINT, json=query_payload, headers=HEADERS)
                response.raise_for_status()
                query_result = response.json()
                print("Query successful. Synthesized Answer:")
                print(query_result.get("answer", "No answer provided."))
                print("-" * 20)


            except httpx.HTTPStatusError as e:
                print(f"Error during query for ad ID {ad_id}: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                print(f"An unexpected error occurred during query for ad ID {ad_id}: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
