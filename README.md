# Employee Compensation Analysis

A modular data pipeline for inspecting, cleaning, analyzing, enriching, and reporting on public employee compensation data.

## Data sources

- Primary: [San Francisco Employee Compensation](https://data.sf.gov/City-Management-and-Ethics/Employee-Compensation/88g8-5mnd), maintained by the San Francisco Controller's Office. The pipeline requests up to 5,000 rows and excludes employee names and other direct identifiers.
- Secondary: [San Francisco Budget](https://data.sf.gov/City-Management-and-Ethics/Budget/xdgd-c79v), queried for salary-object spending and aggregated by fiscal year and department.

The primary extract contains compensation records, not a longitudinal employee roster. It does not provide reliable employee IDs, age, gender, hire dates, or years of experience. Consequently, the pipeline reports record counts, fiscal-year patterns, and hours-versus-pay; it does not describe these as headcount, hiring, demographics, tenure, or attrition. Budget-to-payroll utilization is not inferred from the limited extract.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m src.main
```

The first run downloads the source extract into `data/raw/`. If the budget API is unavailable, analysis and reports still complete without the optional enrichment. Set `SOCRATA_APP_TOKEN` in `.env` if the open-data service requests an application token. `DATA_LIMIT` and `REQUEST_TIMEOUT` can be adjusted there.

## Outputs

- `data/processed/cleaned_employees.csv`: cleaned compensation records.
- `data/raw/departments.csv`: budget records returned by the secondary API.
- `outputs/charts/`: five Matplotlib figures.
- `outputs/reports/analysis_report.md`: executive report with embedded charts.
- `outputs/analysis_summary.json` and `outputs/analysis_summary.txt`: structured metrics and concise briefing.
- `outputs/cache/`: API response metadata and cached department budget data.

Generated `outputs/` are excluded from Git by design; they are recreated by each pipeline run.