from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import psycopg

from app.core.config import settings

SEED = 20260912
EMPLOYEE_COUNT = 10_000
MONEY_PLACES = Decimal("0.01")
BASE_DATE = datetime(2026, 1, 1, tzinfo=UTC)
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "app" / "db" / "schema.sql"


@dataclass(frozen=True)
class CountrySeed:
    code: str
    name: str
    currency: str
    rate_to_usd: Decimal
    salary_factor: Decimal


COUNTRIES = (
    CountrySeed("US", "United States", "USD", Decimal("1.0000000000"), Decimal("1.00")),
    CountrySeed("IN", "India", "INR", Decimal("0.0120000000"), Decimal("0.32")),
    CountrySeed("GB", "United Kingdom", "GBP", Decimal("1.2700000000"), Decimal("0.85")),
    CountrySeed("DE", "Germany", "EUR", Decimal("1.0900000000"), Decimal("0.80")),
    CountrySeed("CA", "Canada", "CAD", Decimal("0.7400000000"), Decimal("0.82")),
    CountrySeed("AU", "Australia", "AUD", Decimal("0.6600000000"), Decimal("0.83")),
    CountrySeed("JP", "Japan", "JPY", Decimal("0.0067000000"), Decimal("0.72")),
    CountrySeed("SG", "Singapore", "SGD", Decimal("0.7400000000"), Decimal("0.88")),
    CountrySeed("BR", "Brazil", "BRL", Decimal("0.2000000000"), Decimal("0.45")),
    CountrySeed("ZA", "South Africa", "ZAR", Decimal("0.0550000000"), Decimal("0.42")),
)

ROLE_BANDS: dict[str, tuple[tuple[str, int, int], ...]] = {
    "Engineering": (
        ("Software Engineer", 70_000, 145_000),
        ("Senior Software Engineer", 110_000, 190_000),
        ("Engineering Manager", 130_000, 215_000),
        ("QA Engineer", 60_000, 125_000),
    ),
    "Data": (
        ("Data Analyst", 60_000, 120_000),
        ("Data Engineer", 85_000, 165_000),
        ("Data Scientist", 90_000, 180_000),
    ),
    "Product": (
        ("Product Manager", 85_000, 170_000),
        ("Product Designer", 70_000, 145_000),
        ("Product Operations Manager", 65_000, 130_000),
    ),
    "Sales": (
        ("Account Executive", 55_000, 135_000),
        ("Sales Manager", 80_000, 165_000),
        ("Sales Development Representative", 42_000, 85_000),
    ),
    "Finance": (
        ("Financial Analyst", 60_000, 115_000),
        ("Accountant", 52_000, 105_000),
        ("Finance Manager", 90_000, 160_000),
    ),
    "Human Resources": (
        ("HR Specialist", 48_000, 95_000),
        ("Recruiter", 50_000, 105_000),
        ("HR Manager", 75_000, 135_000),
    ),
    "Marketing": (
        ("Marketing Specialist", 48_000, 100_000),
        ("Content Strategist", 52_000, 110_000),
        ("Marketing Manager", 78_000, 145_000),
    ),
    "Operations": (
        ("Operations Analyst", 48_000, 95_000),
        ("Project Manager", 65_000, 130_000),
        ("Operations Manager", 72_000, 140_000),
    ),
    "Legal": (
        ("Legal Counsel", 95_000, 190_000),
        ("Compliance Analyst", 60_000, 120_000),
        ("Contracts Manager", 72_000, 140_000),
    ),
    "Customer Support": (
        ("Support Specialist", 38_000, 75_000),
        ("Technical Support Engineer", 52_000, 105_000),
        ("Support Manager", 65_000, 120_000),
    ),
}

COUNTRY_WEIGHTS = (28, 18, 10, 9, 8, 6, 7, 5, 5, 4)
DEPARTMENT_WEIGHTS = (25, 10, 10, 12, 8, 7, 9, 5, 6, 8)

FIRST_NAMES = (
    "Aarav",
    "Aisha",
    "Akira",
    "Alice",
    "Amara",
    "Ana",
    "Arjun",
    "Benjamin",
    "Camila",
    "Charlotte",
    "Daniel",
    "David",
    "Elena",
    "Emma",
    "Ethan",
    "Fatima",
    "Gabriel",
    "Grace",
    "Hana",
    "Haruto",
    "Isabella",
    "James",
    "Kenji",
    "Lena",
    "Liam",
    "Lucas",
    "Maya",
    "Mia",
    "Mohammed",
    "Noah",
    "Olivia",
    "Priya",
    "Rafael",
    "Riya",
    "Samuel",
    "Sofia",
    "Thabo",
    "Wei",
    "Yuki",
    "Zoe",
)

LAST_NAMES = (
    "Anderson",
    "Brown",
    "Chen",
    "Costa",
    "Davis",
    "Dubois",
    "Garcia",
    "Gupta",
    "Harris",
    "Hernandez",
    "Ito",
    "Johnson",
    "Jones",
    "Khan",
    "Kim",
    "Kumar",
    "Lee",
    "Martin",
    "Martinez",
    "Miller",
    "Mokoena",
    "Morris",
    "Muller",
    "Nakamura",
    "Nguyen",
    "Okafor",
    "Patel",
    "Robinson",
    "Rossi",
    "Santos",
    "Schmidt",
    "Silva",
    "Singh",
    "Smith",
    "Suzuki",
    "Taylor",
    "Thomas",
    "Walker",
    "Wang",
    "Williams",
)


def generate_employees(count: int = EMPLOYEE_COUNT, seed: int = SEED) -> list[dict[str, Any]]:
    """Return the same analytics-friendly employee population for a given seed."""
    rng = random.Random(seed)
    departments = tuple(ROLE_BANDS)
    employees: list[dict[str, Any]] = []

    for sequence in range(1, count + 1):
        country = rng.choices(COUNTRIES, weights=COUNTRY_WEIGHTS, k=1)[0]
        department = rng.choices(departments, weights=DEPARTMENT_WEIGHTS, k=1)[0]
        role, minimum_usd, maximum_usd = rng.choice(ROLE_BANDS[department])
        market_usd = Decimal(str(rng.randint(minimum_usd, maximum_usd)))
        adjusted_usd = market_usd * country.salary_factor
        native_salary = (adjusted_usd / country.rate_to_usd).quantize(
            MONEY_PLACES, rounding=ROUND_HALF_UP
        )
        salary_usd = (native_salary * country.rate_to_usd).quantize(
            MONEY_PLACES, rounding=ROUND_HALF_UP
        )
        created_at = BASE_DATE - timedelta(days=rng.randint(30, 2_800))
        is_active = rng.random() >= 0.05
        deactivated_at = None
        if not is_active:
            days_since_creation = (BASE_DATE - created_at).days
            deactivated_at = created_at + timedelta(
                days=rng.randint(1, min(365, days_since_creation))
            )

        employees.append(
            {
                "employee_id": f"EMP-{sequence:05d}",
                "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                "country": country.code,
                "department": department,
                "role": role,
                "annual_salary_native": native_salary,
                "currency": country.currency,
                "salary_usd": salary_usd,
                "is_active": is_active,
                "deactivated_at": deactivated_at,
                "created_at": created_at,
                "updated_at": deactivated_at or created_at,
            }
        )

    return employees


def seed_database(database_url: str, reset: bool = False) -> None:
    employees = generate_employees()
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_PATH.read_text(encoding="utf-8"), prepare=False)
            if reset:
                cursor.execute("TRUNCATE TABLE employees RESTART IDENTITY")

            cursor.executemany(
                """
                INSERT INTO fx_rates (currency, rate_to_usd)
                VALUES (%(currency)s, %(rate_to_usd)s)
                ON CONFLICT (currency) DO UPDATE
                SET rate_to_usd = EXCLUDED.rate_to_usd
                """,
                [
                    {"currency": country.currency, "rate_to_usd": country.rate_to_usd}
                    for country in COUNTRIES
                ],
            )
            cursor.executemany(
                """
                INSERT INTO countries (code, name, currency)
                VALUES (%(code)s, %(name)s, %(currency)s)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name, currency = EXCLUDED.currency
                """,
                [
                    {"code": country.code, "name": country.name, "currency": country.currency}
                    for country in COUNTRIES
                ],
            )
            cursor.executemany(
                """
                INSERT INTO departments (name)
                VALUES (%(name)s)
                ON CONFLICT (name) DO NOTHING
                """,
                [{"name": department} for department in ROLE_BANDS],
            )
            cursor.executemany(
                """
                INSERT INTO employees (
                    employee_id, name, country, department, role,
                    annual_salary_native, currency, salary_usd, is_active,
                    deactivated_at, created_at, updated_at
                )
                VALUES (
                    %(employee_id)s, %(name)s, %(country)s, %(department)s, %(role)s,
                    %(annual_salary_native)s, %(currency)s, %(salary_usd)s, %(is_active)s,
                    %(deactivated_at)s, %(created_at)s, %(updated_at)s
                )
                ON CONFLICT (employee_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    country = EXCLUDED.country,
                    department = EXCLUDED.department,
                    role = EXCLUDED.role,
                    annual_salary_native = EXCLUDED.annual_salary_native,
                    currency = EXCLUDED.currency,
                    salary_usd = EXCLUDED.salary_usd,
                    is_active = EXCLUDED.is_active,
                    deactivated_at = EXCLUDED.deactivated_at,
                    created_at = EXCLUDED.created_at,
                    updated_at = EXCLUDED.updated_at
                """,
                employees,
            )

        connection.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed deterministic salary management data")
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove every employee before loading the deterministic seed population",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    seed_database(arguments.database_url, reset=arguments.reset)
    print(f"Seeded {EMPLOYEE_COUNT:,} deterministic employees.")
