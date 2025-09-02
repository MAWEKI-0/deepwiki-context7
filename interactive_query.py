import httpx
import asyncio

# Configuration
QUERY_ENDPOINT = "http://localhost:8000/query-ads"
HEADERS = {"Content-Type": "application/json"}

async def main():
    print("--- AdGenesis Interactive Query Client ---")
    print("Type your question and press Enter. Type 'exit' to quit.")
    print("Ensure the FastAPI server is running (`python src/main.py`) and that you have ingested data using `test_runner.py`.")

    async with httpx.AsyncClient(timeout=120.0) as client:
        while True:
            try:
                query_text = await asyncio.to_thread(input, "\nQuery: ")
                if query_text.lower() == 'exit':
                    print("Exiting...")
                    break

                if not query_text:
                    continue

                query_payload = {
                    "query": query_text,
                    "k": 5 # Retrieve top 5 relevant ads
                }

                print("Sending query to the AdGenesis Engine...")
                response = await client.post(QUERY_ENDPOINT, json=query_payload, headers=HEADERS)
                response.raise_for_status()

                query_result = response.json()
                print("\n--- Synthesized Answer ---")
                print(query_result.get("answer", "No answer provided."))
                print(f" (Retrieved {query_result.get('retrieved_ads_count', 0)} ads for context)")
                print("-" * 26)

            except httpx.HTTPStatusError as e:
                print(f"\nError: Could not query the API. Status code: {e.response.status_code}")
                print(f"Details: {e.response.text}")
            except httpx.RequestError:
                print(f"\nError: Could not connect to the server at {QUERY_ENDPOINT}.")
                print("Please ensure the FastAPI server is running (`python src/main.py`).")
            except Exception as e:
                print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
