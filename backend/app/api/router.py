from fastapi import APIRouter

from app.api.analytics import router as analytics_router
from app.api.employees import router as employee_router

api_router = APIRouter()
api_router.include_router(employee_router)
api_router.include_router(analytics_router)


@api_router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Confirm that the application process is available."""
    return {"status": "ok"}
