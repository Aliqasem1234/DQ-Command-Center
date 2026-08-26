# Quickstart

## Prerequisites

- Docker Desktop (Windows/macOS) or Docker Engine + Compose v2 (Linux)
- Nothing else needs to be installed on the host - backend, frontend, and
  database all run in containers.

## 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set real values for at least:

- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY` and `SECRET_KEY` (32+ random characters each - e.g.
  `openssl rand -base64 48`)
- `INIT_ADMIN_EMAIL` / `INIT_ADMIN_PASSWORD` / `INIT_ADMIN_NAME` (leave all
  three empty to register the first user through the UI instead - see
  ADMIN_SETUP_GUIDE.md)

`docker-compose.yml` reads these into the Postgres and backend containers;
nothing is hardcoded in the app itself.

## 2. Build and start

```bash
docker compose build
docker compose up -d
```

On Windows, `RUN_TESTS_ON_WINDOWS.ps1` does the same two steps plus
prerequisite checks and HTTP smoke tests:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_TESTS_ON_WINDOWS.ps1
```

The backend container runs Alembic migrations and the secure
initialization routine automatically on every start - no manual DB setup
step.

## 3. Verify

```bash
docker compose ps      # all four services should show as running/healthy
```

- Frontend: http://localhost
- Backend health check: http://localhost:8000/health
- API docs (non-production only): http://localhost:8000/docs

Log in with the admin account you configured in step 1 (see
ADMIN_SETUP_GUIDE.md if you left `INIT_ADMIN_*` empty).

## 4. Stop

```bash
docker compose down          # stop and remove containers, keep data
docker compose down -v       # also delete the Postgres volume (fresh DB next start)
```

## Local development notes

- `docker-compose.override.yml` (auto-applied by `docker compose up`) runs
  the frontend via the Vite dev server with hot reload and mounts
  `./backend`/`./frontend` into the containers, so source edits apply
  without a rebuild. It is **not** meant for production - see
  PRODUCTION_DEPLOYMENT.md.
- If you're on Windows/macOS and file edits aren't showing up in the running
  frontend container, that's a known Docker Desktop bind-mount limitation;
  `vite.config.ts` already enables polling to work around it, but a
  container restart (`docker compose restart frontend`) always picks up
  the current files as a fallback.
- Changing `.env` requires `docker compose up -d` (which recreates
  containers whose config changed), not `docker compose restart` (which
  reuses the existing container's already-resolved environment).
