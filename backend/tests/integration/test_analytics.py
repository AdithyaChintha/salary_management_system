from decimal import Decimal

import psycopg
import pytest

from app.core.config import settings
from app.repositories.analytics import AnalyticsFilters, Distribution
from app.repositories.postgres_analytics import PostgresAnalyticsRepository
from app.services.analytics import AnalyticsService


@pytest.fixture
def analytics_service(monkeypatch: pytest.MonkeyPatch) -> AnalyticsService:
    try:
        with psycopg.connect(settings.database_url) as probe:
            probe.execute("SELECT 1")
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is unavailable for analytics integration tests")

    original_connect = psycopg.connect

    def fixture_connection(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connection.execute("CREATE TEMP TABLE countries (code text, name text)")
        connection.execute(
            "CREATE TEMP TABLE employees (country text, department text, "
            "salary_usd numeric(18,2), is_active boolean)"
        )
        connection.execute(
            "INSERT INTO countries (code, name) VALUES ('IN', 'India'), ('US', 'United States')"
        )
        rows = [
            ("IN", "Engineering", 10, True),
            ("IN", "Engineering", 20, True),
            ("IN", "Engineering", 30, True),
            ("IN", "Finance", 40, True),
            ("US", "Engineering", 50, True),
            ("US", "Engineering", 60, True),
            ("US", "Finance", 70, True),
            ("US", "Finance", 80, True),
            ("IN", "Engineering", 1000, False),
        ]
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO employees (country, department, salary_usd, is_active) "
                "VALUES (%s, %s, %s, %s)",
                rows,
            )
        connection.commit()
        return connection

    monkeypatch.setattr("app.repositories.postgres_analytics.psycopg.connect", fixture_connection)
    return AnalyticsService(PostgresAnalyticsRepository(settings.database_url))


def test_global_analytics_exclude_inactive_and_calculate_quartiles(
    analytics_service: AnalyticsService,
) -> None:
    result = analytics_service.calculate()

    assert result.active_headcount == 8
    assert result.total_payroll_usd == Decimal("360.00")
    assert result.average_salary_usd == Decimal("45.00")
    assert result.median_salary_usd == Decimal("45.00")
    assert result.lowest_salary_usd == Decimal("10.00")
    assert result.highest_salary_usd == Decimal("80.00")
    assert result.quartile_cutoffs_usd == (Decimal("27.50"), Decimal("45.00"), Decimal("62.50"))
    assert [band.headcount for band in result.percentile_pay_bands] == [2, 2, 2, 2]
    assert result.department_distribution == [
        Distribution("Engineering", 5),
        Distribution("Finance", 3),
    ]
    assert result.country_distribution == [
        Distribution("India", 4),
        Distribution("United States", 4),
    ]


def test_filters_recalculate_every_metric_from_matching_population(
    analytics_service: AnalyticsService,
) -> None:
    result = analytics_service.calculate(
        AnalyticsFilters(
            country="India", min_salary_usd=Decimal("20"), max_salary_usd=Decimal("40")
        )
    )

    assert result.active_headcount == 3
    assert result.total_payroll_usd == Decimal("90.00")
    assert result.average_salary_usd == Decimal("30.00")
    assert result.median_salary_usd == Decimal("30.00")
    assert result.quartile_cutoffs_usd == (Decimal("25.00"), Decimal("30.00"), Decimal("35.00"))
    assert sum(band.headcount for band in result.percentile_pay_bands) == 3
    assert result.country_distribution == [Distribution("India", 3)]
    assert result.department_distribution == [
        Distribution("Engineering", 2),
        Distribution("Finance", 1),
    ]


def test_empty_population_has_zero_totals_and_null_salary_statistics(
    analytics_service: AnalyticsService,
) -> None:
    result = analytics_service.calculate(AnalyticsFilters(department="Missing"))

    assert result.active_headcount == 0
    assert result.total_payroll_usd == Decimal("0.00")
    assert result.average_salary_usd is None
    assert result.median_salary_usd is None
    assert result.highest_salary_usd is None
    assert result.lowest_salary_usd is None
    assert result.quartile_cutoffs_usd == (None, None, None)
    assert all(band.headcount == 0 for band in result.percentile_pay_bands)
    assert result.country_distribution == []
    assert result.department_distribution == []


def test_country_and_salary_filters_recalculate_pay_bands(
    analytics_service: AnalyticsService,
) -> None:
    result = analytics_service.calculate(
        AnalyticsFilters(country="US", min_salary_usd=Decimal("50"))
    )

    assert result.active_headcount == 4
    assert [band.headcount for band in result.percentile_pay_bands] == [1, 1, 1, 1]
