# Design decisions, assumptions, and trade-offs

This is an assessment/demo MVP for approximately 10,000 synthetic employee records and one already-authenticated HR manager persona. The main goal is correct current-salary CRUD and understandable, consistent analytics—not payroll processing.

## Why these choices

| Choice | Why it fits this MVP | Trade-off |
| --- | --- | --- |
| PostgreSQL | Relational keys/checks enforce employee, country, currency, and department integrity. SQL can filter, sort, paginate, aggregate, and calculate percentiles near the data. | Requires a local PostgreSQL instance and credentials; the seed script cannot create the server or database. Pgvector is not used or needed. |
| Soft delete (deactivate/reactivate) | Mistakes are recoverable, and inactive employees remain inspectable while current-workforce metrics exclude them. A timestamp records when deactivation occurred. | This is current state, not a full audit trail; production needs authorization and audited changes. |
| Stored `salary_usd` | Native salary remains the business value; a normalized USD value makes cross-country salary filtering and dashboard calculations straightforward. Native and USD values are written together on salary/country edits. | Denormalized data needs recalculation if FX rates ever change. With fixed demo rates, there is no live refresh path. |
| Fixed, seeded FX rates | Makes seed data, tests, and dashboard values deterministic and avoids an external FX API dependency. Country maps to one native currency. | Rates are illustrative, not live or suitable for financial decisions. The seed upserts the configured constants; no user-facing FX editing exists. |
| Quartile pay bands | Four filtered-population bands show relative pay distribution, not just a global average; recalculating cutoffs after filtering keeps them relevant. | Ties can make band headcounts uneven, and percentile bands do not explain individual pay fairness or compensation policy. |
| No salary history | The stated MVP concerns each employee's **current** annual base salary; overwriting one snapshot keeps schema and CRUD simple. | Previous pay and effective dates cannot be recovered. Add history only when a real audit/reporting requirement is defined. |
| No auth/SSO/RBAC | The assessment assumes an already-authenticated single HR manager, so identity infrastructure would not demonstrate the core salary/analytics logic. | This is the largest production blocker: never deploy with real salary data without authentication, least-privilege authorization, and auditing. |
| No bulk ingestion | Deterministic seeding demonstrates scale; HR changes are individual UI operations. CSV/payroll import validation and error recovery would be a separate workflow. | Importing operational HR data at scale is not supported. The seed is **not** a general importer and overwrites its own seeded IDs on rerun. |
| No AI in the MVP | Defined dashboard questions can be answered deterministically and tested exactly. Natural-language access to sensitive salary data adds privacy, authorization, and accuracy risks without helping the core acceptance criteria. | Ad hoc questions must use the supported filters; any future AI layer needs scoped queries, strong access controls, and evaluation. |

## Other assumptions

- Only annual **base** salary is represented. Bonus, equity, tax, allowances, and payroll execution are excluded.
- Country and department are predefined. Role is free text. The browser's option lists mirror the seed, so they must be updated or served by an API if reference data becomes editable.
- Country determines one local currency; an employee cannot choose a different payment currency. Money uses PostgreSQL `NUMERIC` and Python `Decimal`, not binary floating point.
- The API accepts direct clients as well as the UI, so it validates currency, salary, and state transitions even if the UI already checked them.
- The dashboard reports **USD globally**. A country-filtered dashboard is still USD; a dedicated native-currency country salary view is not implemented.
- The backend uses one SQL schema script and direct psycopg queries, not ORM models or a migration framework. The seed applies `CREATE ... IF NOT EXISTS`; future schema evolution would need versioned migrations.
- Requests use a new database connection per repository operation. This is adequate for a local demo but should be measured and pooled for production traffic.
- No container/deployment configuration is supplied. `.env` is local configuration, not a secret manager.

## Out of scope

Authentication/SSO/RBAC, salary-change audit trails, effective-dated salary history, other compensation components, bulk CSV/Excel/payroll ingestion, live FX integration, AI/natural-language querying, microservices, queues, and distributed processing. These omissions are intentional MVP boundaries, not claims that the features are unnecessary in a real HR system.

## Production improvements

1. Add authentication, fine-grained salary access, audit logging, encryption/secrets management, restricted CORS, and data-retention policies before using real employee data.
2. Add versioned database migrations, connection pooling, operational health checks, backups, and monitored error/request logging.
3. Benchmark populated-database query plans; consider a trigram index or dedicated search approach for leading-wildcard name/ID search only if measurements justify it.
4. Define effective-dated salary history and a controlled FX rate version/recalculation policy if those become business requirements.
5. Serve country/department choices from reference-data endpoints if they cease to be fixed, and add the missing native-currency country view if required.
6. Add deployment/browser end-to-end tests and performance targets. The current browser click-through was not available in [Phase 10 verification](phase-10-verification.md).
