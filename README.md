# Salary Management System

An internal demo for managing current employee base salaries across countries and viewing active-workforce analytics. The backend is FastAPI + PostgreSQL; the frontend is React + TypeScript. It assumes a single, already-authenticated HR manager and is **not** production-ready for confidential payroll data.

## Quick start

Prerequisites: Python 3.12+, Node.js 20+, a running PostgreSQL server, and a PostgreSQL role allowed to create tables in a database. PostgreSQL 16+ is the intended version. Docker is not required.

1. Create a PostgreSQL role and an empty database. For example, in `psql` as a PostgreSQL administrator (replace the placeholder password):

   ```sql
   CREATE ROLE salary_user LOGIN PASSWORD 'choose-a-local-password';
   CREATE DATABASE salary_management OWNER salary_user;
   ```

   If your role/database already exist, skip this step. The seed script creates **tables inside an existing database**; it cannot create the PostgreSQL server, role, or database.

2. In the repository root, copy `.env.example` to `.env` and set `DATABASE_URL` to the role, password, host, port, and database you actually created. In PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

   Example value: `DATABASE_URL=postgresql://salary_user:choose-a-local-password@localhost:5432/salary_management`. URL-encode real passwords containing characters such as `@`, `:`, or `/`. Keep `.env` private; only `VITE_` variables are exposed to browser code. The backend accepts either `postgresql://` or `postgresql+psycopg://`.

3. Install and seed the backend:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -e ".[dev]"
   python -m scripts.seed
   uvicorn app.main:app --reload
   ```

   On macOS/Linux, activate with `source .venv/bin/activate`. Run subsequent commands from `backend/`. The API is at `http://localhost:8000`, with OpenAPI docs at `http://localhost:8000/docs` and a process health check at `/api/v1/health` (not a database health check).

4. In a second terminal, start the frontend:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

   Open `http://localhost:5173`. The frontend calls `http://localhost:8000/api/v1` by default. If you change that URL, set `VITE_API_BASE_URL` before starting Vite; if you change the frontend origin, update `CORS_ORIGINS` in `.env` too.

### Seeding safely

`python -m scripts.seed` executes [the schema](backend/app/db/schema.sql), loads fixed reference data, and deterministically upserts 10,000 employees with IDs `EMP-00001` through `EMP-10000`. It does not duplicate those IDs. **Rerunning it overwrites edits and active status for those seeded IDs.** Manually created employees with other IDs are retained by a normal rerun. It also restores the seeded FX rates, country mappings, and departments.

`python -m scripts.seed --reset` first truncates the entire `employees` table and then reloads the seeded employees. **This deletes manually created employees too; use it only on disposable demo data.** The seed command accepts `--database-url` to target a different existing database explicitly.

## Tests and verification

From `backend/`, with the development dependencies installed:

```powershell
python -m pytest tests/unit -q
python -m pytest tests/integration tests/api -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

The PostgreSQL integration tests require a reachable `DATABASE_URL`; they skip when PostgreSQL is unavailable. The employee smoke test uses a uniquely named temporary schema and cleans it up, leaving seeded records untouched. Unit and employee API tests use controlled fakes; dashboard API tests use PostgreSQL temporary-table fixtures. Ruff's repository-wide checks currently report a few pre-existing formatting/import findings; see [the quality pass](docs/quality-pass.md).

From `frontend/`:

```powershell
npm test
npm run lint
npm run format:check
npm run build
```

Frontend tests use mocked API responses. The latest structured verification, including real-database lifecycle checks and uncovered items, is in [Phase 10 verification](docs/phase-10-verification.md).

## What is implemented

- Employee creation, lookup, editing, deactivation, reactivation, search, filters, sorting, and server-side pagination (10/25/50/100 rows).
- Native-currency annual salary plus stored, normalized USD salary. Country determines currency; the employee ID is immutable after creation.
- Active-workforce dashboard with payroll, headcount, average/median/extreme salaries, country/department distributions, and filtered-population quartile pay bands.
- Validation in the request schema and service, with PostgreSQL constraints as the final safeguard. Expected errors use a structured JSON body.

For component boundaries and data flow, see [Architecture](docs/architecture.md). For endpoint details, see [API overview](docs/api.md). For the rationale, assumptions, limitations, and future work, see [Design decisions](docs/design-decisions.md).
