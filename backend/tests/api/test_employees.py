import pytest
from fastapi.testclient import TestClient

from app.services.employee import EmployeeService
from tests.unit.test_employee_service import FakeEmployeeRepository


@pytest.fixture
def employee_client() -> TestClient:
    from app.api.employees import get_employee_service
    from app.main import app

    repository = FakeEmployeeRepository()
    app.dependency_overrides[get_employee_service] = lambda: EmployeeService(repository)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def employee_payload() -> dict[str, object]:
    return {
        "employee_id": "EMP-001",
        "name": "Rahul Sharma",
        "country": "IN",
        "department": "Engineering",
        "role": "Software Engineer",
        "annual_salary_native": "5000000.00",
        "currency": "INR",
    }


def test_employee_lifecycle(employee_client: TestClient) -> None:
    created = employee_client.post("/api/v1/employees", json=employee_payload())
    assert created.status_code == 201
    assert created.json()["salary_usd"] == "60000.00"

    fetched = employee_client.get("/api/v1/employees/EMP-001")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Rahul Sharma"

    updated = employee_client.patch("/api/v1/employees/EMP-001", json={"name": "Rahul S"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Rahul S"

    deactivated = employee_client.post("/api/v1/employees/EMP-001/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert deactivated.json()["deactivated_at"] is not None

    blocked = employee_client.patch("/api/v1/employees/EMP-001", json={"name": "X"})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "inactive_employee"

    reactivated = employee_client.post("/api/v1/employees/EMP-001/reactivate")
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True
    assert reactivated.json()["deactivated_at"] is None


def test_conflicts_and_validation(employee_client: TestClient) -> None:
    payload = employee_payload()
    assert employee_client.post("/api/v1/employees", json=payload).status_code == 201
    duplicate = employee_client.post("/api/v1/employees", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_employee_id"

    missing = employee_client.get("/api/v1/employees/MISSING")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "employee_not_found"

    bad_currency = employee_client.post(
        "/api/v1/employees", json={**payload, "employee_id": "EMP-002", "currency": "USD"}
    )
    assert bad_currency.status_code == 422
    assert bad_currency.json()["error"]["code"] == "invalid_country_currency"

    bad_department = employee_client.post(
        "/api/v1/employees",
        json={**payload, "employee_id": "EMP-004", "department": "Unknown"},
    )
    assert bad_department.status_code == 422
    assert bad_department.json()["error"]["code"] == "invalid_employee"

    bad_salary = employee_client.post(
        "/api/v1/employees", json={**payload, "employee_id": "EMP-003", "annual_salary_native": -1}
    )
    assert bad_salary.status_code == 422


def test_list_filters_and_pagination(employee_client: TestClient) -> None:
    for number, name in enumerate(("Rahul Sharma", "Rahul Patel", "Anita Rao"), 1):
        payload = {**employee_payload(), "employee_id": f"EMP-{number:03d}", "name": name}
        assert employee_client.post("/api/v1/employees", json=payload).status_code == 201

    response = employee_client.get(
        "/api/v1/employees",
        params={
            "search": "rahul",
            "country": "India",
            "department": "Engineering",
            "min_salary_usd": 40000,
            "max_salary_usd": 90000,
            "page": 1,
            "page_size": 1,
            "sort_by": "name",
            "sort_order": "asc",
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["page_size"] == 1
    assert response.json()["items"][0]["name"] == "Rahul Patel"

    invalid = employee_client.get("/api/v1/employees", params={"page_size": 101})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    reversed_range = employee_client.get(
        "/api/v1/employees",
        params={"min_salary_usd": 90000, "max_salary_usd": 40000},
    )
    assert reversed_range.status_code == 422
    assert reversed_range.json()["error"]["code"] == "invalid_employee"

    employee_client.post("/api/v1/employees/EMP-001/deactivate")
    inactive = employee_client.get("/api/v1/employees", params={"is_active": "false"})
    assert inactive.status_code == 200
    assert [item["employee_id"] for item in inactive.json()["items"]] == ["EMP-001"]


def test_country_department_sort_and_100_row_page(employee_client: TestClient) -> None:
    for employee_id, country, department in (
        ("EMP-001", "US", "Finance"),
        ("EMP-002", "IN", "Engineering"),
        ("EMP-003", "US", "Engineering"),
    ):
        response = employee_client.post(
            "/api/v1/employees",
            json={
                **employee_payload(),
                "employee_id": employee_id,
                "country": country,
                "currency": "USD" if country == "US" else "INR",
                "department": department,
            },
        )
        assert response.status_code == 201

    by_country = employee_client.get(
        "/api/v1/employees", params={"sort_by": "country", "page_size": 100}
    )
    assert by_country.status_code == 200
    assert by_country.json()["page_size"] == 100
    assert [item["employee_id"] for item in by_country.json()["items"]] == [
        "EMP-002",
        "EMP-001",
        "EMP-003",
    ]

    by_department = employee_client.get(
        "/api/v1/employees", params={"sort_by": "department", "sort_order": "desc"}
    )
    assert [item["department"] for item in by_department.json()["items"]] == [
        "Finance",
        "Engineering",
        "Engineering",
    ]


def test_unexpected_api_error_is_structured_without_leaking_details() -> None:
    from app.api.employees import get_employee_service
    from app.main import app

    def broken_service():
        raise RuntimeError("private database detail")

    app.dependency_overrides[get_employee_service] = broken_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/employees/EMP-001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Unexpected server error"}
    }
