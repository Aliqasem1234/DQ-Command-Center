# DQ Command Center V2 — Full Product for Every User, Strict Isolation, Dark UI

**Date:** 2026-10-16 · **Follows:** `QA_REPORT_2026-10-16.md`, `PRODUCTION_READINESS_2026-10-16.md` (both kept as history) · **State:** uncommitted on `master`; the development stack is running

## 1. Summary

Anyone who registers now gets the complete Data Quality product on **their own data**:
- upload, profile, scan, inspect issues;
- create and manage rules;
- clean, download and delete datasets;
- monitoring, governance/sharing, and their own activity log.

Platform administration (users, roles, departments, the global system log, platform-wide statistics) stays separate and is restricted.

The core user workflow was verified end to end in a real browser (Chrome via Playwright) as a brand-new account, on both the development stack and the production build: **31/31 checks**. A dark-theme audit of 32 pages and dialogs found **0 problems**. The backend suite has **103 tests**, including a new two-user isolation suite that was mutation-checked.

## 2. How product permissions work now

- **Product vs administration.** Permissions are split into *product* permissions (`datasets:*`, `data_quality:*`, `data_governance:*`, `analytics:view`, `reports:*`, `dashboard:view`, `profile:edit`) and *administration* permissions (`users:manage`, `roles:manage`, `departments:manage`, `audit:view`).
- **Every account gets the product.** Every new account receives the `User` role, which now holds **all product permissions and no administration permission**. Nobody is made an administrator.
- **Migration 012** applied the change to the existing database: it granted the new permissions to `User` and removed `audit:view` from `Manager` (that permission reads *everyone's* audit log). The seed mapping matches it for fresh installs.
- **Permissions decide what kind of action is allowed.** Row-level isolation (§3) decides which data it applies to, so a `:manage` permission never reaches anyone else's data.
- **Administrators** (`Admin`, `Super Admin`) keep their existing powers, and the previously fixed escalation guards still apply.

## 3. How isolation is enforced (backend, not the UI)

Every rule lives in `backend/app/core/dataset_access.py` and is applied in SQL. Foreign IDs answer **404**, so nobody can probe which IDs exist.

| Data | Rule |
|---|---|
| Datasets, versions, files, rows, downloads, profiling elements, cleaning | owner, steward, active governance assignee, or super admin |
| Deleting a dataset; sharing it (governance assignment) | **owner** (or super admin) only. Someone it was shared with can work on it but can't delete it, revoke the sharing or re-share it |
| Quality rules and everything derived from them (results, metrics, monitoring trends, rule performance, failing rules, reports, error summaries) | rules on accessible datasets, plus rules without a dataset that the user created or owns |
| Quality issues, check runs, dashboard figures, trends | only the user's accessible datasets. A foreign `dataset_id` in a query is intersected with that scope, so it can't widen it |
| Domains | **owned by their creator**, with names unique per owner. Previously names were globally unique, so one user could block and detect another's "Finance" |
| Governance policies and assignments | the user's datasets and domains (assignees can also see assignments that name them) |
| Audit | `GET /audit/my-logs`: your own actions, for everyone. `GET /audit/logs`: everyone's, administrators only |
| Platform views (`/dashboard/stats`, `/dashboard/enhanced` …) | `/stats` needs `users:manage`; the cross-tenant ones need super admin. Before this change, `/stats` and `/enhanced` needed **only a login** |

Smaller isolation fixes:
- **Dataset names** are unique per owner. Previously, uploading "Kunder" failed if *any* user had one, which also revealed that it existed.
- **`POST /datasets`** can no longer create a dataset "owned" by someone else.
- **Search** no longer returns other users' domains.
- **Sharing works by exact email.** The user directory used to list **every registered account and email** to anyone with governance permissions; it now only matches an exact email address.

## 4. Dashboard and metric correctness

- **Health score** = the average quality score of the latest scanned version of each of *your* datasets, the same number each dataset page shows. With nothing scanned it is **unknown** ("—" plus a hint), not "100% excellent".
  - The old formula divided pass rates by a severity weight, so a fully passing critical rule scored 50.
  - The old formula also used a run-level pass rate that is always 0 for automatic checks, because those checks only exist while they find problems.
- **Dimensions** = the average share of records passing each active check (latest result).
- **Trend** = daily average quality score. Each scan now records its score (`quality_check_runs.quality_score`, added in migration 012). Older runs, which only have a check pass rate, are not mixed into the line. The trend-direction maths was also biased, and is corrected.
- **No datasets yet:** the dashboard shows a welcome state with a "Ladda upp din första datauppsättning" button that opens the upload dialog directly.
- **Pre-existing bug fixed:** `/monitoring/rule-performance` (and the trend query) always failed because of an invalid SQL cast, and silently returned `[]`.

## 5. Sidebar: review and changes

| Item | Purpose / users | Backend | Data scoped | Verified |
|---|---|---|---|---|
| **ÖVERSIKT** · Instrumentpanel | Your quality overview: everyone | `/dashboard/summary`, `/quality-issues/open` | yes | browser: empty state, then real figures matching the dataset score |
| **DATA** · Datauppsättningar | Upload, profile, scan, issues, clean, versions, download, delete: everyone | `/dataset-files/*`, `/datasets/*` | yes | browser end to end |
| **DATAKVALITET** · Kvalitetsregler | Automatic rules from scans, plus your own rule definitions (optionally tied to one of your datasets): everyone | `/data-quality/rules*` | yes | browser: create a rule tied to a dataset |
| · Övervakning | Rule and result statistics per dimension: everyone | `/data-quality/metrics` | yes (was global) | renders; scoping by tests |
| **DATASTYRNING** · Styrning | Roles/sharing by email, policies: everyone | `/governance/*` | yes (was global) | browser: unknown email message, share, shared user's access |
| · Revisionslogg (**new route** `/activity`) | Your own activity: everyone | `/audit/my-logs` (new) | yes | browser |
| **INSTÄLLNINGAR** · Min profil | Name and account details | `/auth/me` | — | renders |
| · Säkerhet (**new route** `/security`) | Change password (moved here from the profile page, same component) | `/auth/change-password` | — | renders; the password change was verified in the previous phase, not re-run on the new page |
| **ADMINISTRATION** · Användare, Roller och behörigheter, Avdelningar, Systemlogg | Platform administration (shown only with the matching permission) | admin APIs | n/a | browser: role dialog, every page renders; regular users get /forbidden and 403 |

Considered and deliberately **not** added, to avoid placeholder pages:
- a separate "Profilering" page (profiling is a tab of each dataset);
- a "Kvalitetsresultat" page (results appear in each dataset's Problem tab and in Övervakning);
- "Systeminställningar" (no such settings exist).

The dashboard item, previously the only one without a section heading, is now under ÖVERSIKT.

## 6. Dark theme

- `<html class="dark">` is set in `index.html`, so there's no light flash before React loads.
- The theme store and toggle are removed, and the old `dq-theme-storage` preference is deleted on load.
- Chart colours come from one dark palette (`src/theme/chart.ts`).
- Root-cause fix: the global `.dark a` link rule out-ranked component classes, so every link styled as a button (e.g. "Gå till startsidan" on 404/403) had light-blue text on blue (contrast 1.9:1). It now uses `:where(.dark) a`.
- **Audit method:** a script inspects every visible element on 32 views (public pages, all app pages, every dialog, the user menu, all dataset tabs). It flags light surfaces and any text below 3:1 contrast against its real background. It ran with a stored *light* preference to simulate an old visitor. Result: **0 problems** on both the dev and production builds. Screenshots were also checked by eye.
- Rule dimensions, severities and statuses now display in Swedish/English instead of raw enum values, and the trend legend reads "Kvalitetspoäng %".

## 7. Tests actually run

| Layer | Result |
|---|---|
| Backend suite (unit + HTTP integration) | **103 passed** (93 before this phase) |
| ↳ new `tests/test_product_isolation.py` | 10 tests: two self-registered users; full workflow incl. delete; every aggregate empty for the other user; domains/names per user; rules/policies/assignments private; sharing grants access but not delete or re-share; no ownership planting; personal audit; Manager loses global audit; super admin platform views still work |
| ↳ mutation check | disabling the rule-visibility clause makes 4 tests fail |
| Frontend `tsc -b` / `vitest` / `npm run build` | pass / **13 passed** / pass |
| Migration 012 | up → down → up on a restored copy of the live DB; fresh install (12 migrations); applied to the live DB after a backup |
| Docker | both Compose files validate; dev → prod → dev switches; production restart; data preserved |
| **Browser, new regular user (dev and production build)** | **31/31** on each: steps 1–18 of the brief, plus rules, activity log, sharing by email, deletion |
| Browser, administrator and session workflow | 18/18 (role change in UI, upload/clean/download, refresh/back/forward, token refresh, logout, cross-user 404) |
| Browser, production flows | error boundary 4/4 (production build); Manager governance with the email field; reset/deactivation sessions; admin API 403s; lockout (after waiting out the rate limiter) |
| Browser, dark-theme audit | 32 views, **0 problems** (dev and production build) |

## 8. Remaining defects and limitations

| Severity | Item |
|---|---|
| Medium (product scope) | **User-defined quality rules are definitions only. They are not executed**: there is no rule engine. Quality checks are the automatic scan's checks. Documented here rather than faked |
| Medium | Stored quality scores and older check runs were computed before the corrected formulas. They update when a dataset is rescanned; older runs don't appear in the trend line |
| Low | Accuracy and Timeliness always show "Ingen data", because no automatic check exists for them (truthful, but noticeable) |
| Low | The `Manager`/`Analyst` roles now offer nothing beyond `User` for product use. The role model could be simplified in a later change |
| Low | `/roles/all` and `/departments/all` return role and department *names* to any signed-in user (no user data) |
| Low | The demo users' datasets sit in domains owned by the super admin. Domain names therefore aren't shown to the demo users (they are deactivation candidates anyway) |
| Carried over | No TLS; no SMTP; known-credential accounts still active (run `python -m app.tools.prepare_external_testing`). **Note:** this phase's browser runs created more test accounts (`qa.prod.a.*`, `qa.prod.b.*`, `qa.mgr.*`, `qa.usr.*`, `qa.rst.*`, `qa.lvr.*`, `qa.lck.*` @example.com). Their password is not in the repository, so the tool won't flag them; deactivate them from **Users** before external testing |

## 9. Not verified

- The Säkerhet page's password change was not re-run after moving it (same component, verified in the previous phase).
- English locale: new keys were added to both languages, but this phase's browser runs used Swedish.
- Keyboard-only navigation and screen readers; mobile layout of the new sidebar sections (earlier phases checked 390 px).
- Performance with large files or many datasets.

## 10. Files changed in this phase

- **Backend:**
  - new: `alembic/versions/012_user_product_access.py`, `tests/test_product_isolation.py`;
  - changed: `core/dataset_access.py`, `core/seed_secure.py`, `models/data_hierarchy.py`, `api/v1/{data_hierarchy_routes,dataset_files,data_quality,results,dashboard,governance,audit}.py`, `services/{quality_analytics,data_quality,monitoring,results_reporting,data_hierarchy,dataset_upload,governance,audit,quality_discovery,file_storage}_service.py`, `schemas/{data_hierarchy,data_quality_rule}.py`, `tests/test_rbac.py` (2 tests updated for email lookup).
- **Frontend:**
  - new: `theme/chart.ts`, `pages/profile/SecurityPage.tsx`;
  - removed: `store/themeStore.ts`;
  - changed: `index.html`, `main.tsx`, `App.tsx`, `index.css`, `layouts/MainLayout.tsx`, `routes/index.tsx`, dashboard, datasets list/detail, rules, governance, audit, profile and error pages, services (`audit`, `domain`, `governance`), types (`dashboard`, `dataset`, `dataQuality`), both locale files.

## 11. Running it

- Development: `docker compose up -d`, then http://localhost.
- Production-like: `docker compose down` (never `-v`), then `docker compose -f docker-compose.prod.yml up -d --build`.
- Tests:
  - `docker exec dq-backend python -m pytest -q -p no:logging`
  - `cd frontend; npx tsc -b; npx vitest run; npm run build`
- Backups taken during this phase (session scratchpad): `backup_pre_012.dump`, `backup_pre_prod_run2.dump`.
