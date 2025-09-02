import os
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    get_response_synthesizer,
)
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.vector_stores.supabase import SupabaseVectorStore
from supabase import Client

from src.config import Settings
from src.dependencies import get_settings
from src.logger import logger
from src.models import AdKnowledgeObject, StrategicAnalysis

# Configure Google AI (This will be moved into the functions that use it)
# genai.configure(api_key=settings.GOOGLE_API_KEY)

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


# --- Custom Retriever ---
class SupabaseHybridRetriever(BaseRetriever):
    def __init__(
        self,
        supabase_client: Client,
        embedding_model: GoogleGenerativeAIEmbeddings,
        k: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ):
        self._supabase_client = supabase_client
        self._embedding_model = embedding_model
        self._k = k
        self._filter_criteria = filter_criteria or {}
        super().__init__()

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Asynchronously retrieves nodes from Supabase using a hybrid approach.
        """
        query_embedding = await self._embedding_model.aembed_query(
            query_bundle.query_str
        )

        params = {
            "query_embedding": query_embedding,
            "match_count": self._k,
            "filter_criteria": self._filter_criteria,
        }

        response = (
            self._supabase_client.rpc("match_documents_adaptive", params).execute()
        )

        if not response.data:
            logger.error(
                f"Failed to retrieve ads from Supabase: {response.error}"
            )
            return []

        nodes = []
        for ad_data in response.data:
            ad_object = AdKnowledgeObject(**ad_data)
            node = TextNode(
                text=ad_object.model_dump_json(indent=2),
                metadata={"source": "Supabase"},
            )
            # Note: The RPC function does not currently return a score.
            nodes.append(NodeWithScore(node=node, score=1.0))
        return nodes


# --- Query Engine Functions ---
async def synthesize_answer(
    query: str,
    gemini_pro: ChatGoogleGenerativeAI,
    embedding_model: GoogleGenerativeAIEmbeddings,
    settings: Settings,  # Inject settings here
    filter_criteria: Optional[Dict[str, Any]] = None,
    k: int = 5,
    max_critique_loops: int = 2,
) -> str:
    """
    Synthesizes a data-grounded answer from retrieved ad data using a LlamaIndex query engine.
    """
    # --- LlamaIndex Integration ---
    retriever = SupabaseHybridRetriever(
        supabase_client=get_settings().supabase_client,
        embedding_model=embedding_model,
        k=k,
        filter_criteria=filter_criteria,
    )

    response_synthesizer = get_response_synthesizer(
        llm=gemini_pro,
        text_qa_template=query_synthesis_prompt,
        refine_template=critique_prompt,
    )

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )

    # Synthesize the answer using the query engine
    response = await query_engine.aquery(query)

    return response.response


# The main function is now removed as it was for testing purposes and will be replaced by a proper test suite.
