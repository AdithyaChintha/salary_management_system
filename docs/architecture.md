# Architecture Notes

## Initial shape

The system starts as a single FastAPI backend, a React single-page application, and PostgreSQL. This is sufficient for the expected dataset and keeps transactional employee updates and analytics straightforward.

## Backend boundaries

The backend separates API routing, configuration, database infrastructure, schemas, services,
and repositories. The employee service owns lifecycle, validation, and salary-normalization rules,
while its repository contract isolates those rules from PostgreSQL and future HTTP handlers.
The employee API validates request shapes with Pydantic and delegates business decisions to the
service. PostgreSQL performs filtered, sorted, paginated employee listing; API errors use a stable
`error.code` and `error.message` structure.

## Frontend boundaries

The frontend reserves folders for API access, reusable components, features, pages, and test support. Feature code should remain grouped by domain rather than accumulating in the application entry point.

## Configuration

Runtime configuration comes from environment variables. Local secrets belong in the ignored root `.env` file. Browser-visible settings must use Vite's `VITE_` prefix and must never contain secrets.

## Persistence approach

PostgreSQL tables and constraints will be defined in one SQL schema script. The backend will use
parameterized `psycopg` queries directly, so no ORM model layer is required. Request validation
will live in Pydantic schemas, while PostgreSQL constraints remain the final integrity safeguard.

## Analytics

The analytics repository aggregates only active employees in PostgreSQL. Country (code or name),
department, and inclusive USD salary filters apply to every calculation. Mean and percentile
cutoffs are rounded to cents for output; band membership uses unrounded percentile cutoffs.
Band intervals are `[min, p25]`, `(p25, p50]`, `(p50, p75]`, and `(p75, max]`, so equal
salaries can make band headcounts uneven. An empty population returns zero headcount/payroll,
null salary statistics, and empty distributions. The single dashboard endpoint at
`GET /api/v1/analytics/dashboard` returns a summary, both distributions, all four pay bands,
quartile cutoffs, and salary extrema. Monetary values are JSON decimal strings, matching the
employee API and preserving cents exactly.

## Deferred decisions

- API resource contracts and error schema
- Dashboard presentation and interaction design
- Authentication and authorization (out of MVP scope)
- Production packaging and deployment
