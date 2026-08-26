# Admin Setup Guide

There is no hardcoded administrator account in this application. The admin
account is created one of two ways, both driven entirely by your own
`.env` configuration.

## Option A: auto-created on first startup (recommended for a new deployment)

Set these three variables in `.env` before the first `docker compose up`:

```bash
INIT_ADMIN_EMAIL=admin@yourcompany.com
INIT_ADMIN_PASSWORD=<a strong, unique password>
INIT_ADMIN_NAME=Your Name
```

On every backend startup, `app/core/seed_secure.py` checks whether a user
with `INIT_ADMIN_EMAIL` already exists. If not, it creates that user with
`is_super_admin=True` and assigns the "Super Admin" role (which has every
permission). If a user with that email already exists, nothing happens -
this is safe to leave set across restarts/redeploys.

Credentials are never logged. The only place a plaintext credential
appears is your own `.env` file, which is git-ignored.

**Change the password after first login** if you shared `.env` with anyone
else during setup, or generated it non-interactively.

## Option B: register through the UI

Leave `INIT_ADMIN_EMAIL`/`INIT_ADMIN_PASSWORD` empty. No admin account is
auto-created. Open the app, use "Register", and create the first account
normally. It will **not** be a super-admin by default - promote it via a
database update or by having an existing super-admin assign the role
through Roles → assign, once one exists.

## Verifying admin access works

1. Log in with the account from Option A or B.
2. Confirm you can reach Users, Roles, Departments, and Audit Log in the
   sidebar (these require the `users:manage`/`roles:manage`/
   `departments:manage`/`audit:view` permissions, which only Super Admin
   and Admin roles hold).
3. Log in as a non-admin user (e.g. one of the demo users if you seeded
   demo data - see below) and confirm those same routes return 403 rather
   than data. Both directions matter: a working admin account that can't
   do anything is as broken as a "non-admin" that can do everything.

## Demo/seed data

When `ENVIRONMENT=development` (the default), the backend also seeds:

- System roles: Super Admin, Admin, Manager, Analyst, User
- Demo departments: Finance, Sales, Operations, Technology
- Three demo users (`demo1@dqcommandcenter.io` / `demo2@...` / `demo3@...`,
  password `[REDACTED-DEV-CREDENTIAL]`, no elevated permissions) - useful for
  testing RBAC boundaries without touching the real admin account
- A small set of demo domains/datasets/quality rules/issues so the
  dashboard and list pages have real (not fake) data to show immediately

This only runs in development and is skipped automatically once it detects
the demo data already exists (checked by looking for the "Finance" domain).
Do not rely on this in a production deployment - set `ENVIRONMENT=production`
and it will not run (see PRODUCTION_DEPLOYMENT.md).

## Rotating admin credentials later

There is no "reset admin password" CLI. Either use the normal
forgot-password flow (requires SMTP configured - see SECURITY.md for the
dev-mode fallback), or update `password_hash` directly in the `users`
table using the same Argon2 hashing the app uses
(`app.core.security.hash_password`).
