from fastapi.testclient import TestClient

from app.main import app, get_assistant
from app.schemas import ResearchResponse, SourceMetadata, StageStatus


class FakeAssistant:
    def research(self, payload):
        return ResearchResponse(
            question=payload.question,
            report="## Findings\n- Evidence one [1]",
            sources=[
                SourceMetadata(
                    id=1,
                    title="Example source",
                    url="https://example.com/report",
                    publisher="example.com",
                    retrieved_at="2026-01-01T00:00:00Z",
                    snippet="Example snippet",
                )
            ],
            stages=[StageStatus(stage="search", status="ok", detail="Collected 1 result")],
            warnings=["Example warning"],
            uncertainty="Limited evidence.",
            setup_error=None,
        )


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_page_contains_workspace_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="research-form"' in response.text
    assert '/static/site.css' in response.text
    assert '/static/site.js' in response.text


def test_static_assets_are_served():
    css = client.get('/static/site.css')
    js = client.get('/static/site.js')
    assert css.status_code == 200
    assert js.status_code == 200
    assert 'workspace' in css.text
    assert 'submitQuestion' in js.text


def test_research_endpoint_with_override():
    app.dependency_overrides[get_assistant] = lambda: FakeAssistant()
    response = client.post('/api/research', json={'question': 'Test question about AI safety'})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data['question'] == 'Test question about AI safety'
    assert data['report'].startswith('## Findings')
    assert data['sources'][0]['publisher'] == 'example.com'
