

# **Project Genesis: The AdGenesis Intelligence Engine**

*   **Document Version:** 1.1
*   **Date:** 2025-08-25
*   **Status:** **ACTIVE - Single Source of Truth**
*   **Purpose:** This document serves as the foundational charter for the AdGenesis Intelligence Engine. It outlines the project's vision, strategy, architecture, technology stack, and implementation roadmap. All contributors (human and AI) are expected to align their work with the principles and specifications laid out herein.

---

## **Part I: The Vision & Strategy (The "Why")**

### **1.1. The North Star Vision**

We are not building a simple ad database or a search tool. We are building an **automated market analyst**.

The AdGenesis Intelligence Engine will transform the chaotic, high-volume stream of competitor advertising into a structured, queryable **Intelligence Dossier**. Its purpose is to move our strategy **from reactive observation to proactive, data-driven action** by revealing the underlying tactics, emotional appeals, and marketing angles of our competitors.

### **1.2. The Core Philosophy**

Our architecture is guided by three fundamental principles:

1.  **Compile, Don't Just Search.**
    The system's primary intelligence is built during ingestion, not at query time. We pre-process and analyze every ad *once* to create a rich, structured `knowledge_object`. When we ask a question, the final LLM is not a raw interpreter struggling with messy text; it is a high-level strategist reading pre-compiled reports. This is the key to our system's accuracy and reliability.

2.  **Structure is Intelligence.**
    Unstructured text is ambiguous. A well-defined schema is not. By forcing every piece of ad data into a standardized, machine-readable format (`knowledge_object`), we turn a library of documents into a true database. This allows for quantitative analysis, trend identification, and pattern matching that is impossible with simple semantic search. The schema is the backbone of our intelligence.

3.  **The Right Mind for the Right Task.**
    We will employ a cascade of AI models from the Google AI ecosystem, each chosen for its specific strengths. A fast, cost-effective model (e.g., **gemini-1.5-flash-latest**) will perform initial triage and visual description. A powerful, deep-reasoning model (e.g., **gemini-1.5-pro-latest**) will conduct the final, high-stakes strategic analysis. This ensures we achieve maximum insight at an optimal cost.

### **1.3. The System in Action: A User Story**

*   **Instead of:** Manually scrolling through hundreds of competitor ads, trying to spot a pattern.
*   **I will:** Ask the AdGenesis Engine, "What is the dominant marketing angle our top three competitors used for their summer campaigns, and which visual styles were most common?"
*   **The system will:** Instantly retrieve the pre-analyzed, structured data for those ads and synthesize a data-grounded report: "Competitor A heavily used 'Scarcity' (35% of ads) with product-focused visuals. Competitor B focused on 'Social Proof' (42% of ads) using user-generated content styles. Competitor C had no dominant angle, suggesting a fragmented strategy."

---

## **Part II: The System Architecture (The "What")**

The system operates as two distinct, independent services: an offline **Ingestion & Enrichment Pipeline** and an online **Query & Synthesis Engine**.

### **2.1. The Heart of the System: The `Ads` Table Schema**

The schema for our `Ads` table in Supabase is the most critical component of this architecture. Each ad is transformed into a row conforming to this structure.

*   **`id`** (`UUID`, Primary Key, Default: `uuid_generate_v4()`)
    *   **Description:** Unique identifier for the enriched ad record.
    *   **Populated By:** Supabase (auto)
*   **`ad_id`** (`BIGINT`, Not Null, Indexed)
    *   **Description:** The original ID from the Meta Ad Library data source.
    *   **Populated By:** Ingestion Script
*   **`raw_data_snapshot`** (`JSONB`, Not Null)
    *   **Description:** A complete JSON snapshot of the original, unprocessed ad data for auditing and reprocessing.
    *   **Populated By:** Ingestion Script
*   **`status`** (`TEXT`, Not Null, Default: `'PENDING'`, Indexed)
    *   **Description:** The processing state of the ad. Values: `PENDING`, `ENRICHING`, `ENRICHED`, `FAILED`.
    *   **Populated By:** Enrichment Pipeline
*   **`enriched_at`** (`TIMESTAMPTZ`)
    *   **Description:** Timestamp of when the enrichment process was successfully completed.
    *   **Populated By:** Enrichment Pipeline
*   **`error_log`** (`TEXT`)
    *   **Description:** Stores any error messages if the enrichment process fails.
    *   **Populated By:** Enrichment Pipeline
*   **`strategic_analysis`** (`JSONB`)
    *   **Description:** **Core Enriched Data.** A structured object containing the deep strategic analysis.
    *   **Populated By:** `gemini-1.5-pro-latest` (Slow Pass)
    *   **Sub-Schema:**
        *   `marketing_angle` (`TEXT`): e.g., "Pain-Agitate-Solution", "Social Proof".
        *   `emotional_appeal` (`TEXT`): e.g., "Hope", "Fear", "Urgency".
        *   `cta_analysis` (`TEXT`): A brief analysis of the call-to-action's clarity.
        *   `key_claims` (`TEXT[]`): An array of the primary claims from the ad copy.
        *   `confidence_score` (`FLOAT`): The LLM's self-reported confidence (0.0 to 1.0).
*   **`visual_analysis`** (`JSONB`)
    *   **Description:** A structured object containing the analysis of the ad creative.
    *   **Populated By:** `gemini-1.5-flash-latest` (Fast Pass)
*   **`audience_persona`** (`TEXT`)
    *   **Description:** A concise, generated description of the inferred target audience.
    *   **Populated By:** `gemini-1.5-pro-latest` (Slow Pass)
*   **`vector_summary`** (`VECTOR(768)`, Indexed)
    *   **Description:** A vector embedding of a concise summary of the ad's core strategy. Used for semantic search.
    *   **Populated By:** `text-embedding-004`
*   **`created_at`** (`TIMESTAMPTZ`, Default: `now()`)
    *   **Description:** Timestamp of when the raw record was first ingested.
    *   **Populated By:** Supabase (auto)

### **2.2. Data Flow**

#### **Ingestion & Enrichment Flow (Offline Pipeline):**

1.  The FastAPI `/ingest-ad` endpoint receives a raw ad. It creates a new record in the `Ads` table with `status = 'PENDING'`.
2.  The endpoint immediately dispatches an `enrichment_task` job to the **Celery task queue** with the new ad's ID.
3.  A separate, scalable **Celery worker process** picks up the job from the queue. It updates the ad's `status` to `ENRICHING`.
4.  **Fast Pass:** The worker sends the ad creative URL to **`gemini-1.5-flash-latest`** for visual analysis.
5.  **Slow Pass:** The worker compiles a rich prompt (raw text, targeting data, visual analysis) and sends it to **`gemini-1.5-pro-latest`** for deep strategic analysis.
6.  An embedding model generates the vector for `vector_summary`.
7.  The worker updates the row in Supabase with all enriched data and sets the `status` to `ENRICHED`. If any step fails after retries, the `status` is set to `FAILED` and an error is logged.

#### **Query & Synthesis Flow (Online API):**

1.  A user sends a natural language query to the FastAPI `/query-ads` endpoint.
2.  The Query Engine uses a custom retriever to call a **Supabase RPC function (`match_documents_adaptive`)**, performing a high-efficiency hybrid search (vector similarity + structured filtering) directly within the database.
3.  The full, structured `knowledge_objects` for the retrieved ads are fetched.
4.  These objects are formatted into a clean context and sent to **`gemini-1.5-pro-latest`** with a "strategist" prompt.
5.  The strategist LLM analyzes the structured data, identifies patterns, and formulates a comprehensive, data-grounded answer.
6.  The final answer is returned to the user via the API.

---

## **Part III: The Technology Stack (The "How")**

*   **Google AI (Gemini Pro & Flash): The Brains**
    *   **Role:** Provides our core multi-modal and reasoning capabilities, fitting our "Right Mind for the Right Task" philosophy.
*   **Celery & Redis: The Production-Grade Worker System**
    *   **Role:** Manages the offline enrichment pipeline. Provides reliability, scalability, and resilience with persistent queues, automatic retries, and dead-lettering for failed jobs.
*   **Pydantic: The Blueprint and Quality Control Inspector**
    *   **Role:** Enforces our "Structure is Intelligence" principle by defining strict, validated data contracts for all LLM outputs and API schemas.
*   **LangChain: The Factory Assembly Line**
    *   **Role:** The orchestration engine for the **Enrichment Pipeline**. We use it to build the multi-step chain that takes raw data, calls the various LLMs, and parses their outputs against our Pydantic models.
*   **LlamaIndex: The Intelligent Librarian**
    *   **Role:** The core of our **Query Engine**. We use its advanced RAG capabilities and custom retriever to intelligently query our structured knowledge base.
*   **FastAPI: The Professional Front Door**
    *   **Role:** Serves our **Query Engine**. Provides a clean, fast, and auto-documenting API for users or future applications.
*   **Supabase (PostgreSQL + pgvector): The Dossier Cabinet**
    *   **Role:** The central nervous system of the project. Stores all raw and enriched data, provides the `pgvector` extension for semantic search, and hosts our high-performance RPC function for hybrid retrieval.
*   **CrewAI: The Future Expansion Module**
    *   **Role:** Planned for future enhancements. Once the Intelligence Dossier is built, we can deploy a CrewAI agent team to proactively monitor data and generate insights.

---

## **Part IV: The Implementation Plan (The "When")**

This project will be executed in three distinct phases, moving from data foundation to intelligent application.

*   **Phase 1: Foundation - The Enrichment Pipeline (3 Weeks)**
    *   **Objective:** Perfect the process of transforming a single raw ad into a fully enriched `knowledge_object` in Supabase.
    *   **Deliverables:** Finalized Supabase schema; a robust, Python-based Enrichment Pipeline script; successful ingestion of the test dataset.
    *   **Success Criteria:** The pipeline reliably processes ads from `PENDING` to `ENRICHED` with consistent, high-quality structured data.

*   **Phase 2: Core Engine - The Query API (3 Weeks)**
    *   **Objective:** Enable basic strategic questioning of the enriched data.
    *   **Deliverables:** A FastAPI endpoint for queries; implemented hybrid retrieval logic (vector + SQL); a "strategist" LLM prompt for one-shot answers.
    *   **Success Criteria:** The API can accurately answer direct questions by retrieving and synthesizing the correct structured data.

*   **Phase 3: Intelligence Layer - Advanced Reasoning (2 Weeks)**
    *   **Objective:** Introduce HRM-inspired iterative refinement.
    *   **Deliverables:** Multi-step prompting for the "strategist" LLM, including a "self-critique" loop.
    *   **Success Criteria:** The system can answer complex, open-ended questions with nuanced, multi-faceted responses that demonstrate a clear reasoning path.
