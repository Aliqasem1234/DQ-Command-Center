# Security and Privacy

What the application actually guarantees today, how each control is implemented, and what is still missing. Every **verified** item has an automated test or a recorded real-browser check behind it. **Recommendation** marks things that are not implemented.

> Not production-secure yet. There is no HTTPS, and both stacks bind to `127.0.0.1` on purpose. See §9 before letting anyone else connect.

## 1. Authentication (verified)

- **Passwords** are hashed with **Argon2id** via `argon2-cffi` (`app/core/security.py`: time cost 3, 64 MiB memory, parallelism 4) and never stored or logged in plain text. Minimum length 8, maximum 128.
- **Login** returns a short-lived **access token** (JWT, 15 minutes by default) and a **refresh token** (JWT, 7 days).
  - Tokens are signed and verified with **PyJWT**, using HMAC only (`JWT_ALGORITHM` must be HS256/384/512; anything else is refused at startup).
  - The algorithm is pinned on decode, and `exp`, `iat`, `sub` and `type` are required, so unsigned, expired, foreign-key or expiry-less tokens are rejected (`test_security_hardening.py`).
  - Refresh tokens are stored hashed in `refresh_tokens` and rotated on every use.
  - Logout revokes the refresh token.
- **Errors don't reveal accounts:**
  - Wrong password and unknown e-mail give the same message (`test_login_nonexistent_and_wrong_password_are_indistinguishable`).
  - An unknown e-mail still runs one Argon2 verification, so response time doesn't reveal which addresses are registered.
  - "Account is deactivated" is only shown to someone who entered the correct password.
  - E-mails are compared case-insensitively.
  - Remaining, accepted: registration answers "Email already registered", and a locked account says so. Both are rate-limited.
- **Lockout:** 5 failed logins lock the account for 15 minutes (`LOCKOUT_THRESHOLD`, `LOCKOUT_DURATION_MINUTES`).
- **Deactivation ends access immediately.** Existing tokens stop working and refresh is refused (`test_deactivated_user_loses_existing_sessions_immediately`).
- **Password change ends every other session.** All refresh tokens are revoked, and the response carries a fresh token pair for the current session (`test_password_change_ends_other_sessions_and_keeps_this_one`).
- **Password reset:**
  - All existing sessions end (`test_password_reset_ends_existing_sessions`).
  - The reset token is single-use, expires after 1 hour, and is **never returned in the API response** unless the local-only flag `DEV_EXPOSE_AUTH_TOKENS=true` is set in development. Production refuses to start with it on.
  - Without SMTP the e-mail isn't delivered, so an operator must issue a token (see `PROJECT_OWNER_GUIDE.md`).

**Token storage:** tokens are kept in the browser's `localStorage`. A cross-site-scripting (XSS) bug could therefore read them. This is mitigated by the strict production Content-Security-Policy (`script-src 'self'`, no inline scripts). *Recommendation:* move to httpOnly cookies in a future version.

## 2. Authorization (verified)

- **Roles hold permissions; routes check permissions** (`app/core/rbac.py`).
- **Every registered user** gets the `User` role, which holds every *product* permission (datasets, data quality, governance, reports) and **no** administration permission.
- **Administration** (`users:manage`, `roles:manage`, `departments:manage`, `audit:view`) belongs to the `Admin` and `Super Admin` roles only.
  - An `Admin` can't grant or modify `Super Admin` (`test_admin_cannot_escalate_to_super_admin`).
- **Data isolation** is enforced in the database queries by one module, `app/core/dataset_access.py`.
  - You can access a dataset if you own it, are its steward, have been explicitly shared it (governance assignment), or are a super admin.
  - Rules, results, issues, metrics, dashboards, trends, domains, policies, search and audit history are all filtered through it.
  - Another user's ID answers **404**, so IDs can't even be confirmed to exist.
  - Evidence: `test_product_isolation.py`, a sweep of every GET endpoint (0 leaks), and a two-user browser test.
- **Sharing works by exact e-mail only.** There is no user directory, so users can't list who is registered. The lookup returns only an id and e-mail.
  - Only the **owner** can share, revoke sharing or delete a dataset.
- **Frontend:** the browser cache is separate for each signed-in identity, so switching accounts in one tab can't show the previous user's data (`IdentityScopedQueryProvider.test.tsx`). The UI hides actions you lack permission for, but **the backend is the security boundary**.

## 3. Rate limiting (verified)

- **Backend** (slowapi, per client IP): register 5/min, login 10/min, forgot-password 3/min, everything else 120/min.
- **nginx** adds the same auth limits.
- The backend sees the real client IP, because nginx overwrites `X-Forwarded-For` and uvicorn trusts only private proxy ranges.
- Limits are kept in process memory, which is correct for the single backend process used today.
- `RATE_LIMIT_PER_MINUTE` exists in `.env` but **the code does not read it**: the limits are fixed in code.

## 4. Configuration safety (verified)

In **every** environment, `DATABASE_URL`, `DATABASE_URL_SYNC` and `JWT_SECRET_KEY` have no code default. Startup fails if they are:
- missing or empty (Docker Compose turns an unset `${VAR}` into an empty string, so that's checked explicitly);
- for `JWT_SECRET_KEY`, shorter than 32 characters or one of the placeholders earlier versions shipped.

Configuration errors never echo the submitted values (`hide_input_in_errors`), so a failed start can't leak a secret into the logs.

The tests need no real secrets: `tests/conftest.py` sets throw-away, test-only values when the variables are missing. The application itself never falls back to a default.

When `ENVIRONMENT=production`, startup also **refuses** any of these:
- default or short (<32 character) `SECRET_KEY`;
- a database password under 16 characters, or one containing a development/example marker (`dev`, `pass`, `change`, `example`, `secret`, `test`, `demo`);
- `DEV_EXPOSE_AUTH_TOKENS=true`;
- `CORS_ORIGINS=*`;
- `LOG_LEVEL=DEBUG`;
- an unknown `ENVIRONMENT` value (`tests/test_config.py`).

Production also:
- turns off `/docs`, `/redoc` and `/openapi.json`;
- never seeds demo users, and **refuses login for the development demo accounts** (`demo1–3@…`) even if a development database is reused. The answer is the same as for an unknown account (`test_demo_accounts_cannot_sign_in_in_production`).

`SECRET_KEY` is validated but not otherwise used by the code today.

## 5. Network exposure (verified by probing)

| | Development (`docker-compose.yml`) | Production-like (`docker-compose.prod.yml`) |
|---|---|---|
| App (nginx) | 127.0.0.1:80 | 127.0.0.1:80 |
| Vite dev server | 127.0.0.1:5173 | not running |
| Backend API | 127.0.0.1:8000 | **not published** |
| PostgreSQL | 127.0.0.1:5432 | **not published** |

`DEV_BIND_ADDRESS` / `PROD_BIND_ADDRESS` change the bind address. **Don't set them to `0.0.0.0` without HTTPS.**

## 6. HTTP headers

- **Production nginx** sends a strict CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy` and `COOP`. HSTS is sent but only takes effect over HTTPS.
- `server_tokens` is off.

## 7. Privacy and data handling

- **Uploaded files** are stored on the `backend_uploads` Docker volume under one folder per dataset. Only the owner (and anyone it's explicitly shared with) can download them.
- **Deleting a dataset** removes its database rows (cascade) and its files.
- **Logs and records never contain:** passwords, tokens, or (for cleaning operations and rule results) cell values. The audit log stores operation types and counts. Rule results store row numbers, not values.
  - SQL statement logging (which would include bound parameters such as password hashes) is **off** unless `SQL_ECHO=true` is set in development.
  - Unexpected processing errors are logged on the server; the client gets a generic message without paths or library details.
  - Quality-issue descriptions from automatic scans include up to 5 example values. These are visible only to people who can access the dataset.
- **Database dumps** contain password hashes and user data. `backups/` and `*.dump` are git-ignored; store dumps outside OneDrive or other shared folders if possible.

## 8. Known risks (prioritised)

| Priority | Risk | Status |
|---|---|---|
| Critical before external access | No HTTPS | open (deployment task) |
| High | Test and demo accounts with publicly known passwords still active in the development database | open. Tool: `python -m app.tools.prepare_external_testing --apply` (older browser-test passwords via `--candidates-file`, kept outside the repo). Demo accounts are already refused in production |
| High | No SMTP: password reset and verification need an operator | open |
| Medium | Tokens in `localStorage` (XSS impact) | mitigated by CSP |
| Medium | Lockout can be triggered by anyone who knows an e-mail | accepted for beta |
| Low | An access token stays valid ≤15 min after a password *reset* (refresh is revoked at once) | accepted |
| Low | Aggregate metrics are per user; administrators see everything (super admin global access) | by design |
| Low | No malware scanning of uploaded files (they're parsed as CSV/Excel only, never executed) | open |
| Medium | The repository is **public**, and GitHub still serves commits from before the history rewrite by their old hashes. They contain old development credentials, none of which is valid anywhere | open: ask GitHub Support to purge cached/unreferenced commits |
| ~~Medium~~ | Backend container ran as root | **fixed 2026-10-25**: unprivileged user `app` (uid 10001), all capabilities dropped; the uploads volume is migrated by the one-shot `uploads-permissions` service (§11) |
| ~~Medium~~ | Frontend dev tooling (Vite 6, Vitest 2, esbuild, Tailwind 3) had known advisories | **fixed 2026-10-25**: Vite 8, Vitest 5, Tailwind 4, jsdom 30; `npm audit`: 0 vulnerabilities |
| ~~Medium~~ | `.xlsx` decompression bombs could exhaust memory; `.xls` was accepted but could never be read | **fixed 2026-10-25**: an `.xlsx` must be a real workbook that unpacks to at most 500 MB; `.xls` is refused (`test_security_hardening.py`) |
| ~~Low~~ | `passlib` unmaintained; `pytest` 8 local `/tmp` advisory | **fixed 2026-10-25**: `argon2-cffi` directly; pytest 9.1 |
| Low | Commit metadata shows the author's personal e-mail address | owner decision (GitHub no-reply address for future commits) |

## 9. Before anyone else connects

1. Put HTTPS in front of nginx (a reverse proxy with a certificate, or a tunnel that terminates TLS).
2. Use `docker-compose.prod.yml` with `PROD_CORS_ORIGINS=https://<your-host>`.
3. Deactivate known-credential accounts (see `PROJECT_OWNER_GUIDE.md` → Owner checklist).
4. Remove `INIT_ADMIN_PASSWORD` from `.env` once the admin exists, and rotate any secret that has been shared.
5. Configure SMTP, or accept operator-issued password resets.

## 10. Dependencies

Checked with `pip-audit` (the full backend container environment) and `npm audit`, on 2026-10-25.

**Backend.** One remaining finding:
- FastAPI 0.142 with Starlette 1.7, which fixes 7 Starlette advisories (multipart DoS, Range-header DoS, Host-header URL injection, and others).
- python-multipart 0.0.32 and python-dotenv 1.2.4.
- `python-jose` (unmaintained, with unfixed advisories) was replaced by PyJWT 2.15.
- The unused `apscheduler` was removed.
- `passlib` (unmaintained, and broken on Python 3.13) was replaced by `argon2-cffi` directly: same Argon2id parameters and format, and existing hashes verify (`test_existing_passlib_hashes_still_verify`).
- pytest 9.1, pytest-asyncio 1.4 and pytest-cov 7.1.
- **Result:** `pip-audit` on the container environment: **no known vulnerabilities**.

**Frontend.** `npm audit` reports **0 vulnerabilities**:
- Vite 8, Vitest 5, `@vitejs/plugin-react` 6, Tailwind CSS 4 (via `@tailwindcss/vite`; PostCSS and autoprefixer are no longer needed), jsdom 30, `i18next-http-backend` 4, axios 1.20.
- The Tailwind 4 stylesheet reproduces the v3 cascade (see `frontend/src/index.css`). Screenshots of 18 views were compared pixel by pixel before and after, and the dark-theme audit (32 views) passes.

**Base images:** `python:3.12-slim`, `node:22-alpine` (Node 20 is end-of-life), `nginx:1.28-alpine` (stable), `postgres:16-alpine`.

Re-run before every release:

```powershell
docker exec dq-backend pip freeze > freeze.txt; pip-audit -r freeze.txt --no-deps --disable-pip
cd frontend; npm audit
```

## 11. Container hardening

- Only nginx publishes a port in the production-like stack (`127.0.0.1` by default). PostgreSQL and the API are not published.
- The backend runs as the unprivileged user **`app` (uid/gid 10001)**, with **all Linux capabilities dropped** and `no-new-privileges`, in both stacks. Its only writable path is the uploads volume.
- The one-shot `uploads-permissions` service runs before the backend on every start.
  - It hands the uploads volume to uid 10001; nothing is moved, rewritten or deleted.
  - It has no network and only `CHOWN`, `FOWNER` and `DAC_READ_SEARCH`.
  - It was verified on the existing volume: all 65 files were byte-identical (SHA-256) afterwards.
- nginx runs with `no-new-privileges`.
- Secrets are required (`${VAR:?}`); the backend refuses unsafe values at startup (§4).

## 12. Test credentials vs production secrets

| Kind | Where it lives | Rule |
|---|---|---|
| **Production / real secrets**: DB password, `JWT_SECRET_KEY`, `SECRET_KEY`, `INIT_ADMIN_PASSWORD`, SMTP password | `.env` (git-ignored, never committed) or a secret store | Never in code, docs, tests, scripts, examples or logs. No code defaults. Generate randomly; rotate if ever shared |
| **Test-only credentials**: fixed passwords in `backend/tests/` | the test files | Used only against a throw-away in-memory SQLite database. Must never be used for a real account. `prepare_external_testing` flags any real account that uses one |
| **Browser test accounts** (`e2e/`) | generated at run time | A fresh random password per run, never stored or printed |
| **Demo accounts** (development seed) | development database only | Random passwords, nobody can sign in; refused at login in production |
| **Placeholders** in `.env.example` and docs | the repository | Only obviously fake values (`change-this-…`, `<long random>`, `[REDACTED-DEV-CREDENTIAL]`). The backend refuses the JWT placeholder at startup |

**Legacy development credentials.** Earlier versions shipped a default database password and fixed admin, demo and browser-test passwords in code, docs and scripts.
- All of them have been removed from the source code, and none of them is used by the current configuration.
- Anything that has ever been committed must be treated as public, even after a history rewrite, because old clones and forks may still hold it.
- If a real secret is ever committed: **rotate it first**, then consider cleaning history (`git filter-repo --replace-text`, with a verified backup and a lease-protected push).
