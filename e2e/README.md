# End-to-end tests (real browser + real API)

These scripts drive the **running** application in Google Chrome (via
`playwright-core`, using the Chrome already installed on the machine) and
call the real API. They are not part of `pytest`/`vitest`.

## Setup (once)

```powershell
cd e2e
npm install
```

## Run (with the development stack up: `docker compose up -d`)

| Command | What it checks |
|---|---|
| `$env:BASE="http://localhost:5173"; npm run isolation` | Two new users + admin in one tab: no cross-user data on any page, API probes with the other user's IDs, sharing, cross-tab switching |
| `$env:BASE="http://localhost:5173"; npm run cleaning` | Cleaning operations, preview, confirmation, versions, restore, executable rules |
| `$env:BASE="http://localhost:5173"; npm run new-user` | Complete first-time user workflow (register → upload → scan → clean → download → delete) |
| `npm run sweep` | Calls every GET endpoint in the OpenAPI schema as user B with user A's IDs (needs the dev backend on 127.0.0.1:8000) |
| `$env:BASE="http://localhost:5173"; npm run dark` | Dark-theme contrast audit of 32 pages and dialogs |

Each script prints `PASS`/`FAIL` lines. Scripts that log in as the admin
read `INIT_ADMIN_EMAIL`/`INIT_ADMIN_PASSWORD` from `../.env` (never printed).

**Notes**
- Every run registers new `qa.*@example.com` test accounts and datasets.
  Each run uses a fresh random password that is never stored or printed, so
  nobody can sign in to those accounts afterwards. They still clutter the
  database; deactivate them (Users page) before inviting external testers.
- Never put a fixed password in these scripts: anything committed here is
  readable by everyone who can read the repository and its history.
- Login is rate limited (10/minute). Running several suites back to back
  can hit the limit; the scripts wait and retry, or wait a minute between suites.
- `BASE` defaults to `http://localhost` (nginx).
