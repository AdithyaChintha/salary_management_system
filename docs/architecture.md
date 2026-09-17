# Architecture

The app has one React single-page frontend, one FastAPI backend, and one PostgreSQL database. This is enough for the approximately 10,000-record demo and keeps employee writes transactional and analytics queryable without distributed infrastructure.

## Request path

The frontend calls `/api/v1` through `frontend/src/api/`. FastAPI routes in `backend/app/api/` parse Pydantic request schemas, delegate to services, and return response schemas. Services in `backend/app/services/` own business rules. Repositories in `backend/app/repositories/` own parameterized SQL. The schema in `backend/app/db/schema.sql` supplies keys, relationships, checks, and indexes; `backend/scripts/seed.py` applies it and loads deterministic demo data.

Employee creation validates a unique business ID, predefined country/currency and department, and positive native salary. The service calculates USD salary from the configured fixed FX rate and writes both monetary values in one database statement. A database uniqueness constraint closes a race with concurrent creates. Update and status-transition SQL also guard the current active state, closing read/write races around deactivation. `employees.id` is the internal primary key; `employee_id` is the immutable, user-facing unique key.

Employee listing filters and paginates in PostgreSQL. Its count and page queries share a repeatable-read snapshot, so a concurrent update cannot produce a mismatched total and row set. Sorting uses a fixed allowlist, not raw client SQL. B-tree indexes cover common active/country/department/salary access paths. Leading-wildcard name/ID search is simple at this demo scale but is not optimized by the name B-tree index.

Analytics aggregate active employees in PostgreSQL rather than transferring all rows to Python. Country, department, and inclusive normalized-USD salary filters apply to the same snapshot for summary, distributions, and pay bands. Quartile cutoffs are computed for that filtered population. Pay-band membership uses unrounded database cutoffs; displayed amounts are rounded to cents. Equal salaries can make the four band headcounts uneven. Empty results return zero headcount/payroll and null salary statistics.

## Frontend and configuration

`frontend/src/App.tsx` owns the employee directory state; `Dashboard.tsx` owns dashboard filters and displays; `EmployeeForm.tsx` owns the create/edit form. Requests are server-driven. Country and department options currently mirror seeded reference data, so changing the reference tables alone will not update those dropdowns.

The backend reads the root `.env` using Pydantic settings. The browser uses Vite's `VITE_API_BASE_URL`. Only `VITE_` variables should hold browser-visible values. The default CORS origin is `http://localhost:5173`; it must match the actual frontend origin.

The process health endpoint does not verify database connectivity. No connection pool, authentication, audit trail, or salary history is included in this MVP. See [Design decisions](design-decisions.md) for why, and [Phase 10 verification](phase-10-verification.md) for tested versus uncovered behavior.
