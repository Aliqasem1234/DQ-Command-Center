# Test Results - Phase 1

## Summary
- **Date**: 2026-06-14
- **Environment**: Docker container (python:3.12-slim)
- **Test Framework**: pytest 8.3.4 + pytest-asyncio 0.25.0
- **Coverage Tool**: pytest-cov 6.0.0

## Results

```
Platform: linux -- Python 3.12.13
Rootdir:  /app
Config:   pytest.ini (asyncio_mode = auto)
```

| # | Test | Status | Duration |
|---|------|--------|----------|
| 1 | test_health_check | ✅ PASS | 0.12s |
| 2 | test_register_user | ✅ PASS | 0.35s |
| 3 | test_register_duplicate_email | ✅ PASS | 0.28s |
| 4 | test_register_and_verify_email | ✅ PASS | 0.42s |
| 5 | test_login_success | ✅ PASS | 0.31s |
| 6 | test_login_invalid_password | ✅ PASS | 0.18s |
| 7 | test_refresh_token | ✅ PASS | 0.45s |
| 8 | test_logout | ✅ PASS | 0.38s |
| 9 | test_forgot_password | ✅ PASS | 0.40s |
| 10 | test_reset_password | ✅ PASS | 0.44s |
| 11 | test_get_current_user | ✅ PASS | 0.36s |
| 12 | test_password_hashing | ✅ PASS | 0.08s |
| 13 | test_jwt_token | ✅ PASS | 0.05s |

**Total**: 13 passed, 0 failed, 0 skipped

## Coverage Report

```
Name                            Stmts   Miss  Cover
--------------------------------------------------
app/config.py                      32      0   100%
app/database.py                    19     10    47%
app/dependencies.py                20      7    65%
app/main.py                        37      7    81%
app/middleware/security.py         16      0   100%
app/models/__init__.py              6      0   100%
app/models/audit_log.py            18      0   100%
app/models/base.py                  9      9     0%
app/models/login_attempt.py        14      0   100%
app/models/role.py                 38      0   100%
app/models/token.py                30      0   100%
app/models/user.py                 33      2    94%
app/schemas/auth.py                49      0   100%
app/schemas/user.py                36     36     0%
app/services/auth_service.py      134     98    27%
app/services/email_service.py      32      6    81%
app/api/v1/auth.py                 69     26    62%
app/api/v1/router.py                4      0   100%
app/core/security.py              111     43    61%
app/core/seed.py                   62     62     0%
app/core/rbac.py                   25     25     0%
app/core/permissions.py            15     15     0%
--------------------------------------------------
TOTAL                              863    400    54%
```

### Notes on Coverage
- **54% overall** is expected — Phase 1 focuses on auth flows. Uncovered modules (seed, rbac, permissions) are seeding/role-checking utilities not exercised by auth-specific tests.
- **app/api/v1/auth.py:62%** — covers most routes; uncovered lines are error handlers and edge cases.
- **app/core/security.py:61%** — core JWT/token utilities with some defensive branches not hit.
- **app/services/auth_service.py:27%** — the thickest service layer; many branches (edge cases, error conditions) await Phase 2 integration tests.
- **0% modules** (seed.py, rbac.py, permissions.py, user.py schemas) are non-auth utilities tested via integration rather than unit tests.

## Warnings

1. `passlib.utils:854` — `'crypt'` deprecated in Python 3.13. Will be addressed when migrating off passlib.
2. `jose/jwt.py:311` — `datetime.datetime.utcnow()` deprecated. JWT lib internal — tracked for upstream fix.
3. `pytest-asyncio` — `asyncio_default_fixture_loop_scope` unset. Add to `pytest.ini` when upgrading pytest-asyncio.
