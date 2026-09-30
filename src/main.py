"""Run the end-to-end employee compensation analysis."""

import logging

import pandas as pd

from src.analysis.analyzer import DataAnalyzer
from src.api.client import APIClient
from src.config import settings
from src.data.cleaner import DataCleaner
from src.data.loader import DataLoader
from src.reports.generator import ReportGenerator
from src.visualization.charts import VisualizationManager


def run_pipeline() -> dict[str, object]:
    """Load, clean, enrich, analyze, visualize, and report."""
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    loader = DataLoader()
    source = loader.load()
    loader.inspect(source)

    cleaner = DataCleaner()
    cleaned = cleaner.clean(source)
    cleaned.to_csv(settings.PROCESSED_DIR / "cleaned_employees.csv", index=False)

    budget_rows = APIClient().fetch_department_budget(set(cleaned["year"].astype(int)))
    summary = DataAnalyzer().analyze(cleaned, cleaner.quality, budget_rows)
    charts = VisualizationManager(settings.CHARTS_DIR).render_all(
        cleaned,
        pd.DataFrame(summary["department_summary"]),
        pd.DataFrame(summary["annual_summary"]),
    )
    ReportGenerator(settings.OUTPUT_DIR, settings.REPORTS_DIR).generate(summary, charts)
    logging.info("Pipeline complete: %s cleaned rows; reports saved under %s", len(cleaned), settings.OUTPUT_DIR)
    return summary


if __name__ == "__main__":
    run_pipeline()