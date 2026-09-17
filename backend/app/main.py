import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.services.analytics import InvalidAnalyticsFiltersError
from app.services.employee import (
    DuplicateEmployeeIdError,
    EmployeeNotFoundError,
    EmployeeServiceError,
    EmployeeStateError,
    InactiveEmployeeError,
    InvalidCountryCurrencyError,
    InvalidEmployeeError,
)

logger = logging.getLogger(__name__)


def employee_error_response(_request, error: EmployeeServiceError) -> JSONResponse:
    mappings = (
        (EmployeeNotFoundError, 404, "employee_not_found"),
        (DuplicateEmployeeIdError, 409, "duplicate_employee_id"),
        (InactiveEmployeeError, 409, "inactive_employee"),
        (EmployeeStateError, 409, "invalid_employee_state"),
        (InvalidCountryCurrencyError, 422, "invalid_country_currency"),
        (InvalidEmployeeError, 422, "invalid_employee"),
    )
    for error_type, status_code, code in mappings:
        if isinstance(error, error_type):
            return JSONResponse(
                status_code=status_code, content={"error": {"code": code, "message": str(error)}}
            )
    return JSONResponse(
        status_code=500, content={"error": {"code": "unknown_error", "message": "Unexpected error"}}
    )


def validation_error_response(_request, error: RequestValidationError) -> JSONResponse:
    details = [
        {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": "validation_error", "message": "Invalid request", "details": details}
        },
    )


def analytics_filter_error_response(_request, error: InvalidAnalyticsFiltersError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "invalid_analytics_filters", "message": str(error)}},
    )


def unexpected_error_response(_request, error: Exception) -> JSONResponse:
    logger.error("Unhandled API error", exc_info=(type(error), error, error.__traceback__))
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Unexpected server error"}},
    )


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.add_exception_handler(EmployeeServiceError, employee_error_response)
    application.add_exception_handler(RequestValidationError, validation_error_response)
    application.add_exception_handler(InvalidAnalyticsFiltersError, analytics_filter_error_response)
    application.add_exception_handler(Exception, unexpected_error_response)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
