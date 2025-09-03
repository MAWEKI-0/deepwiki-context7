from datetime import datetime
from typing import Optional
from pydantic import ConfigDict
from uuid import UUID

from pydantic import BaseModel, Field

# Sub-Schema for `strategic_analysis` (JSONB Object)
class VisualAnalysis(BaseModel):
    visual_style: str = Field(..., description="e.g., 'minimalist', 'bold & vibrant', 'user-generated content', 'product-focused'")
    key_visual_elements: list[str] = Field(..., description="A list of prominent visual elements in the ad creative.")
    color_palette: str = Field(..., description="e.g., 'warm tones', 'cool tones', 'monochromatic', 'bright & contrasting'")
    overall_impression: str = Field(..., description="A brief summary of the ad's visual impact and message conveyed visually.")

class StrategicAnalysis(BaseModel):
    marketing_angle: str = Field(..., description="e.g., 'Pain-Agitate-Solution', 'Social Proof', 'Scarcity', 'Feature-Benefit'.")
    emotional_appeal: str = Field(..., description="e.g., 'Hope', 'Fear', 'Exclusivity', 'Convenience', 'Urgency'.")
    cta_analysis: str = Field(..., description="A brief analysis of the call-to-action's clarity and effectiveness.")
    key_claims: list[str] = Field(..., description="An array of the primary claims or promises made in the ad copy.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="The LLM's self-reported confidence (0.0 to 1.0) in its analysis.")

# Schema for the `Ads` table
class AdKnowledgeObject(BaseModel):
    id: Optional[UUID] = Field(None, description="Unique identifier for the enriched ad record. Populated by Supabase (auto).")
    ad_id: int = Field(..., description="The original ID from the Meta Ad Library data source. Indexed for lookups.")
    raw_data_snapshot: dict = Field(..., description="A complete JSON snapshot of the original, unprocessed ad data for auditing and reprocessing.")
    status: str = Field("PENDING", description="The processing state of the ad. Values: `PENDING`, `ENRICHING`, `ENRICHED`, `FAILED`.")
    enriched_at: Optional[datetime] = Field(None, description="Timestamp of when the enrichment process was successfully completed.")
    error_log: Optional[str] = Field(None, description="Stores any error messages if the enrichment process fails.")
    strategic_analysis: Optional[StrategicAnalysis] = Field(None, description="Core Enriched Data. A structured object containing the deep strategic analysis.")
    visual_analysis: Optional[VisualAnalysis] = Field(None, description="A structured object containing the analysis of the ad creative (image/video).")
    audience_persona: Optional[str] = Field(None, description="A concise, generated description of the inferred target audience for the ad.")
    vector_summary: Optional[list[float]] = Field(None, description="A vector embedding of a concise, natural language summary of the ad's core strategy. Used for semantic search.")

    model_config = ConfigDict(extra='ignore')
