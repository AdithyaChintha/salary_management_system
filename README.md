# Salary Management System

Repository skeleton for an internal salary management application. Business features are intentionally not implemented yet.

## Stack

- Backend: Python 3.12, FastAPI, psycopg, PostgreSQL
- Frontend: React 18, TypeScript, Vite, Recharts
- Tests: Pytest, Vitest, React Testing Library
- Quality: Ruff for Python; ESLint and Prettier for TypeScript

## Repository layout

```text
backend/   FastAPI application, database infrastructure, and tests
frontend/  React/TypeScript application and component tests
docs/      Architecture and development notes
```

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+

Docker is not included in this initial scaffold. The application connects to any PostgreSQL instance configured through `DATABASE_URL`.

## Environment setup

Copy `.env.example` to `.env` and adjust the values for your machine. Do not commit `.env`.

## Backend setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`; interactive documentation is available at `/docs`.

Backend checks:

```bash
ruff check .
ruff format --check .
pytest
```

## Database and deterministic seed data

Create an empty PostgreSQL database, configure `DATABASE_URL` in the root `.env`, and run:

```bash
cd backend
python -m scripts.seed
```

The command creates the schema if needed and upserts the same 10,000 employees on every run.
It does not duplicate seed employees. To deliberately remove every employee before reseeding:

```bash
python -m scripts.seed --reset
```

`--reset` is destructive to the `employees` table and should only be used for local/demo data.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

Frontend checks:

```bash
npm run lint
npm run format:check
npm test
npm run build
```

## Current scope

The project includes a single PostgreSQL schema script and deterministic demo data for 10,000
employees. The employee service and PostgreSQL repository implement employee lifecycle and
salary normalization. Employee CRUD and paginated search are available under `/api/v1/employees`.
Analytics remain unimplemented.
