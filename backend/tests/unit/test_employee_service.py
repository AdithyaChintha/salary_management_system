from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.repositories.employee import EmployeeRecord, EmployeeWrite
from app.services.employee import (
    CreateEmployee,
    DuplicateEmployeeIdError,
    EmployeeNotFoundError,
    EmployeeService,
    EmployeeStateError,
    InactiveEmployeeError,
    InvalidCountryCurrencyError,
    InvalidEmployeeError,
    UpdateEmployee,
)


class FakeEmployeeRepository:
    def __init__(self) -> None:
        self.employees: dict[str, EmployeeRecord] = {}
        self.country_currencies = {"US": "USD", "IN": "INR"}
        self.fx_rates = {"USD": Decimal("1"), "INR": Decimal("0.012")}
        self.next_id = 1

    def get_by_employee_id(self, employee_id: str) -> EmployeeRecord | None:
        return self.employees.get(employee_id)

    def employee_id_exists(self, employee_id: str) -> bool:
        return employee_id in self.employees

    def get_country_currency(self, country: str) -> str | None:
        return self.country_currencies.get(country)

    def get_fx_rate(self, currency: str) -> Decimal | None:
        return self.fx_rates.get(currency)

    def create(self, employee: EmployeeWrite) -> EmployeeRecord:
        now = datetime.now(UTC)
        record = EmployeeRecord(
            id=self.next_id,
            **employee.__dict__,
            is_active=True,
            deactivated_at=None,
            created_at=now,
            updated_at=now,
        )
        self.next_id += 1
        self.employees[employee.employee_id] = record
        return record

    def update(self, employee_id: str, employee: EmployeeWrite) -> EmployeeRecord:
        current = self.employees[employee_id]
        record = replace(current, **employee.__dict__, updated_at=datetime.now(UTC))
        self.employees[employee_id] = record
        return record

    def set_active(
        self, employee_id: str, *, is_active: bool, changed_at: datetime
    ) -> EmployeeRecord:
        current = self.employees[employee_id]
        record = replace(
            current,
            is_active=is_active,
            deactivated_at=None if is_active else changed_at,
            updated_at=changed_at,
        )
        self.employees[employee_id] = record
        return record


@pytest.fixture
def repository() -> FakeEmployeeRepository:
    return FakeEmployeeRepository()


@pytest.fixture
def service(repository: FakeEmployeeRepository) -> EmployeeService:
    return EmployeeService(repository)


def employee_request(**changes: object) -> CreateEmployee:
    values = {
        "employee_id": "EMP-001",
        "name": "Ada Lovelace",
        "country": "IN",
        "department": "Engineering",
        "role": "Software Engineer",
        "annual_salary_native": Decimal("1000000"),
        "currency": "INR",
    }
    values.update(changes)
    return CreateEmployee(**values)  # type: ignore[arg-type]


def test_create_normalizes_input_and_calculates_usd(service: EmployeeService) -> None:
    employee = service.create_employee(
        employee_request(employee_id=" EMP-001 ", country="in", currency="inr")
    )

    assert employee.employee_id == "EMP-001"
    assert employee.country == "IN"
    assert employee.currency == "INR"
    assert employee.annual_salary_native == Decimal("1000000.00")
    assert employee.salary_usd == Decimal("12000.00")
    assert employee.is_active is True


def test_create_rejects_duplicate_employee_id(service: EmployeeService) -> None:
    service.create_employee(employee_request())

    with pytest.raises(DuplicateEmployeeIdError):
        service.create_employee(employee_request())


@pytest.mark.parametrize("salary", [Decimal("0"), Decimal("-1"), Decimal("NaN")])
def test_create_rejects_invalid_salary(
    service: EmployeeService, salary: Decimal
) -> None:
    with pytest.raises(InvalidEmployeeError):
        service.create_employee(employee_request(annual_salary_native=salary))


def test_country_and_currency_must_match(service: EmployeeService) -> None:
    with pytest.raises(InvalidCountryCurrencyError):
        service.create_employee(employee_request(country="US", currency="INR"))


def test_fetch_returns_employee_or_not_found(service: EmployeeService) -> None:
    created = service.create_employee(employee_request())

    assert service.fetch_employee("EMP-001") == created
    with pytest.raises(EmployeeNotFoundError):
        service.fetch_employee("MISSING")


def test_update_merges_fields_and_recalculates_salary(service: EmployeeService) -> None:
    service.create_employee(employee_request())

    updated = service.update_employee(
        "EMP-001",
        UpdateEmployee(
            country="US",
            currency="USD",
            annual_salary_native=Decimal("90000.129"),
            role="Senior Software Engineer",
        ),
    )

    assert updated.name == "Ada Lovelace"
    assert updated.country == "US"
    assert updated.annual_salary_native == Decimal("90000.13")
    assert updated.salary_usd == Decimal("90000.13")
    assert updated.role == "Senior Software Engineer"


def test_inactive_employee_cannot_be_updated_or_recalculated(
    service: EmployeeService,
) -> None:
    service.create_employee(employee_request())
    service.deactivate_employee("EMP-001")

    with pytest.raises(InactiveEmployeeError):
        service.update_employee("EMP-001", UpdateEmployee(name="New Name"))
    with pytest.raises(InactiveEmployeeError):
        service.recalculate_salary_usd("EMP-001")


def test_deactivate_and_reactivate_manage_soft_delete_state(service: EmployeeService) -> None:
    service.create_employee(employee_request())

    inactive = service.deactivate_employee("EMP-001")
    assert inactive.is_active is False
    assert inactive.deactivated_at is not None

    active = service.reactivate_employee("EMP-001")
    assert active.is_active is True
    assert active.deactivated_at is None


def test_repeating_same_state_transition_is_rejected(service: EmployeeService) -> None:
    service.create_employee(employee_request())

    with pytest.raises(EmployeeStateError):
        service.reactivate_employee("EMP-001")

    service.deactivate_employee("EMP-001")
    with pytest.raises(EmployeeStateError):
        service.deactivate_employee("EMP-001")


def test_recalculate_uses_latest_fx_rate(
    service: EmployeeService, repository: FakeEmployeeRepository
) -> None:
    service.create_employee(employee_request())
    repository.fx_rates["INR"] = Decimal("0.0135")

    updated = service.recalculate_salary_usd("EMP-001")

    assert updated.salary_usd == Decimal("13500.00")
