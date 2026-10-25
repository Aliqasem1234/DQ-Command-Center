# Testing and Release

Every command below was run successfully in this repository on 2026-10-25. Run them from the project root in PowerShell or Git Bash, with the development stack up (`docker compose up -d`).

## 1. Test layers

| Layer | Where | What it proves |
|---|---|---|
| Backend unit + API integration | `backend/tests/` (pytest, 178 tests) | Business logic and HTTP behaviour against an in-memory SQLite database. Doesn't touch your real data |
| Frontend unit | `frontend/src/**/__tests__` (vitest, 15 tests) | Error messages (Swedish/English), permissions helper, per-user query cache |
| Type check | `tsc -b` | The TypeScript code is consistent |
| Production build | `npm run build` | The frontend compiles for production |
| Real browser + real API | `e2e/` (Playwright, see `e2e/README.md`) | The running app behaves correctly for real users in Chrome |

### Backend test files

| File | Tests | Focus |
|---|---|---|
| `test_auth.py` | 21 | registration, login, lockout, reset, sessions, health; demo accounts refused in production |
| `test_admin.py` | 22 | users, roles, departments, audit (admin) |
| `test_rbac.py` | 20 | permissions, escalation guards, ownership, deactivation |
| `test_product_isolation.py` | 10 | two ordinary users: every surface isolated, sharing |
| `test_data_quality.py` | 12 | rule CRUD |
| `test_quality_accuracy.py` | 3 | profiling and score against hand-computed values |
| `test_cleaning_engine.py` | 20 | every cleaning operation, known input → output |
| `test_rule_engine.py` | 17 | every executable rule type |
| `test_cleaning_and_rules_api.py` | 7 | preview = apply, restore, rule run and score, empty dataset, isolation |
| `test_config.py` | 27 | no code defaults for DB/JWT secrets; production refuses unsafe settings; errors never echo secrets |
| `test_prepare_external_testing.py` | 5 | known-password account detection, extra candidates file, demo e-mails |
| `test_security_hardening.py` | 14 | password change ends sessions, login enumeration guards, JWT claims and algorithms, no internal details in errors, validation errors don't echo input, `.xlsx` validation and zip-bomb guard, `.xls` refused, old passlib hashes still verify |

## 2. Commands

```powershell
# Backend tests (inside the running backend container; source is mounted in dev)
docker exec dq-backend python -m pytest -q -p no:logging

# One file, or one test
docker exec dq-backend python -m pytest -q -p no:logging tests/test_cleaning_engine.py
docker exec dq-backend python -m pytest -q -p no:logging -k restore

# Frontend tests, type check, production build
cd frontend
npx vitest run
npx tsc -b
npm run build      # creates frontend/dist (git-ignored); delete it afterwards if you like
cd ..

# Docker configuration validation (prints nothing when valid)
docker compose config --quiet
docker compose -f docker-compose.prod.yml config --quiet

# Browser + API suites (one-time: cd e2e; npm install)
cd e2e
$env:BASE="http://localhost:5173"; npm run isolation
$env:BASE="http://localhost:5173"; npm run cleaning
npm run sweep
cd ..
```

`-p no:logging` hides verbose library debug logging. It doesn't affect the results.

The tests need no `.env` and no real secrets: `tests/conftest.py` sets throw-away, test-only values when the variables are missing, so `cd backend; python -m pytest` also works outside Docker.

Don't use `docker compose config` without `--quiet` when sharing output: it prints the resolved database URL, **including its password**.

### All automated checks at once

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-checks.ps1
```

It runs the backend tests (inside the dev container), both Compose validations, the frontend type check, the unit tests and the production build, and reports which ones failed.

## 3. Reading failures

- **pytest `FAILED tests/x.py::name`:** read the lines starting with `E` just above it. They show the assertion and the actual value. Re-run just that test with `-k name`.
- **Import or startup errors:** `docker exec dq-backend python -c "import app.main"` shows the traceback.
- **`tsc` errors:** they give file:line. Fix the type, don't silence it with `any`.
- **e2e `FAIL`:** the text after `--` shows what the page contained. A "Timeout" during login usually means the **rate limiter** (10 logins/min). Wait a minute and re-run.
- **A test that fails only sometimes:** check whether it depends on the clock or the order. Report it rather than retrying until it passes.

## 4. Multi-user isolation

The isolation guarantee is covered three ways:
- `test_product_isolation.py` and `test_rbac.py`: an API test per surface;
- `npm run sweep`: every GET endpoint, with the other user's IDs;
- `npm run isolation`: a real browser, switching accounts in one tab.

When you add an endpoint that returns user data, **use `app/core/dataset_access.py`** and add a case to `test_product_isolation.py`. The suites were mutation-checked: removing the filters makes them fail.

## 5. Release checklist

Run before every release, or before sharing the app with anyone.

1. `git status`: review every change; `git diff` for accidental secrets (search for `PASSWORD=`, `SECRET`, `eyJ`).
2. Back up the database and uploads (see `PROJECT_OWNER_GUIDE.md` → Backup and recovery).
3. Run the backend tests, frontend tests, `tsc`, build and both `config --quiet` commands; all must pass.
4. Start the production-like stack and check that all services are healthy:
   ```powershell
   docker compose down          # NEVER add -v
   docker compose -f docker-compose.prod.yml up -d --build
   docker compose -f docker-compose.prod.yml ps
   ```
5. Run the e2e isolation and cleaning suites against `http://localhost`.
6. Check the logs for errors: `docker compose -f docker-compose.prod.yml logs --tail 200 backend`.
7. Commit (and only then push). Switch back to development with `docker compose -f docker-compose.prod.yml down; docker compose up -d`.

## 6. Manual browser checklist

Open http://localhost with DevTools (Console and Network). "Pass" means no red console errors and no unexpected 4xx/5xx requests.

1. **Login** with the admin account ([ADMIN_SETUP.md](ADMIN_SETUP.md)). You land on `/dashboard`.
2. **Dashboard** shows real numbers, or an explicit empty state for a new user.
3. **Every sidebar page** shows data or an explicit empty state, never a blank page.
4. **Datasets:** upload a CSV, scan it, open Rensa, preview a cleaning step, apply it, then restore the original version and download it.
5. **Administration** (admin only): add, edit and delete a department, then check that the System log lists all three actions by name.
6. **RBAC:** register an ordinary user. Administration pages are hidden, and their API routes answer 403.
7. **Isolation:** the ordinary user sees none of the admin's datasets, rules or domains.
8. **Password change** (Settings → Säkerhet): you stay signed in, and another browser signed in to the same account is signed out at its next request.
9. **Language:** switch Svenska and English; no raw `namespace.key` strings.
10. **Logout** returns to `/login`; `/dashboard` then redirects to `/login`.

## 7. What isn't tested automatically

- Real e-mail delivery (no SMTP configured).
- HTTPS deployment.
- Load and performance with large files (the upload limit is 50 MB).
- English-language UI in the browser (the keys exist, and Swedish is browser-tested).
- Linting: no linter is configured (ESLint was never installed; the dead `lint` script was removed).
