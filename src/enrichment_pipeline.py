import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import google.generativeai as genai
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from pydantic import BaseModel, Field
from supabase import Client

from src.config import Settings
from src.models import AdKnowledgeObject, StrategicAnalysis
from src.logger import logger
from src.dependencies import get_settings

# Configure Google AI (This will be moved into the functions that use it)
# genai.configure(api_key=settings.GOOGLE_API_KEY)

# --- Pydantic Output Parsers ---
strategic_analysis_parser = PydanticOutputParser(pydantic_object=StrategicAnalysis)

# --- Prompt Templates ---
VISUAL_ANALYSIS_PROMPT_TEMPLATE = """
You are an expert marketing analyst. Your task is to analyze an ad creative and provide a structured visual analysis.
Focus on the visual style, key elements, and overall impression.

Ad Creative URL: {ad_creative_url}

Provide your analysis as a JSON object with the following structure:
{{
    "visual_style": "e.g., 'minimalist', 'bold & vibrant', 'user-generated content', 'product-focused'",
    "key_visual_elements": ["list", "of", "prominent", "elements"],
    "color_palette": "e.g., 'warm tones', 'cool tones', 'monochromatic', 'bright & contrasting'",
    "overall_impression": "A brief summary of the ad's visual impact and message conveyed visually."
}}
"""
visual_analysis_prompt = PromptTemplate(
    template=VISUAL_ANALYSIS_PROMPT_TEMPLATE,
    input_variables=["ad_creative_url"],
)

STRATEGIC_ANALYSIS_PROMPT_TEMPLATE = """
You are a highly experienced marketing strategist. Your goal is to perform a deep strategic analysis of an advertisement.
Consider the raw ad text, targeting data, and the provided visual analysis.
Extract the core marketing angle, emotional appeal, call-to-action effectiveness, and key claims.

Raw Ad Data: {raw_ad_data}
Targeting Data: {targeting_data}
Visual Analysis: {visual_analysis}

{format_instructions}

Provide your analysis in the specified JSON format.
"""
strategic_analysis_prompt = PromptTemplate(
    template=STRATEGIC_ANALYSIS_PROMPT_TEMPLATE,
    input_variables=["raw_ad_data", "targeting_data", "visual_analysis"],
    partial_variables={"format_instructions": strategic_analysis_parser.get_format_instructions()},
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

def perform_visual_analysis(ad_creative_url: str, gemini_flash: ChatGoogleGenerativeAI) -> Dict[str, Any]:
    """Performs visual analysis using Gemini 1.5 Flash."""
    chain = visual_analysis_prompt | gemini_flash
    response = chain.invoke({"ad_creative_url": ad_creative_url})
    return response.json() # Assuming Gemini Flash returns valid JSON directly

def perform_strategic_analysis(raw_ad_data: Dict[str, Any], targeting_data: Dict[str, Any], visual_analysis: Dict[str, Any], gemini_pro: ChatGoogleGenerativeAI) -> StrategicAnalysis:
    """Performs deep strategic analysis using Gemini 1.5 Pro."""
    chain = strategic_analysis_prompt | gemini_pro | strategic_analysis_parser
    response = chain.invoke({
        "raw_ad_data": raw_ad_data,
        "targeting_data": targeting_data,
        "visual_analysis": visual_analysis
    })
    return response

def generate_audience_persona(raw_ad_data: Dict[str, Any], strategic_analysis: StrategicAnalysis, visual_analysis: Dict[str, Any], gemini_pro: ChatGoogleGenerativeAI) -> str:
    """Generates a concise audience persona using Gemini 1.5 Pro."""
    chain = audience_persona_prompt | gemini_pro
    response = chain.invoke({
        "raw_ad_data": raw_ad_data,
        "strategic_analysis": strategic_analysis.model_dump_json(), # Pass as JSON string
        "visual_analysis": visual_analysis
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
    settings: Settings, # Inject settings here
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
