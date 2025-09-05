

**Project Genesis: The AdGenesis Intelligence Engine**

*   **Document Version:** 1.0
*   **Date:** 2025-08-24
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
    We will employ a cascade of AI models from the Google AI ecosystem, each chosen for its specific strengths. A fast, cost-effective model will perform initial triage and visual description. A powerful, deep-reasoning model will conduct the final, high-stakes strategic analysis. This ensures we achieve maximum insight at an optimal cost. *(Note: For initial deployment and testing, a single versatile model, `gemini-2.5-flash-lite`, is used for all generation tasks.)*

### **1.3. The System in Action: A User Story**

*   **Instead of:** Manually scrolling through hundreds of competitor ads, trying to spot a pattern.
*   **I will:** Ask the AdGenesis Engine, "What is the dominant marketing angle our top three competitors used for their summer campaigns, and which visual styles were most common?"
*   **The system will:** Instantly retrieve the pre-analyzed, structured data for those ads and synthesize a data-grounded report: "Competitor A heavily used 'Scarcity' (35% of ads) with product-focused visuals. Competitor B focused on 'Social Proof' (42% of ads) using user-generated content styles. Competitor C had no dominant angle, suggesting a fragmented strategy."

---

## **Part II: The System Architecture (The "What")**

The system operates as two distinct, independent services: an offline **Ingestion & Enrichment Pipeline** and an online **Query & Synthesis Engine**.

### **2.1. The Heart of the System: The `knowledge_object` Schema**

table_name: ads
description: This table holds the core, enriched intelligence for every ad processed.

columns:
  - name: id
    type: UUID (Primary Key)
    description: Unique identifier for the enriched ad record.
    populated_by: Supabase (auto)

  - name: ad_id
    type: BIGINT
    description: The original ID from the Meta Ad Library data source. Indexed for lookups.
    populated_by: Ingestion Script

  - name: raw_data_snapshot
    type: JSONB
    description: A complete JSON snapshot of the original, unprocessed ad data for auditing and reprocessing.
    populated_by: Ingestion Script

  - name: status
    type: TEXT
    description: "The processing state of the ad. Values: `PENDING`, `ENRICHING`, `ENRICHED`, `FAILED`. Indexed for the worker queue."
    populated_by: Enrichment Pipeline

  - name: enriched_at
    type: TIMESTAMPTZ
    description: Timestamp of when the enrichment process was successfully completed.
    populated_by: Enrichment Pipeline

  - name: created_at
    type: TIMESTAMPTZ
    description: Timestamp of when the record was initially created.
    populated_by: Supabase (auto)

  - name: error_log
    type: TEXT
    description: Stores any error messages if the enrichment process fails.
    populated_by: Enrichment Pipeline

  - name: strategic_analysis
    type: JSONB
    description: "**Core Enriched Data.** A structured object containing the deep strategic analysis."
    populated_by: gemini-2.5-flash-lite
    sub_schema:
      - name: marketing_angle
        type: TEXT
        example: "Pain-Agitate-Solution", "Social Proof", "Scarcity", "Feature-Benefit"
      - name: emotional_appeal
        type: TEXT
        example: "Hope", "Fear", "Exclusivity", "Convenience", "Urgency"
      - name: cta_analysis
        type: TEXT
        description: A brief analysis of the call-to-action's clarity and effectiveness.
      - name: key_claims
        type: TEXT[]
        description: An array of the primary claims or promises made in the ad copy.
      - name: confidence_score
        type: FLOAT
        description: The LLM's self-reported confidence (0.0 to 1.0) in its analysis.

  - name: visual_analysis
    type: JSONB
    description: A structured object containing the analysis of the ad creative (image/video).
    populated_by: gemini-2.5-flash-lite
    sub_schema:
      - name: visual_style
        type: TEXT
        example: "'minimalist', 'bold & vibrant', 'user-generated content', 'product-focused'"
      - name: key_visual_elements
        type: TEXT[]
        description: A list of prominent visual elements in the ad creative.
      - name: color_palette
        type: TEXT
        example: "'warm tones', 'cool tones', 'monochromatic', 'bright & contrasting'"
      - name: overall_impression
        type: TEXT
        description: A brief summary of the ad's visual impact and message conveyed visually.

  - name: audience_persona
    type: TEXT
    description: A concise, generated description of the inferred target audience for the ad.
    populated_by: gemini-2.5-flash-lite

  - name: vector_summary
    type: VECTOR(768)
    description: A vector embedding of a concise, natural language summary of the ad's core strategy. Used for semantic search.
    populated_by: Embedding Model

### **2.2. Data Flow**

#### **Ingestion & Enrichment Flow (Asynchronous Pipeline):**

1.  A new, raw ad JSON is ingested via a FastAPI endpoint. The system creates a new record in the Supabase `ads` table, populates its `raw_data_snapshot`, and sets its `status` to `PENDING`.
2.  The API endpoint immediately dispatches an `enrichment_task` to a **Celery** message queue (managed by **Redis**). This makes the ingestion process non-blocking and highly scalable.
3.  A Celery worker picks up the task. It atomically updates the ad's `status` to `ENRICHING` to prevent duplicate processing.
4.  **Fast Pass:** It sends the ad creative URL to **gemini-2.5-flash-lite** for visual analysis. The result populates the `visual_analysis` field.
5.  **Slow Pass:** It compiles a rich prompt containing the raw ad text, targeting data, and the new visual analysis. This is sent to **gemini-2.5-flash-lite**.
6.  The model performs the deep analysis, returning a structured JSON that populates `strategic_analysis` and `audience_persona`.
7.  A separate call to an embedding model generates the vector for `vector_summary`.
8.  The worker updates the row in Supabase with all enriched data, sets `status` to `ENRICHED`, and updates the `enriched_at` timestamp.
9.  If any step fails, the task can be retried. After exhausting retries, the `status` is set to `FAILED`, and an error is logged in `error_log`.

#### **Query & Synthesis Flow (Online API):**

1.  A user sends a natural language query to the FastAPI endpoint (e.g., "What's the main strategy for ads targeting new mothers?").
2.  The Query Engine translates the query into a hybrid retrieval plan.
3.  **Hybrid Retrieval:** It performs a single, efficient RPC call to Supabase (`match_documents_adaptive`) which executes:
    *   **Vector Search:** Finds the top K most semantically similar ads using the `vector_summary` field.
    *   **Structured Filter:** Simultaneously filters results based on metadata passed in the query (e.g., `WHERE strategic_analysis->>'marketing_angle' = 'Scarcity'`).
4.  The full, structured `knowledge_objects` (the entire rows) for the retrieved ads are fetched.
5.  **Synthesis & Refinement:** These objects are formatted into a clean context and sent to a smart LLM with a "strategist" prompt. The LLM formulates an initial answer. This answer is then passed through a "self-critique" loop, where another prompt asks the LLM to review its own answer against the source data for accuracy and completeness, providing a final, refined response.
6.  This final, data-grounded answer is returned to the user via the API.

---

## **Part III: The Technology Stack (The "How")**

Each tool in our stack has a specific, clearly defined purpose that aligns with our architectural principles.

*   **Google AI (Gemini): The Brains**
    *   **What it is:** Our chosen provider for state-of-the-art Large Language Models.
    *   **Its Role:**
        *   **gemini-2.5-flash-lite:** The versatile and cost-effective workhorse for all generative tasks in the current implementation, including visual analysis, strategic analysis, and query synthesis. The architecture is designed to easily incorporate more powerful models for specific tasks in the future.
    *   **Why It's Right:** Provides the necessary multi-modal and reasoning capabilities, fitting perfectly into our "Right Mind for the Right Task" philosophy.

*   **Pydantic: The Blueprint and Quality Control Inspector**
    *   **What it is:** A Python library for data validation.
    *   **Its Role:** The foundation of our "Structure is Intelligence" principle. We define our `knowledge_object` sub-schemas (`StrategicAnalysis`, `VisualAnalysis`) as Pydantic classes. This forces the LLM's output into a strict, validated contract, ensuring data integrity and eliminating manual validation code.

*   **LangChain: The Factory Assembly Line**
    *   **What it is:** A framework for orchestrating LLM-powered workflows.
    *   **Its Role:** The engine of our **Enrichment Pipeline**. We use LangChain Expression Language (LCEL) to build the multi-step chains that take raw ad data, pass it through the analysis models, and use a Pydantic Output Parser to guarantee a perfectly structured `knowledge_object`.

*   **LlamaIndex: The Intelligent Librarian**
    *   **What it is:** A data framework specializing in connecting custom data sources to LLMs for advanced RAG.
    *   **Its Role:** The core of our **Query Engine**. We use its `RetrieverQueryEngine` and a custom `BaseRetriever` to build the hybrid retriever that combines semantic vector search with structured SQL filtering, providing the "strategist" LLM with the most precise context possible.

*   **FastAPI: The Professional Front Door**
    *   **What it is:** A modern, high-performance web framework for building APIs in Python.
    *   **Its Role:** It serves our **Ingestion and Query Engines**. It provides clean, fast, and auto-documenting API endpoints. Its seamless integration with Pydantic makes it a perfect fit.

*   **Supabase (PostgreSQL + pgvector): The Dossier Cabinet**
    *   **What it is:** Our managed database and backend-as-a-service platform.
    *   **Its Role:** The central nervous system of the project. It stores the raw data, the enriched `knowledge_objects`, and the vector embeddings. Its `pgvector` extension is critical for enabling semantic search, and its RPC functionality allows for powerful, custom retrieval functions.

*   **Celery & Redis: The Asynchronous Workforce**
    *   **What it is:** Celery is a distributed task queue, and Redis is an in-memory data store.
    *   **Its Role:** They form the backbone of our offline **Enrichment Pipeline**. When a new ad is ingested, a task is sent to a Celery queue (using Redis as the broker). This allows the API to respond instantly while independent, scalable Celery workers perform the heavy, time-consuming LLM analysis in the background.

*   **CrewAI: The Future Expansion Module**
    *   **What it is:** A framework for orchestrating autonomous AI agents.
    *   **Its Role:** While not a core component of the current version, CrewAI is planned for **future enhancements**. Once the Intelligence Dossier is built, we could deploy a CrewAI team (e.g., a "Trend Analyst" agent and a "Creative Copywriter" agent) to autonomously monitor the data, identify emerging trends, and proactively suggest new ad campaigns.
