# Project history

Dated reports kept because they explain **why** the current code looks the way it does: security incidents, design decisions and the fixes that followed. They are snapshots. Test counts, file paths and links in them describe the project on the date in the file name, and some files they mention have since moved or been removed.

| Report | What it records |
|---|---|
| [QA_REPORT_2026-10-16.md](QA_REPORT_2026-10-16.md) | First full QA and stabilization pass: 29 fixes, including authentication, RBAC and configuration safety |
| [PRODUCTION_READINESS_2026-10-16.md](PRODUCTION_READINESS_2026-10-16.md) | Why the production-like stack (`docker-compose.prod.yml`) exists and how it differs from development |
| [PRODUCT_ACCESS_AND_ISOLATION_2026-10-16.md](PRODUCT_ACCESS_AND_ISOLATION_2026-10-16.md) | The decision that every user gets the full product on their own data, and the per-user isolation model |
| [ISOLATION_INCIDENT_2026-10-18.md](ISOLATION_INCIDENT_2026-10-18.md) | Incident: another user's data shown after switching accounts in one browser tab. Root cause (shared frontend cache) and fix |

Reports from an early AI-assisted session (October 2026) were removed from the tree because several of their claims proved inaccurate. They remain in the Git history.

For the current state, use [../FEATURE_INVENTORY.md](../FEATURE_INVENTORY.md), [../SECURITY_AND_PRIVACY.md](../SECURITY_AND_PRIVACY.md) and [../TESTING_AND_RELEASE.md](../TESTING_AND_RELEASE.md).
