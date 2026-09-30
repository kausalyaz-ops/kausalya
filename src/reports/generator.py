"""Machine-readable, plain-text, and Markdown executive summaries."""

import json
import math
from pathlib import Path
from typing import Any


class ReportGenerator:
    """Write summaries and a chart-embedded Markdown report."""

    def __init__(self, output_dir: Path, reports_dir: Path) -> None:
        self.output_dir = output_dir
        self.reports_dir = reports_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, summary: dict[str, Any], charts: list[str]) -> None:
        self._write_json(summary)
        self._write_text(summary)
        self._write_markdown(summary, charts)

    def _write_json(self, summary: dict[str, Any]) -> None:
        (self.output_dir / "analysis_summary.json").write_text(
            json.dumps(self._json_safe(summary), indent=4, allow_nan=False, default=self._json_default),
            encoding="utf-8",
        )

    def _write_text(self, summary: dict[str, Any]) -> None:
        dataset = summary["dataset"]
        stats = summary["statistics"]
        lines = [
            "EMPLOYEE COMPENSATION ANALYSIS",
            f"Source: {dataset['source']}",
            f"Cleaned compensation records: {dataset['cleaned_compensation_records']:,}",
            f"Fiscal years: {', '.join(map(str, dataset['fiscal_years']))}",
            f"Mean record salary: ${stats['mean_salary']:,.0f}",
            f"Median record salary: ${stats['median_salary']:,.0f}",
            "",
            "KEY FINDINGS",
            *[f"- {finding}" for finding in summary["key_findings"]],
            "",
            "CAVEAT: This capped extract contains compensation records, not verified unique employees.",
        ]
        (self.output_dir / "analysis_summary.txt").write_text("\n".join(lines), encoding="utf-8")

    def _write_markdown(self, summary: dict[str, Any], charts: list[str]) -> None:
        dataset = summary["dataset"]
        quality = summary["data_quality"]
        stats = summary["statistics"]
        department_rows = "\n".join(
            f"| {row['department']} | {row['record_count']:,} | ${row['avg_salary']:,.0f} | {row['overtime_share']:.1%} |"
            for row in sorted(summary["department_summary"], key=lambda row: row["avg_salary"], reverse=True)[:10]
        )
        annual_rows = "\n".join(
            f"| {row['year']} | {row['compensation_records']:,} | ${row['average_salary']:,.0f} |"
            for row in summary["annual_summary"]
        )
        chart_sections = "\n\n".join(
            f"### {Path(chart).stem.replace('_', ' ').title()}\n\n![{Path(chart).stem.replace('_', ' ')}](../charts/{chart})"
            for chart in charts
        )
        findings = "\n".join(f"{index}. {finding}" for index, finding in enumerate(summary["key_findings"], start=1))
        recommendations = "\n".join(f"- {item}" for item in summary["recommendations"])
        limitations = "\n".join(f"- {item}" for item in dataset["limitations"])
        content = f"""# Employee Compensation Analysis

## Executive Summary

The pipeline cleaned **{dataset['cleaned_compensation_records']:,} compensation records** from a capped public extract spanning fiscal years {', '.join(map(str, dataset['fiscal_years']))}. Mean record salary was **${stats['mean_salary']:,.0f}** and the median was **${stats['median_salary']:,.0f}**. Findings describe this extract only and should not be generalized to the full city workforce.

## Dataset Overview

- Source: [San Francisco Controller's Office Employee Compensation]({dataset['source_url']})
- Observation unit: {dataset['observation_unit']}
- Departments represented: {dataset['departments']}
- Distinct job titles: {dataset['unique_job_titles']}
- Fiscal years: {', '.join(map(str, dataset['fiscal_years']))}
- Selected fields: department, job family/title, fiscal year, salary components, total compensation, hours, and employment type. Direct employee identifiers were excluded.

## Data Quality Audit

- Source rows: {quality['rows_before']:,}; cleaned rows: {quality['rows_after']:,}
- Exact duplicates removed: {quality['duplicate_rows_removed']:,}
- Critical or negative-salary rows removed: {quality['critical_or_negative_salary_rows_removed']:,}
- Numeric median imputations: `{json.dumps(quality['numeric_median_imputations'], sort_keys=True)}`
- Missing values observed in raw fields: `{json.dumps(quality['source_missing_values'], sort_keys=True)}`

## Statistical Findings

- Mean salary: ${stats['mean_salary']:,.2f}; median: ${stats['median_salary']:,.2f}
- Standard deviation: ${stats['salary_standard_deviation']:,.2f}
- Range: ${stats['salary_minimum']:,.2f} to ${stats['salary_maximum']:,.2f}
- Hours/salary Pearson correlation: {stats['hours_salary_correlation']:.3f}
- A NumPy broadcasting example applied 3% and 5% scenarios to the first ten salary records; these are scenarios, not forecasts.

### Department Summary (Top 10 by Mean Record Salary)

| Department | Records | Mean salary | Overtime / salary |
|---|---:|---:|---:|
{department_rows}

### Annual Record Summary

| Fiscal year | Compensation records | Mean salary |
|---:|---:|---:|
{annual_rows}

## Visualizations

{chart_sections}

## Key Findings

{findings}

## Actionable Recommendations

{recommendations}

## Interpretation Limits

{limitations}

The secondary official budget dataset is left-joined on fiscal year and department code so all primary compensation records remain in scope. Unmatched budgets remain null. Because this extract is capped, no payroll-to-budget utilization ratio is reported.
"""
        (self.reports_dir / "analysis_report.md").write_text(content, encoding="utf-8")

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): ReportGenerator._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [ReportGenerator._json_safe(item) for item in value]
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        if hasattr(value, "item"):
            return ReportGenerator._json_safe(value.item())
        return value

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "item"):
            return value.item()
        if hasattr(value, "isoformat"):
            return value.isoformat()
        raise TypeError(f"Value of type {type(value).__name__} is not JSON serializable")