from fastapi.testclient import TestClient

from app.main import app


def test_health_live() -> None:
    client = TestClient(app)
    res = client.get("/health/live")
    assert res.status_code == 200
