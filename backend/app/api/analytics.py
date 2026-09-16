from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.config import settings
from app.repositories.analytics import AnalyticsFilters
from app.repositories.postgres_analytics import PostgresAnalyticsRepository
from app.schemas.analytics import DashboardFilters, DashboardResponse
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService(PostgresAnalyticsRepository(settings.database_url))


Service = Annotated[AnalyticsService, Depends(get_analytics_service)]
Filters = Annotated[DashboardFilters, Query()]


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(filters: Filters, service: Service) -> DashboardResponse:
    analytics = service.calculate(AnalyticsFilters(**filters.model_dump()))
    return DashboardResponse(
        summary={
            "headcount": analytics.active_headcount,
            "total_payroll_usd": analytics.total_payroll_usd,
            "average_salary_usd": analytics.average_salary_usd,
            "median_salary_usd": analytics.median_salary_usd,
        },
        by_country=[asdict(item) for item in analytics.country_distribution],
        by_department=[asdict(item) for item in analytics.department_distribution],
        pay_bands=[asdict(item) for item in analytics.percentile_pay_bands],
        quartile_cutoffs_usd=analytics.quartile_cutoffs_usd,
        highest_salary_usd=analytics.highest_salary_usd,
        lowest_salary_usd=analytics.lowest_salary_usd,
    )
