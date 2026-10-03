from fastapi.testclient import TestClient

from app.main import app, get_assistant
from app.schemas import ResearchResponse


class FakeAssistant:
    def research(self, payload):
        return ResearchResponse(
            question=payload.question,
            report="Test report [1]",
            sources=[],
            stages=[],
            warnings=[],
            uncertainty=None,
            setup_error=None,
        )


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_research_endpoint_with_override():
    app.dependency_overrides[get_assistant] = lambda: FakeAssistant()
    client = TestClient(app)
    response = client.post("/api/research", json={"question": "Test question about AI safety"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "Test question about AI safety"
    assert "report" in data
