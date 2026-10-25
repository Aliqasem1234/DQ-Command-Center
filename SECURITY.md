# Security Policy

DQ Command Center is a **portfolio project**. It runs locally and is **not production-ready**: there is no HTTPS, no e-mail delivery, and it has not been through an independent security review. Don't deploy it to a public server as-is.

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Use GitHub's private vulnerability reporting instead (*Security* tab → *Report a vulnerability*), or contact the repository owner through their GitHub profile.

Include the steps to reproduce, the affected endpoint or file, and the impact you expect. Please don't include real personal data or secrets in the report.

## What is in place

All of these are verified by automated tests; details and evidence are in [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md).

- **Passwords and lockout:** Argon2id password hashing and account lockout.
- **Tokens:** short-lived JWT access tokens. Refresh tokens are stored hashed, rotated on use, and revoked on logout, password change, password reset and deactivation.
- **Authorization:** checked on the backend for every route, with per-user data isolation enforced in the database queries.
- **Configuration:** no code defaults for secrets. Startup fails on missing or placeholder secrets, and production refuses weak settings.
- **Rate limiting:** on the auth endpoints, in both the API and nginx.

## Supported versions

Only the latest commit on `master` is maintained.

## Secrets

No real secret belongs in this repository. Real values live only in a local, git-ignored `.env`. The test files contain **test-only** passwords, which are used solely against a throw-away in-memory database.

Development credentials from early versions have been removed from the code and from the history of this repository, and they are not valid anywhere. They may still exist in old clones or caches, so treat any password that was ever committed as public.
