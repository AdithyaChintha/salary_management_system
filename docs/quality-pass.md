# Phase 9 quality pass

This review keeps the existing FastAPI service/repository split and React UI. Changes below are limited to observed correctness or usability issues.

| Area | Finding and change | Reason |
| --- | --- | --- |
| Employee validation and conflicts | Employee updates now include `is_active = TRUE` in the SQL `WHERE` clause. Status changes also require the opposite current state; a failed conditional write becomes the existing 409 service error. Added race-simulation unit tests. | A status change between the service's read and write could previously permit an edit of an inactive employee or repeat a transition. |
| Pagination and query consistency | The employee list's `count(*)` and page query now use one repeatable-read, read-only snapshot. | Concurrent CRUD could previously produce a total and item list from different database states. Existing `(is_active, ...)` indexes remain appropriate for common filters; no new index is justified without query-plan evidence at demo scale. |
| Request efficiency | The frontend API client sends `Content-Type: application/json` only when it sends a body. Added tests for GET and POST. | A JSON content type on GET requests can trigger avoidable CORS preflight requests. |
| Loading and pagination UX | The employee count and pagination footer show loading text while a new page is pending, instead of temporarily claiming there are zero records. | The old display was misleading when filtering or changing pages. Existing empty and retry states remain. |
| Accessibility | Sortable columns now expose `aria-sort`. The employee form focuses its first field, traps Tab focus, closes on Escape, and restores focus to its opener. Added a keyboard interaction test. | Keyboard and assistive-technology users need the same state and navigation cues as pointer users. |

## Reviewed without a change

- API response consistency: expected validation, not-found, and conflict errors already use a structured `error` body. An unexpected infrastructure exception still uses FastAPI's default 500 response; standardizing that and adding request-correlated logging are production-hardening work, not necessary to change the demo's architecture now.
- Analytics query efficiency: aggregation, percentiles, and distributions run in PostgreSQL against one repeatable-read snapshot, without transferring the workforce to Python. A query-plan benchmark on a populated database would be needed before adding more indexes. The leading-wildcard employee name/ID search will not benefit from the current B-tree name index; at the seeded scale this is acceptable.
- Validation: Pydantic request bounds, service country/currency and department checks, and database constraints cover the main invalid-input paths. Country/department options are static in the frontend, matching the demo seed data; if those become editable, serve options from the API.
- Duplication and naming: the service/repository boundary is clear. No broad refactor is justified for the small amount of repeated filter logic.
- Configuration: `.env` and `VITE_API_BASE_URL` already support local setup. The backend's default database URL is a demo convenience, not a production credential; production should require an explicit secret and restricted CORS origins.
- Logging: no application-level request/error logging was added. The backend currently relies on server logs; structured request IDs and sanitized database-error logging should be considered if deployed beyond a local demo.

## Verification

- Backend: 34 tests passed; changed Python files pass Ruff lint and format checks.
- Frontend: 15 tests passed; ESLint and production build passed. Vite reports a bundle-size advisory for the chart-heavy bundle.
- Not run: real PostgreSQL integration/query-plan tests; the current tests use service fakes and HTTP dependency overrides. Two backend dependency deprecation warnings and repository-wide pre-existing format findings remain.
