from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class AnalyticsFilters:
    country: str | None = None
    department: str | None = None
    min_salary_usd: Decimal | None = None
    max_salary_usd: Decimal | None = None


@dataclass(frozen=True)
class Distribution:
    name: str
    headcount: int


@dataclass(frozen=True)
class PayBand:
    label: str
    lower_usd: Decimal | None
    upper_usd: Decimal | None
    headcount: int


@dataclass(frozen=True)
class WorkforceAnalytics:
    active_headcount: int
    total_payroll_usd: Decimal
    average_salary_usd: Decimal | None
    median_salary_usd: Decimal | None
    highest_salary_usd: Decimal | None
    lowest_salary_usd: Decimal | None
    department_distribution: list[Distribution]
    country_distribution: list[Distribution]
    quartile_cutoffs_usd: tuple[Decimal | None, Decimal | None, Decimal | None]
    percentile_pay_bands: list[PayBand]


class AnalyticsRepository(Protocol):
    def calculate(self, filters: AnalyticsFilters) -> WorkforceAnalytics: ...
