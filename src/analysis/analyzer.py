"""Pandas aggregations and vectorized numerical summaries."""

from typing import Any

import numpy as np
import pandas as pd

from src.utils.helpers import high_salary_records, unique_values


class DataAnalyzer:
    """Compute metrics, relational enrichment, and data-backed findings."""

    def analyze(
        self, frame: pd.DataFrame, quality: dict[str, Any], budget_rows: list[dict[str, Any]]
    ) -> dict[str, Any]:
        enriched = self._merge_budget(frame, budget_rows)
        by_department = (
            enriched.groupby(["department_code", "department"], dropna=False)
            .agg(
                record_count=("record_id", "count"),
                avg_salary=("salary", "mean"),
                median_salary=("salary", "median"),
                max_salary=("salary", "max"),
                total_salary=("salary", "sum"),
                avg_hours=("hours", "mean"),
                total_overtime=("overtime", "sum"),
                salary_budget=("salary_budget", "first"),
            )
            .reset_index()
        )
        by_department["overtime_share"] = np.divide(
            by_department["total_overtime"],
            by_department["total_salary"].replace(0, np.nan),
        ).fillna(0.0)
        by_department["composite_score"] = self._weighted_department_score(by_department)
        by_year = (
            enriched.groupby("year")
            .agg(
                compensation_records=("record_id", "count"),
                average_salary=("salary", "mean"),
                median_salary=("salary", "median"),
                total_salary=("salary", "sum"),
                average_hours=("hours", "mean"),
            )
            .reset_index()
            .sort_values("year")
        )

        salary = enriched["salary"].to_numpy(dtype=float)
        hours = enriched["hours"].to_numpy(dtype=float)
        salary_column = salary.reshape(-1, 1)
        scenario_multipliers = np.array([1.03, 1.05])
        scenario_matrix = salary_column[:10] * scenario_multipliers
        salary_mean = float(np.mean(salary))
        salary_std = float(np.std(salary))
        correlation = float(np.corrcoef(hours, salary)[0, 1]) if len(salary) > 1 else 0.0
        high_pay = high_salary_records(enriched, limit=10)
        active_hours = list(filter(lambda value: value > 0, hours.tolist()))
        job_titles = unique_values(enriched["job"])
        minimum_maximum_salary = (float(np.min(salary)), float(np.max(salary)))
        department_summaries = by_department.to_dict(orient="records")
        annual_summaries = by_year.to_dict(orient="records")
        return {
            "dataset": {
                "source": "San Francisco Controller's Office Employee Compensation",
                "source_url": "https://data.sf.gov/City-Management-and-Ethics/Employee-Compensation/88g8-5mnd",
                "source_extract_rows": int(quality["rows_before"]),
                "cleaned_compensation_records": int(len(enriched)),
                "fiscal_years": [int(value) for value in sorted(enriched["year"].unique())],
                "departments": int(enriched["department_code"].nunique()),
                "unique_job_titles": len(job_titles),
                "observation_unit": "compensation record; not a unique employee",
                "limitations": [
                    "The extract is capped at the configured row limit and is not a complete workforce census.",
                    "Employee identifiers, demographics, hire dates, and experience are not available in the selected fields.",
                    "Annual record counts do not represent hires or verified headcount.",
                    "Department budgets are context only; partial extract totals are not used as budget-utilization ratios.",
                ],
            },
            "data_quality": quality,
            "statistics": {
                "mean_salary": salary_mean,
                "median_salary": float(np.median(salary)),
                "salary_standard_deviation": salary_std,
                "salary_minimum": minimum_maximum_salary[0],
                "salary_maximum": minimum_maximum_salary[1],
                "salary_total": float(np.sum(salary)),
                "hours_salary_correlation": correlation,
                "records_with_positive_hours": len(active_hours),
                "high_salary_threshold_90th_percentile": float(enriched["salary"].quantile(0.9)),
                "numpy_preview_10_by_2_salary_scenarios": scenario_matrix.tolist(),
            },
            "department_summary": department_summaries,
            "annual_summary": annual_summaries,
            "enrichment": {
                "budget_rows_received": len(budget_rows),
                "records_with_budget_match": int(enriched["salary_budget"].notna().sum()),
                "records_without_budget_match": int(enriched["salary_budget"].isna().sum()),
                "join": "left on fiscal year and department code",
            },
            "high_salary_records_preview": [
                {key: value for key, value in record.items() if key in {"year", "department", "job", "salary"}}
                for record in high_pay
            ],
            "key_findings": self._findings(by_department, by_year, salary_mean, correlation),
            "recommendations": self._recommendations(quality, by_department, correlation),
        }

    @staticmethod
    def _merge_budget(frame: pd.DataFrame, rows: list[dict[str, Any]]) -> pd.DataFrame:
        if not rows:
            return frame.assign(salary_budget=np.nan)
        budget = pd.DataFrame(rows)
        required = {"fiscal_year", "department_code", "salary_budget"}
        if not required.issubset(budget.columns):
            return frame.assign(salary_budget=np.nan)
        budget["year"] = pd.to_numeric(budget["fiscal_year"], errors="coerce")
        budget["salary_budget"] = pd.to_numeric(budget["salary_budget"], errors="coerce")
        budget = budget.dropna(subset=["year", "department_code"])
        budget["year"] = budget["year"].astype(int)
        budget = budget.drop_duplicates(["year", "department_code"])
        return pd.merge(
            frame,
            budget[["year", "department_code", "salary_budget"]],
            on=["year", "department_code"],
            how="left",
            validate="many_to_one",
        )

    @staticmethod
    def _weighted_department_score(by_department: pd.DataFrame) -> np.ndarray:
        features = by_department[["avg_salary", "overtime_share"]].to_numpy(dtype=float)
        maxima = np.nanmax(features, axis=0)
        normalized = np.divide(features, maxima, out=np.zeros_like(features), where=maxima != 0)
        weights = np.array([0.7, 0.3])
        return np.dot(normalized, weights)

    @staticmethod
    def _findings(
        department: pd.DataFrame, annual: pd.DataFrame, salary_mean: float, correlation: float
    ) -> list[str]:
        if department.empty or annual.empty:
            return ["The extract is too small to support department or annual findings."]
        highest_pay = department.loc[department["avg_salary"].idxmax()]
        lowest_pay = department.loc[department["avg_salary"].idxmin()]
        overtime_department = department.loc[department["overtime_share"].idxmax()]
        busiest_year = annual.loc[annual["compensation_records"].idxmax()]
        largest_yearly_mean = annual.loc[annual["average_salary"].idxmax()]
        pay_ratio = highest_pay["avg_salary"] / max(float(lowest_pay["avg_salary"]), 1.0)
        return [
            (
                f"{highest_pay['department']} has the highest mean record salary "
                f"(${highest_pay['avg_salary']:,.0f}; n={int(highest_pay['record_count'])}); "
                f"{lowest_pay['department']} is lowest (${lowest_pay['avg_salary']:,.0f})."
            ),
            f"The highest department mean is {pay_ratio:.2f}x the lowest department mean in this extract.",
            (
                f"{overtime_department['department']} has the largest overtime-to-salary ratio "
                f"({overtime_department['overtime_share']:.1%}) among represented departments."
            ),
            (
                f"Fiscal {int(busiest_year['year'])} has the most compensation records "
                f"({int(busiest_year['compensation_records'])}); this is record volume, not hiring activity."
            ),
            (
                f"Mean record salary is ${salary_mean:,.0f}; hours-versus-salary correlation is "
                f"{correlation:.2f}. Fiscal {int(largest_yearly_mean['year'])} has the highest annual mean "
                f"(${largest_yearly_mean['average_salary']:,.0f})."
            ),
        ]

    @staticmethod
    def _recommendations(
        quality: dict[str, Any], department: pd.DataFrame, correlation: float
    ) -> list[str]:
        recommendations = [
            "Treat compensation records as observations, not employees; obtain a de-identified employee key before estimating headcount or retention.",
            "Add hire-date and experience fields from an authorized HR source before interpreting tenure or hiring trends.",
        ]
        if quality["rows_removed_total"] or quality["numeric_median_imputations"]:
            recommendations.append("Review the data-quality exceptions before using this extract for operational pay decisions.")
        else:
            recommendations.append("Retain the data-quality audit on refresh; this extract required no critical-row removal or numeric imputation.")
        if not department["salary_budget"].notna().any():
            recommendations.append("Resolve unmatched fiscal-year/department budget keys before comparing salary budgets with compensation.")
        if abs(correlation) >= 0.5:
            recommendations.append("Investigate the observed hours-pay association with job family and employment type controls before attributing cause.")
        else:
            recommendations.append("Do not use hours alone as a pay proxy; compare compensation within job family and employment type.")
        return recommendations[:5]