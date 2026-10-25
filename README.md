# DQ Command Center

A Data Quality and Data Governance platform, built as a portfolio project. Every registered user works on **their own data**; platform administration is separate.

- **Upload** a CSV or Excel (`.xlsx`) file to create a dataset. It is profiled automatically (real per-column statistics), scanned for quality issues and scored.
- **Clean** with deterministic operations (trim, normalise dates, convert types, standardise categories, remove duplicates, handle missing values). Each run is previewed row by row, with the quality score before and after, and saving creates a new version. Earlier versions can be downloaded or restored.
- **Check** with executable quality rules (required, unique, e-mail, numeric range, allowed values, date range). They run on every scan or on demand.
- **Govern** with domains, sharing by exact e-mail, policies and a personal activity log. Administrators manage users, roles, departments and the system log.

No AI is used for cleaning or scoring: the same input always gives the same output.

## Status

**Not production-ready:** there is no HTTPS and no e-mail delivery (see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)). It runs locally, bound to `127.0.0.1`.

Verified on 2026-10-25 against a running Docker stack:
- 178 backend tests;
- 15 frontend tests, type check and production build;
- real-browser suites: two-user isolation, cleaning/versioning/rules, a 55-endpoint isolation sweep, and a dark-theme contrast audit of 32 views.

See [docs/FEATURE_INVENTORY.md](docs/FEATURE_INVENTORY.md) for the honest feature-by-feature status.

## Stack

- **Backend:** FastAPI (async), SQLAlchemy 2, PostgreSQL 16, Alembic, pandas
- **Frontend:** React 19, TypeScript, Vite 8, Tailwind CSS 4, TanStack Query, Zustand, i18next (Swedish and English)
- **Security:**
  - Argon2id password hashing;
  - JWT (PyJWT, HMAC) access tokens, and refresh tokens that are hashed, rotated and revoked;
  - RBAC, with per-user data isolation in the database queries;
  - an unprivileged backend container.
- **Infra:** Docker Compose (PostgreSQL, backend, frontend/nginx)

## Quick start (Windows, macOS or Linux with Docker)

1. **Configure.** Copy the template and fill in your own values:
   ```bash
   cp .env.example .env
   ```
   - Required: `POSTGRES_PASSWORD`, the same password inside `DATABASE_URL` and `DATABASE_URL_SYNC`, and `JWT_SECRET_KEY`.
   - Optional: `INIT_ADMIN_*` to create the first administrator ([docs/ADMIN_SETUP.md](docs/ADMIN_SETUP.md)).
   - There are no code defaults: the backend refuses to start with missing or placeholder secrets.
   - Generate secrets with `python -c "import secrets; print(secrets.token_hex(32))"`.
2. **Start** the development stack:
   ```bash
   docker compose up -d --build
   docker compose ps        # postgres, backend, nginx healthy; uploads-permissions "exited (0)"
   ```
   Migrations run automatically.
3. **Open** http://localhost (or the Vite dev server on http://localhost:5173). API docs are at http://localhost:8000/docs, in development only.
4. **Stop** with `docker compose down`.

   > **Never run `docker compose down -v`.** `-v` deletes the database and every uploaded file. Take a backup first (owner guide → Backup and recovery).

`scripts/run-checks.ps1` runs every automated check (tests, type check, build, Compose validation). `scripts/rebuild-dev.ps1` rebuilds and restarts the development stack.

## Documentation

| Doc | Purpose |
|---|---|
| [PROJECT_OWNER_GUIDE.md](PROJECT_OWNER_GUIDE.md) | **Start here:** architecture, database, security, operation, backups, troubleshooting |
| [docs/FEATURE_INVENTORY.md](docs/FEATURE_INVENTORY.md) | What is implemented and how thoroughly it is verified |
| [docs/DATA_CLEANING_GUIDE.md](docs/DATA_CLEANING_GUIDE.md) | Every cleaning operation and quality rule |
| [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md) | Verified security controls, dependencies and remaining risks |
| [docs/TESTING_AND_RELEASE.md](docs/TESTING_AND_RELEASE.md) | Test suites, browser tests, manual checklist, release checklist |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Development vs production-like stack, required secrets, containers, go-live requirements |
| [docs/ADMIN_SETUP.md](docs/ADMIN_SETUP.md) | How the first administrator is created (no hardcoded credentials) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Data model, service layout, architectural debt |
| [docs/history/](docs/history/) | Dated reports: incidents and design decisions |
| [SECURITY.md](SECURITY.md) | Security policy and how to report a vulnerability |
