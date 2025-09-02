Of course. This document is the culmination of our entire planning session. It synthesizes every key decision, architectural principle, and strategic clarification into a single, comprehensive charter. This is the **Genesis Document** for the AdGenesis Intelligence Engine. It is designed to be the definitive source of truth, onboarding guide, and North Star for every human and AI contributor to this project.

---

# **Project Genesis: The AdGenesis Intelligence Engine**

*   **Document Version:** 1.0?
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
    We will employ a cascade of AI models from the Google AI ecosystem, each chosen for its specific strengths. A fast, cost-effective model (e.g., **gemini-2.5-flash-lite**) will perform initial triage and visual description. A powerful, deep-reasoning model (e.g., **gemini-2.5-flash-lite**) will conduct the final, high-stakes strategic analysis. This ensures we achieve maximum insight at an optimal cost.

### **1.3. The System in Action: A User Story**

*   **Instead of:** Manually scrolling through hundreds of competitor ads, trying to spot a pattern.
*   **I will:** Ask the AdGenesis Engine, "What is the dominant marketing angle our top three competitors used for their summer campaigns, and which visual styles were most common?"
*   **The system will:** Instantly retrieve the pre-analyzed, structured data for those ads and synthesize a data-grounded report: "Competitor A heavily used 'Scarcity' (35% of ads) with product-focused visuals. Competitor B focused on 'Social Proof' (42% of ads) using user-generated content styles. Competitor C had no dominant angle, suggesting a fragmented strategy."

---

## **Part II: The System Architecture (The "What")**

The system operates as two distinct, independent services: an offline **Ingestion & Enrichment Pipeline** and an online **Query & Synthesis Engine**.

### **2.1. The Heart of the System: The `knowledge_object` Schema**

table_name: Ads
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

  - name: error_log
    type: TEXT
    description: Stores any error messages if the enrichment process fails.
    populated_by: Enrichment Pipeline

  - name: strategic_analysis
    type: JSONB
    description: "**Core Enriched Data.** A structured object containing the deep strategic analysis."
    populated_by: gemini-2.5-flash-lite (Slow)
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

  - name: audience_persona
    type: TEXT
    description: A concise, generated description of the inferred target audience for the ad.
    populated_by: gemini-2.5-flash-lite

  - name: vector_summary
    type: VECTOR(768)
    description: A vector embedding of a concise, natural language summary of the ad's core strategy. Used for semantic search. (Dimension updated to match implementation).
    populated_by: Embedding Model
    
#### **Sub-Schema for `strategic_analysis` (JSONB Object):**

*   `marketing_angle`: (TEXT) e.g., "Pain-Agitate-Solution", "Social Proof", "Scarcity", "Feature-Benefit".
*   `emotional_appeal`: (TEXT) e.g., "Hope", "Fear", "Exclusivity", "Convenience", "Urgency".
*   `cta_analysis`: (TEXT) A brief analysis of the call-to-action's clarity and effectiveness.
*   `key_claims`: (TEXT[]) An array of the primary claims or promises made in the ad copy.
*   `confidence_score`: (FLOAT) The LLM's self-reported confidence (0.0 to 1.0) in its analysis.

### **2.2. Data Flow**

#### **Ingestion & Enrichment Flow (Offline Pipeline):**

1.  A new, raw ad JSON is ingested into the Supabase `Ads` table. Its `raw_data_snapshot` is populated, and its `status` is set to `PENDING`.
2.  The Python-based Enrichment Pipeline worker continuously polls the database for ads with `status = 'PENDING'`.
3.  Upon finding one, it sets the `status` to `ENRICHING`.
4.  **Fast Pass:** It sends the ad creative URL to **gemini-2.5-flash-lite** for visual analysis. The result populates the `visual_analysis` field.
5.  **Slow Pass:** It compiles a rich prompt containing the raw ad text, the targeting data, and the new visual analysis from the fast pass. This is sent to **gemini-2.5-flash-lite**.
6.  gemini-2.5-flash-lite performs the deep analysis, returning a structured JSON that populates `strategic_analysis` and `audience_persona`.
7.  A separate call to an embedding model generates the vector for `vector_summary`.
8.  The worker updates the row in Supabase with all enriched data, sets `status` to `ENRICHED`, and updates the `enriched_at` timestamp.
9.  If any step fails, the `status` is set to `FAILED`, and an error is logged in `error_log`.

#### **Query & Synthesis Flow (Online API):**

1.  A user sends a natural language query to the FastAPI endpoint (e.g., "What's the main strategy for ads targeting new mothers?").
2.  The Query Engine translates the query into a hybrid retrieval plan.
3.  **Hybrid Retrieval:** It performs two simultaneous queries on Supabase:
    *   **Vector Search:** Finds the top K most semantically similar ads using the `vector_summary` field.
    *   **Structured Filter:** If applicable, it filters based on metadata (e.g., `WHERE audience_persona LIKE '%new mothers%'`).
4.  The full, structured `knowledge_objects` (the entire rows) for the retrieved ads are fetched.
5.  **Synthesis:** These objects are formatted into a clean context and sent to a smart LLM with a "strategist" prompt.
6.  The strategist LLM analyzes the structured data, identifies patterns, and formulates a comprehensive, data-grounded answer.
7.  This final answer is returned to the user via the API.

---

## **Part III: The Technology Stack (The "How")**

Each tool in our stack has a specific, clearly defined purpose that aligns with our architectural principles.

*   **Google AI (Gemini Pro & Flash): The Brains**
    *   **What it is:** Our chosen provider for state-of-the-art Large Language Models.
    *   **Its Role:**
        *   **gemini-2.5-flash-lite:** The fast, cost-effective workhorse for high-volume tasks like the initial visual analysis.
        *   **Ggemini-2.5-flash-lite:** The powerful, deep-reasoning expert for high-stakes tasks like the core strategic analysis and final query synthesis.
    *   **Why It's Right:** Provides the necessary multi-modal and reasoning capabilities, fitting perfectly into our "Right Mind for the Right Task" philosophy.

*   **Pydantic: The Blueprint and Quality Control Inspector**
    *   **What it is:** A Python library for data validation.
    *   **Its Role:** The foundation of our "Structure is Intelligence" principle. We will define our `knowledge_object` sub-schemas as Pydantic classes. This forces the LLM's output into a strict, validated contract, ensuring data integrity from the moment of creation and eliminating manual validation code.

*   **LangChain: The Factory Assembly Line**
    *   **What it is:** A framework for orchestrating LLM-powered workflows.
    *   **Its Role:** The engine of our **Enrichment Pipeline**. We will use LangChain Expression Language (LCEL) to build the multi-step chain that takes a raw ad, passes it through the Fast Pass (vision) and Slow Pass (strategy) models, and uses a Pydantic Output Parser to guarantee a perfectly structured `knowledge_object`.

*   **LlamaIndex: The Intelligent Librarian**
    *   **What it is:** A data framework specializing in connecting custom data sources (like our Supabase DB) to LLMs for advanced RAG.
    *   **Its Role:** The core of our **Query Engine**. We will use its advanced capabilities to build the hybrid retriever that combines semantic vector search with structured SQL filtering, providing the "strategist" LLM with the most precise context possible.

*   **FastAPI: The Professional Front Door**
    *   **What it is:** A modern, high-performance web framework for building APIs in Python.
    *   **Its Role:** It will serve our **Query Engine**. It provides a clean, fast, and auto-documenting API endpoint for users or future applications to interact with the AdGenesis system's intelligence. Its seamless integration with Pydantic makes it a perfect fit.

*   **Supabase (PostgreSQL + pgvector): The Dossier Cabinet**
    *   **What it is:** Our managed database and backend-as-a-service platform.
    *   **Its Role:** The central nervous system of the project. It will store the raw data, the enriched `knowledge_objects`, and the vector embeddings. Its `pgvector` extension is critical for enabling the semantic search component of our hybrid retrieval strategy.

*   **CrewAI: The Future Expansion Module**
    *   **What it is:** A framework for orchestrating autonomous AI agents.
    *   **Its Role:** While not a core component of Phase 1 or 2, CrewAI is planned for **future enhancements**. Once the Intelligence Dossier is built, we could deploy a CrewAI team (e.g., a "Trend Analyst" agent and a "Creative Copywriter" agent) to autonomously monitor the data, identify emerging trends, and proactively suggest new ad campaigns.

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


---

## **Part VI: Getting Started & Immediate Next Steps**

1.  **Review & Acknowledge:** All team members must review this Genesis Document in full.
2.  **Environment Setup:** Set up local Python development environments with access to Google AI, Supabase, and other required libraries.
3.  **Commence Phase 1:** The immediate focus is on **Task 1 of Phase 1: Finalizing and implementing the Supabase schema**. This is the bedrock upon which everything else will be built. The Pydantic models for the `knowledge_object` should be the first piece of code written.

---

## **1.0?**

This version signifies that all architectural components are in place and the system is functional from end to end, as per the Genesis Document. However, it has not yet undergone rigorous end-to-end testing or validation with a live dataset. This version is considered a "standing" but unverified build.
