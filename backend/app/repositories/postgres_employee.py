from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any

import psycopg
from psycopg import errors
from psycopg.rows import dict_row

from app.repositories.employee import (
    DuplicateEmployeeIdConflict,
    EmployeeListQuery,
    EmployeePage,
    EmployeeRecord,
    EmployeeWrite,
)


class PostgresEmployeeRepository:
    """SQL persistence for employees; business rules belong in EmployeeService."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def list(self, query: EmployeeListQuery) -> EmployeePage:
        conditions: list[str] = []
        params: list[object] = []
        if query.search:
            conditions.append("(e.name ILIKE %s OR e.employee_id ILIKE %s)")
            pattern = f"%{query.search}%"
            params.extend((pattern, pattern))
        if query.country:
            conditions.append("(c.code ILIKE %s OR c.name ILIKE %s)")
            params.extend((query.country, query.country))
        if query.department:
            conditions.append("e.department = %s")
            params.append(query.department)
        if query.is_active is not None:
            conditions.append("e.is_active = %s")
            params.append(query.is_active)
        if query.min_salary_usd is not None:
            conditions.append("e.salary_usd >= %s")
            params.append(query.min_salary_usd)
        if query.max_salary_usd is not None:
            conditions.append("e.salary_usd <= %s")
            params.append(query.max_salary_usd)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        # These identifiers are selected by the service from fixed allowlists.
        sort_column = {
            "name": "e.name",
            "employee_id": "e.employee_id",
            "salary_usd": "e.salary_usd",
            "created_at": "e.created_at",
        }[query.sort_by]
        direction = "DESC" if query.sort_order == "desc" else "ASC"
        join = " FROM employees e JOIN countries c ON c.code = e.country"
        with self._connect() as connection, connection.cursor() as cursor:
            # Keep the count and page rows from the same snapshot.
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            cursor.execute("SELECT count(*) AS total" + join + where, params)
            count_row = cursor.fetchone()
            cursor.execute(
                "SELECT e.*"
                + join
                + where
                + f" ORDER BY {sort_column} {direction}, e.id ASC LIMIT %s OFFSET %s",
                [*params, query.page_size, (query.page - 1) * query.page_size],
            )
            return EmployeePage(
                items=[self._to_record(row) for row in cursor.fetchall()],
                total=int(count_row["total"]),
                page=query.page,
                page_size=query.page_size,
            )

    def get_by_employee_id(self, employee_id: str) -> EmployeeRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM employees WHERE employee_id = %s",
                (employee_id,),
            )
            row = cursor.fetchone()
            return self._to_record(row) if row else None

    def employee_id_exists(self, employee_id: str) -> bool:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM employees WHERE employee_id = %s)",
                (employee_id,),
            )
            row = cursor.fetchone()
            return bool(row and row["exists"])

    def get_country_currency(self, country: str) -> str | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT currency FROM countries WHERE code = %s", (country,))
            row = cursor.fetchone()
            return str(row["currency"]) if row else None

    def get_fx_rate(self, currency: str) -> Decimal | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT rate_to_usd FROM fx_rates WHERE currency = %s", (currency,))
            row = cursor.fetchone()
            return Decimal(row["rate_to_usd"]) if row else None

    def department_exists(self, department: str) -> bool:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM departments WHERE name = %s)",
                (department,),
            )
            row = cursor.fetchone()
            return bool(row and row["exists"])

    def create(self, employee: EmployeeWrite) -> EmployeeRecord:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO employees (
                        employee_id, name, country, department, role,
                        annual_salary_native, currency, salary_usd
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    self._write_values(employee),
                )
                row = cursor.fetchone()
                assert row is not None
                return self._to_record(row)
        except errors.UniqueViolation as error:
            if error.diag.constraint_name == "employees_employee_id_key":
                raise DuplicateEmployeeIdConflict(employee.employee_id) from error
            raise

    def update(self, employee_id: str, employee: EmployeeWrite) -> EmployeeRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE employees
                SET name = %s,
                    country = %s,
                    department = %s,
                    role = %s,
                    annual_salary_native = %s,
                    currency = %s,
                    salary_usd = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE employee_id = %s AND is_active = TRUE
                RETURNING *
                """,
                (
                    employee.name,
                    employee.country,
                    employee.department,
                    employee.role,
                    employee.annual_salary_native,
                    employee.currency,
                    employee.salary_usd,
                    employee_id,
                ),
            )
            row = cursor.fetchone()
            return self._to_record(row) if row else None

    def set_active(
        self, employee_id: str, *, is_active: bool, changed_at: datetime
    ) -> EmployeeRecord | None:
        deactivated_at = None if is_active else changed_at
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE employees
                SET is_active = %s, deactivated_at = %s, updated_at = %s
                WHERE employee_id = %s AND is_active = %s
                RETURNING *
                """,
                (is_active, deactivated_at, changed_at, employee_id, not is_active),
            )
            row = cursor.fetchone()
            return self._to_record(row) if row else None

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self.database_url, row_factory=dict_row)

    @staticmethod
    def _write_values(employee: EmployeeWrite) -> tuple[object, ...]:
        return (
            employee.employee_id,
            employee.name,
            employee.country,
            employee.department,
            employee.role,
            employee.annual_salary_native,
            employee.currency,
            employee.salary_usd,
        )

    @staticmethod
    def _to_record(row: Mapping[str, Any]) -> EmployeeRecord:
        return EmployeeRecord(
            **{field: row[field] for field in EmployeeRecord.__dataclass_fields__}
        )
