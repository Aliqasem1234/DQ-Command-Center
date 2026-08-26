# Production Deployment

This is a checklist of what actually needs to change from the local Docker
Compose setup, not a guarantee that following it makes the app
"production-ready" in every sense (see the honest gaps noted throughout and
in SECURITY.md).

## 1. Don't use `docker-compose.override.yml` in production

Compose auto-applies it if present in the same directory. It's meant for
local dev (bind-mounted source, Vite dev server with HMR, `ENVIRONMENT:
development`). For production, either delete it on the deploy host or run
explicitly without it:

```bash
docker compose -f docker-compose.yml up -d
```

## 2. Set real environment variables

At minimum, in your production `.env` (or your platform's secrets manager -
**do not** commit a production `.env`):

```bash
ENVIRONMENT=production
POSTGRES_PASSWORD=<random, 24+ chars>
JWT_SECRET_KEY=<random, 32+ chars — e.g. openssl rand -base64 48>
SECRET_KEY=<random, 32+ chars, different from JWT_SECRET_KEY>
DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>:5432/<db>
DATABASE_URL_SYNC=postgresql://<user>:<pass>@<host>:5432/<db>
CORS_ORIGINS=https://your-real-domain.com
```

`app/config.py` will **refuse to start** with `ENVIRONMENT=production` if
`SECRET_KEY`/`JWT_SECRET_KEY` are short/default or the database URL still
contains the dev placeholder password - this is enforced, not just
documented.

With `ENVIRONMENT=production`:

- Swagger/ReDoc/OpenAPI JSON are automatically disabled.
- Demo data seeding is automatically skipped.
- The `/auth/register` and `/auth/forgot-password` dev-mode token
  disclosure in the API response is automatically disabled.

## 3. Build a production frontend image

`frontend/Dockerfile` has a `production` stage that runs `vite build` and
serves the static output through its own nginx (`frontend/nginx.conf`,
with a SPA fallback for client-side routing). Build and smoke-test it
directly:

```bash
docker build --target production -t dq-frontend-prod ./frontend
docker run -p 8080:80 dq-frontend-prod   # http://localhost:8080 should serve the app
```

**This is not yet wired into `docker-compose.yml`.** The base compose file
has no `target:` on the frontend service (so it uses the Dockerfile's first
stage, `build`, which only produces `dist/` and doesn't run anything), and
`docker-compose.override.yml` pins it to `target: development` (the Vite
dev server) for local work. More importantly, the top-level `nginx`
service's config (`nginx/nginx.conf`) always proxies `/` to
`http://frontend:5173` - the Vite dev server's port - not to the static
file server the `production` stage exposes on port 80. Before deploying
this to a real environment, either:

- add a `docker-compose.prod.yml` that sets the frontend build `target` to
  `production`, drops the dev-only port mapping, and changes
  `nginx/nginx.conf`'s upstream for `/` from `frontend:5173` to
  `frontend:80` (requires templating the nginx config, since Compose can't
  rewrite file contents - see nginx's `envsubst`/templates support), or
- skip the frontend's own nginx entirely and instead have the top-level
  `nginx` service serve `frontend`'s built `dist/` directory directly by
  bind-mounting it, removing the extra hop.

Do not run the Vite dev server in production regardless of which option
you pick - no HMR overhead, no dev-only error overlays exposing source.

## 4. Network exposure

`docker-compose.yml` publishes backend (`8000`), frontend (`5173`), and
Postgres (`5432`) directly on the host in addition to nginx (`80`). In
production, only nginx should be reachable from outside the host - remove
or firewall the other `ports:` mappings so nginx is the sole entry point
(this also makes the nginx-level rate limits and CSP meaningful again,
rather than bypassable by hitting the backend port directly).

## 5. TLS

`nginx/nginx.conf` as shipped is HTTP-only. Terminate TLS at nginx (or a
load balancer in front of it) before exposing this publicly -
`Strict-Transport-Security` is already set by the backend, but it's
meaningless without HTTPS actually being served.

## 6. Database

- Run `alembic upgrade head` against a real, backed-up Postgres instance
  (the backend container does this automatically on startup - confirm
  your deployment doesn't skip that or race multiple replicas against it).
- Set up regular backups (`scripts/backup-db.ps1` is a Windows-local
  example; use your platform's managed Postgres backup feature in a real
  deployment instead of relying on that script).
- Do not use the `postgres_data` named volume as your only durability
  story for anything you can't afford to lose.

## 7. Email

Set `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM_EMAIL`. Without
these, the app runs in mock mode: password reset and email verification
"send" but nothing is actually delivered (see SECURITY.md). This is fine
for a demo, not for real users who need those flows to work.

## 8. Rate limiting at scale

The current rate limiter keeps counters in process memory
(`app/core/limiter.py`). Fine for one backend instance; if you run
multiple replicas behind a load balancer, move to a Redis-backed slowapi
storage backend so limits are enforced across all of them, not per-instance.

## 9. Logging

`LOG_LEVEL=DEBUG` is the dev default and is noisy (includes raw SQL). Set
`LOG_LEVEL=INFO` or `WARNING` in production, and confirm your log
aggregation doesn't capture anything you wouldn't want in production logs
(the app itself no longer logs credentials or tokens - see SECURITY.md -
but verify at the infrastructure layer too).

## What this document does not cover

Horizontal scaling, CI/CD pipeline setup, monitoring/alerting, and
disaster recovery are all real production concerns not addressed by this
codebase or this document - treat them as separate work, not something
implied by following this checklist.
