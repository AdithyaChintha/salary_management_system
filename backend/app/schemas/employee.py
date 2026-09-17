from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    country: str = Field(min_length=2, max_length=2)
    department: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=200)
    annual_salary_native: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    department: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, min_length=1, max_length=200)
    annual_salary_native: Decimal | None = Field(
        default=None, gt=0, max_digits=18, decimal_places=2
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class EmployeeResponse(EmployeeCreate):
    id: int
    salary_usd: Decimal
    is_active: bool
    deactivated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int
    page: int
    page_size: int


class EmployeeFilters(BaseModel):
    search: str | None = None
    country: str | None = None
    department: str | None = None
    is_active: bool | None = None
    min_salary_usd: Decimal | None = Field(default=None, ge=0)
    max_salary_usd: Decimal | None = Field(default=None, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    sort_by: Literal["name", "employee_id", "salary_usd", "country", "department", "created_at"] = (
        "name"
    )
    sort_order: Literal["asc", "desc"] = "asc"
