import pytest
from fastapi.testclient import TestClient

from app.api.analytics import get_analytics_service
from app.main import app
from app.services.analytics import AnalyticsService

pytest_plugins = ["tests.integration.test_analytics"]


@pytest.fixture
def dashboard_client(analytics_service: AnalyticsService) -> TestClient:
    app.dependency_overrides[get_analytics_service] = lambda: analytics_service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_dashboard_matches_controlled_workforce(dashboard_client: TestClient) -> None:
    response = dashboard_client.get("/api/v1/analytics/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == {
        "headcount": 8,
        "total_payroll_usd": "360.00",
        "average_salary_usd": "45.00",
        "median_salary_usd": "45.00",
    }
    assert data["highest_salary_usd"] == "80.00"
    assert data["lowest_salary_usd"] == "10.00"
    assert data["quartile_cutoffs_usd"] == ["27.50", "45.00", "62.50"]
    assert data["by_country"] == [
        {"name": "India", "headcount": 4},
        {"name": "United States", "headcount": 4},
    ]
    assert data["by_department"] == [
        {"name": "Engineering", "headcount": 5},
        {"name": "Finance", "headcount": 3},
    ]
    assert [band["headcount"] for band in data["pay_bands"]] == [2, 2, 2, 2]


def test_dashboard_applies_same_filters_to_all_metrics(dashboard_client: TestClient) -> None:
    response = dashboard_client.get(
        "/api/v1/analytics/dashboard",
        params={
            "country": "India",
            "department": "Engineering",
            "min_salary_usd": 20,
            "max_salary_usd": 30,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == {
        "headcount": 2,
        "total_payroll_usd": "50.00",
        "average_salary_usd": "25.00",
        "median_salary_usd": "25.00",
    }
    assert data["lowest_salary_usd"] == "20.00"
    assert data["highest_salary_usd"] == "30.00"
    assert data["quartile_cutoffs_usd"] == ["22.50", "25.00", "27.50"]
    assert data["by_country"] == [{"name": "India", "headcount": 2}]
    assert data["by_department"] == [{"name": "Engineering", "headcount": 2}]
    assert sum(band["headcount"] for band in data["pay_bands"]) == 2


def test_dashboard_empty_population_and_invalid_filters(dashboard_client: TestClient) -> None:
    empty = dashboard_client.get("/api/v1/analytics/dashboard", params={"department": "Missing"})
    assert empty.status_code == 200
    assert empty.json()["summary"] == {
        "headcount": 0,
        "total_payroll_usd": "0.00",
        "average_salary_usd": None,
        "median_salary_usd": None,
    }
    assert empty.json()["by_country"] == []
    assert empty.json()["pay_bands"][0]["headcount"] == 0

    bad_range = dashboard_client.get(
        "/api/v1/analytics/dashboard",
        params={"min_salary_usd": 50, "max_salary_usd": 10},
    )
    assert bad_range.status_code == 422
    assert bad_range.json()["error"]["code"] == "invalid_analytics_filters"

    malformed = dashboard_client.get(
        "/api/v1/analytics/dashboard", params={"min_salary_usd": "not-a-number"}
    )
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "validation_error"
