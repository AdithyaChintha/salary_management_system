# Architecture Notes

## Initial shape

The system starts as a single FastAPI backend, a React single-page application, and PostgreSQL. This is sufficient for the expected dataset and keeps transactional employee updates and analytics straightforward.

## Backend boundaries

The backend package reserves separate areas for API routing, configuration, database infrastructure, schemas, services, and repositories. These packages are intentionally empty until their business contracts are designed.

## Frontend boundaries

The frontend reserves folders for API access, reusable components, features, pages, and test support. Feature code should remain grouped by domain rather than accumulating in the application entry point.

## Configuration

Runtime configuration comes from environment variables. Local secrets belong in the ignored root `.env` file. Browser-visible settings must use Vite's `VITE_` prefix and must never contain secrets.

## Persistence approach

PostgreSQL tables and constraints will be defined in one SQL schema script. The backend will use
parameterized `psycopg` queries directly, so no ORM model layer is required. Request validation
will live in Pydantic schemas, while PostgreSQL constraints remain the final integrity safeguard.

## Deferred decisions

- API resource contracts and error schema
- Analytics query design
- Authentication and authorization (out of MVP scope)
- Production packaging and deployment
