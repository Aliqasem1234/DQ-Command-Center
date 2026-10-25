# Feature Inventory (verified 2026-10-18)

How far each feature really goes, judged from the code and from tests that were actually run. Having a page or an endpoint is not counted as "working".

**Legend**
- **A**: implemented and verified (automated tests **and** a real-browser run)
- **B**: implemented, not fully verified
- **C**: partially implemented
- **D**: not implemented
- **E**: broken or misleading

## Core product (every registered user, on their own data)

| Feature | Status | Evidence / notes |
|---|---|---|
| Registration, login, logout, session refresh | A | `tests/test_auth.py`; browser flows |
| Account lockout (5 failed logins, 15 min) | A | browser lockout test |
| Password change (Settings → Säkerhet) | B | API tested (ends every other session, keeps this one); UI not re-run in a browser after the 2026-10-25 change |
| Password reset by e-mail | C | Works with an operator-issued token; **no SMTP configured**, so users can't receive the e-mail |
| E-mail verification | C | Token flow exists; not enforced, and not deliverable without SMTP |
| Upload CSV/Excel → dataset + automatic profiling | A | `test_product_isolation.py`; browser |
| Profiling (types, nulls, uniques, min/max/mean) | A | `test_quality_accuracy.py` (hand-computed values) |
| Automatic quality scan (missing, duplicates, e-mail/date/number validity, inconsistent casing) | A | `test_quality_accuracy.py`; browser |
| Quality score (share of clean cells, no score for empty tables) | A | `test_quality_accuracy.py`, `test_cleaning_and_rules_api.py` |
| Cleaning: 9 deterministic operations with row-aligned preview | A | `test_cleaning_engine.py` (20 tests); browser `cleaning_flow.js` |
| Before/after quality score in the preview | A | API test; browser |
| Confirmation before row-removing cleaning | A | browser |
| Dataset versions (every cleaning creates a new version) | A | API + browser |
| Restore an earlier version (copy into a new version) | A | API + browser |
| Version history (operations per version) | A | browser |
| Download any version | A | byte-exact browser check |
| Delete own dataset (owner only) | A | API + browser |
| Executable quality rules (6 types) run on scan and on demand | A | `test_rule_engine.py`, `test_cleaning_and_rules_api.py`; browser |
| Other rule types | C (by design) | Stored as **documentation only** and labelled "Endast definition" in the UI |
| Dashboard (health, issues, trend, dimensions; empty state) | A | isolation tests; browser |
| Monitoring page | A | browser (empty state and with data) |
| Accuracy / Timeliness dimensions | D | No measurement exists; shown honestly as "Ingen data" |
| Domains (per-user grouping) | A | `test_product_isolation.py` |
| Governance: share a dataset by exact e-mail; policies | A | API + browser |
| Personal activity log (Revisionslogg) | A | API + browser |
| Swedish/English UI | B | Swedish browser-tested; English keys exist but weren't browser-run this phase |
| Dark theme (dark only) | A | automated contrast audit of 32 views |

## Administration (Admin / Super Admin only)

| Feature | Status | Notes |
|---|---|---|
| Users: create, edit, deactivate, assign roles | A | escalation guards tested (`test_rbac.py`); deactivation ends sessions |
| Roles & permissions | B | CRUD tested in an earlier phase |
| Departments | B | CRUD tested in an earlier phase |
| System log (everyone's audit trail) | A | 403 for non-admins verified |
| Platform statistics endpoints (`/dashboard/stats`, `/dashboard/enhanced`) | B | access control tested; no UI uses them |

## Platform

| Area | Status | Notes |
|---|---|---|
| Per-user data isolation (backend) | A | `test_product_isolation.py`, `test_rbac.py`; 55-endpoint sweep; two-user browser test |
| Per-identity frontend cache | A | `IdentityScopedQueryProvider.test.tsx` (mutation-checked) |
| Background scheduler | D | Not implemented; the unused scheduler stub and `apscheduler` were removed. Scheduled scans are out of scope (`ARCHITECTURE.md`) |
| Report export (PDF/Excel) | D | Only file downloads of dataset versions exist |
| Data lineage | D | Table exists (`data_lineage`), no API or UI |
| Quality targets / rule effectiveness | C | Tables exist and are read by unused endpoints; nothing populates them |
| Development stack (Vite) | A | `docker-compose.yml` |
| Production-like stack (built frontend, no DB/API ports) | A | `docker-compose.prod.yml` |
| HTTPS / TLS | D | Required before anyone else connects |
| Lint (ESLint) | D | Not configured (the dead `npm run lint` script was removed) |

## Removed as unused (2026-10-25)

- `nginx/Dockerfile`, `frontend/nginx.conf` and the `build`/`production` stages of `frontend/Dockerfile`: no Compose file used them. The production stack is built by `nginx/Dockerfile.prod`.
- `backend/app/tasks/scheduler.py` and the `apscheduler` dependency: never started.
- `RUN_TESTS_ON_WINDOWS.ps1` (described an old setup): replaced by `scripts/run-checks.ps1`. `rebuild-docker.ps1` became `scripts/rebuild-dev.ps1`.
