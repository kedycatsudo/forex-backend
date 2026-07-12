# Local Full-Stack Runbook (Dev)

This runbook defines the exact startup flow for running backend + frontend locally.

## Prerequisites

- Docker + Docker Compose installed
- Python virtualenv (optional for host tooling)
- Frontend dependencies installed (`npm install` or `pnpm install` in frontend project)

---

## 1) Start backend stack

From backend repository root:

```bash
docker-compose up --build -d
docker-compose ps
```

Expected:
- `app_postgres` = healthy
- `app_api` = up (health may show `starting` briefly)

Check backend logs if needed:

```bash
docker-compose logs -f --tail=200 api postgres
```

---

## 2) Run database migrations

Apply latest schema:

```bash
make migrate
```

Equivalent command:

```bash
docker-compose exec api alembic upgrade head
```

Optional verification:

```bash
docker-compose exec api alembic current
docker-compose exec api alembic history
```

---

## 3) Start frontend

From frontend repository root:

```bash
npm run dev
```

(or `pnpm dev` / `yarn dev` depending on project)

Typical frontend URL:
- http://localhost:3000 (or framework default)

---

## 4) Quick validation

- Backend liveness: `GET http://localhost:8000/health/live`
- Backend readiness: `GET http://localhost:8000/health/ready`
- Frontend loads in browser and can call backend APIs successfully.

---

## Troubleshooting

## A) Port conflicts

Symptoms:
- Errors like `address already in use`
- Frontend/backend won’t start

Check used ports:
```bash
lsof -i :8000
lsof -i :5433
lsof -i :3000
```

Fix:
- Stop conflicting process, or
- Change mapped ports in `docker-compose.yml` / frontend dev config

Then restart:
```bash
docker-compose down
docker-compose up -d
```

---

## B) DB connection failures

Symptoms:
- API logs show DB connection refused/auth failed
- Alembic migration fails

Checks:
1. Postgres container healthy:
```bash
docker-compose ps
```
2. Correct DB URL in backend env:
- Containerized backend should use compose host (e.g. `postgres`)
- Not `localhost` from inside container
3. Migrations applied:
```bash
make migrate
```

If needed, inspect API logs:
```bash
docker-compose logs -f --tail=200 api
```

---

## C) CORS / environment mismatch

Symptoms:
- Browser CORS errors
- Frontend calls wrong API URL
- 4xx/5xx only from browser (curl works)

Checks:
1. Frontend API base URL points to backend local URL (example `http://localhost:8000`)
2. Backend CORS config includes frontend origin (example `http://localhost:3000`)
3. Restart backend after env/config changes:
```bash
docker-compose restart api
```

---

## Common daily commands

```bash
# backend
docker-compose up -d
make migrate
make lint
make test

# stop backend
docker-compose down
```