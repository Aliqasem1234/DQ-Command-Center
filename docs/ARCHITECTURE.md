# Architecture

## Data hierarchy

Real foreign-key relationships (`app/models/data_hierarchy.py`,
`app/models/data_quality_rule.py`), not string-based references:

```
DataDomain (data_domains)
  └── Dataset (datasets)                     FK: domain_id
        ├── DataElement (data_elements)      FK: dataset_id
        │     └── DataElementMetadata        FK: element_id (profiling stats)
        ├── DataQualityRule (data_quality_rules)   FK: dataset_id / element_id
        │     ├── DataQualityResult          FK: rule_id
        │     └── RuleEffectiveness          FK: rule_id
        ├── QualityCheckRun                  FK: dataset_id
        ├── QualityIssue                     FK: rule_id, dataset_id
        └── DataLineage                      FK: source_dataset_id, target_dataset_id

DataGovernance   - role assignment (owner/steward/curator/analyst) scoped to
                   a domain, dataset, or element (exactly one FK set)
GovernancePolicy - policy (retention/access/quality/privacy) scoped to a
                   domain or dataset
```

RBAC is separate from the data hierarchy: `User` → `UserRole` → `Role` →
`RolePermission` → `Permission`, with a `is_super_admin` flag that
unconditionally bypasses permission checks.

## Real data ingestion, profiling, and cleaning

A `Dataset` can now be backed by an actual uploaded file (CSV or Excel)
rather than existing only as metadata. `DatasetVersion` (FK: `dataset_id`,
self-referential FK: `source_version_id`) is an immutable chain: the
original upload is version 1, and every cleaning operation produces a new
version rather than mutating an existing one. Files live on disk under
`UPLOAD_DIR/{dataset_id}/{uuid}.{ext}` (`app/services/file_storage_service.py`)
- server-generated names only, never the client-supplied filename, with an
extension allowlist and a streamed size cap.

Pipeline (`app/api/v1/dataset_files.py`, mounted at `/api/v1/dataset-files`,
kept separate from the pre-existing `/api/v1/datasets` metadata routes):

```
upload -> profile (app/services/profiling_service.py)
       -> scan (app/services/quality_discovery_service.py)
       -> clean/preview, clean (app/services/data_cleaning_service.py)
       -> download
```

`profile_dataset_version` reads the file with pandas (`dtype=str`, so
invalid values are never silently coerced away before they can be flagged),
infers a logical type per column via regex/`pd.to_datetime` sampling with
deliberately lenient thresholds (see the docstring on `infer_column_type` -
a strict threshold would reclassify a "mostly dates, a few garbage values"
column as plain text and defeat the point), and writes the result onto the
existing `DataElement`/`DataElementMetadata` models - the same ones the
Data Explorer pages already read, so profiled columns show up there with no
separate code path.

`scan_dataset_version` runs real checks (completeness/validity/uniqueness/
consistency/duplicate rows) against the actual file content and reconciles
findings against previously auto-discovered `DataQualityRule` rows (tagged
`rule_definition={"source": "auto_discovered", "check_key": ...}`), so a
re-scan updates existing issues and auto-resolves ones that no longer
reproduce, rather than accumulating duplicates. Quality score is always
`100 - (bad_cells / total_cells * 100)` computed from what was actually
found - never randomized or estimated.

Cleaning (`data_cleaning_service.py`) always operates on an in-memory copy
and is preview-first: `POST .../clean/preview` returns a diff summary and
up to 20 sample before/after rows without writing anything; only
`POST .../clean` persists, and it does so as a brand-new `DatasetVersion`
- the source file is never touched. `diff_sample` computes the changed-row
mask with one vectorized comparison before building sample dicts, not a
Python loop over every row - that distinction matters at scale (a row-by-row
version of this took 6s on 20k rows; the vectorized version takes ~0.1s).

A failed upload (e.g. a corrupt/unparseable file) is fully rolled back -
the `Dataset`, `DatasetVersion`, and stored file are all removed rather than
leaving a permanently broken entry behind - and reported as HTTP 422
(`DatasetProcessingError`), distinct from the HTTP 409 used for a genuine
conflict like a duplicate dataset name.

**Explicitly out of scope for this capability, not stubbed:** direct DB
source connections (Postgres/MySQL/SQL Server - file upload only),
fuzzy/similarity-based duplicate detection (only exact-row dedup), a
recommendations engine beyond the detected issues themselves, lineage/impact
analysis for uploaded files, a remediation workflow status pipeline beyond
the issue's open/resolved state, scheduled scans, and alerting. None of
these have partial implementations or dead UI buttons - they simply don't
exist yet.

## Backend layout

```
backend/app/
  api/v1/          route handlers (thin - validate input, call a service, shape the response)
  services/        business logic, one module per domain concept
  models/          SQLAlchemy ORM models
  schemas/         Pydantic request/response models
  core/            security.py (JWT/password hashing), rbac.py (permission
                   checks), limiter.py (shared rate limiter), seed_secure.py
                   (startup init)
  middleware/      security headers
alembic/versions/  migrations, applied in order at container startup
```

The frontend mirrors this: `src/services/*.ts` (one per backend domain,
all routed through the single authenticated axios client in `services/api.ts`),
`src/store/` (Zustand: auth, theme, UI state), `src/pages/`, `src/hooks/useAuth.ts`.

## Known architectural debt

Be aware of these before extending the code - they were identified and, where
noted, partially reconciled during the audit that produced this document, but
a full consolidation was out of scope.

**Two independent "create quality rule" paths.** `app/services/data_quality_service.py`
(behind `/api/v1/data-quality/rules`) creates rules with free-text
`data_source`/`target_field` string fields. `app/services/data_hierarchy_service.py`
(behind the hierarchy routes) creates rules with real `dataset_id`/`element_id`
foreign keys. Both write to the same `data_quality_rules` table and the same
ORM model, so data from either path is visible through either read path, but
a rule created via one API won't have the fields the other API expects
populated. The frontend's Data Quality Rules page currently uses the
free-text path. Before building more on top of this, pick one targeting
model and migrate the other call sites onto it.

**Two dashboard summary endpoints with overlapping but not identical data.**
`/api/v1/dashboard/*` (`app/api/v1/dashboard.py`) serves admin-facing stats
(user counts, audit activity) plus a DQ/governance rollup via
`enhanced_dashboard_service.py`. `/api/v1/dashboard/health` and
`/api/v1/dashboard/summary` (in `data_hierarchy_routes.py`, via
`quality_analytics_service.py`) serve a health-score-focused view with real
trend data. The frontend dashboard currently calls the second one. Worth
consolidating into one dashboard service if you're adding more widgets.

**The frontend's production Docker stage was never wired up.**
The development stack (`docker-compose.yml`) proxies nginx to the Vite dev
server (`frontend:5173`). The production-like stack
(`docker-compose.prod.yml`) builds the frontend into static files and
serves them from nginx (`nginx/Dockerfile.prod`, `nginx/nginx.prod.conf`).
It publishes only nginx on `127.0.0.1` and doesn't publish the database or
API ports. `frontend/Dockerfile` only builds the development image.

**In-memory rate limiting.** `slowapi`'s default backend keeps counters in
process memory - they reset on every container restart/redeploy and aren't
shared across replicas. Fine for a single-instance deployment; move to a
Redis-backed limiter before scaling horizontally.

## What was actually broken when this audit started

Worth recording once, here, rather than re-discovering it: prior AI-authored
completion reports in this repository (since removed) claimed
"production-ready" and "100% complete." None of the following was true when
this pass began, and all of it was found by actually running the app, not by
reading the code:

- The backend could not start at all (a SQLAlchemy reserved-attribute
  collision, plus ~10 wrong imports across route/service files).
- Every non-super-admin request to a permission-gated endpoint crashed with
  a 500 (lazy-loading a relationship on an async session with no eager-load
  configured - masked because super-admin short-circuits past the check).
- The governance module queried tables an earlier migration had already
  dropped.
- `alembic.ini` had a hardcoded dev database password, silently ignored
  by `.env` - migrations broke the moment a real password was set.
- The default `docker compose up` path seeded a super-admin account with a
  hardcoded, publicly-visible password and echoed it to container logs.
- The frontend login page never called the app's auth store, so every
  successful login bounced back to the login screen.
- `UserListPage`, `RoleListPage`, `DepartmentListPage`, `AuditLogPage`,
  `DataQualityRulesPage`, and `DataQualityMonitoringPage` were hardcoded
  fake data with dead Add/Edit/Delete buttons.
- `POST` and `GET /api/v1/data-quality/rules` both crashed on every call
  (a dropped-then-still-referenced column, and a SQLAlchemy 1.x API call
  that doesn't exist in 2.0).
- 27-32 translation keys used in the UI didn't exist in one or both locale
  files, so raw keys like `common.add` rendered literally.

All of the above is fixed and verified live as of this document. See git log
for the individual commits and their verification notes.
