import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.main import app

# Create a TestClient instance
client = TestClient(app)

# --- Mock Dependencies ---
# It's good practice to override dependencies for testing to avoid external calls.
# For now, we will focus on mocking the query engine's synthesize_answer function.

def test_health_check():
    """
    Tests the /health endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("src.main.synthesize_answer", new_callable=AsyncMock)
def test_query_ad_intelligence_success(mock_synthesize_answer):
    """
    Tests the /query-ads endpoint, ensuring it returns a successful response
    and calls the underlying query synthesis function correctly.
    """
    # Configure the mock to return a specific value
    mock_synthesize_answer.return_value = "This is a synthesized test answer."

    # Define the request payload
    payload = {
        "query": "What are the best performing ads?",
        "k": 5
    }

    # Make the request to the test client
    response = client.post("/query-ads", json=payload)

    # Assertions
    assert response.status_code == 200
    assert response.json() == {
        "query": "What are the best performing ads?",
        "answer": "This is a synthesized test answer."
    }

    # Verify that our mock was called correctly
    # We don't need to check the dependency-injected args here,
    # just that it was called with the arguments from the request body.
    mock_synthesize_answer.assert_called_once()
    call_args, call_kwargs = mock_synthesize_answer.call_args
    assert call_kwargs["query"] == "What are the best performing ads?"
    assert call_kwargs["k"] == 5

@patch("src.main.synthesize_answer", new_callable=AsyncMock)
def test_query_ad_intelligence_api_error(mock_synthesize_answer):
    """
    Tests how the /query-ads endpoint handles an exception from the query engine.
    """
    # Configure the mock to raise an exception
    mock_synthesize_answer.side_effect = Exception("LLM provider is down")

    payload = {"query": "This will fail"}

    # Make the request to the test client
    response = client.post("/query-ads", json=payload)

    # Assertions
    assert response.status_code == 500
    assert response.json() == {
        "message": "Internal server error",
        "detail": "LLM provider is down",
    }
