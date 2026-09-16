from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.repositories.employee import (
    DuplicateEmployeeIdConflict,
    EmployeeRecord,
    EmployeeRepository,
    EmployeeWrite,
)

MONEY_PLACES = Decimal("0.01")


class EmployeeServiceError(Exception):
    """Base class for expected employee business errors."""


class EmployeeNotFoundError(EmployeeServiceError):
    pass


class DuplicateEmployeeIdError(EmployeeServiceError):
    pass


class InvalidEmployeeError(EmployeeServiceError):
    pass


class InvalidCountryCurrencyError(EmployeeServiceError):
    pass


class InactiveEmployeeError(EmployeeServiceError):
    pass


class EmployeeStateError(EmployeeServiceError):
    pass


@dataclass(frozen=True)
class CreateEmployee:
    employee_id: str
    name: str
    country: str
    department: str
    role: str
    annual_salary_native: Decimal
    currency: str


@dataclass(frozen=True)
class UpdateEmployee:
    name: str | None = None
    country: str | None = None
    department: str | None = None
    role: str | None = None
    annual_salary_native: Decimal | None = None
    currency: str | None = None


class EmployeeService:
    def __init__(self, repository: EmployeeRepository) -> None:
        self.repository = repository

    def create_employee(self, request: CreateEmployee) -> EmployeeRecord:
        employee_id = self._required_text(request.employee_id, "employee_id")
        if self.repository.employee_id_exists(employee_id):
            raise DuplicateEmployeeIdError(employee_id)

        write = self._build_write(
            employee_id=employee_id,
            name=request.name,
            country=request.country,
            department=request.department,
            role=request.role,
            annual_salary_native=request.annual_salary_native,
            currency=request.currency,
        )
        try:
            return self.repository.create(write)
        except DuplicateEmployeeIdConflict as error:
            # The database unique constraint closes the race between the pre-check and insert.
            raise DuplicateEmployeeIdError(employee_id) from error

    def fetch_employee(self, employee_id: str) -> EmployeeRecord:
        normalized_id = self._required_text(employee_id, "employee_id")
        employee = self.repository.get_by_employee_id(normalized_id)
        if employee is None:
            raise EmployeeNotFoundError(normalized_id)
        return employee

    def update_employee(self, employee_id: str, request: UpdateEmployee) -> EmployeeRecord:
        current = self.fetch_employee(employee_id)
        if not current.is_active:
            raise InactiveEmployeeError(current.employee_id)

        write = self._build_write(
            employee_id=current.employee_id,
            name=request.name if request.name is not None else current.name,
            country=request.country if request.country is not None else current.country,
            department=(
                request.department if request.department is not None else current.department
            ),
            role=request.role if request.role is not None else current.role,
            annual_salary_native=(
                request.annual_salary_native
                if request.annual_salary_native is not None
                else current.annual_salary_native
            ),
            currency=request.currency if request.currency is not None else current.currency,
        )
        return self.repository.update(current.employee_id, write)

    def deactivate_employee(self, employee_id: str) -> EmployeeRecord:
        employee = self.fetch_employee(employee_id)
        if not employee.is_active:
            raise EmployeeStateError(f"Employee {employee.employee_id} is already inactive")
        return self.repository.set_active(
            employee.employee_id, is_active=False, changed_at=datetime.now(UTC)
        )

    def reactivate_employee(self, employee_id: str) -> EmployeeRecord:
        employee = self.fetch_employee(employee_id)
        if employee.is_active:
            raise EmployeeStateError(f"Employee {employee.employee_id} is already active")
        return self.repository.set_active(
            employee.employee_id, is_active=True, changed_at=datetime.now(UTC)
        )

    def recalculate_salary_usd(self, employee_id: str) -> EmployeeRecord:
        employee = self.fetch_employee(employee_id)
        if not employee.is_active:
            raise InactiveEmployeeError(employee.employee_id)
        write = self._build_write(
            employee_id=employee.employee_id,
            name=employee.name,
            country=employee.country,
            department=employee.department,
            role=employee.role,
            annual_salary_native=employee.annual_salary_native,
            currency=employee.currency,
        )
        return self.repository.update(employee.employee_id, write)

    def validate_country_currency(self, country: str, currency: str) -> tuple[str, str]:
        normalized_country = self._required_text(country, "country").upper()
        normalized_currency = self._required_text(currency, "currency").upper()
        expected_currency = self.repository.get_country_currency(normalized_country)
        if expected_currency is None or expected_currency != normalized_currency:
            raise InvalidCountryCurrencyError(
                f"{normalized_currency} is not the configured currency for {normalized_country}"
            )
        return normalized_country, normalized_currency

    def _build_write(
        self,
        *,
        employee_id: str,
        name: str,
        country: str,
        department: str,
        role: str,
        annual_salary_native: Decimal,
        currency: str,
    ) -> EmployeeWrite:
        normalized_country, normalized_currency = self.validate_country_currency(
            country, currency
        )
        salary = self._positive_money(annual_salary_native)
        rate = self.repository.get_fx_rate(normalized_currency)
        if rate is None or rate <= 0:
            raise InvalidCountryCurrencyError(
                f"No positive USD exchange rate exists for {normalized_currency}"
            )
        return EmployeeWrite(
            employee_id=self._required_text(employee_id, "employee_id"),
            name=self._required_text(name, "name"),
            country=normalized_country,
            department=self._required_text(department, "department"),
            role=self._required_text(role, "role"),
            annual_salary_native=salary,
            currency=normalized_currency,
            salary_usd=(salary * rate).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP),
        )

    @staticmethod
    def _required_text(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise InvalidEmployeeError(f"{field} must not be blank")
        return normalized

    @staticmethod
    def _positive_money(value: Decimal) -> Decimal:
        try:
            money = Decimal(value).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError) as error:
            raise InvalidEmployeeError("annual_salary_native must be a number") from error
        if not money.is_finite() or money <= 0:
            raise InvalidEmployeeError("annual_salary_native must be greater than zero")
        return money
