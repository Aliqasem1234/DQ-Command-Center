# Administrator Setup

There is no hardcoded administrator account. The first administrator is created in one of two ways, both driven by your own git-ignored `.env`.

## Option A: created automatically on startup (recommended)

Set these before the first start:

```bash
INIT_ADMIN_EMAIL=admin@example.com
INIT_ADMIN_PASSWORD=<a long, unique password>
INIT_ADMIN_NAME=Your Name
```

On every backend start, `app/core/seed_secure.py` checks whether a user with `INIT_ADMIN_EMAIL` exists. If not, it creates that user as super admin with the "Super Admin" role (every permission). If the user already exists, nothing happens.

- Credentials are never logged.
- Remove `INIT_ADMIN_PASSWORD` from `.env` once the admin exists. The browser test suites in `e2e/` read it to sign in as the admin; keep it only while you run them.
- Change the password after the first login if `.env` was ever shared.

## Option B: register through the UI

Leave `INIT_ADMIN_EMAIL`/`INIT_ADMIN_PASSWORD` empty and register normally. The account gets the `User` role: the full product on its own data, but no administration. To make it an administrator, an existing super admin assigns the role on the Users page.

## Checking access

1. Sign in as the admin. Users, Roles, Departments and the System log appear in the sidebar.
   - Super Admin holds `users:manage`, `roles:manage`, `departments:manage` and `audit:view`.
   - The Admin role holds only `users:manage` and `audit:view`.
2. Sign in as an ordinary registered user. The same pages and their API routes answer **403**.

Both directions are covered by `backend/tests/test_rbac.py` and `test_admin.py`.

## Development demo data

With `ENVIRONMENT=development`, the backend also seeds:
- the system roles;
- demo departments;
- three demo users (`demo1–3@dqcommandcenter.io`) with **random passwords**, so nobody can sign in to them;
- a few demo domains, datasets and rules.

Production never seeds demo data, and login refuses the demo accounts even if a development database is reused.

## Resetting an admin password

- Use **Settings → Säkerhet** while signed in. Changing the password ends every other session.
- Without SMTP, the forgot-password e-mail is not delivered. An operator can issue a reset (see `PROJECT_OWNER_GUIDE.md`).
