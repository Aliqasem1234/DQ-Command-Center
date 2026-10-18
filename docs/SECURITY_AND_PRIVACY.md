# Security and Privacy

What the application actually guarantees today, how each control is implemented, and what is still missing. Every **verified** item has an automated test or a recorded real-browser check behind it. **Recommendation** marks things that are not implemented.

> Not production-secure yet. There is no HTTPS, and both stacks bind to `127.0.0.1` on purpose. See §9 before letting anyone else connect.

## 1. Authentication (verified)

- **Passwords** are hashed with **Argon2id** (`app/core/security.py`: time cost 3, 64 MiB memory, parallelism 4) and never stored or logged in plain text. Minimum length 8, maximum 128.
- **Login** returns a short-lived **access token** (JWT, HS256, 15 minutes by default) and a **refresh token** (JWT, 7 days).
  - Refresh tokens are stored hashed in `refresh_tokens` and rotated on every use.
  - Logout revokes the refresh token.
- **Errors don't reveal accounts:** wrong password and unknown e-mail give the same message (`test_login_nonexistent_and_wrong_password_are_indistinguishable`). E-mails are compared case-insensitively.
- **Lockout:** 5 failed logins lock the account for 15 minutes (`LOCKOUT_THRESHOLD`, `LOCKOUT_DURATION_MINUTES`).
- **Deactivation ends access immediately.** Existing tokens stop working and refresh is refused (`test_deactivated_user_loses_existing_sessions_immediately`).
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

## 9. Before anyone else connects

1. Put HTTPS in front of nginx (a reverse proxy with a certificate, or a tunnel that terminates TLS).
2. Use `docker-compose.prod.yml` with `PROD_CORS_ORIGINS=https://<your-host>`.
3. Deactivate known-credential accounts (see `PROJECT_OWNER_GUIDE.md` → Owner checklist).
4. Remove `INIT_ADMIN_PASSWORD` from `.env` once the admin exists, and rotate any secret that has been shared.
5. Configure SMTP, or accept operator-issued password resets.

## 10. Test credentials vs production secrets

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
