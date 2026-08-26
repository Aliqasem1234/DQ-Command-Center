# Known Issues - Phase 1

## Critical
None.

## High
| # | Issue | Module | Status |
|---|-------|--------|--------|
| H1 | `python-jose` uses deprecated `datetime.utcnow()` — no functional impact, but deprecation warning appears in logs | `jose/jwt.py` | Upstream dependency — pin to version or replace with PyJWT in Phase 2 |
| H2 | Email verification tokens are included in API response for dev convenience — must be removed in production | `app/services/auth_service.py` | Configure via `EMAIL_MODE=production` in `.env` |

## Medium
| # | Issue | Module | Status |
|---|-------|--------|--------|
| M1 | Slowapi rate limiter stores counters in memory — resets on container restart; Redis-backed needed for production | `app/main.py` | Planned for Phase 2 (traefik/redis) |
| M2 | `docker-compose.yml` uses `version` attribute (obsolete in Compose v2.29+) — harmless warning | `docker-compose.yml` | Remove `version:` lines to suppress |
| M3 | Backend container uses `WatchFiles` reloader in development — auto-restarts on file changes; disable in production | `Dockerfile` | Already disabled via compose profile; no action needed |
| M4 | Frontend runs Vite dev server (not production build) — HMR enabled, slower than static serve | `docker-compose.override.yml` | Acceptable for dev; production will serve built files via nginx |

## Low
| # | Issue | Module | Status |
|---|-------|--------|--------|
| L1 | No frontend unit tests yet — coverage will be added in Phase 2 | Frontend | Planned |
| L2 | No end-to-end tests — authentication flows only tested via unit tests and manual curl | Project-wide | Planned for Phase 2 |
| L3 | `pytest-asyncio` `asyncio_default_fixture_loop_scope` warning — harmless, will fix on next pytest-asyncio upgrade | `pytest.ini` | Add config after upgrade |
| L4 | `passlib` `crypt` deprecation for Python 3.13 — passlib still functional but may break in future Python versions | `core/security.py` | Migrate to `bcrypt` or `argon2-cffi` directly in Phase 2 |
| L5 | Test coverage below 60% for auth service and API layer — acceptable for Phase 1 scope | Backend tests | Improve coverage in Phase 2 |

## Non-Issues (by design)
- **Refresh tokens returned in response body** instead of HttpOnly cookies — Phase 1 uses body for simplicity; cookie-based storage is pre-configured in the frontend axios interceptor
- **SQLite for unit tests** — aiosqlite with StaticPool; adequate for auth testing, no production impact
- **Verification token in response** — development convenience; disabled when `EMAIL_MODE=production`
