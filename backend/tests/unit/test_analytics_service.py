from decimal import Decimal

import pytest

from app.repositories.analytics import AnalyticsFilters
from app.services.analytics import AnalyticsService, InvalidAnalyticsFiltersError


class RecordingRepository:
    def __init__(self) -> None:
        self.filters = None

    def calculate(self, filters):
        self.filters = filters
        return "result"


def test_service_normalizes_filters() -> None:
    repository = RecordingRepository()
    result = AnalyticsService(repository).calculate(
        AnalyticsFilters(country=" India ", department=" Engineering ", min_salary_usd=Decimal("0"))
    )

    assert result == "result"
    assert repository.filters == AnalyticsFilters(
        country="India", department="Engineering", min_salary_usd=Decimal("0")
    )


@pytest.mark.parametrize(
    "filters",
    [
        AnalyticsFilters(country=" "),
        AnalyticsFilters(min_salary_usd=Decimal("-1")),
        AnalyticsFilters(max_salary_usd=Decimal("NaN")),
        AnalyticsFilters(min_salary_usd=Decimal("30"), max_salary_usd=Decimal("20")),
    ],
)
def test_service_rejects_invalid_filters(filters: AnalyticsFilters) -> None:
    with pytest.raises(InvalidAnalyticsFiltersError):
        AnalyticsService(RecordingRepository()).calculate(filters)
