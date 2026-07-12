# forex-backend

Backend API for the Forex project (FastAPI + PostgreSQL + Alembic).

## Tech Stack

- FastAPI
- SQLAlchemy (async)
- Alembic
- PostgreSQL
- Docker / Docker Compose
- Pytest / Ruff

---

## Local Development

## 1) Start services

```bash
docker-compose up -d
```

This starts:
- `api` on `http://localhost:8000`
- `postgres` on `localhost:5433` (container 5432)

## 2) Run migrations

```bash
make migrate
```

## 3) Verify health

```bash
curl http://localhost:8000/health/live
```

Expected:

```json
{
  "status": "ok",
  "service": "forex-backend"
}
```

---

## Common Commands

```bash
make lint
make test
make migrate
```

---

## CI Baseline

GitHub Actions workflow runs on PR and push to `main`:

- Lint
- Migrations
- Tests

Workflow file:

- `.github/workflows/ci.yml`

---

## Troubleshooting

## Port already in use (`:8000`)

Check process:

```bash
lsof -i :8000
```

If Docker backend is already running, do not start another `uvicorn` manually.

## Database connection issues

```bash
docker-compose ps
docker-compose logs -f --tail=200 api postgres
```

Then rerun:

```bash
make migrate
```

## Driver mismatch (`psycopg` vs `psycopg2`)

If database URL uses:

- `postgresql+psycopg://...` → install `psycopg` (v3)
- `postgresql+psycopg2://...` → install `psycopg2-binary`

Make sure local, Docker, and CI use consistent dependency definitions.

---

## Project Structure (high-level)

- `app/` — FastAPI application code
- `alembic/` — DB migrations
- `tests/` — test suite
- `docker-compose.yml` — local stack
- `Makefile` — common dev commands