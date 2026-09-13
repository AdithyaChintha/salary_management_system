from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Confirm that the application process is available."""
    return {"status": "ok"}

