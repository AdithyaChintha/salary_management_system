# API overview

Base URL: `http://localhost:8000/api/v1`. FastAPI's interactive OpenAPI reference is at `http://localhost:8000/docs`. There is no authentication in this demo; do not expose it to an untrusted network or use real payroll records.

| Method and path | Purpose |
| --- | --- |
| `GET /health` | Process liveness only; does not check PostgreSQL. |
| `POST /employees` | Create an employee; returns 201. |
| `GET /employees` | Search, filter, sort, and paginate employees. |
| `GET /employees/{employee_id}` | Fetch one employee by business ID. |
| `PATCH /employees/{employee_id}` | Update fields and recalculate stored USD salary. Inactive employees cannot be edited. |
| `POST /employees/{employee_id}/deactivate` | Soft-delete by setting inactive state and timestamp. |
| `POST /employees/{employee_id}/reactivate` | Restore the same record to active. |
| `GET /analytics/dashboard` | Return all dashboard metrics for one active, filtered population. |

## Employees

Create body example:

```json
{
  "employee_id": "HR-10001",
  "name": "Rahul Sharma",
  "country": "IN",
  "department": "Engineering",
  "role": "Software Engineer",
  "annual_salary_native": "2000000.00",
  "currency": "INR"
}
```

`country` is a configured two-letter code, and `currency` must match its configured three-letter native currency. The UI derives currency from country; a direct API caller still supplies it so the backend can validate the mapping. Departments are predefined; role is free text. Salary must be positive. `employee_id` is unique and cannot be changed by PATCH. The response adds internal `id`, `salary_usd`, `is_active`, `deactivated_at`, `created_at`, and `updated_at`. Monetary values are serialized as decimal strings to preserve cents.

PATCH accepts any subset of `name`, `country`, `department`, `role`, `annual_salary_native`, and `currency`. If country changes, supply the matching currency in the same request. For example:

```json
{ "annual_salary_native": "2500000.00" }
```

The backend computes USD using the seeded rate and stores native and USD values in the same SQL update. The current salary is overwritten; there is no salary history.

List query parameters:

| Parameter | Behavior |
| --- | --- |
| `search` | Case-insensitive substring search over name or employee ID. |
| `country` | Country code or name, case-insensitive exact match. |
| `department` | Exact department name. |
| `is_active` | `true` or `false`; omit for both statuses. The **UI** defaults to active-only, while a bare API request returns both. |
| `min_salary_usd`, `max_salary_usd` | Inclusive normalized-USD bounds; minimum cannot exceed maximum. |
| `page` | One-based page number; default 1. |
| `page_size` | 1–100; API default 25. The UI offers 10, 25, 50, and 100. |
| `sort_by` | `name` (default), `employee_id`, `salary_usd`, `country`, `department`, or `created_at`. |
| `sort_order` | `asc` (default) or `desc`. |

Example: `GET /employees?search=rahul&country=India&department=Engineering&min_salary_usd=40000&max_salary_usd=90000&page=1&page_size=25&sort_by=name&sort_order=asc`. The response has `items`, `total`, `page`, and `page_size`. Page count is `ceil(total / page_size)`; an out-of-range page returns an empty `items` array rather than an error.

## Dashboard

`GET /analytics/dashboard` accepts optional `country`, `department`, `min_salary_usd`, and `max_salary_usd` filters. All metrics exclude inactive employees and use the same filtered population. Country accepts a code or name; salary bounds are inclusive and in normalized USD.

Response sections are `summary` (`headcount`, `total_payroll_usd`, `average_salary_usd`, `median_salary_usd`), `by_country`, `by_department`, `pay_bands`, `quartile_cutoffs_usd`, `highest_salary_usd`, and `lowest_salary_usd`. Each distribution has `name` and `headcount`. Each pay band has `label` (`p0_p25`, `p25_p50`, `p50_p75`, `p75_p100`), `lower_usd`, `upper_usd`, and `headcount`. Quartiles are recalculated for every filter set. Equal salaries may produce uneven band counts. For an empty selection, headcount/payroll are zero, distributions are empty, and salary statistics are null.

This is a global USD-reporting endpoint, even when filtered to one country. A separate native-currency country salary view is not implemented; see [Phase 10 verification](phase-10-verification.md).

## Errors

Expected failures return a JSON `error` object with `code` and `message`; request-shape errors can also include `details` with field locations. Examples:

```json
{ "error": { "code": "duplicate_employee_id", "message": "HR-10001" } }
```

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request",
    "details": [{ "location": ["body", "annual_salary_native"], "message": "...", "type": "..." }]
  }
}
```

Typical statuses: 404 for missing employee, 409 for duplicate ID/inactive edit/invalid status transition, 422 for invalid request or business validation, and 500 for unexpected server errors. Unexpected errors are logged server-side and return a generic message without internal exception details.
