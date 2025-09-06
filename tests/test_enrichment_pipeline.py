import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from uuid import uuid4
from langchain_core.messages import AIMessage
from langchain_core.language_models import FakeListChatModel

from src.enrichment_pipeline import (
    perform_visual_analysis,
    perform_strategic_analysis,
    generate_audience_persona,
    generate_vector_summary,
    enrich_ad,
)
from src.models import AdKnowledgeObject, StrategicAnalysis, VisualAnalysis
from src.logger import logger

# Mock data for testing
MOCK_AD_CREATIVE_URL = "http://example.com/ad_creative.jpg"
MOCK_RAW_AD_DATA = {
    "ad_creative_url": MOCK_AD_CREATIVE_URL,
    "targeting_data": {"age": "25-34", "gender": "female"},
    "ad_text": "Buy our amazing product now!",
}
MOCK_TARGETING_DATA = {"age": "25-34", "gender": "female"}

@pytest.fixture
def mock_gemini_flash():
    """Fixture for a mocked Gemini 1.5 Flash model using FakeListChatModel."""
    mock_visual_analysis_content = VisualAnalysis(
        visual_style="minimalist",
        key_visual_elements=["product image", "text overlay"],
        color_palette="cool tones",
        overall_impression="clean and modern",
    ).model_dump_json()
    return FakeListChatModel(responses=[mock_visual_analysis_content])

@pytest.fixture
def mock_gemini_pro():
    """Fixture for a mocked Gemini 1.5 Pro model using FakeListChatModel."""
    mock_strategic_analysis_content = StrategicAnalysis(
        marketing_angle="Feature-Benefit",
        emotional_appeal="Convenience",
        cta_analysis="Clear and prominent",
        key_claims=["fast delivery", "high quality"],
        confidence_score=0.95,
    ).model_dump_json()
    mock_audience_persona_content = "Young professionals interested in tech gadgets."

    return FakeListChatModel(responses=[
        mock_strategic_analysis_content, # For strategic analysis
        mock_audience_persona_content, # For audience persona
    ])

@pytest.fixture
def mock_embedding_model():
    """Fixture for a mocked GoogleGenerativeAIEmbeddings model."""
    mock = MagicMock()
    mock.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]
    return mock

@pytest.fixture
def mock_supabase_client():
    """Fixture for a mocked Supabase client."""
    mock = MagicMock()
    mock.from_.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    return mock

@pytest.fixture
def sample_ad_knowledge_object():
    """Fixture for a sample AdKnowledgeObject."""
    return AdKnowledgeObject(
        id=uuid4(),
        ad_id=123,
        raw_data_snapshot=MOCK_RAW_AD_DATA,
        status="PENDING",
    )

# --- Unit Tests for individual enrichment functions ---

def test_perform_visual_analysis(mock_gemini_flash):
    result = perform_visual_analysis(MOCK_AD_CREATIVE_URL, mock_gemini_flash)
    assert isinstance(result, VisualAnalysis)
    assert result.visual_style == "minimalist"
    # FakeListChatModel does not have an 'invoke' method to assert on directly
    # We assume it was called by the chain if the result is correct.

def test_perform_strategic_analysis(mock_gemini_pro):
    visual_analysis_mock = VisualAnalysis(
        visual_style="minimalist",
        key_visual_elements=["product image", "text overlay"],
        color_palette="cool tones",
        overall_impression="clean and modern",
    )
    result = perform_strategic_analysis(
        MOCK_RAW_AD_DATA, MOCK_TARGETING_DATA, visual_analysis_mock, mock_gemini_pro
    )
    assert isinstance(result, StrategicAnalysis)
    assert result.marketing_angle == "Feature-Benefit"
    # FakeListChatModel does not have an 'invoke' method to assert on directly
    # We assume it was called by the chain if the result is correct.

def test_generate_audience_persona(mock_gemini_pro):
    strategic_analysis_mock = StrategicAnalysis(
        marketing_angle="Feature-Benefit",
        emotional_appeal="Convenience",
        cta_analysis="Clear and prominent",
        key_claims=["fast delivery", "high quality"],
        confidence_score=0.95,
    )
    visual_analysis_mock = VisualAnalysis(
        visual_style="minimalist",
        key_visual_elements=["product image", "text overlay"],
        color_palette="cool tones",
        overall_impression="clean and modern",
    )
    # Create a local FakeListChatModel for this specific test
    local_gemini_pro = FakeListChatModel(responses=["Young professionals interested in tech gadgets."])

    result = generate_audience_persona(
        MOCK_RAW_AD_DATA, strategic_analysis_mock, visual_analysis_mock, local_gemini_pro
    )
    assert isinstance(result, str)
    assert result == "Young professionals interested in tech gadgets."
    # No assert_called_once on the fixture mock, as we used a local one


@patch("src.enrichment_pipeline.audience_persona_prompt")
def test_generate_audience_persona_visual_analysis_is_json(mock_prompt):
    """
    Tests that the visual_analysis object is passed as a JSON string
    to the LLM chain in generate_audience_persona.
    """
    # Create mock objects for the function arguments
    strategic_analysis_mock = StrategicAnalysis(
        marketing_angle="Test Angle",
        emotional_appeal="Test Appeal",
        cta_analysis="Test CTA",
        key_claims=["Test Claim"],
        confidence_score=0.9,
    )
    visual_analysis_mock = VisualAnalysis(
        visual_style="Test Style",
        key_visual_elements=["Test Element"],
        color_palette="Test Palette",
        overall_impression="Test Impression",
    )
    # Mock the chain and its invoke method
    mock_chain = MagicMock()
    # mock_prompt.format_prompt.return_value = mock_chain
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="Test Persona")

    # Recreate the chain with the mocked prompt and a mocked LLM
    chain = mock_prompt | mock_llm

    # Call the function
    generate_audience_persona(
        raw_ad_data={},
        strategic_analysis=strategic_analysis_mock,
        visual_analysis=visual_analysis_mock,
        gemini_pro=mock_llm,  # Pass the mocked LLM
    )

    # Assert that invoke was called on the LLM
    mock_llm.invoke.assert_called_once()

    # Get the arguments passed to invoke
    invoke_args, invoke_kwargs = mock_llm.invoke.call_args

    # The actual prompt object is passed, so we need to inspect its 'messages'
    # The first message's content will be the formatted string
    prompt_input = invoke_args[0].to_messages()[0].content

    # A bit of a hacky way to check, but we can see if the JSON string is in the prompt
    assert visual_analysis_mock.model_dump_json() in prompt_input


def test_generate_vector_summary(mock_embedding_model):
    text = "Test summary text"
    result = generate_vector_summary(text, mock_embedding_model)
    assert isinstance(result, list)
    assert result == [0.1, 0.2, 0.3, 0.4]
    mock_embedding_model.embed_query.assert_called_once_with(text)

# --- Unit Tests for enrich_ad orchestration function ---

@patch("src.enrichment_pipeline.perform_visual_analysis")
@patch("src.enrichment_pipeline.perform_strategic_analysis")
@patch("src.enrichment_pipeline.generate_audience_persona")
@patch("src.enrichment_pipeline.generate_vector_summary")
def test_enrich_ad_success(
    mock_generate_vector_summary,
    mock_generate_audience_persona,
    mock_perform_strategic_analysis,
    mock_perform_visual_analysis,
    sample_ad_knowledge_object,
    mock_gemini_flash,
    mock_gemini_pro,
    mock_embedding_model,
    mock_supabase_client,
):
    """Tests the successful execution of the enrich_ad pipeline."""
    # Configure mocks for successful execution
    mock_visual_analysis = VisualAnalysis(
        visual_style="minimalist",
        key_visual_elements=["product image"],
        color_palette="cool",
        overall_impression="clean",
    )
    mock_strategic_analysis = StrategicAnalysis(
        marketing_angle="Direct Response",
        emotional_appeal="Urgency",
        cta_analysis="Buy Now",
        key_claims=["limited time"],
        confidence_score=0.9,
    )
    mock_perform_visual_analysis.return_value = mock_visual_analysis
    mock_perform_strategic_analysis.return_value = mock_strategic_analysis
    mock_generate_audience_persona.return_value = "Tech-savvy young adults"
    mock_generate_vector_summary.return_value = [0.5, 0.6, 0.7]

    enriched_ad = enrich_ad(
        sample_ad_knowledge_object,
        mock_gemini_flash,
        mock_gemini_pro,
        mock_embedding_model,
        mock_supabase_client,
    )

    # Assertions for successful enrichment
    assert enriched_ad.status == "ENRICHED"
    assert enriched_ad.enriched_at is not None
    assert enriched_ad.error_log is None
    assert enriched_ad.visual_analysis == mock_visual_analysis
    assert enriched_ad.strategic_analysis == mock_strategic_analysis
    assert enriched_ad.audience_persona == "Tech-savvy young adults"
    assert enriched_ad.vector_summary == [0.5, 0.6, 0.7]

    # Verify that all sub-functions were called
    mock_perform_visual_analysis.assert_called_once_with(
        MOCK_AD_CREATIVE_URL, mock_gemini_flash
    )
    mock_perform_strategic_analysis.assert_called_once_with(
        MOCK_RAW_AD_DATA, MOCK_TARGETING_DATA, mock_visual_analysis, mock_gemini_pro
    )
    mock_generate_audience_persona.assert_called_once()
    mock_generate_vector_summary.assert_called_once()
    # Note: We cannot assert on mock_gemini_flash.invoke or mock_gemini_pro.invoke directly
    # because they are FakeListChatModel instances, not MagicMock objects with call tracking.
    # The assertions on the return values of the patched functions are sufficient.


@patch("src.enrichment_pipeline.perform_visual_analysis")
def test_enrich_ad_visual_analysis_failure(
    mock_perform_visual_analysis,
    sample_ad_knowledge_object,
    mock_gemini_flash,
    mock_gemini_pro,
    mock_embedding_model,
    mock_supabase_client,
):
    """Tests error handling when visual analysis fails."""
    mock_perform_visual_analysis.side_effect = Exception("Visual analysis failed")

    enriched_ad = enrich_ad(
        sample_ad_knowledge_object,
        mock_gemini_flash,
        mock_gemini_pro,
        mock_embedding_model,
        mock_supabase_client,
    )

    assert enriched_ad.status == "FAILED"
    assert "Visual analysis failed" in enriched_ad.error_log
    assert enriched_ad.enriched_at is None
    mock_perform_visual_analysis.assert_called_once()
    # Ensure other functions were not called
    # FakeListChatModel does not have an 'invoke' method to check if called
    assert not mock_embedding_model.embed_query.called

@patch("src.enrichment_pipeline.perform_visual_analysis")
@patch("src.enrichment_pipeline.perform_strategic_analysis")
def test_enrich_ad_strategic_analysis_failure(
    mock_perform_strategic_analysis,
    mock_perform_visual_analysis,
    sample_ad_knowledge_object,
    mock_gemini_flash,
    mock_gemini_pro,
    mock_embedding_model,
    mock_supabase_client,
):
    """Tests error handling when strategic analysis fails."""
    mock_visual_analysis = VisualAnalysis(
        visual_style="minimalist",
        key_visual_elements=["product image"],
        color_palette="cool",
        overall_impression="clean",
    )
    mock_perform_visual_analysis.return_value = mock_visual_analysis
    mock_perform_strategic_analysis.side_effect = Exception("Strategic analysis failed")

    enriched_ad = enrich_ad(
        sample_ad_knowledge_object,
        mock_gemini_flash,
        mock_gemini_pro,
        mock_embedding_model,
        mock_supabase_client,
    )

    assert enriched_ad.status == "FAILED"
    assert "Strategic analysis failed" in enriched_ad.error_log
    assert enriched_ad.enriched_at is None
    mock_perform_visual_analysis.assert_called_once()
    mock_perform_strategic_analysis.assert_called_once()
    # Ensure subsequent functions were not called
    # FakeListChatModel does not have an 'invoke' method to check if called
    assert not mock_embedding_model.embed_query.called

def test_enrich_ad_missing_ad_creative_url(
    sample_ad_knowledge_object,
    mock_gemini_flash,
    mock_gemini_pro,
    mock_embedding_model,
    mock_supabase_client,
):
    """Tests error handling when ad_creative_url is missing."""
    sample_ad_knowledge_object.raw_data_snapshot.pop("ad_creative_url")

    enriched_ad = enrich_ad(
        sample_ad_knowledge_object,
        mock_gemini_flash,
        mock_gemini_pro,
        mock_embedding_model,
        mock_supabase_client,
    )

    assert enriched_ad.status == "FAILED"
    assert "Ad creative URL not found" in enriched_ad.error_log
    assert enriched_ad.enriched_at is None
    # Ensure no LLM calls were made
    # FakeListChatModel does not have an 'invoke' method to check if called
    assert not mock_embedding_model.embed_query.called
