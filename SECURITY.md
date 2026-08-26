# Security

This document describes the actual, verified security posture of the
application - not an aspirational checklist. Everything under "In place"
was tested against a running instance; everything under "Known gaps" is a
real, unresolved limitation.

## Authentication

- Passwords hashed with **Argon2** (`passlib`, `app/core/security.py`).
- JWT access tokens (15 min default) and refresh tokens (7 days default),
  signed HS256, algorithm pinned on decode (no algorithm-confusion risk).
- Refresh tokens are stored **hashed** (SHA-256) and **rotated** on every
  use - the old token is revoked when a new one is issued.
- Per-account lockout after `LOCKOUT_THRESHOLD` failed attempts
  (`LOCKOUT_DURATION_MINUTES`), backed by the `login_attempts` table.
- Login/register/forgot-password enforce rate limits both at the API layer
  (`slowapi`, see `app/core/limiter.py`) and again at the nginx layer -
  fixed in this pass; previously only nginx enforced them, and the
  backend's own port (8000) is published directly by `docker-compose.yml`,
  making nginx trivially bypassable.
- **Known gap**: login for a non-existent email returns immediately
  (skipping the Argon2 hash comparison an existing-user wrong-password
  attempt would run), which is a timing side-channel that could be used to
  enumerate valid emails. Low severity, not fixed in this pass.
- **Known gap**: the rate limiter's counters are in-process memory (see
  ARCHITECTURE.md) - fine for one instance, not for a multi-replica
  deployment without a shared backend.

## Admin provisioning

There is no hardcoded admin account anywhere in the codebase. The only
mechanism is `app/core/seed_secure.py`, run once at every backend startup:
if `INIT_ADMIN_EMAIL` and `INIT_ADMIN_PASSWORD` are set in `.env`, it
creates that user as super-admin *if a user with that email doesn't already
exist*; otherwise no admin is auto-created and the first real user must
register through the UI. See ADMIN_SETUP_GUIDE.md.

A previous version of this codebase had a *second*, insecure seed path
(`app/core/seed.py` / `backend/scripts/seed.py`, wired up by
`docker-compose.override.yml`) that always created
`admin@dqcommandcenter.com` / `[REDACTED-DEV-CREDENTIAL]` and echoed it to container
logs on every startup. That path has been deleted, not disabled - it no
longer exists in this codebase.

## Authorization (RBAC)

`User → UserRole → Role → RolePermission → Permission`, enforced via
`app.core.rbac.require_permission("code")` / `require_roles([...])` as a
FastAPI dependency on each protected route. `is_super_admin=True`
unconditionally bypasses every permission check (no additional gate - be
aware of this if you add a "break glass" audit requirement later).

This was **broken for every non-super-admin user** until fixed in this
pass: the permission checker read `current_user.roles` without eager
loading, which crashes under SQLAlchemy's async engine unless the related
rows happen to already be in the session's identity map. It worked by
accident for super-admins (the check short-circuits before touching
`.roles`) and 500'd for everyone else on every permission-gated endpoint.
Fixed by eager-loading the `roles → role → role_permissions → permission`
chain in `get_current_user()`.

## Input validation / injection

No raw SQL string interpolation anywhere in the backend - all queries go
through SQLAlchemy Core/ORM `select()`. Request/response bodies are
Pydantic-validated. `EmailStr` validation rejects reserved/special-use
domains (`.local`, `.internal`, etc.) - a real constraint, not a bug, but
worth knowing if you're picking a placeholder email for a demo account.

## Headers / transport

- `SecurityHeadersMiddleware` sets `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Strict-Transport-Security`, `Referrer-Policy`,
  `Permissions-Policy`, `Cross-Origin-Opener-Policy`,
  `Cross-Origin-Resource-Policy`, and now a real `Content-Security-Policy`
  (added in this pass - previously the backend set no CSP at all, so
  hitting it directly instead of through nginx had zero CSP protection).
- CORS origins come from `CORS_ORIGINS` (explicit allowlist, never `*`).
- Swagger/ReDoc/OpenAPI JSON are now **disabled when `ENVIRONMENT=production`**
  (added in this pass - previously served unconditionally in every
  environment, exposing the full route/schema surface with no auth).

## Secrets

- `backend/app/config.py` refuses to boot with an insecure/short
  `SECRET_KEY` or `JWT_SECRET_KEY`, or the default dev database password,
  when `ENVIRONMENT=production` (a `pydantic` model validator, added in
  this pass).
- `alembic.ini` no longer hardcodes a database URL - migrations now read
  the same `DATABASE_URL_SYNC` the app itself uses. Previously it had a
  hardcoded dev password baked in, so changing `POSTGRES_PASSWORD` in
  `.env` broke every migration until this was fixed.
- Mock-mode email (no SMTP configured, the default) no longer logs the
  email body. It previously logged the full password-reset/email-verification
  link, including the raw token, at INFO level - anyone with log read
  access could hijack either flow. Real SMTP sending is now actually
  implemented (`smtplib` + STARTTLS) rather than a stub that logged and
  returned `True` without sending anything.
- `.env` is git-ignored; `.env.example` contains no real secrets, only
  placeholders the app's own startup validator will reject in production.

## Audit logging

Every create/update/delete on departments, users, roles, data quality
rules, governance assignments/policies, and role-permission changes writes
an `audit_logs` row (`app/utils/audit_logger.py`) with actor, action,
entity type/id/**name** (added in this pass so entries show "Customer
Orders" instead of a bare UUID), and before/after values where applicable.
Verified live: created and deleted real records through the UI and
confirmed the corresponding audit rows.

## Running this in production

See PRODUCTION_DEPLOYMENT.md for the full checklist. At minimum: generate
real random secrets, set `ENVIRONMENT=production`, remove or gate
`docker-compose.override.yml` (it disables prod-mode settings and is meant
for local dev only), and don't expose port 5432/8000 directly on a public
host - route everything through nginx.
