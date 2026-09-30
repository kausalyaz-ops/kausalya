"""Public compensation data ingestion and schema inspection."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.config import settings
from src.utils.exceptions import InvalidDatasetError

LOGGER = logging.getLogger(__name__)
SOURCE_FIELDS = (
    "year,department_code,department,organization_group,job_family,job,"
    "salaries,overtime,other_salaries,total_salary,total_benefits,"
    "total_compensation,hours,employment_type"
)
REQUIRED_COLUMNS = {"year", "department_code", "department", "job", "total_salary"}


class DataLoader:
    """Load a local immutable extract, downloading it once when absent."""

    def __init__(self, source_path: Path | None = None) -> None:
        self.source_path = source_path or settings.RAW_DIR / "employees.csv"

    def load(self) -> pd.DataFrame:
        if not self.source_path.exists():
            self.download()
        frame = pd.read_csv(self.source_path)
        missing = REQUIRED_COLUMNS.difference(frame.columns)
        if missing:
            raise InvalidDatasetError(f"Required source columns are missing: {sorted(missing)}")
        if frame.empty:
            raise InvalidDatasetError("The source dataset contains no records.")
        LOGGER.info("Loaded %s source records from %s", len(frame), self.source_path)
        return frame

    def download(self) -> Path:
        self.source_path.parent.mkdir(parents=True, exist_ok=True)
        params: dict[str, Any] = {"$select": SOURCE_FIELDS, "$limit": settings.DATA_LIMIT}
        headers = {"X-App-Token": settings.SOCRATA_APP_TOKEN} if settings.SOCRATA_APP_TOKEN else {}
        attempt = 0
        while attempt < 2:
            try:
                response = requests.get(
                    settings.EMPLOYEE_DATA_URL,
                    params=params,
                    headers=headers,
                    timeout=settings.REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                rows = response.json()
                break
            except requests.exceptions.Timeout as exc:
                attempt += 1
                if attempt == 2:
                    raise InvalidDatasetError(
                        "Timed out twice while downloading the public source dataset."
                    ) from exc
                LOGGER.warning("Source request timed out; retrying once")
                continue
            except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError) as exc:
                raise InvalidDatasetError(f"Could not download a valid source dataset: {exc}") from exc
        if not isinstance(rows, list) or not rows:
            raise InvalidDatasetError("The public source returned no compensation records.")
        frame = pd.DataFrame(rows)
        missing = REQUIRED_COLUMNS.difference(frame.columns)
        if missing:
            raise InvalidDatasetError(f"Required source columns are missing: {sorted(missing)}")
        frame.to_csv(self.source_path, index=False)
        LOGGER.info("Saved %s privacy-filtered records to %s", len(frame), self.source_path)
        return self.source_path

    @staticmethod
    def inspect(frame: pd.DataFrame) -> dict[str, Any]:
        """Log common Pandas profiles and return a JSON-friendly baseline."""
        LOGGER.info("Dataset shape: %s", frame.shape)
        LOGGER.info("Dataset columns and types:\n%s", frame.dtypes.to_string())
        LOGGER.info("Head:\n%s", frame.head().to_string(index=False))
        LOGGER.info("Tail:\n%s", frame.tail().to_string(index=False))
        LOGGER.info("Describe:\n%s", frame.describe(include="all").to_string())
        frame.info(buf=None)
        return {
            "rows": int(frame.shape[0]),
            "columns": int(frame.shape[1]),
            "column_names": [str(column) for column in frame.columns],
            "missing_values": {str(key): int(value) for key, value in frame.isna().sum().items()},
        }