from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.security.internal_auth import require_internal_api_key


def test_internal_auth_rejects_without_key() -> None:
    app = FastAPI()

    @app.get("/internal/secure", dependencies=[Depends(require_internal_api_key)])
    def secure() -> dict[str, str]:
        return {"ok": "true"}

    client = TestClient(app)
    res = client.get("/internal/secure")
    assert res.status_code in (401, 403)
