from decimal import Decimal, ROUND_HALF_UP

from scripts.seed import COUNTRIES, EMPLOYEE_COUNT, ROLE_BANDS, SEED, generate_employees


def test_seed_has_expected_employee_count_and_unique_ids() -> None:
    employees = generate_employees()

    assert len(employees) == EMPLOYEE_COUNT
    assert len({employee["employee_id"] for employee in employees}) == EMPLOYEE_COUNT


def test_seed_is_deterministic() -> None:
    first = generate_employees(count=50, seed=SEED)
    second = generate_employees(count=50, seed=SEED)

    assert first == second


def test_country_currency_and_salary_normalization_are_consistent() -> None:
    employees = generate_employees()
    countries = {country.code: country for country in COUNTRIES}

    for employee in employees:
        country = countries[employee["country"]]
        expected_usd = (employee["annual_salary_native"] * country.rate_to_usd).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        assert employee["currency"] == country.currency
        assert employee["salary_usd"] == expected_usd
        assert employee["annual_salary_native"] > 0
        assert employee["salary_usd"] > 0


def test_seed_uses_all_reference_values_and_valid_soft_delete_state() -> None:
    employees = generate_employees()

    assert {employee["country"] for employee in employees} == {
        country.code for country in COUNTRIES
    }
    assert {employee["department"] for employee in employees} == set(ROLE_BANDS)
    assert {employee["is_active"] for employee in employees} == {True, False}
    assert all(
        (employee["is_active"] and employee["deactivated_at"] is None)
        or (not employee["is_active"] and employee["deactivated_at"] is not None)
        for employee in employees
    )
