# Incident 2026-10-18 — Other users' data shown after switching accounts

## Symptom

A regular user on `http://localhost:5173` saw other people's data in four places:
- datasets ("QA kunder…", "QA accuracy…", "QA mgr data…");
- quality rules;
- monitoring counts;
- governance assignments.

## Root cause (verified at runtime)

**The frontend kept one React Query cache for every identity.** The backend's scoping was not at fault.

- **The cache was shared across accounts.** Query keys such as `['all-datasets']`, `['data-quality-rules']`, `['data-quality-metrics']` and `['governance-assignments']` are not user-specific. Logging out never cleared the cache, and `staleTime` is 5 minutes. So after one account signed out and another signed in on the same tab, every page was served from the previous account's cache, **without a single API request**.
- **Reproduced in Chrome:** the super admin browsed the four pages, logged out via the menu, and a freshly registered user logged in. That user saw the admin's 10 datasets, 192 rules and the admin's assignments, and the network log showed zero API calls after the switch.
- **The backend was correct.** The listing services, evaluated for the affected accounts (`qasem40@…`, `aliqassem404040@…`), returned 0 datasets, rules, assignments, policies and domains.
- **The login history fits.** The super admin and regular accounts had been used alternately in the same browser (refresh tokens keep a session for 7 days).

## Fix

- `frontend/src/query/IdentityScopedQueryProvider.tsx` (new) gives every signed-in identity, and "signed out", its own `QueryClient`. On any identity change it:
  - clears the old client;
  - creates a new one;
  - remounts the tree, so components keeping fetched data in local state refetch too.
- **Identity changes covered:** login, logout, a failed token refresh, and a switch made in another tab (the auth store re-hydrates on the `storage` event).
- **In-flight requests:** late responses to the previous identity's requests land in the discarded client.
- `query/client.ts` now exports `createQueryClient()` instead of a single shared instance; `App.tsx` uses the new provider.
- `LoginPageModern.tsx`: an already-authenticated visitor (e.g. after signing in in another tab) is redirected to the dashboard instead of being shown the form.
- `DataQualityMonitoringPage.tsx` showed made-up values for users without data: "Hälsopoäng 0%" and "Frisk" for checks that never ran. It now:
  - shows an empty state with the next action;
  - uses the dashboard's health definition ("—" until something is scanned), where the old run-based pass rate read 0% for every real user;
  - shows "Ingen data" for dimensions without checks;
  - translates dimension names.
- `governance/assignable-users` (exact-email sharing lookup) now returns only `id` and `email`, not the person's full name.

No database or migration changes; nothing was deleted.

## Verification

| Check | Result |
|---|---|
| Original reproduction, re-run on :5173 | After the switch: fresh requests return 0 items; empty states on all four pages |
| Two-user browser test (:5173), one tab admin → A → B → admin with client-side navigation, plus reload, direct URLs, 17 cross-user API probes per direction, lists/search/issues/audit/dashboard, sharing by email, cross-tab switch, admin user management, dark-theme audit | **24/24** |
| Every GET endpoint in the OpenAPI schema called as user B with user A's IDs | **55 endpoints, 0 leaks** (only the deliberate exact-email lookup matches) |
| Admin and session workflow (browser) | 18/18 |
| Dark-theme audit, 32 views (:5173) | 0 problems |
| Backend suite | 103 passed |
| Frontend: `tsc`, `vitest` (incl. new `IdentityScopedQueryProvider.test.tsx`), `npm run build` | OK / 15 passed / OK |
| Mutation check: provider reverted to one shared client | the new test fails |

## Notes

- The production image (`docker-compose.prod.yml`) was not rebuilt in this pass. Run `docker compose -f docker-compose.prod.yml up -d --build` the next time you use it.
- Browser tests created more test accounts (`qa.switch.*`, `qa.iso.*`, `qa.sweep.*` @example.com). Deactivate them under Användare before external testing.
