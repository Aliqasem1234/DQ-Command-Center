# DQ Command Center

An enterprise Data Quality & Data Governance platform: manage data domains,
datasets, and fields; define and run data quality rules across the six
standard DQ dimensions (accuracy, completeness, consistency, validity,
uniqueness, timeliness); track quality results and health scores; assign
ownership/stewardship and governance policies; and audit every change.

Upload a real CSV or Excel file to create a dataset: it is profiled
automatically (real per-column statistics), scanned for quality issues on
request, and scored. Deterministic cleaning operations are previewed
(row by row, with a before/after quality score) before they are saved, and
every cleaning run creates a new version - earlier versions can be
downloaded or restored. Executable quality rules (required, unique, e-mail,
numeric range, allowed values, date range) run on every scan or on demand.
Every registered user works only on their own data; administration is
separate.

**Start here:** [PROJECT_OWNER_GUIDE.md](PROJECT_OWNER_GUIDE.md) explains the
whole project - architecture, database, security, operation, backups and
troubleshooting.

## Stack

- **Backend**: FastAPI (async), SQLAlchemy 2.0, PostgreSQL, Alembic migrations
- **Frontend**: React 19 + TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- **Auth**: JWT access/refresh tokens, Argon2 password hashing, RBAC (roles → permissions)
- **i18n**: English and Swedish
- **Infra**: Docker Compose (Postgres, backend, frontend, nginx)

See [ARCHITECTURE.md](ARCHITECTURE.md) for the data model and service layout,
[SECURITY.md](SECURITY.md) for the security posture, and the guides below to
run it.

## Getting started

| Doc | Purpose |
|---|---|
| [PROJECT_OWNER_GUIDE.md](PROJECT_OWNER_GUIDE.md) | **Owner guide**: everything needed to understand, run and maintain the project |
| [docs/FEATURE_INVENTORY.md](docs/FEATURE_INVENTORY.md) | What is implemented and how thoroughly it is verified |
| [docs/DATA_CLEANING_GUIDE.md](docs/DATA_CLEANING_GUIDE.md) | Every cleaning operation and quality rule |
| [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md) | Verified security controls and remaining risks |
| [docs/TESTING_AND_RELEASE.md](docs/TESTING_AND_RELEASE.md) | Test suites, browser tests, release checklist |
| [QUICKSTART.md](QUICKSTART.md) | Get the full stack running locally in a few minutes |
| [ADMIN_SETUP_GUIDE.md](ADMIN_SETUP_GUIDE.md) | How the first administrator account is created (no hardcoded credentials) |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Backend/frontend test suites, the Windows Docker test script, manual QA checklist |
| [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) | What changes for a real deployment |
| [SECURITY.md](SECURITY.md) | Auth, RBAC, rate limiting, headers, and known gaps |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Data hierarchy, service structure, known architectural debt |

## Status

Verified on 2026-10-18 against a running Docker stack: 164 backend tests,
15 frontend tests, type check and production build pass, and real-browser
suites (two-user isolation, cleaning/versioning/rules, dark-theme audit)
pass. See [docs/FEATURE_INVENTORY.md](docs/FEATURE_INVENTORY.md) for the
honest feature-by-feature status and the owner guide's "Current risks"
section before treating this as production-ready (notably: no HTTPS or
SMTP yet).

Older reports from an early AI-assisted session were moved to
`docs/archive/` because several of their claims proved inaccurate.
