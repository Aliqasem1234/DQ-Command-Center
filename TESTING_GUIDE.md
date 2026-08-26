# Testing Guide

## Backend: automated tests

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

47 tests, using an in-memory SQLite database (no Docker/Postgres needed for
this suite - see `tests/conftest.py`). Covers auth (login, registration,
lockout, token refresh), RBAC/permission checks, department/user/role CRUD,
and data quality rule CRUD + metrics.

Do not trust a green run alone as proof the app works end-to-end - this
suite runs against SQLite with in-memory fixtures and mocked-out rate
limiting, and it caught real bugs during this project's audit that only
fully surfaced against real Postgres in Docker (see ARCHITECTURE.md's
"what was broken" section). Always also do the Docker + browser checks
below before calling a change verified.

## Frontend: type checking and build

```bash
cd frontend
npm install
npx tsc -b          # type check, zero errors expected
npx vite build      # production bundle, should complete with no errors
```

There is a `vitest` test runner configured (`npm test`) but no test files
currently exist under `src/` - this is a real gap, not a hidden suite;
adding component tests is future work, not something already covered.

## Full stack: Docker

```bash
docker compose build --no-cache   # clean rebuild, catches stale-cache issues
docker compose up -d
docker compose ps                 # all 4 services should be running/healthy
docker compose logs --tail=200    # scan for tracebacks/"ERROR" - should be none
```

On Windows, `RUN_TESTS_ON_WINDOWS.ps1` automates the above plus prerequisite
and HTTP smoke checks. It never deletes files or containers other than what
it created for this stack.

## Manual browser QA checklist

Open http://localhost with DevTools open (Console + Network tabs). For
every step below, "pass" means no red console errors and no unexpected
4xx/5xx network requests.

1. **Login** - sign in with your admin account (ADMIN_SETUP_GUIDE.md).
   Confirm redirect to `/dashboard`, not a bounce back to `/login`.
2. **Dashboard** - health score, open issues, dataset/rule counts, and the
   quality trend chart should reflect real seeded data (or an honest empty
   state if you haven't created any data quality rules yet) - never
   `Math.random()`-style fake numbers.
3. **Navigate** every sidebar item: Departments, Users, Roles, Audit Log,
   Data Quality → Rules, Data Quality → Monitoring, Profile. Each should
   show real data or an explicit empty state, never a blank page.
4. **CRUD** - on Departments (or Roles/Users/Data Quality Rules), click
   Add, fill the form, Save - the new row should appear without a page
   reload. Edit it. Delete it with the confirm dialog. Check Audit Log
   afterward - all three actions should appear there with the real entity
   name, not a bare UUID.
5. **RBAC** - log out, log in as a demo user (`demo1@dqcommandcenter.io`,
   see ADMIN_SETUP_GUIDE.md), and confirm Users/Roles/Departments/Audit
   Log/domains all return 403 rather than data or a 500. (A 500 here means
   a lazy-loaded relationship regressed - see SECURITY.md's RBAC note.)
6. **Language** - switch English ⇄ Svenska in the top nav. No raw
   `namespace.key`-looking strings anywhere, no leftover Arabic text.
7. **Profile** - edit your full name, save, reload the page - the change
   should persist (calls `PUT /api/v1/auth/me`).
8. **Logout** - should redirect to `/login` and clear the session; going
   back to `/dashboard` afterward should bounce to `/login`.
9. **API docs** - http://localhost:8000/docs (only available when
   `ENVIRONMENT` is not `production`) - try a few endpoints with "Try it
   out" using a token from step 1's login response.

## What "passing" does not mean

A green pytest run, a clean `tsc -b`, and `docker compose ps` showing
"healthy" are necessary but not sufficient. All three passed on this
codebase before this audit while the login page was completely
non-functional and the entire RBAC system 500'd for non-admins - none of
those checks would have caught either bug. The manual browser checklist
above is not optional busywork; it's the only step that actually exercises
the thing a user experiences.
