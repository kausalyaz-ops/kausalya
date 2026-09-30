"""Small reusable filtering and formatting helpers."""

from collections.abc import Iterable
from typing import Any

import pandas as pd


def sanitize_strings(values: Iterable[Any]) -> list[str]:
    """Normalize text values and drop empty entries."""
    return list(filter(None, map(lambda value: str(value).strip(), values)))


def unique_values(values: Iterable[Any]) -> set[str]:
    """Return normalized distinct values."""
    return set(sanitize_strings(values))


def filter_records(frame: pd.DataFrame, **filters: Any) -> pd.DataFrame:
    """Apply exact-match filters for any provided column/value pairs."""
    result = frame
    for column, value in filters.items():
        if column in result.columns:
            result = result.loc[result[column] == value]
    return result


def high_salary_records(
    frame: pd.DataFrame, threshold: float | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    """Return high-pay records, stopping at an optional result limit."""
    if frame.empty or "salary" not in frame:
        return []
    cutoff = threshold if threshold is not None else float(frame["salary"].quantile(0.9))
    records: list[dict[str, Any]] = []
    for record in frame.to_dict(orient="records"):
        salary = record.get("salary")
        if pd.isna(salary) or salary < cutoff:
            continue
        if limit is not None and len(records) >= limit:
            break
        records.append(record)
    return records


def sort_by_salary(frame: pd.DataFrame, descending: bool = True) -> pd.DataFrame:
    """Sort compensation rows using a compact key function."""
    if "salary" not in frame:
        return frame.copy()
    return frame.sort_values(by="salary", key=lambda values: values, ascending=not descending)