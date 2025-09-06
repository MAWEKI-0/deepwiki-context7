import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import google.genai as genai
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from pydantic import BaseModel, Field
from supabase import Client

from src.config import Settings
from src.models import AdKnowledgeObject, StrategicAnalysis, VisualAnalysis
from src.logger import logger
from src.dependencies import get_settings

# Configure Google AI (This will be moved into the functions that use it)
# genai.configure(api_key=settings.GOOGLE_API_KEY)

# --- JSON Output Parser ---
json_parser = JsonOutputParser()

# --- Prompt Templates ---
VISUAL_ANALYSIS_PROMPT_TEMPLATE = """
You are an expert marketing analyst. Your task is to analyze an ad creative and provide a structured visual analysis.
Focus on the visual style, key elements, and overall impression.
Return a JSON object with the following keys: 'visual_style', 'key_visual_elements', 'color_palette', 'overall_impression'.

Ad Creative URL: {ad_creative_url}

Provide your analysis as a single JSON object.
"""
visual_analysis_prompt = PromptTemplate(
    template=VISUAL_ANALYSIS_PROMPT_TEMPLATE,
    input_variables=["ad_creative_url"],
)

STRATEGIC_ANALYSIS_PROMPT_TEMPLATE = """
You are a highly experienced marketing strategist. Your goal is to perform a deep strategic analysis of an advertisement.
Consider the raw ad text, targeting data, and the provided visual analysis.
Extract the core marketing angle, emotional appeal, call-to-action effectiveness, and key claims.
Return a JSON object with the following keys: 'marketing_angle', 'emotional_appeal', 'cta_analysis', 'key_claims', 'confidence_score'.

Raw Ad Data: {raw_ad_data}
Targeting Data: {targeting_data}
Visual Analysis: {visual_analysis}

Provide your analysis as a single JSON object.
"""
strategic_analysis_prompt = PromptTemplate(
    template=STRATEGIC_ANALYSIS_PROMPT_TEMPLATE,
    input_variables=["raw_ad_data", "targeting_data", "visual_analysis"],
)

AUDIENCE_PERSONA_PROMPT_TEMPLATE = """
Based on the following ad data, generate a concise description of the inferred target audience persona.

Raw Ad Data: {raw_ad_data}
Strategic Analysis: {strategic_analysis}
Visual Analysis: {visual_analysis}

Audience Persona:
"""
audience_persona_prompt = PromptTemplate(
    template=AUDIENCE_PERSONA_PROMPT_TEMPLATE,
    input_variables=["raw_ad_data", "strategic_analysis", "visual_analysis"],
)

# --- Enrichment Pipeline Functions ---

def perform_visual_analysis(ad_creative_url: str, gemini_flash: ChatGoogleGenerativeAI) -> VisualAnalysis:
    """Performs visual analysis using Gemini 1.5 Flash and returns a VisualAnalysis object."""
    chain = visual_analysis_prompt | gemini_flash | json_parser
    response_dict = chain.invoke({"ad_creative_url": ad_creative_url})
    return VisualAnalysis(**response_dict)

def perform_strategic_analysis(raw_ad_data: Dict[str, Any], targeting_data: Dict[str, Any], visual_analysis: VisualAnalysis, gemini_pro: ChatGoogleGenerativeAI) -> StrategicAnalysis:
    """Performs deep strategic analysis using Gemini 1.5 Pro."""
    chain = strategic_analysis_prompt | gemini_pro | json_parser
    response_dict = chain.invoke({
        "raw_ad_data": raw_ad_data,
        "targeting_data": targeting_data,
        "visual_analysis": visual_analysis.model_dump()
    })
    return StrategicAnalysis(**response_dict)

def generate_audience_persona(raw_ad_data: Dict[str, Any], strategic_analysis: StrategicAnalysis, visual_analysis: VisualAnalysis, gemini_pro: ChatGoogleGenerativeAI) -> str:
    """Generates a concise audience persona using Gemini 1.5 Pro."""
    chain = audience_persona_prompt | gemini_pro
    response = chain.invoke({
        "raw_ad_data": raw_ad_data,
        "strategic_analysis": strategic_analysis.model_dump_json(), # Pass as JSON string
        "visual_analysis": visual_analysis.model_dump()
    })
    return response.content.strip()

def generate_vector_summary(text: str, embedding_model: GoogleGenerativeAIEmbeddings) -> List[float]:
    """Generates a vector embedding for the ad's core strategy."""
    embeddings = embedding_model.embed_query(text)
    return embeddings

def enrich_ad(
    ad_data: AdKnowledgeObject,
    gemini_flash: ChatGoogleGenerativeAI,
    gemini_pro: ChatGoogleGenerativeAI,
    embedding_model: GoogleGenerativeAIEmbeddings,
    supabase: Client,
) -> AdKnowledgeObject:
    """
    Orchestrates the ad enrichment process.
    """
    ad_data.status = "ENRICHING"
    # Update status in DB (optional, for real-time tracking)
    # supabase.from("ads").update({"status": "ENRICHING"}).eq("id", ad_data.id).execute()

    try:
        # 1. Fast Pass: Visual Analysis
        # Assuming raw_data_snapshot contains 'ad_creative_url'
        ad_creative_url = ad_data.raw_data_snapshot.get("ad_creative_url")
        if not ad_creative_url:
            raise ValueError("Ad creative URL not found in raw_data_snapshot.")
        
        visual_analysis = perform_visual_analysis(ad_creative_url, gemini_flash)
        ad_data.visual_analysis = visual_analysis

        # 2. Slow Pass: Strategic Analysis
        # Assuming raw_data_snapshot contains 'targeting_data'
        targeting_data = ad_data.raw_data_snapshot.get("targeting_data", {})
        strategic_analysis = perform_strategic_analysis(
            ad_data.raw_data_snapshot, targeting_data, visual_analysis, gemini_pro
        )
        ad_data.strategic_analysis = strategic_analysis

        # 3. Generate Audience Persona
        audience_persona = generate_audience_persona(
            ad_data.raw_data_snapshot, strategic_analysis, visual_analysis, gemini_pro
        )
        ad_data.audience_persona = audience_persona

        # 4. Generate Vector Summary
        summary_text = f"Marketing Angle: {strategic_analysis.marketing_angle}. Emotional Appeal: {strategic_analysis.emotional_appeal}. CTA: {strategic_analysis.cta_analysis}. Audience: {audience_persona}"
        vector_summary = generate_vector_summary(summary_text, embedding_model)
        ad_data.vector_summary = vector_summary

        ad_data.status = "ENRICHED"
        ad_data.enriched_at = datetime.now()

    except Exception as e:
        ad_data.status = "FAILED"
        ad_data.error_log = str(e)
        logger.error(f"Enrichment failed for ad {ad_data.ad_id}: {e}")

    return ad_data

# The main function is now removed as it was for testing purposes and will be replaced by a proper test suite.
