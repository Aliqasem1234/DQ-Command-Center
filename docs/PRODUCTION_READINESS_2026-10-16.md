# DQ Command Center V2 — Production Readiness Follow-up

**Date:** 2026-10-16 · **Follows:** `docs/QA_REPORT_2026-10-16.md` (kept unchanged as history) · **State:** all changes uncommitted on `master`

## 1. Verdict

**Not yet approved for external testers.** A production-like stack now exists and was verified end to end. It serves the compiled frontend, publishes no database or backend ports, enables no API docs, and refuses unsafe configuration. Three things still stand between it and outside users:

1. **No TLS.** Passwords and tokens would cross the network in clear text. Both stacks are therefore bound to `127.0.0.1` only. Put an HTTPS terminator in front before anyone else connects (§8, R-1).
2. **13 known-credential accounts are still active in the live database.** These are the 3 seeded demo users plus 10 QA test accounts whose passwords are in the repository. The tool and procedure to disable them are ready and verified on a copy of the database (§7). They were **not** run against the live data, because that decision is yours.
3. **No email delivery.** Without SMTP, testers can't reset forgotten passwords themselves. Configure SMTP, or use the operator procedure in §7.

Everything else in scope was verified, apart from the items listed in §9. No data was lost: the volume was preserved, a backup was taken before the switch, and row counts were compared before and after every restart.

## 2. Phase 1: verified starting state

Re-checked against the code and the running containers rather than taken from the earlier report.

| Item | Found |
|---|---|
| Uncommitted changes | 66 paths, as listed in the first report; nothing committed |
| Earlier fixes (spot-checked in code) | Dataset access checks on all 10 `dataset-files` routes; token echo opt-in; refresh tokens revoked on reset; Super Admin escalation guard; docs disabled in production |
| Tests reproduced | backend **71 passed**, frontend **13 passed**, `tsc` OK |
| How the app was served | nginx :80 → **Vite dev server** (`frontend` service, `target: development`, `npm run dev`) and `/api` → uvicorn :8000; source bind-mounted |
| Published ports | **0.0.0.0**:80, :5173, :8000, :5432, reachable from the LAN |
| Data volumes | `dq-command-center-v2_postgres_data`, `dq-command-center-v2_backend_uploads`. Other `dq-*` volumes on this machine belong to other Compose projects and were not touched |
| Mode | `ENVIRONMENT=development`: demo seed, `/docs` public, SQL echo |

Note: one `docker compose config` call during this inspection printed the resolved database URL, password included, into my local tool log. It wasn't written to any file. Later output was redacted.

## 3. Changes made in this phase

### 3.1 New defects found and fixed

| ID | Severity | Defect (reproduced) | Fix | Regression test |
|---|---|---|---|---|
| PR-01 | **High** | **Deactivating a user didn't end their sessions.** Live repro: after an admin deactivated a user, the old access token still got 200, and refresh kept issuing new tokens indefinitely | `get_current_user` and refresh rotation now reject inactive accounts; deactivation also revokes all refresh tokens | `test_deactivated_user_loses_existing_sessions_immediately` (both deactivation paths); browser: the user's open tab is sent to /login |
| PR-02 | High | Unknown `ENVIRONMENT` values (`prod`, `staging`) silently ran a half-development mode, with docs on and no secret checks | `ENVIRONMENT` normalised (case and whitespace) and restricted to `development`/`test`/`production` | `tests/test_config.py` |
| PR-03 | High | Production could start with `DEV_EXPOSE_AUTH_TOKENS=true` (ignored, but not rejected), `CORS_ORIGINS=*` alongside credentialed CORS, `LOG_LEVEL=DEBUG`, or the dev DB password in `DATABASE_URL_SYNC` | Startup refuses all of these in production | `tests/test_config.py` (13 cases) |
| PR-04 | Medium | `/health` reported "healthy" while the database was down, so container health checks were meaningless | `/health` runs `SELECT 1` with a 3 s timeout and answers 503 + `"database":"unreachable"` when it fails | `test_health_reports_unhealthy_when_database_is_unreachable` |
| PR-05 | Medium | Profile and scan disagreed: a whitespace-only cell counted as filled in the profile but missing in the scan | Profile treats whitespace-only cells as missing | `tests/test_quality_accuracy.py` |
| PR-06 | Medium | The quality score contradicted its own definition ("weighted by how much data each failing check affects"). It summed per-check counts in mixed units: a duplicate row counted as 1 cell, a duplicated ID counted distinct values, overlaps were counted twice. The hand-checked file scored **80** instead of **73.3** | Score = share of cells affected by *any* failing check, each cell counted once | `tests/test_quality_accuracy.py`; live API now matches all 17 expected values |
| PR-07 | Medium | No `.dockerignore`. The frontend image copied the host's Windows `node_modules` over the Linux one; the backend image included `test.db`, `.coverage` and local uploads | `backend/.dockerignore`, `frontend/.dockerignore` | image contents inspected |
| PR-08 | Medium | The dev seed created demo users with a password stored in the repo | Demo users now get a random, never-logged password (they only own showcase data). Existing ones are handled by §7 | — |
| PR-09 | Low | `index.html` hard-coded a permissive CSP (`'unsafe-eval'`, `connect-src http://localhost:*`) that shipped in the production build | Meta tag removed; CSP comes from nginx headers (strict in production) | headers checked |
| PR-10 | Low | `docker-compose.override.yml` re-published port 80 on all interfaces (Compose appends port lists) | Redundant entry removed | `compose config` |

Existing datasets keep their previously stored quality scores until they're rescanned; a rescan uses the corrected formula.

### 3.2 Production configuration (new)

- **`docker-compose.prod.yml`**: standalone; doesn't merge with the dev files.
  - postgres: no published port.
  - backend: production image, no source mount, no published port, `ENVIRONMENT=production`, `LOG_LEVEL=INFO`, token echo forced off, `exec uvicorn` without reload.
  - nginx: serves the compiled frontend and proxies `/api`; the only published port is `127.0.0.1:80`.
  - Secrets come from `.env` through variable interpolation, with `:?` so a missing secret fails loudly.
- **Data-safety interlocks**:
  - Same project name and container names as the dev stack, so Docker refuses to run two PostgreSQL containers on one data directory.
  - Volumes declared `external`, so the file can never create a fresh, empty database by accident.
- **`nginx/Dockerfile.prod`**: multi-stage build (`npm ci` + `npm run build`), then `nginx:1.27-alpine` with only `dist/`.
- **`nginx/nginx.prod.conf`** + **`nginx/security-headers.conf`**:
  - SPA fallback, so refreshing deep links works;
  - `/assets/` cached as immutable, `index.html` and `/locales/` set to `no-cache`;
  - `/docs`, `/redoc`, `/openapi.json` return 404;
  - per-IP rate limits on login/register/forgot (429);
  - `X-Forwarded-For` overwritten with the real peer;
  - strict CSP (`script-src 'self'`), `server_tokens off`, gzip;
  - the backend's duplicate security headers are hidden;
  - 55 MB body limit (the API caps uploads at 50 MB);
  - health check covers both the app shell and `/health` (API + DB).
- **Dev stack**: unchanged behaviour, but all ports bind to `127.0.0.1` (override with `DEV_BIND_ADDRESS`).

### 3.3 Demo/test account tooling (new)

`backend/app/tools/prepare_external_testing.py` (§7):
- Flags seeded demo emails, and any account whose password hash matches one of 15 passwords found in the repository, its docs or git history.
- Dry-run by default.
- `--apply` deactivates (never deletes) non-super-admins, revokes their sessions and writes audit entries.
- Super admins are reported, never changed, and the tool exits with code 2.
- Unit test: `tests/test_prepare_external_testing.py`.

### 3.4 Files changed in this phase

- **New:** `docker-compose.prod.yml`, `nginx/Dockerfile.prod`, `nginx/nginx.prod.conf`, `nginx/security-headers.conf`, `backend/.dockerignore`, `frontend/.dockerignore`, `backend/app/tools/{__init__,prepare_external_testing}.py`, `backend/tests/{test_config,test_quality_accuracy,test_prepare_external_testing}.py`, this report.
- **Modified:** `backend/app/{config,main}.py`, `backend/app/core/{security,seed_secure}.py`, `backend/app/services/{user_service,profiling_service,quality_discovery_service}.py`, `backend/tests/{test_auth,test_rbac}.py`, `docker-compose.yml`, `docker-compose.override.yml`, `frontend/index.html`.

## 4. Current network exposure (measured, not just configured)

Probed from the host with `curl` against 127.0.0.1 and the machine's LAN address.

| Port | Dev stack (now running) | Production stack |
|---|---|---|
| 80 (app) | 127.0.0.1 only | 127.0.0.1 only (`PROD_BIND_ADDRESS`) |
| 5173 (Vite) | 127.0.0.1 only | not running |
| 8000 (API) | 127.0.0.1 only | **not published**, refused |
| 5432 (PostgreSQL) | 127.0.0.1 only | **not published**, refused |
| Any port via the LAN IP | refused | refused |

Production served `/assets/index-*.js`, with no `/@vite/client` or `/src/main.tsx`. The production frontend was confirmed.

## 5. Tests actually run

| Layer | What | Result |
|---|---|---|
| Unit | config validation (13), quality accuracy against a hand-computed file (3), known-password detection (3), error normaliser (frontend, 13) | PASS |
| Integration (HTTP through the ASGI app, SQLite) | full backend suite: auth, RBAC, ownership, governance, reset/deactivation sessions, health | **93 passed**, run in the dev container *and* inside the production image |
| Static | `tsc -b`; `npm run build`; both Compose files `config --quiet` | PASS |
| Migrations | `alembic current` = `heads` = `011` on the live DB; tool `--apply` on a disposable restored copy | PASS; `alembic check` shows drift, see R-9 |
| Live HTTP (production stack) | `/docs` `/redoc` `/openapi.json` → 404; deep link → 200 HTML; missing asset → 404; `/health` with DB; headers (single strict CSP, immutable assets, gzip); forgot-password returns `detail: null`; non-admin → 403 on 9 admin calls; anonymous → 401 | PASS |
| **Browser** (Chrome via Playwright, production build) | crawl of every route as super admin and as Analyst; dataset workflow (role change in UI, upload, profile, clean, version, byte-exact download, reload, back/forward, token refresh, logout, foreign dataset → not found): **18/18**; registration cases; error boundary (failed chunk, component crash, recovery); Manager governance (scoped dataset list, user picker, assignment grants access); password reset in a second tab ends the first tab's session; admin deactivation ends a live session; wrong password and lockout | **All PASS** |
| Browser (dev stack, after switching back) | crawl of every route as super admin | PASS |
| Restarts | `docker compose -f docker-compose.prod.yml restart`; switching dev → prod → dev | all healthy; counts and upload files preserved |

In the browser runs, login retries waited out HTTP 429. The rate limiter fired as designed during the suites; that is not counted as a failure.

## 6. Phase 5: earlier QA gaps

| Gap | Required? | Finding | Status |
|---|---|---|---|
| Error boundary in a browser | Yes | Forced in Chrome on the production build: a page chunk failing to load, and a component throwing on an unexpected API shape. Both show the translated "Något gick fel" page with reload / home, and reload recovers | **Verified** |
| Governance as Manager | Yes | Assign form lists only datasets the Manager can access; user picker populated; assignment saved and grants access; unrelated user still gets 404 | **Verified** |
| Profiling and score accuracy | Yes | Hand-computed 10-row file. Types, null counts, min/max/average and issue counts matched; **two defects found and fixed** (PR-05, PR-06); now 17/17 match through the live API | **Fixed + verified** |
| Background scheduler | **No** | `app/tasks/scheduler.py` is an empty APScheduler wrapper with no jobs, imported nowhere. `ARCHITECTURE.md` explicitly lists "scheduled scans, and alerting" as out of scope | Documented as out of scope; not wired up, since it has nothing to run |

## 7. Preparing the existing database for external testing

Do this on the live database only when you decide to; every step is reversible.

1. **Back up.**
   ```powershell
   docker exec dq-postgres sh -c 'pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -Fc' > backup_before_external.dump
   ```
   Keep the file somewhere other than the temp folder. The backups taken during this work are in the session scratchpad: `...\scratchpad\backup_pre_qa_2026-10-16.dump` and `...\scratchpad\backup_pre_prod_switch.dump`.
2. **Review (dry run, changes nothing).**
   ```powershell
   docker exec dq-backend python -m app.tools.prepare_external_testing
   ```
   Expected today: the 3 `demo*@dqcommandcenter.io` accounts and the `qa.*`/`ab@…`/`samelocal*` test accounts. Your super admin and your two Gmail accounts are **not** flagged. Check that every listed account is disposable; the "datasets" column shows what each one owns.
3. **Apply.**
   ```powershell
   docker exec dq-backend python -m app.tools.prepare_external_testing --apply
   ```
   This deactivates only the listed non-super-admin accounts and ends their sessions. Their datasets stay in place and an audit entry is written. Undo per user from **Users** (or set `is_active = true`). If the tool exits with code 2, a super admin uses a published password: sign in and change it under **Settings → Change password**.
4. **Secrets.**
   - After the super admin exists, remove `INIT_ADMIN_PASSWORD` from `.env` (it's only used to create the first admin).
   - Make sure `DEV_EXPOSE_AUTH_TOKENS` is false or absent.
   - Rotate any secret that has been shared or pasted anywhere.
5. **Start production mode** (§10.2) and re-run step 2. It should report nothing new.
6. **Password resets without SMTP** (operator-only fallback). This prints a one-time reset token for one account. Treat it as a password and deliver it privately; the link is `https://<host>/reset-password?token=<token>`, valid for 1 hour.
   ```powershell
   docker exec dq-backend python -c "import asyncio; from app.database import async_session_factory as f; from app.services.auth_service import forgot_password as fp; exec('async def m():\n    async with f() as db: print(await fp(db, \"user@example.com\"))'); asyncio.run(m())"
   ```

## 8. Remaining security risks

| ID | Severity | Risk | Recommendation |
|---|---|---|---|
| R-1 | **High (blocker)** | No TLS. HSTS is sent but ignored over HTTP | Terminate HTTPS (reverse proxy with a certificate, or a TLS tunnel) in front of nginx; then set `PROD_BIND_ADDRESS` and `PROD_CORS_ORIGINS=https://<host>` |
| R-2 | **High (blocker)** | 13 known-credential accounts still active | §7 |
| R-3 | Medium | No SMTP, so self-service reset/verification doesn't work | Configure SMTP, or use §7 step 6 |
| R-4 | Medium | Access and refresh tokens live in `localStorage`; an XSS would expose them (refresh lasts 7 days) | Mitigated by the strict CSP. Moving to httpOnly cookies is an architectural change |
| R-5 | Low | After a password **reset**, an already-issued access token stays valid for ≤15 min. Refresh is revoked immediately; deactivation is now immediate | Add token versioning if this matters |
| R-6 | Low | Password *change* doesn't end other sessions | Same as R-5 |
| R-7 | Low | Account lockout can be triggered by anyone who knows an email (5 wrong attempts → 15 min lock) | Accept for the beta, or switch to progressive delays |
| R-8 | Low | Rate limits are in-process memory (one uvicorn process: correct; several workers would multiply the limits) | Keep one worker, or move limits to a shared store |
| R-9 | Low | `alembic check` drift: DB enums stored as `VARCHAR`, plus DB-only indexes and `NOT NULL` constraints not declared in the models. The DB is stricter, never weaker | Align the models in a dedicated change; don't autogenerate (it would drop indexes) |
| R-10 | Info | Aggregate quality metrics (health score, trends) still span all datasets | Product decision (carried over) |
| R-11 | Info | The production backend image includes tests and pytest (857 MB) | Optional slimming |
| R-12 | Info | No virus/malware scanning of uploads; files are validated by type and parse only | Consider before accepting files from strangers |

## 9. Not verified

- Behaviour behind a real TLS proxy and public hostname. Not deployed, by design.
- SMTP delivery: no server is configured.
- Load and performance; dark mode and keyboard-only navigation in the production build.
- ESLint: still not installed or configured.
- Fresh-install path for the production file (creating the external volumes on a blank machine). Documented in the file header, but not run here, because that would mean creating new volumes.

## 10. How to run

### 10.1 Development (Vite, hot reload, demo seed, API docs)

```powershell
cd C:\Users\aliqa\OneDrive\Desktop\dq-command-center-v2
docker compose up -d --build
# http://localhost  (API docs: http://localhost/docs, backend: http://127.0.0.1:8000)
docker exec dq-backend python -m pytest -q -p no:logging
cd frontend; npx tsc -b; npx vitest run
```

Ports bind to 127.0.0.1. To reach the dev server from another device on a trusted network, set `DEV_BIND_ADDRESS=0.0.0.0` in `.env`.

### 10.2 Production-like local stack

```powershell
cd C:\Users\aliqa\OneDrive\Desktop\dq-command-center-v2
docker compose down                                    # stop dev - NEVER add -v
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps           # postgres, backend, nginx all healthy
# http://localhost  (only 127.0.0.1:80 is published)
docker compose -f docker-compose.prod.yml logs -f backend
```

Back to dev:

```powershell
docker compose -f docker-compose.prod.yml down
docker compose up -d
```

Both stacks use the same database volume, so data carries over. The production stack needs the same secrets in `.env`. It refuses to start on default or short secrets, or on `DEBUG` logging.

The stack currently running is **development**, as it was at the start of this phase.
