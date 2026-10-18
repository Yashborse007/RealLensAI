from fastapi.testclient import TestClient

from main import app


def test_health_returns_the_ai_service_health_contract():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "service": "RealLens AI AI Service",
        "status": "running",
    }
