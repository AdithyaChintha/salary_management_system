from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.repositories.analytics import (
    AnalyticsFilters,
    Distribution,
    PayBand,
    WorkforceAnalytics,
)

MONEY = Decimal("0.01")


def _money(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


class PostgresAnalyticsRepository:
    """Aggregate one filtered, active workforce without transferring employee rows."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def calculate(self, filters: AnalyticsFilters) -> WorkforceAnalytics:
        conditions = ["e.is_active = TRUE"]
        params: list[object] = []
        if filters.country is not None:
            conditions.append("(c.code ILIKE %s OR c.name ILIKE %s)")
            params.extend((filters.country, filters.country))
        if filters.department is not None:
            conditions.append("e.department = %s")
            params.append(filters.department)
        if filters.min_salary_usd is not None:
            conditions.append("e.salary_usd >= %s")
            params.append(filters.min_salary_usd)
        if filters.max_salary_usd is not None:
            conditions.append("e.salary_usd <= %s")
            params.append(filters.max_salary_usd)
        source = " FROM employees e JOIN countries c ON c.code = e.country WHERE " + " AND ".join(
            conditions
        )

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            # All queries observe the same workforce even if CRUD occurs concurrently.
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT count(*) AS headcount,
                           coalesce(sum(e.salary_usd), 0) AS payroll,
                           avg(e.salary_usd) AS average,
                           min(e.salary_usd) AS lowest,
                           max(e.salary_usd) AS highest,
                           percentile_cont(ARRAY[0.25, 0.50, 0.75])
                               WITHIN GROUP (ORDER BY e.salary_usd) AS cutoffs
                    """
                    + source,
                    params,
                )
                summary = cursor.fetchone()
                assert summary is not None
                cutoffs = tuple(_money(item) for item in (summary["cutoffs"] or [None] * 3))
                assert len(cutoffs) == 3

                cursor.execute(
                    "SELECT e.department AS name, count(*) AS headcount"
                    + source
                    + " GROUP BY e.department ORDER BY headcount DESC, name ASC",
                    params,
                )
                departments = [
                    Distribution(name=row["name"], headcount=row["headcount"])
                    for row in cursor.fetchall()
                ]

                cursor.execute(
                    "SELECT c.name AS name, count(*) AS headcount"
                    + source
                    + " GROUP BY c.name ORDER BY headcount DESC, name ASC",
                    params,
                )
                countries = [
                    Distribution(name=row["name"], headcount=row["headcount"])
                    for row in cursor.fetchall()
                ]

                if summary["headcount"]:
                    # Compare with unrounded cutoffs so band counts match percentile_cont exactly.
                    p25, p50, p75 = summary["cutoffs"]
                    cursor.execute(
                        """
                        SELECT count(*) FILTER (WHERE e.salary_usd <= %s) AS q1,
                               count(*) FILTER (WHERE e.salary_usd > %s
                                                   AND e.salary_usd <= %s) AS q2,
                               count(*) FILTER (WHERE e.salary_usd > %s
                                                   AND e.salary_usd <= %s) AS q3,
                               count(*) FILTER (WHERE e.salary_usd > %s) AS q4
                        """
                        + source,
                        [p25, p25, p50, p50, p75, p75, *params],
                    )
                    counts = cursor.fetchone()
                    assert counts is not None
                    band_counts = (counts["q1"], counts["q2"], counts["q3"], counts["q4"])
                else:
                    band_counts = (0, 0, 0, 0)

        bands = [
            PayBand("p0_p25", _money(summary["lowest"]), cutoffs[0], band_counts[0]),
            PayBand("p25_p50", cutoffs[0], cutoffs[1], band_counts[1]),
            PayBand("p50_p75", cutoffs[1], cutoffs[2], band_counts[2]),
            PayBand("p75_p100", cutoffs[2], _money(summary["highest"]), band_counts[3]),
        ]
        return WorkforceAnalytics(
            active_headcount=summary["headcount"],
            total_payroll_usd=_money(summary["payroll"]) or Decimal("0.00"),
            average_salary_usd=_money(summary["average"]),
            median_salary_usd=cutoffs[1],
            highest_salary_usd=_money(summary["highest"]),
            lowest_salary_usd=_money(summary["lowest"]),
            department_distribution=departments,
            country_distribution=countries,
            quartile_cutoffs_usd=cutoffs,
            percentile_pay_bands=bands,
        )
