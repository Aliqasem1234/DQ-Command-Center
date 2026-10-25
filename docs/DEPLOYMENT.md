# Deployment

The repository ships two Docker Compose stacks. Neither includes HTTPS or e-mail delivery: both are **still required** before anyone outside your own computer uses the app (see "Before going live").

| | `docker-compose.yml` (development) | `docker-compose.prod.yml` (production-like) |
|---|---|---|
| Frontend | Vite dev server (hot reload, source mounted) | Static build served by nginx (`nginx/Dockerfile.prod`) |
| Published ports | nginx `127.0.0.1:80`, Vite `:5173`, API `:8000`, PostgreSQL `:5432`, all on loopback | **only** nginx on `127.0.0.1:80` |
| `ENVIRONMENT` | from `.env` (normally `development`) | always `production` |
| API docs, demo seed | on | off |
| Secrets | from `.env` | required (`${VAR:?}`); unsafe values refused at startup |

Both stacks use the same container names and the same volumes (`dq-command-center-v2_postgres_data`, `dq-command-center-v2_backend_uploads`), so run one at a time.

## Running the production-like stack

```powershell
docker compose down                                   # stop development; NEVER add -v
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps          # postgres, backend, nginx: healthy
```

Back to development:

```powershell
docker compose -f docker-compose.prod.yml down
docker compose up -d
```

## Required configuration

Set these in `.env` (or your platform's secret store; never commit them):

| Variable | Rule enforced at startup |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | must be set |
| `DATABASE_URL`, `DATABASE_URL_SYNC` | must be set; in production the password must be ≥16 characters and not look like a dev/example value |
| `JWT_SECRET_KEY` | ≥32 random characters, not a placeholder, in **every** environment |
| `SECRET_KEY` | ≥32 random characters in production |
| `PROD_CORS_ORIGINS` | the public origin(s), e.g. `https://dq.example.org`; `*` is refused |
| `PROD_LOG_LEVEL` | defaults to `INFO`; `DEBUG` is refused in production |

Generate secrets with `python -c "import secrets; print(secrets.token_hex(32))"`.

## Containers and file permissions

- The backend runs as the unprivileged user **`app` (uid/gid 10001)**, with every Linux capability dropped and `no-new-privileges`. Its only writable path is the uploads volume.
- **`uploads-permissions`** is a one-shot service that runs before the backend on every start.
  - It hands the uploads volume to uid 10001 and exits; nothing is moved, rewritten or deleted.
  - It has no network and only the `CHOWN`, `FOWNER` and `DAC_READ_SEARCH` capabilities.
  - Volumes created by older versions were owned by root, and this service migrates them automatically.
- nginx runs with `no-new-privileges`. It sends a strict Content-Security-Policy and the usual security headers, and proxies `/api` to the backend.
- Migrations (`alembic upgrade head`) run automatically when the backend starts.

## Health checks

- `GET /health` (through nginx, or inside the backend container) answers 200 only when the API can reach the database within 3 seconds. Otherwise it answers 503.
- Each service has a Compose health check. nginx checks both the static app and `/health`.

## Before going live

These are **not implemented** in this repository:

1. **HTTPS.** Put a TLS-terminating reverse proxy or tunnel in front of nginx. Don't bind `PROD_BIND_ADDRESS` to `0.0.0.0` without it; passwords and tokens would travel in clear text. HSTS is already sent but only takes effect over HTTPS.
2. **E-mail delivery.** Set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_FROM_EMAIL`. Without them, password-reset and verification e-mails are not delivered.
3. **Backups.** Schedule database and uploads backups (manual runbook: `PROJECT_OWNER_GUIDE.md` → Backup and recovery). Don't treat the Docker volumes as your only copy.
4. **Scaling.** The rate limiter keeps its counters in process memory. With several backend replicas, move it to a shared store (for example Redis), and make sure only one replica runs migrations.
5. **Operations.** Monitoring, alerting, CI/CD and disaster recovery are not covered by this codebase.
