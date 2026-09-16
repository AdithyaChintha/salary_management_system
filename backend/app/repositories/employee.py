from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class EmployeeRecord:
    id: int
    employee_id: str
    name: str
    country: str
    department: str
    role: str
    annual_salary_native: Decimal
    currency: str
    salary_usd: Decimal
    is_active: bool
    deactivated_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class EmployeeWrite:
    employee_id: str
    name: str
    country: str
    department: str
    role: str
    annual_salary_native: Decimal
    currency: str
    salary_usd: Decimal


@dataclass(frozen=True)
class EmployeeListQuery:
    search: str | None = None
    country: str | None = None
    department: str | None = None
    is_active: bool | None = None
    min_salary_usd: Decimal | None = None
    max_salary_usd: Decimal | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "name"
    sort_order: str = "asc"


@dataclass(frozen=True)
class EmployeePage:
    items: list[EmployeeRecord]
    total: int
    page: int
    page_size: int


class DuplicateEmployeeIdConflict(Exception):
    """The database rejected an employee ID that is already in use."""


class EmployeeRepository(Protocol):
    def list(self, query: EmployeeListQuery) -> EmployeePage: ...
    def get_by_employee_id(self, employee_id: str) -> EmployeeRecord | None: ...

    def employee_id_exists(self, employee_id: str) -> bool: ...

    def get_country_currency(self, country: str) -> str | None: ...

    def get_fx_rate(self, currency: str) -> Decimal | None: ...

    def department_exists(self, department: str) -> bool: ...

    def create(self, employee: EmployeeWrite) -> EmployeeRecord: ...

    def update(self, employee_id: str, employee: EmployeeWrite) -> EmployeeRecord: ...

    def set_active(
        self, employee_id: str, *, is_active: bool, changed_at: datetime
    ) -> EmployeeRecord: ...
