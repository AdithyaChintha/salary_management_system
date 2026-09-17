"""HTTP smoke flow against real PostgreSQL, isolated from the seeded demo records."""

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from app.api.analytics import get_analytics_service
from app.api.employees import get_employee_service
from app.core.config import settings
from app.main import app
from app.repositories.postgres_analytics import PostgresAnalyticsRepository
from app.repositories.postgres_employee import PostgresEmployeeRepository
from app.services.analytics import AnalyticsService
from app.services.employee import EmployeeService

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "app" / "db" / "schema.sql"


@pytest.fixture
def live_client():
    try:
        connection = psycopg.connect(settings.database_url, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is unavailable for live smoke test")

    schema = f"salary_smoke_{uuid4().hex}"
    scratch_url = psycopg.conninfo.make_conninfo(
        settings.database_url, options=f"-csearch_path={schema}"
    )
    try:
        with connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        with psycopg.connect(scratch_url) as scratch:
            scratch.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
            scratch.execute("INSERT INTO fx_rates VALUES ('USD', 1), ('INR', 0.012)")
            scratch.execute(
                "INSERT INTO countries (code, name, currency) VALUES "
                "('US', 'United States', 'USD'), ('IN', 'India', 'INR')"
            )
            scratch.execute("INSERT INTO departments VALUES ('Engineering'), ('Finance')")

        app.dependency_overrides[get_employee_service] = lambda: EmployeeService(
            PostgresEmployeeRepository(scratch_url)
        )
        app.dependency_overrides[get_analytics_service] = lambda: AnalyticsService(
            PostgresAnalyticsRepository(scratch_url)
        )
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        # Only the uniquely named schema created by this fixture is removed.
        with psycopg.connect(settings.database_url) as cleanup:
            cleanup.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema))
            )
        connection.close()


def payload(employee_id: str, *, country: str = "IN", department: str = "Engineering"):
    return {
        "employee_id": employee_id,
        "name": "Smoke Employee",
        "country": country,
        "department": department,
        "role": "Engineer",
        "annual_salary_native": "1000000.00" if country == "IN" else "50000.00",
        "currency": "INR" if country == "IN" else "USD",
    }


def test_employee_and_dashboard_smoke_flow(live_client: TestClient) -> None:
    base = "/api/v1"
    for employee_id, country, department in (
        ("SMOKE-001", "IN", "Engineering"),
        ("SMOKE-002", "US", "Finance"),
        ("SMOKE-003", "US", "Engineering"),
    ):
        created = live_client.post(
            f"{base}/employees", json=payload(employee_id, country=country, department=department)
        )
        assert created.status_code == 201, created.text

    search = live_client.get(f"{base}/employees", params={"search": "SMOKE-001"})
    assert search.status_code == 200
    assert [item["employee_id"] for item in search.json()["items"]] == ["SMOKE-001"]

    updated = live_client.patch(
        f"{base}/employees/SMOKE-001", json={"annual_salary_native": "2000000.00"}
    )
    assert updated.status_code == 200
    assert updated.json()["salary_usd"] == "24000.00"
    assert updated.json()["annual_salary_native"] == "2000000.00"

    before = live_client.get(f"{base}/analytics/dashboard").json()["summary"]
    assert before["headcount"] == 3
    assert Decimal(before["total_payroll_usd"]) == Decimal("124000.00")

    deactivated = live_client.post(f"{base}/employees/SMOKE-001/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    after = live_client.get(f"{base}/analytics/dashboard").json()["summary"]
    assert after["headcount"] == 2
    assert Decimal(after["total_payroll_usd"]) == Decimal("100000.00")

    reactivated = live_client.post(f"{base}/employees/SMOKE-001/reactivate")
    assert reactivated.status_code == 200
    assert live_client.get(f"{base}/analytics/dashboard").json()["summary"] == before

    filtered = live_client.get(
        f"{base}/analytics/dashboard", params={"country": "India", "min_salary_usd": 20000}
    ).json()
    assert filtered["summary"]["headcount"] == 1
    assert filtered["summary"]["total_payroll_usd"] == "24000.00"
    assert filtered["by_country"] == [{"name": "India", "headcount": 1}]

    page = live_client.get(f"{base}/employees", params={"page": 2, "page_size": 1})
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 1
    assert page.json()["items"][0]["employee_id"] == "SMOKE-002"

    duplicate = live_client.post(f"{base}/employees", json=payload("SMOKE-001"))
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_employee_id"

    invalid = live_client.post(
        f"{base}/employees", json={**payload("SMOKE-BAD"), "annual_salary_native": "-1"}
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
