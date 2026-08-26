# DQ Command Center

An enterprise Data Quality & Data Governance platform: manage data domains,
datasets, and fields; define and run data quality rules across the six
standard DQ dimensions (accuracy, completeness, consistency, validity,
uniqueness, timeliness); track quality results and health scores; assign
ownership/stewardship and governance policies; and audit every change.

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
| [QUICKSTART.md](QUICKSTART.md) | Get the full stack running locally in a few minutes |
| [ADMIN_SETUP_GUIDE.md](ADMIN_SETUP_GUIDE.md) | How the first administrator account is created (no hardcoded credentials) |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Backend/frontend test suites, the Windows Docker test script, manual QA checklist |
| [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) | What changes for a real deployment |
| [SECURITY.md](SECURITY.md) | Auth, RBAC, rate limiting, headers, and known gaps |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Data hierarchy, service structure, known architectural debt |

## Status

This codebase has been audited and repaired against a real, running Docker
stack (Postgres + FastAPI + Vite + nginx), not just read. As of this pass:

- The backend actually boots, migrates, and serves requests (it previously
  could not - see the "what was broken" note in ARCHITECTURE.md).
- RBAC works correctly for both super-admin and non-admin roles.
- Login, dashboard, CRUD for departments/users/roles/data quality rules,
  governance assignments/policies, and the audit trail are wired to real
  data end-to-end and were verified in an actual browser session.
- The backend test suite (47 tests) passes.
- English and Swedish translations are complete and symmetric; there is no
  Arabic or RTL code left in the project.

Known remaining gaps are tracked honestly in SECURITY.md and
ARCHITECTURE.md rather than glossed over - please read those before
treating this as a finished product.
