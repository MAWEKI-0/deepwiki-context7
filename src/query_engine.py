import os
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.schema import TextNode
from llama_index.vector_stores.supabase import SupabaseVectorStore
from supabase import Client

from src.config import settings
from src.models import AdKnowledgeObject, StrategicAnalysis
from src.logger import logger

# Configure Google AI
genai.configure(api_key=settings.GOOGLE_API_KEY)

# --- Query & Synthesis Prompt ---
QUERY_SYNTHESIS_PROMPT_TEMPLATE = """
You are the AdGenesis Intelligence Engine, an automated market analyst.
Your task is to answer user queries by synthesizing insights from provided structured ad data.
Focus on identifying patterns, dominant strategies, and key takeaways.
If you cannot find a definitive answer, state that clearly.

User Query: {query}

Retrieved Ad Data (structured knowledge_objects):
{ad_data_context}

Formulate a comprehensive, data-grounded answer based ONLY on the provided ad data.
"""
query_synthesis_prompt = PromptTemplate(
    template=QUERY_SYNTHESIS_PROMPT_TEMPLATE,
    input_variables=["query", "ad_data_context"],
)

CRITIQUE_PROMPT_TEMPLATE = """
You are a critical self-reviewer for the AdGenesis Intelligence Engine.
Your task is to evaluate a generated answer against the original user query and the provided ad data.
Identify any inaccuracies, omissions, or areas where the answer could be more precise or comprehensive,
based *only* on the provided context.

User Query: {query}

Retrieved Ad Data (structured knowledge_objects):
{ad_data_context}

Initial Answer: {initial_answer}

Critique:
1.  **Accuracy Check:** Is the initial answer factually correct based on the `Retrieved Ad Data`?
2.  **Completeness Check:** Does the initial answer address all parts of the `User Query` using the available data?
3.  **Conciseness/Clarity:** Is the answer clear and to the point? Could it be improved?
4.  **Data Grounding:** Does the answer strictly adhere to the provided `Retrieved Ad Data`?

Based on your critique, provide a REVISED_ANSWER. If the initial answer is perfect, simply repeat it.
"""
critique_prompt = PromptTemplate(
    template=CRITIQUE_PROMPT_TEMPLATE,
    input_variables=["query", "ad_data_context", "initial_answer"],
)

# --- Query Engine Functions ---

async def hybrid_retrieve_ads(
    query: str,
    embedding_model: GoogleGenerativeAIEmbeddings,
    supabase: Client,
    filter_criteria: Optional[Dict[str, Any]] = None,
    k: int = 5,
) -> List[AdKnowledgeObject]:
    """
    Performs an efficient hybrid retrieval using a Supabase RPC function.
    """
    query_embedding = await embedding_model.aembed_query(query)
    
    params = {
        'query_embedding': query_embedding,
        'match_count': k,
        'filter_criteria': filter_criteria or {}
    }
    
    response = supabase.rpc('match_documents_adaptive', params).execute()
    
    if response.data:
        return [AdKnowledgeObject(**ad_data) for ad_data in response.data]
    else:
        logger.error(f"Failed to retrieve ads from Supabase: {response.error}")
        return []


async def synthesize_answer(
    query: str,
    retrieved_ads: List[AdKnowledgeObject],
    gemini_pro: ChatGoogleGenerativeAI,
    embedding_model: GoogleGenerativeAIEmbeddings,
    max_critique_loops: int = 2,
) -> str:
    """
    Synthesizes a data-grounded answer from retrieved ad data using a LlamaIndex query engine.
    """
    if not retrieved_ads:
        return "I could not find any relevant ads to answer your query."

    # Configure LlamaIndex settings for this request
    Settings.embed_model = embedding_model
    Settings.llm = gemini_pro

    # --- LlamaIndex Integration ---
    vector_store = SupabaseVectorStore(
        postgres_connection_string=settings.SUPABASE_CONNECTION_STRING,
        collection_name="ads"
    )
    index = VectorStoreIndex.from_vector_store(vector_store)

    # Create a query engine from the index
    query_engine = index.as_query_engine(
        text_qa_template=query_synthesis_prompt,
        refine_template=critique_prompt, # Using critique prompt for refinement
        similarity_top_k=len(retrieved_ads), # Use all retrieved ads
    )

    # Convert retrieved ads to TextNode for LlamaIndex context
    nodes = [TextNode(text=ad.model_dump_json(indent=2)) for ad in retrieved_ads]
    
    # Synthesize the answer using the query engine with the retrieved nodes
    response = await query_engine.asynthesize(query, nodes=nodes)
    
    return response.response

# The main function is now removed as it was for testing purposes and will be replaced by a proper test suite.
