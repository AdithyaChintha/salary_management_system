from decimal import Decimal

from pydantic import BaseModel, Field


class DashboardFilters(BaseModel):
    country: str | None = None
    department: str | None = None
    min_salary_usd: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    max_salary_usd: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)


class DashboardSummary(BaseModel):
    headcount: int
    total_payroll_usd: Decimal
    average_salary_usd: Decimal | None
    median_salary_usd: Decimal | None


class DashboardDistribution(BaseModel):
    name: str
    headcount: int


class DashboardPayBand(BaseModel):
    label: str
    lower_usd: Decimal | None
    upper_usd: Decimal | None
    headcount: int


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    by_country: list[DashboardDistribution]
    by_department: list[DashboardDistribution]
    pay_bands: list[DashboardPayBand]
    quartile_cutoffs_usd: tuple[Decimal | None, Decimal | None, Decimal | None]
    highest_salary_usd: Decimal | None
    lowest_salary_usd: Decimal | None
