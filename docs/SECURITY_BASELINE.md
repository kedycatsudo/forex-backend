## Threat Surface Map

### 1) Public endpoints (internet-facing)
Policy:
- No internal API key required
- Rate limiting: enabled
- Full input validation required
- Structured request/error logging required

Endpoints:
- /api/v1/news/*
- /api/v1/prices/*
- /api/v1/notifications/* (if user-facing)
- /auth/login (if applicable)

---

### 2) Private/Internal endpoints (service-to-service, worker-triggered)
Policy:
- Require `X-Internal-API-Key`
- Optional stricter IP/proxy checks
- Rate limiting optional (usually lower need if private)
- Structured security logging on auth failure

Endpoints:
- /internal/*
- /api/v1/workers/trigger
- /api/v1/jobs/retry (internal-only)

---

### 3) Ops endpoints
Policy:
- `/health/live`: public or internal (team choice; commonly public-safe)
- `/health/ready`: internal preferred (reveals dependency state)
- `/metrics`: internal only
- `/docs`, `/openapi.json`: disabled or protected in prod

Endpoints:
- /health/live
- /health/ready
- /metrics
- /docs
- /openapi.json

## Access Control Rule Table

| Endpoint Group | Rate Limit | Internal API Key | Notes |
|---|---|---|---|
| Public | ✅ Required | ❌ Not required | Internet-facing routes |
| Private/Internal | ◻ Optional | ✅ Required | Service-to-service / worker-triggered |
| Ops | ⚠ Mixed | ⚠ Mixed | `/metrics` + docs protected in prod; health depends on policy |