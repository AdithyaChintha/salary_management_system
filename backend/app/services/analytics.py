from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, InvalidOperation

from app.repositories.analytics import AnalyticsFilters, AnalyticsRepository, WorkforceAnalytics


class InvalidAnalyticsFiltersError(ValueError):
    pass


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    def calculate(self, filters: AnalyticsFilters | None = None) -> WorkforceAnalytics:
        filters = filters or AnalyticsFilters()
        minimum = self._validate_salary(filters.min_salary_usd, "min_salary_usd")
        maximum = self._validate_salary(filters.max_salary_usd, "max_salary_usd")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise InvalidAnalyticsFiltersError("min_salary_usd cannot exceed max_salary_usd")
        country = self._optional_text(filters.country)
        department = self._optional_text(filters.department)
        return self.repository.calculate(
            replace(
                filters,
                country=country,
                department=department,
                min_salary_usd=minimum,
                max_salary_usd=maximum,
            )
        )

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise InvalidAnalyticsFiltersError("country and department must not be blank")
        return value.strip()

    @staticmethod
    def _validate_salary(value: Decimal | None, name: str) -> Decimal | None:
        if value is None:
            return None
        try:
            salary = Decimal(value)
        except (InvalidOperation, TypeError, ValueError) as error:
            raise InvalidAnalyticsFiltersError(f"{name} must be a number") from error
        if not salary.is_finite() or salary < 0:
            raise InvalidAnalyticsFiltersError(f"{name} must be finite and nonnegative")
        return salary
