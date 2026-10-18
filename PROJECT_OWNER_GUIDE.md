# DQ Command Center V2 — Project Owner Guide

**For:** Ali, the owner, and technical reviewers · **Reflects the code as of:** 2026-10-18

This guide explains what the application is, how it is built, and how to run, protect, test and extend it. It describes the actual code. Anything that could not be verified is marked **(unverified)**. Real passwords and secrets never appear here: commands read them from inside the containers or from your `.env` file.

Related documents:
- [docs/FEATURE_INVENTORY.md](docs/FEATURE_INVENTORY.md): what is implemented, and how well it is verified
- [docs/DATA_CLEANING_GUIDE.md](docs/DATA_CLEANING_GUIDE.md): every cleaning operation and quality rule in detail
- [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md): security controls and risks
- [docs/TESTING_AND_RELEASE.md](docs/TESTING_AND_RELEASE.md): tests and the release checklist
- Dated, evidence-based reports in `docs/` (QA, production readiness, isolation)

---

## A. Project overview

**What it does.** DQ Command Center is a web application for **data quality management**. A user uploads a CSV or Excel file and the app then:
1. **profiles** it: column types, missing values, distinct values, min/max/mean;
2. **scans** it for quality problems: missing values, duplicate rows and identifiers, invalid e-mails, dates and numbers, inconsistent spelling or casing;
3. gives it a **quality score**: the share of cells not affected by any failing check;
4. lets the user **clean** it with deterministic operations, previewed before they are saved, each producing a new **version**;
5. runs the user's own **quality rules** (e.g. "age between 0 and 110", "e-mail must be valid");
6. shows a **dashboard** and **monitoring** over the user's own data, plus domains, governance (sharing, policies) and a personal activity log.

**Who it is for.** A portfolio project demonstrating Data Management and Data Quality skills. Anyone can register and use the full product **on their own data**. Platform administration (users, roles, system log) is separate and restricted to administrators. There is no billing or subscription.

**Main user workflow.** Register → upload a file → open the dataset → Profil (profile) → Skanna (scan) → Problem (issues) → Rensa (clean, preview, apply) → Versioner (history, download, restore) → Kvalitetsregler (rules, run) → Instrumentpanel / Övervakning (dashboard, monitoring).

**Important limitations.** These are covered in detail in [section N](#n-current-risks-and-roadmap):
- no HTTPS;
- no e-mail server (SMTP), so password-reset e-mails are not delivered;
- accuracy and timeliness can't be measured, and are shown as "Ingen data";
- no scheduled scans;
- no report export beyond downloading a dataset version;
- some test and demo accounts with known passwords still exist in the development database.

---

## B. System architecture

```mermaid
flowchart LR
    Browser["Browser<br/>(React + TypeScript)"] -->|HTTP :80| Nginx
    subgraph Docker Compose
      Nginx["nginx<br/>gateway"] -->|/api/*| API["FastAPI backend<br/>(Python, uvicorn)"]
      Nginx -->|"/ (dev: Vite dev server)<br/>(prod: built files)"| FE["Frontend"]
      API -->|SQLAlchemy| DB[("PostgreSQL 16")]
      API -->|read/write files| Files[("Upload volume<br/>backend_uploads")]
    end
```

| Part | What it is | Why it's here |
|---|---|---|
| **React + TypeScript** (`frontend/`) | The user interface, built with Vite and styled with Tailwind | Pages, forms and charts. TypeScript catches mistakes before running. TanStack Query fetches and caches server data, Zustand holds login state, and i18next provides Swedish and English |
| **FastAPI** (`backend/app/`) | The Python web API (async), served by uvicorn | All business logic: authentication, permissions, data isolation, profiling, scanning, cleaning, rules |
| **PostgreSQL 16** | The relational database | Users, roles, datasets, versions, rules, results, issues, audit log |
| **SQLAlchemy** | The Python library that maps database tables to Python classes (`backend/app/models/`) | Lets the code query the database safely without hand-written SQL strings |
| **Alembic** (`backend/alembic/versions/`) | Database migrations: numbered scripts that change the schema step by step | Every database can be upgraded to the same schema; run automatically at backend startup |
| **pandas** | A table-processing library | Reads CSV/Excel files and performs profiling, scanning and cleaning |
| **Docker Compose** | Runs all parts as containers with one command | The same setup on every machine; development and production-like configurations |
| **nginx** (`nginx/`) | Web server and reverse proxy | One entry point (port 80): sends `/api` to the backend and everything else to the frontend; adds security headers and rate limits |
| **File storage** | The Docker volume `dq-command-center-v2_backend_uploads`, mounted at `/app/uploads` | Uploaded files and every cleaned or restored version, one folder per dataset |
| **Authentication** | JWT access tokens (15 min) and refresh tokens (7 days); passwords hashed with Argon2id | See [section E](#e-security) |
| **Authorization** | Roles → permissions, plus per-dataset ownership rules in `backend/app/core/dataset_access.py` | See [section F](#f-user-and-administration-model) |
| **Background tasks** | **None run.** `backend/app/tasks/scheduler.py` exists but is never started | Scans and rules run when a user asks (upload, Skanna, Kör) |

---

## C. Repository structure

| Path | Purpose | Edit? |
|---|---|---|
| `backend/app/api/v1/` | HTTP endpoints (thin: validate, call a service, shape the response) | Yes, carefully. Every new data endpoint must use `dataset_access.py` |
| `backend/app/services/` | Business logic (profiling, scanning, cleaning, rules, auth, ...) | Yes, and add tests |
| `backend/app/services/data_cleaning_service.py` | Cleaning operations | Yes; see the cleaning guide |
| `backend/app/services/rule_engine.py` | Executable quality rules | Yes |
| `backend/app/core/dataset_access.py` | **The single data-isolation rule** | ⚠ Security-critical; changes need the isolation tests |
| `backend/app/core/security.py`, `rbac.py`, `dependencies.py` | Tokens, hashing, permission checks | ⚠ Security-critical |
| `backend/app/core/seed_secure.py` | Creates roles and permissions, the first admin, and demo data in development | ⚠ Changes affect every new installation |
| `backend/app/config.py` | Settings read from environment variables, plus production safety checks | ⚠ Don't weaken the checks |
| `backend/app/models/` | Database tables as Python classes | ⚠ Any change needs a new Alembic migration |
| `backend/alembic/versions/` | Migrations `001`–`012` | ⛔ **Never edit or delete an applied migration**; add a new one |
| `backend/tests/` | pytest tests (164) | Yes, add more |
| `backend/app/tools/prepare_external_testing.py` | Finds and deactivates known-password accounts | Use as documented |
| `frontend/src/pages/` | One folder per page | Yes |
| `frontend/src/services/` | API calls | Yes |
| `frontend/src/query/IdentityScopedQueryProvider.tsx` | Keeps cached data separate per signed-in user | ⚠ Security-relevant |
| `frontend/public/locales/{sv,en}/translation.json` | All UI text | Yes; keep both languages in step |
| `frontend/src/index.css` | Design system and dark-theme rules | Carefully; re-run the dark audit |
| `nginx/nginx.conf` | Development gateway | Carefully |
| `nginx/nginx.prod.conf`, `security-headers.conf`, `Dockerfile.prod` | Production gateway and headers | ⚠ Carefully |
| `docker-compose.yml` (+ `docker-compose.override.yml`, git-ignored) | Development stack | Carefully |
| `docker-compose.prod.yml` | Production-like stack | ⚠ Carefully: volumes are deliberately `external` |
| `.env` (git-ignored) | **Your real secrets** | ⛔ Never commit or share |
| `.env.example` | Template with placeholders | Yes, keep it free of real values |
| `e2e/` | Real-browser test scripts | Yes |
| `scripts/backup-db.ps1`, `scripts/init-db.sql` | SQL backup helper; DB extensions on first start | — |
| `docs/` | Reports and guides; `docs/archive/` holds outdated early reports | — |

**Files you should never edit by hand:** applied migrations, `package-lock.json` (use `npm install`), anything under `node_modules/`, and generated files (`dist/`, `*.tsbuildinfo`, `__pycache__`).

---

## D. Database

**Technology.** PostgreSQL 16 in the container `dq-postgres`.
- The database name, user and password come from `POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PASSWORD` in `.env`.
- **Data lives in the Docker volume `dq-command-center-v2_postgres_data`**, not in the project folder.
- Uploaded files live in `dq-command-center-v2_backend_uploads`.

**Main tables and relationships** (from the live schema):

```mermaid
erDiagram
    users ||--o{ user_roles : has
    roles ||--o{ user_roles : ""
    roles ||--o{ role_permissions : grants
    permissions ||--o{ role_permissions : ""
    users ||--o{ datasets : "owns (data_owner_id)"
    data_domains ||--o{ datasets : groups
    users ||--o{ data_domains : "owns (owner_id)"
    datasets ||--o{ dataset_versions : "has versions"
    datasets ||--o{ data_elements : "columns (profiling)"
    data_elements ||--|| data_element_metadata : stats
    datasets ||--o{ data_quality_rules : ""
    data_quality_rules ||--o{ data_quality_results : "each run"
    datasets ||--o{ quality_issues : ""
    datasets ||--o{ quality_check_runs : "each scan"
    datasets ||--o{ data_governance : "sharing / roles"
    datasets ||--o{ governance_policies : ""
    users ||--o{ audit_logs : "actions"
```

Other tables:
- `refresh_tokens`, `password_reset_tokens`, `email_verification_tokens` and `login_attempts`: authentication;
- `departments`;
- `data_lineage`, `quality_targets` and `rule_effectiveness`: these exist but are not used by any feature.

**Deletion behaviour (important):**
- Deleting a dataset deletes its versions, columns, rules, results, issues, sharing and policies (`ON DELETE CASCADE`), and the app also removes its files.
- **Deleting a domain row would delete all datasets in it.** The app has no "delete domain" action. Never delete domains directly in SQL.
- Users are never deleted by the app, only deactivated.

**Migrations.**
- The backend runs `alembic upgrade head` every time it starts.
- Check the current version (it should print `012 (head)`):
  ```powershell
  docker exec dq-backend alembic current
  ```
- To change the schema: edit the model, add a new file in `backend/alembic/versions/` (e.g. `013_...py`) with `upgrade()` and `downgrade()`, test it on a copy (see [section K](#k-backup-and-recovery-runbook)), then restart the backend.

**Inspecting the database** (opens an interactive SQL prompt; type `\dt` for tables, `\q` to quit):
```powershell
docker exec -it dq-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

One-line queries from **PowerShell**: Windows PowerShell 5.1 strips inner double quotes when calling programs, so escape them as `\"`:
```powershell
docker exec dq-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \"select count(*) from users\"'
```
In Git Bash the same command works without the backslashes.

**Backup, restore and verification:** see [section K](#k-backup-and-recovery-runbook).

**Avoiding data loss:**
- **never** run `docker compose down -v`;
- never delete the volumes;
- never run `DROP`/`DELETE` by hand without a verified backup;
- test migrations on a copy first.

---

## E. Security

The verified controls, briefly. Details and evidence are in [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md).

| Control | How it works (verified) |
|---|---|
| Password hashing | Argon2id. Plain passwords are never stored or logged |
| Login | 15-minute access token and 7-day refresh token (rotated on use, revoked on logout) |
| Lockout | 5 failed logins → 15-minute lock |
| Deactivation | Ends the user's sessions immediately |
| Password reset | Ends all sessions; single-use 1-hour token; never returned by the API unless `DEV_EXPOSE_AUTH_TOKENS=true` in development (production refuses to start with it on) |
| Roles and permissions | Routes require permissions; regular users have product permissions only |
| Data isolation | Enforced in database queries; foreign IDs answer 404 |
| Sharing | Exact-e-mail lookup only; only the owner can share, revoke or delete |
| Rate limiting | Register 5/min, login 10/min, forgot 3/min, 120/min otherwise, per client IP (backend and nginx) |
| CORS | Explicit origins from `CORS_ORIGINS` (dev) or `PROD_CORS_ORIGINS` (prod); `*` refused in production |
| API docs | `/docs` is available in development only; production disables it |
| Logs | No passwords, tokens or (for cleaning and rule results) cell values |
| Required secrets | `DATABASE_URL`, `DATABASE_URL_SYNC` and `JWT_SECRET_KEY` have **no code defaults**. The backend refuses to start in any environment if they are missing, empty or a known placeholder, and its error messages never echo the values |
| Production config | Refuses weak or default secrets, short or dev-looking database passwords, DEBUG logging, `*` CORS, token echo and unknown `ENVIRONMENT` |
| Demo accounts | Development-only, with random passwords; login refuses them in production even if a development database is reused |

**Recommendations (not yet done):**
- HTTPS (required before external access);
- SMTP for e-mails;
- httpOnly cookies instead of `localStorage` for tokens;
- deactivating known-password accounts;
- removing `INIT_ADMIN_PASSWORD` from `.env` after the first admin exists.

**Development vs production-like:**
- Development exposes API docs, prints SQL debug logs, seeds demo data and runs the Vite dev server.
- The production-like stack does none of this, publishes only nginx on `127.0.0.1:80`, and doesn't publish the database or API ports.

**Public exposure risk.** `127.0.0.1` means only your computer can connect. Exposing the app to a network **without HTTPS** would send passwords and tokens in clear text. See [section J](#j-production-like-operation).

**Secrets management.**
- All secrets live in `.env`, which is git-ignored and has never been committed.
- Rotate a secret by changing it in `.env` and recreating the backend. Changing `JWT_SECRET_KEY` logs everyone out.
- Don't paste `.env` or `docker compose config` output anywhere: the latter prints the database password.

**Test credentials vs real secrets.**
- *Real secrets* (database password, JWT and secret keys, admin password, SMTP password) exist only in your `.env` or your production secret store. They must never appear in code, docs, tests, scripts or examples.
- *Test-only credentials* are the fixed passwords in `backend/tests/`. They are only ever used against a throw-away in-memory SQLite database. Never use them for a real account.
- *Browser test accounts* (`e2e/`) get a fresh random password on every run.
- The development credentials that earlier versions shipped (old default DB password, old admin and demo passwords) have been removed from the source code and are not valid anywhere. Treat any password that has ever been committed as public. If a real secret is ever committed, **rotate it first**; cleaning Git history comes second.

---

## F. User and administration model

**Ordinary users** (role `User`, given automatically at registration) can:
- upload, profile, scan, clean, version, restore, download and delete **their own** datasets;
- create and run quality rules;
- use the dashboard and monitoring;
- create their own domains;
- share a dataset with another person by e-mail, and create policies;
- read their own activity log;
- change their name and password.

**Administrators:**
- `Admin`: manage users (`users:manage`) and read the system log (`audit:view`).
- `Super Admin`: everything, including roles and departments, and global access to all data.
- An Admin cannot create or modify Super Admins.

The `Manager` and `Analyst` roles have the same product permissions as `User`, and no extra administration permissions.

**How isolation works.** Every query for datasets, or anything tied to them, goes through `backend/app/core/dataset_access.py`. You can access a dataset if you:
- **own** it;
- are its **steward**;
- have an **active governance assignment** on it (it was shared with you); or
- are a **Super Admin**.

Rules, results, issues, metrics, trends, domains, policies, search and audit history are filtered the same way. In the browser, each signed-in identity gets its own cache, so switching accounts can't show stale data.

**Investigating an authorization problem:**
1. Reproduce it with two fresh accounts: `cd e2e; $env:BASE="http://localhost:5173"; npm run isolation`.
2. Find the endpoint in the browser's Network tab (F12) and call it with the other user's ID. It must answer 404 or 403.
3. Check that the endpoint uses `get_accessible_dataset`, `accessible_datasets_clause` or `visible_rules_clause`.
4. If data appears **without** a network request, the problem is client-side caching. Check `IdentityScopedQueryProvider.tsx`.
5. Add a failing test to `backend/tests/test_product_isolation.py` first, then fix it.

---

## G. Data cleaning

All operations are deterministic, previewed first, and saved as a **new version**. The original is never modified, and any earlier version can be restored as a new version. Full details for each operation: [docs/DATA_CLEANING_GUIDE.md](docs/DATA_CLEANING_GUIDE.md).

| Operation | Does | Missing values | Creates version | Reversible |
|---|---|---|---|---|
| Trimma blanksteg | removes leading/trailing spaces | untouched | yes | yes (restore) |
| Slå ihop flera mellanslag | collapses whitespace runs | untouched | yes | yes |
| Ta bort osynliga tecken | removes control and zero-width characters | untouched | yes | yes |
| Standardisera textformat | lower / UPPER / Title case | untouched | yes | yes |
| Normalisera datumformat | to `YYYY-MM-DD`; **never guesses ambiguous dates** | untouched | yes | yes |
| Konvertera datatyp | integer / decimal / boolean; invalid values kept (or emptied) and reported | untouched | yes | yes |
| Standardisera kategorivärden | your `from = to` mapping | untouched | yes | yes |
| Ta bort dubblettrader | exact duplicates on chosen columns; similar rows only reported | treated as equal | yes, with confirmation | yes |
| Hantera saknade värden | fill (value / mean / median / most common) or drop the row | the target | yes (dropping asks for confirmation) | yes |

**Known limitations:**
- no phone normalisation (no country rule);
- no fuzzy merging (on purpose);
- the score is computed on the remaining rows, so removing rows can raise it. The preview warns about this.

---

## H. Testing

The commands below are verified. More detail is in [docs/TESTING_AND_RELEASE.md](docs/TESTING_AND_RELEASE.md).

```powershell
docker exec dq-backend python -m pytest -q -p no:logging   # backend: 164 tests
cd frontend; npx vitest run; npx tsc -b; npm run build; cd ..  # frontend: 15 tests, types, build
docker compose config --quiet                                  # dev compose valid (prints nothing)
docker compose -f docker-compose.prod.yml config --quiet       # prod compose valid
cd e2e; npm install                                            # once
$env:BASE="http://localhost:5173"; npm run isolation           # two-user browser isolation
$env:BASE="http://localhost:5173"; npm run cleaning            # cleaning, versions, rules in the browser
npm run sweep                                                  # every GET endpoint, cross-user
```

**Interpreting failures:**
- **pytest:** read the `E` lines.
- **e2e "Timeout" at login:** usually the rate limiter. Wait a minute.
- **Never** "fix" a failing isolation test by loosening its assertion.

---

## I. Daily operation

| Task | Command |
|---|---|
| Start development | `docker compose up -d`, then open http://localhost (Vite directly: http://localhost:5173) |
| Stop safely (keeps all data) | `docker compose down` ⛔ **never add `-v`** |
| Status and health | `docker compose ps` (postgres, backend and nginx should say `healthy`) |
| Rebuild after dependency or Dockerfile changes | `docker compose up -d --build backend` (or `frontend`) |
| Pick up backend code changes | `docker compose restart backend` (dev runs without auto-reload) |
| Frontend code changes | picked up automatically (Vite hot reload) |
| Logs | `docker compose logs --tail 100 backend` (also `frontend`, `nginx`, `postgres`) |
| Pending migration? | `docker exec dq-backend alembic current` should say `012 (head)` |
| Which backend and frontend are running? | `docker ps` (images `dq-command-center-v2-backend` and `-frontend` = dev; `...:prod` = production-like) |
| Is the API alive? | open http://localhost/health (should show `"database":"ok"`) |

**Diagnosing problems:**
- **Failed login:**
  - "Fel e-postadress eller lösenord": wrong credentials.
  - "Kontot är tillfälligt låst": 5 failures; wait 15 minutes.
  - "För många försök": rate limit; wait a minute.
  - "Kontot har avaktiverats": an admin deactivated the account.
  - Then check `docker compose logs --tail 100 backend`.
- **Upload errors:**
  - Only `.csv`, `.xlsx` and `.xls` up to 50 MB are accepted.
  - A file that can't be parsed gives "Filen kunde inte läsas".
  - The same dataset name twice for **one** user is refused.
- **Database connectivity:**
  - `docker compose ps` should show postgres as healthy.
  - `/health` shows `"database":"unreachable"` when the backend can't reach the database.
  - Check `docker compose logs --tail 50 postgres`.

---

## J. Production-like operation

| | Development (`docker-compose.yml`) | Production-like (`docker-compose.prod.yml`) |
|---|---|---|
| Frontend | Vite dev server (hot reload) | compiled build served by nginx |
| `ENVIRONMENT` | development (demo seed, API docs, SQL debug log) | production (strict checks, no docs, no demo seed) |
| Published ports | 127.0.0.1: 80, 5173, 8000, 5432 | **127.0.0.1:80 only** |
| Database | same volume | same volume (declared `external`) |

**Switching:**
```powershell
docker compose down                                    # NEVER -v
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
# back to development:
docker compose -f docker-compose.prod.yml down
docker compose up -d
```

Both stacks use the same container names, so Docker refuses to run them at the same time (which protects the database). The production-like stack needs the same secrets in `.env`; it refuses to start with unsafe ones.

**Before external testers can connect:**
1. HTTPS in front of nginx;
2. `PROD_BIND_ADDRESS` and `PROD_CORS_ORIGINS` set for the real host;
3. known-password accounts deactivated;
4. SMTP configured (or operator-issued password resets accepted);
5. a fresh backup.

`127.0.0.1` is **not** a secure public deployment; it is simply not public.

---

## K. Backup and recovery runbook

Steps 1–4 were run successfully on this machine in PowerShell; step 5 is marked unverified. Store backups **outside** the project folder, and ideally outside OneDrive, because they contain password hashes and user data. `backups/` and `*.dump` are git-ignored as a safety net.

**1. Back up the database:**
```powershell
$dest = "D:\dq-backups"            # choose your own folder
New-Item -ItemType Directory -Force $dest | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
docker exec dq-postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/dq.dump'
docker cp dq-postgres:/tmp/dq.dump "$dest\db-$stamp.dump"
docker exec dq-postgres sh -c 'unlink /tmp/dq.dump'
```

**2. Back up uploaded files:**
```powershell
docker cp dq-backend:/app/uploads "$dest\uploads-$stamp"
```

**3. Verify the backup** (both checks must look right):
```powershell
docker run --rm -v "${dest}:/backup:ro" postgres:16-alpine pg_restore -l "/backup/db-$stamp.dump" | Select-String "TABLE DATA" | Measure-Object   # ~26 tables
(Get-ChildItem "$dest\uploads-$stamp" -Recurse -File).Count; docker exec dq-backend sh -c 'find /app/uploads -type f | wc -l'          # counts must match
```

**4. Restore into a separate test database** (safe; the real database is untouched):
```powershell
docker cp "$dest\db-$stamp.dump" dq-postgres:/tmp/restore-test.dump
docker exec dq-postgres sh -c 'createdb -U "$POSTGRES_USER" dq_restore_test && pg_restore -U "$POSTGRES_USER" -d dq_restore_test --no-owner /tmp/restore-test.dump'
docker exec dq-postgres sh -c 'psql -U "$POSTGRES_USER" -d dq_restore_test -tAc \"select count(*) from users\"'
docker exec dq-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \"select count(*) from users\"'   # compare
docker exec dq-postgres sh -c 'dropdb -U "$POSTGRES_USER" dq_restore_test && unlink /tmp/restore-test.dump'
```
This exact drill was run on 2026-10-18: the users, datasets and versions counts matched (74 | 37 | 49).

**5. Recover after a failed deployment or bad migration** **(unverified)**. Steps 3–4 overwrite live data, so they were deliberately **not** run against the real database. The same `pg_restore` was proven only into a separate database (step 4 above). Rehearse on a copy first if you ever need it:
1. Stop the app but keep the database running: `docker compose stop backend frontend nginx`.
2. Take a fresh backup of the current state (step 1), even if it's broken.
3. Restore the last good backup **into the real database**. This replaces its contents; do it only with a verified backup:
   ```powershell
   docker cp "$dest\db-GOOD.dump" dq-postgres:/tmp/good.dump
   docker exec dq-postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner /tmp/good.dump && unlink /tmp/good.dump'
   ```
4. If files are missing, copy them back: `docker cp "$dest\uploads-GOOD\." dq-backend:/app/uploads`.
5. Check out the code version that matches the backup (`git log`), then `docker compose up -d`.
6. Confirm: `docker compose ps` is healthy, `/health` reports the database ok, counts match, and you can log in and open a dataset.

**6. Confirm user data is intact after any operation:** compare the users, datasets and dataset_versions counts and the upload file count with the values from before (steps 3–4).

`docker compose down -v` deletes the database and all uploads. **It is never part of normal operation.**

---

## L. Environment variables

Defined in `.env` (copy from `.env.example`) and passed to containers by the Compose files. "Restart" means recreate the affected container (`docker compose up -d`).

| Name | Purpose | Required | Safe example | Sensitive | Notes |
|---|---|---|---|---|---|
| `POSTGRES_USER` / `POSTGRES_DB` | DB user and database name | yes | `dq_user` / `dq_command_center` | low | changing them later needs a DB migration plan |
| `POSTGRES_PASSWORD` | DB password | yes | `<long random>` | **yes** | must match the password in `DATABASE_URL` |
| `DATABASE_URL` | async DB URL for the app | yes, **no default** | `postgresql+asyncpg://USER:PASS@postgres:5432/DB` | **yes** | startup fails if missing; production refuses a DB password under 16 characters or one that looks like a dev/example value |
| `DATABASE_URL_SYNC` | sync DB URL for Alembic | yes, **no default** | `postgresql://USER:PASS@postgres:5432/DB` | **yes** | same rules as `DATABASE_URL` |
| `JWT_SECRET_KEY` | signs login tokens | yes, **no default** | `<64 random chars>` | **yes** | ≥32 chars and not a placeholder, in every environment; changing it logs everyone out |
| `SECRET_KEY` | general secret | yes in prod | `<64 random chars>` | **yes** | validated at startup but **not used by the code today** |
| `JWT_ALGORITHM` | token algorithm | no | `HS256` | no | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | access token lifetime | no | `15` | no | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | refresh token lifetime | no | `7` | no | |
| `INIT_ADMIN_EMAIL` / `_PASSWORD` / `_NAME` | first super admin, created once if missing | no | `admin@example.com` / `<strong>` / `Administrator` | password: **yes** | remove the password once the admin exists |
| `CORS_ORIGINS` | allowed browser origins (dev) | yes | `http://localhost` | no | `*` refused in production |
| `PROD_CORS_ORIGINS` | allowed origins (prod stack) | no | `https://dq.example.org` | no | default `http://localhost` |
| `RATE_LIMIT_PER_MINUTE` | — | no | `20` | no | **not used by the code**; limits are fixed in code |
| `LOCKOUT_THRESHOLD` / `LOCKOUT_DURATION_MINUTES` | login lockout | no | `5` / `15` | no | |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS` | outgoing e-mail | no | `smtp.example.org`, `587`, ... | password: **yes** | empty = e-mails are only logged as "would send" |
| `APP_NAME` | display name | no | `DQ Command Center` | no | |
| `ENVIRONMENT` | `development` / `test` / `production` | yes | `development` | no | any other value is refused |
| `LOG_LEVEL` | log detail (dev) | no | `INFO` | no | `DEBUG` refused in production |
| `PROD_LOG_LEVEL` | log level (prod stack) | no | `INFO` | no | |
| `DEV_EXPOSE_AUTH_TOKENS` | return reset/verify tokens in responses (local only) | no | `false` | **yes (if true)** | refused in production; never enable on a reachable machine |
| `DEV_BIND_ADDRESS` | host address for dev ports | no | `127.0.0.1` | — | `0.0.0.0` exposes everything to your network |
| `PROD_BIND_ADDRESS` / `PROD_HTTP_PORT` | host address and port for the prod stack | no | `127.0.0.1` / `80` | — | needs HTTPS before any non-local address |
| `VITE_API_BASE_URL` | API path used by the frontend | no | `/api` | no | baked into the production build |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `VITE_ENV`, `EMAIL_MODE` | — | — | — | — | present in `.env` but **not read by the code** |

Settings not in `.env`, defined in `backend/app/config.py`: `UPLOAD_DIR` (`uploads`) and `MAX_UPLOAD_SIZE_MB` (`50`).

---

## M. Troubleshooting

| Symptom | Safe diagnosis |
|---|---|
| Page blank or "Något gick fel" | reload; `docker compose logs --tail 100 frontend`; the browser console (F12) |
| "Det gick inte att nå servern" | `docker compose ps`; is the backend healthy? `docker compose logs --tail 100 backend` |
| Backend restarting or unhealthy | logs; a common cause is a failed migration (the log shows the Alembic error), or production config refusing an unsafe setting (the message names it) |
| A user sees data that isn't theirs | treat it as a security incident: [section F](#f-user-and-administration-model), "Investigating" |
| Port already in use | another program uses 80/5173/8000/5432. Stop it, or change `DEV_BIND_ADDRESS`/ports. Don't delete volumes |
| `docker compose -f docker-compose.prod.yml up` says the volume doesn't exist | intentional protection on a fresh machine: create the volumes first (see the file header), **never** on a machine with data |
| Changes to backend code not visible | `docker compose restart backend` |
| Upload works but the score is "—" | the dataset hasn't been scanned yet (press **Skanna**), or the file has no rows |
| Rule shows "Endast definition" | its type isn't executable, or it has no dataset or column |
| Login suddenly fails for many users | `JWT_SECRET_KEY` changed (everyone must log in again), or the rate limiter |

---

## N. Current risks and roadmap

**Critical before external access (verified):**
1. No HTTPS.
2. Accounts with publicly known passwords:
   - demo users and earlier QA accounts: `docker exec dq-backend python -m app.tools.prepare_external_testing` (then `--apply`);
   - older browser-test accounts (`qa.*@example.com`) were created with fixed passwords that are no longer in the source. Either deactivate them on the Users page, or pass those passwords to the tool in a file kept **outside** the repository (`--candidates-file`). New browser runs use random passwords.
3. No SMTP: password resets need an operator.

**Reliability gaps:**
- one backend process, with in-memory rate limits;
- no scheduled scans;
- no automatic backups (manual runbook only);
- the database schema differs from the models in minor, harmless ways (`alembic check` drift: enum storage, extra indexes).

**Product limitations:**
- no accuracy or timeliness measurement;
- no report export (PDF/Excel);
- lineage, quality targets and rule effectiveness tables are unused;
- only single-table rules (no cross-table referential checks);
- no phone normalisation.

**Technical debt:**
- ESLint not installed;
- unused files (`nginx/Dockerfile`, the frontend production stage, `scheduler.py`, the `apscheduler` dependency);
- `SECRET_KEY` and `RATE_LIMIT_PER_MINUTE` defined but unused;
- `Manager` and `Analyst` roles now redundant with `User`;
- the production backend image contains the tests.

**Recommended next steps:**
1. HTTPS plus the external-tester checklist;
2. SMTP;
3. scheduled backups;
4. report export of the quality summary;
5. ESLint in CI with the backend, frontend and e2e suites;
6. role-model simplification;
7. timeliness rules (e.g. "date not older than N days").

---

## O. Owner checklist

**Before each release:**
- [ ] `git status` / `git diff` reviewed; no secrets in the diff
- [ ] Database and uploads backed up **and verified** ([section K](#k-backup-and-recovery-runbook))
- [ ] Backend tests, frontend tests, `tsc` and build pass; both `config --quiet` are clean
- [ ] Production-like stack starts healthy; e2e isolation and cleaning suites pass
- [ ] Logs free of errors after a test run
- [ ] Commit (then push)

**Before inviting external testers:**
- [ ] HTTPS in place; `PROD_BIND_ADDRESS` and `PROD_CORS_ORIGINS` set
- [ ] Production-like stack in use (`ENVIRONMENT=production`)
- [ ] `prepare_external_testing` shows no active known-password accounts; `qa.*@example.com` test accounts deactivated
- [ ] `INIT_ADMIN_PASSWORD` removed from `.env`; admin password strong and changed
- [ ] SMTP configured, or a plan for operator-issued resets
- [ ] Fresh verified backup
- [ ] Privacy note for testers: what data they should and shouldn't upload

---

## P. Glossary

| Term | Meaning |
|---|---|
| API | The set of URLs the frontend calls to read or change data (`/api/v1/...`) |
| Backend / frontend | Server-side program (FastAPI) / what runs in the browser (React) |
| Container / image / volume | A running isolated program / its packaged template / persistent storage that survives container restarts |
| Docker Compose | A tool that starts several containers together from a YAML file |
| Migration (Alembic) | A versioned script that changes the database structure |
| ORM (SQLAlchemy) | Code that maps database tables to Python classes |
| JWT | A signed token proving who you are; expires after a set time |
| Access / refresh token | A short-lived login proof / a longer-lived token used to get new access tokens |
| Argon2id | A slow, memory-hard password-hashing method that makes stolen hashes hard to crack |
| RBAC | Role-based access control: users have roles, roles have permissions |
| Data isolation | Each user can only reach their own (or explicitly shared) data |
| 404 vs 403 | Not found / forbidden. The app answers 404 for other users' objects so their existence isn't revealed |
| CORS | The browser rule deciding which websites may call the API |
| CSP | Content-Security-Policy: a browser rule limiting where scripts may come from (limits the damage of XSS) |
| XSS | Cross-site scripting: malicious script running in your page |
| Rate limiting | A maximum number of requests per minute, against password guessing |
| Reverse proxy (nginx) | A server in front of the app that forwards requests and adds protections |
| TLS / HTTPS | Encryption of traffic between browser and server |
| Profiling | Computing statistics about each column |
| Quality dimension | A category of quality: completeness, validity, uniqueness, consistency, accuracy, timeliness |
| Quality score | Share of cells not affected by any failing check (this app's definition) |
| Deterministic | Same input and settings always give the same output (no randomness, no AI) |
| Version (dataset) | An immutable copy of the data; cleaning and restore create new ones |
| pg_dump / pg_restore | PostgreSQL tools to back up and restore a database |
| E2E test | End-to-end test: drives the real app in a browser like a user would |
