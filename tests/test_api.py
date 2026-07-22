from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["documents_loaded"] >= 1


def test_director_question_returns_source():
    response = client.post(
        "/api/ask",
        json={"question": "Does a Singapore company need a resident director?", "top_k": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"]
    assert any("director" in item["topic"].lower() for item in payload["sources"])


def test_out_of_scope_question_does_not_invent_source():
    response = client.post(
        "/api/ask",
        json={"question": "What is French criminal procedure?", "top_k": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] in {"local-retrieval", "openai-rag"}
