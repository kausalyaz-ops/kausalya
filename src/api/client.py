"""Resilient client for department salary-budget data."""

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.config import settings

LOGGER = logging.getLogger(__name__)


class APIClient:
    """Fetch, validate, and cache the official department budget benchmark."""

    def __init__(self, endpoint: str | None = None, timeout: int | None = None) -> None:
        self.endpoint = endpoint or settings.DEPARTMENT_BUDGET_API_URL
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self.cache_path = settings.CACHE_DIR / "department_budget.json"
        self.metadata_path = settings.CACHE_DIR / "api_metadata.json"

    def get_json(self, params: dict[str, Any]) -> list[dict[str, Any]] | None:
        headers = {"X-App-Token": settings.SOCRATA_APP_TOKEN} if settings.SOCRATA_APP_TOKEN else {}
        response: requests.Response | None = None
        try:
            response = requests.get(self.endpoint, params=params, headers=headers, timeout=self.timeout)
            if response.status_code in {400, 401, 404, 500}:
                LOGGER.warning("Budget API returned HTTP %s", response.status_code)
            response.raise_for_status()
            payload = json.loads(response.text)
            if not isinstance(payload, list):
                LOGGER.warning("Budget API returned an unexpected JSON shape")
                return None
            return payload
        except requests.exceptions.Timeout:
            LOGGER.warning("Budget API request timed out; trying the local cache")
        except requests.exceptions.RequestException as exc:
            LOGGER.warning("Budget API request failed: %s", exc)
        except json.JSONDecodeError as exc:
            LOGGER.warning("Budget API returned invalid JSON: %s", exc)
        finally:
            if response is not None:
                LOGGER.info("Budget API request completed with HTTP %s", response.status_code)
        return self._read_cache()

    def fetch_department_budget(self, years: set[int]) -> list[dict[str, Any]]:
        """Aggregate official salary-object budgets by fiscal year and department."""
        if not years:
            return []
        year_filter = ", ".join(f"'{year}'" for year in sorted(years))
        params = {
            "$select": "fiscal_year,department_code,department,sum(budget) as salary_budget",
            "$where": (
                "character_code='001' AND revenue_or_spending='Spending' "
                f"AND fiscal_year in ({year_filter})"
            ),
            "$group": "fiscal_year,department_code,department",
            "$limit": 50000,
        }
        rows = self.get_json(params)
        if not rows:
            return []
        settings.RAW_DIR.mkdir(parents=True, exist_ok=True)
        Path(settings.RAW_DIR / "departments.csv").write_text(
            self._rows_to_csv(rows), encoding="utf-8"
        )
        settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(rows, indent=4), encoding="utf-8")
        metadata = {
            "endpoint": self.endpoint,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "records": len(rows),
            "fiscal_years": sorted({str(row.get("fiscal_year", "")) for row in rows}),
        }
        self.metadata_path.write_text(json.dumps(metadata, indent=4), encoding="utf-8")
        return rows

    def _read_cache(self) -> list[dict[str, Any]] | None:
        if not self.cache_path.exists():
            return None
        try:
            value = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else None
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Could not read budget cache: %s", exc)
            return None

    @staticmethod
    def _rows_to_csv(rows: list[dict[str, Any]]) -> str:
        buffer = io.StringIO()
        columns = list(rows[0]) if rows else []
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue()