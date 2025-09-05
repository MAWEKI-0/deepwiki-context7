### Project Genesis: The AdGenesis Intelligence Engine - A Detailed Analysis

**1. North Star Vision & Core Purpose**
The AdGenesis Intelligence Engine is envisioned as an **automated market analyst**, not merely an ad database or search tool. Its primary purpose is to transform the vast, unstructured stream of competitor advertising into a structured, queryable "Intelligence Dossier". The ultimate goal is to shift strategic decision-making from reactive observation to **proactive, data-driven action** by identifying underlying competitor tactics, emotional appeals, and marketing angles.

**2. Core Philosophy & Guiding Principles**
The architecture of the AdGenesis Intelligence Engine is built upon three fundamental principles:

*   **Compile, Don't Just Search:** Intelligence is primarily built during the ingestion phase through pre-processing and analysis of each ad into a rich, structured `knowledge_object`. This ensures that the Language Learning Model (LLM) at query time acts as a high-level strategist working with pre-compiled reports, enhancing accuracy and reliability.
*   **Structure is Intelligence:** Unstructured text is inherently ambiguous, whereas a well-defined schema (`knowledge_object`) provides clarity. By enforcing a standardized, machine-readable format for ad data, the system converts raw documents into a true database, enabling quantitative analysis, trend identification, and pattern matching impossible with simple semantic search. The schema forms the intelligence backbone.
*   **The Right Mind for the Right Task:** The system employs a cascade of AI models from the Google AI ecosystem, each selected for its specific strengths to achieve maximum insight at optimal cost. For example, a fast, cost-effective model (`gemini-2.5-flash-lite`) handles initial triage and visual description, while a more powerful model would ideally perform high-stakes strategic analysis. Currently, `gemini-2.5-flash-lite` is used for all generation tasks in the initial deployment.

**3. System Architecture Overview**
The system is divided into two distinct and independent services:

*   **Offline Ingestion & Enrichment Pipeline (Asynchronous):** Responsible for processing raw ad data and transforming it into structured intelligence.
*   **Online Query & Synthesis Engine (Synchronous API):** Responsible for receiving user queries, retrieving relevant enriched data, and synthesizing data-grounded answers.

**4. The `knowledge_object` Schema (The Heart of the System)**
The core intelligence is stored in a Supabase table named `ads`. The `AdKnowledgeObject` Pydantic model defines this schema, ensuring data integrity. Key columns and their descriptions include:

*   `id`: UUID, Primary Key, unique identifier (auto-populated by Supabase).
*   `ad_id`: BIGINT, original ID from the Meta Ad Library (indexed for lookups).
*   `raw_data_snapshot`: JSONB, a complete JSON snapshot of the original, unprocessed ad data for auditing.
*   `status`: TEXT, processing state (`PENDING`, `ENRICHING`, `ENRICHED`, `FAILED`) (indexed for worker queue).
*   `enriched_at`: TIMESTAMPTZ, timestamp of successful enrichment.
*   `created_at`: TIMESTAMPTZ, timestamp of record creation (auto-populated by Supabase).
*   `error_log`: TEXT, stores error messages if enrichment fails.
*   `strategic_analysis`: JSONB, **Core Enriched Data**, a structured object with deep strategic analysis populated by `gemini-2.5-flash-lite`.
    *   Its sub-schema (`StrategicAnalysis` Pydantic model) includes `marketing_angle`, `emotional_appeal`, `cta_analysis`, `key_claims`, and `confidence_score`.
*   `visual_analysis`: JSONB, structured analysis of ad creative (image/video) populated by `gemini-2.5-flash-lite`.
    *   Its sub-schema (`VisualAnalysis` Pydantic model) includes `visual_style`, `key_visual_elements`, `color_palette`, and `overall_impression`.
*   `audience_persona`: TEXT, concise description of the inferred target audience, populated by `gemini-2.5-flash-lite`.
*   `vector_summary`: VECTOR(768), a vector embedding of a natural language summary of the ad's core strategy, used for semantic search, populated by an Embedding Model.

**5. Ingestion & Enrichment Flow (Asynchronous Pipeline)**
This pipeline is designed for scalability and non-blocking operation.

1.  **Ingestion:** A raw ad JSON is received via a FastAPI endpoint (`/ingest-ad`). A new record is created in the Supabase `ads` table with `raw_data_snapshot` populated and `status` set to `PENDING`.
2.  **Task Dispatch:** The API immediately dispatches an `enrichment_task` to a **Celery** message queue, managed by **Redis**, making the ingestion non-blocking.
3.  **Worker Processing:** A Celery worker picks up the task and atomically updates the ad's `status` to `ENRICHING` to prevent duplicate processing.
4.  **Fast Pass (Visual Analysis):** The ad creative URL is sent to `gemini-2.5-flash-lite` for visual analysis, populating the `visual_analysis` field.
5.  **Slow Pass (Strategic Analysis):** A rich prompt, including raw ad text, targeting data, and visual analysis, is sent to `gemini-2.5-flash-lite` for deep strategic analysis, populating `strategic_analysis` and `audience_persona`.
6.  **Vector Summary Generation:** A separate call to an embedding model generates the `vector_summary`.
7.  **Database Update:** The worker updates the Supabase row with all enriched data, sets `status` to `ENRICHED`, and updates `enriched_at`.
8.  **Error Handling & Retries:** If any step fails, the task can be retried. After exhausting retries (3 max, with 60s delay), the `status` is set to `FAILED`, an error is logged in `error_log`, and the task is moved to a dead-letter queue (DLQ).

**6. Query & Synthesis Flow (Online API)**
This flow provides data-grounded answers to natural language queries.

1.  **User Query:** A user sends a natural language query to the FastAPI endpoint (`/query-ads`).
2.  **Hybrid Retrieval Plan:** The Query Engine translates the query into a hybrid retrieval plan.
3.  **Supabase RPC Call:** A single, efficient RPC call is made to Supabase, executing the `match_documents_adaptive` function.
    *   **Vector Search:** Finds the top K most semantically similar ads using the `vector_summary` field.
    *   **Structured Filter:** Simultaneously filters results based on metadata in the query (e.g., `WHERE strategic_analysis->>'marketing_angle' = 'Scarcity'`).
4.  **Data Fetching:** The full, structured `knowledge_objects` (entire rows) for the retrieved ads are fetched.
5.  **Synthesis & Refinement:** These objects are formatted into context and sent to a smart LLM (`gemini-2.5-flash-lite`) with a "strategist" prompt. The LLM formulates an initial answer, which then goes through a "self-critique" loop. A second prompt asks the LLM to review its own answer against the source data for accuracy and completeness, providing a final, refined response.
6.  **Return Answer:** The final, data-grounded answer is returned to the user via the API.

**7. Technology Stack**
Each technology plays a specific, defined role:

*   **Google AI (Gemini): The Brains**
    *   `gemini-2.5-flash-lite`: The versatile and cost-effective workhorse for all generative tasks (visual analysis, strategic analysis, query synthesis) in the current implementation.
    *   `gemini-embedding-001`: The embedding model used for generating `vector_summary`.
*   **Pydantic: The Blueprint and Quality Control Inspector**
    *   Enforces the "Structure is Intelligence" principle by defining `knowledge_object` sub-schemas (`StrategicAnalysis`, `VisualAnalysis`) as Pydantic classes. This ensures strict, validated output from LLMs.
*   **LangChain: The Factory Assembly Line**
    *   Engine of the Enrichment Pipeline, using LangChain Expression Language (LCEL) to build multi-step chains for ad data analysis and guarantee structured `knowledge_object` output via Pydantic Output Parser.
*   **LlamaIndex: The Intelligent Librarian**
    *   Core of the Query Engine, utilizing `RetrieverQueryEngine` and a custom `BaseRetriever` (`SupabaseHybridRetriever`) for hybrid retrieval that combines semantic vector search with structured SQL filtering.
*   **FastAPI: The Professional Front Door**
    *   High-performance web framework serving Ingestion and Query Engines, providing clean, fast, and auto-documenting API endpoints (`/ingest-ad`, `/query-ads`, `/ads/{ad_id}/status`, `/health`).
*   **Supabase (PostgreSQL + pgvector): The Dossier Cabinet**
    *   Managed database and backend-as-a-service, serving as the central nervous system. Stores raw data, enriched `knowledge_objects`, and vector embeddings. Its `pgvector` extension is crucial for semantic search, and RPC functionality supports custom retrieval functions like `match_documents_adaptive`.
*   **Celery & Redis: The Asynchronous Workforce**
    *   Celery is the distributed task queue, and Redis is the in-memory data store (broker). They form the backbone of the offline Enrichment Pipeline, allowing the API to respond instantly while LLM analysis runs in the background.
*   **CrewAI: The Future Expansion Module**
    *   Planned for future enhancements to orchestrate autonomous AI agents for tasks like trend analysis and proactive campaign suggestions.

**8. Project Setup & Configuration**

*   **Dependencies:** Listed in `requirements.txt`, including `fastapi`, `uvicorn`, `pydantic`, `supabase`, `langchain-google-genai`, `llama-index`, `google-generativeai`, `loguru`, `celery`, `redis`, `pytest`, `httpx`, `pytest-asyncio`.
*   **Environment Variables:** Managed via `src/config.py` using `pydantic-settings`, reading from a `.env` file. Critical variables include `SUPABASE_URL`, `SUPABASE_KEY`, `GOOGLE_API_KEY`, `REDIS_URL`.
*   **Celery Configuration (`src/celeryconfig.py`):** Defines task queues, exchanges, and dead-letter queue mechanisms to ensure robust asynchronous processing. It includes settings for `task_acks_late`, `task_reject_on_worker_lost`, and Redis transport options for production.
*   **Supabase Migrations:**
    *   `20250824000000_create_ads_table.sql`: Creates the `public.ads` table, including `UUID`, `BIGINT`, `JSONB`, `TEXT`, `TIMESTAMPTZ`, and `VECTOR(768)` types. It also enables `uuid-ossp` and `vector` extensions, and sets up indexes for `ad_id`, `status`, and `vector_summary` (using HNSW for efficient vector search). Row Level Security (RLS) is enabled, restricting all access to the `service_role` for security.
    *   `20250825000000_create_match_documents_adaptive_function.sql`: Defines a PL/pgSQL function for hybrid retrieval, `match_documents_adaptive`, which takes a `query_embedding`, `match_count`, and `filter_criteria` (JSONB) to perform combined vector search and structured filtering.

**9. Testing and Validation**

*   **`test_runner.py`:** A script designed to test the end-to-end flow. It reads a `test_dataset.json`, ingests each ad via the FastAPI `/ingest-ad` endpoint, waits for the Celery enrichment task to complete, checks its status, and then queries for related ads using the `/query-ads` endpoint.
*   **`scripts/validate_data.py`:** This script fetches a random sample of enriched ads from Supabase and validates them against the `AdKnowledgeObject` Pydantic model, ensuring data integrity post-enrichment.
*   **Unit Tests (`tests/` directory):**
    *   `test_enrichment_pipeline.py`: Contains unit tests for individual enrichment functions (`perform_visual_analysis`, `perform_strategic_analysis`, `generate_audience_persona`, `generate_vector_summary`) and the orchestration function `enrich_ad`, using mocked LLM and Supabase clients to isolate logic and test error handling.
    *   `test_main.py`: Tests the FastAPI endpoints (`/health`, `/query-ads`), focusing on API response and proper invocation of underlying services like `synthesize_answer` using a `TestClient` and mocks.



**Conclusion**
The AdGenesis Intelligence Engine is a sophisticated, multi-component system designed to provide deep strategic insights into competitor advertising. It leverages an asynchronous, scalable pipeline for data ingestion and enrichment, transforming raw ad data into structured "knowledge objects." An online query engine then uses a hybrid retrieval approach and a self-critiquing LLM to synthesize data-grounded answers. The robust technology stack, adherence to strong architectural principles like "Structure is Intelligence" and "The Right Mind for the Right Task," and emphasis on structured data and asynchronous processing position it well to achieve its vision of an automated market analyst, moving clients from reactive observation to proactive, data-driven action.

