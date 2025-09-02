from fastapi.testclient import TestClient

def test_health_check(test_client: TestClient):
    """
    Test the health check endpoint.
    """
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
