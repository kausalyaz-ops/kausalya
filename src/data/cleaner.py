"""Type standardization, deduplication, and missing-value handling."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd

from src.utils.exceptions import InvalidDatasetError
from src.utils.helpers import sanitize_strings

NUMERIC_COLUMNS = (
    "salaries",
    "overtime",
    "other_salaries",
    "total_salary",
    "total_benefits",
    "total_compensation",
    "hours",
)


class BaseDataProcessor(ABC):
    """Base contract for domain-specific data processors."""

    def __init__(self, required_columns: set[str]) -> None:
        self.required_columns = required_columns

    @abstractmethod
    def process(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Validate and standardize source columns."""


class EmployeeDataProcessor(BaseDataProcessor):
    """Standardize compensation fields while preserving source measures."""

    def __init__(self) -> None:
        super().__init__({"year", "department_code", "department", "job", "total_salary"})

    def process(self, frame: pd.DataFrame) -> pd.DataFrame:
        missing = self.required_columns.difference(frame.columns)
        if missing:
            raise InvalidDatasetError(f"Required source columns are missing: {sorted(missing)}")

        result = frame.copy()
        for column in ("department", "department_code", "organization_group", "job_family", "job"):
            if column in result:
                result[column] = result[column].fillna("").astype(str).str.strip()
        result["year"] = pd.to_numeric(result["year"], errors="coerce")
        for column in NUMERIC_COLUMNS:
            if column in result:
                result[column] = pd.to_numeric(result[column], errors="coerce")
        return result


class DataCleaner:
    """Clean source records and retain an auditable quality summary."""

    def __init__(self, processor: BaseDataProcessor | None = None) -> None:
        self.processor = processor or EmployeeDataProcessor()
        self.quality: dict[str, Any] = {}

    def clean(self, source: pd.DataFrame) -> pd.DataFrame:
        before = len(source)
        missing_before = {str(key): int(value) for key, value in source.isna().sum().items()}
        frame = self.processor.process(source)
        duplicates = int(frame.duplicated().sum())
        frame = frame.drop_duplicates().copy()
        invalid_critical = frame["year"].isna() | frame["total_salary"].isna()
        invalid_critical |= frame["department_code"].eq("") | frame["job"].eq("")
        invalid_salary = frame["total_salary"].lt(0).fillna(False)
        dropped = int((invalid_critical | invalid_salary).sum())
        frame = frame.loc[~(invalid_critical | invalid_salary)].copy()
        imputed: dict[str, int] = {}
        for column in NUMERIC_COLUMNS:
            if column in frame:
                missing = int(frame[column].isna().sum())
                if missing:
                    median = frame[column].median()
                    if pd.notna(median):
                        frame[column] = frame[column].fillna(median)
                        imputed[column] = missing
        if frame.empty:
            raise InvalidDatasetError("No valid records remain after critical-value validation.")

        frame["year"] = frame["year"].astype("int64")
        frame["salary"] = frame["total_salary"]
        frame["record_id"] = np.arange(1, len(frame) + 1, dtype=np.int64)
        self.quality = {
            "rows_before": before,
            "rows_after": int(len(frame)),
            "duplicate_rows_removed": duplicates,
            "critical_or_negative_salary_rows_removed": dropped,
            "numeric_median_imputations": imputed,
            "source_missing_values": missing_before,
            "rows_removed_total": int(before - len(frame)),
        }
        return frame.reset_index(drop=True)