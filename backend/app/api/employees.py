from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.config import settings
from app.repositories.employee import EmployeeListQuery
from app.repositories.postgres_employee import PostgresEmployeeRepository
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeFilters,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.employee import CreateEmployee, EmployeeService, UpdateEmployee

router = APIRouter(prefix="/employees", tags=["employees"])


def get_employee_service() -> EmployeeService:
    return EmployeeService(PostgresEmployeeRepository(settings.database_url))


Service = Annotated[EmployeeService, Depends(get_employee_service)]
Filters = Annotated[EmployeeFilters, Query()]


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, service: Service):
    return service.create_employee(CreateEmployee(**payload.model_dump()))


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    filters: Filters,
    service: Service,
):
    return service.list_employees(EmployeeListQuery(**filters.model_dump()))


@router.get("/{employee_id}", response_model=EmployeeResponse)
def fetch_employee(employee_id: str, service: Service):
    return service.fetch_employee(employee_id)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    service: Service,
):
    return service.update_employee(employee_id, UpdateEmployee(**payload.model_dump()))


@router.post("/{employee_id}/deactivate", response_model=EmployeeResponse)
def deactivate_employee(employee_id: str, service: Service):
    return service.deactivate_employee(employee_id)


@router.post("/{employee_id}/reactivate", response_model=EmployeeResponse)
def reactivate_employee(employee_id: str, service: Service):
    return service.reactivate_employee(employee_id)
