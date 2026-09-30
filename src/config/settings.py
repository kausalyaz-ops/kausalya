"""Centralized paths and environment-backed settings."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "outputs"
CHARTS_DIR = OUTPUT_DIR / "charts"
REPORTS_DIR = OUTPUT_DIR / "reports"
CACHE_DIR = OUTPUT_DIR / "cache"

EMPLOYEE_DATA_URL = os.getenv(
    "EMPLOYEE_DATA_URL", "https://data.sf.gov/resource/88g8-5mnd.json"
)
DEPARTMENT_BUDGET_API_URL = os.getenv(
    "DEPARTMENT_BUDGET_API_URL", "https://data.sf.gov/resource/xdgd-c79v.json"
)
SOCRATA_APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN", "").strip()
DATA_LIMIT = max(500, int(os.getenv("DATA_LIMIT", "5000")))
REQUEST_TIMEOUT = max(1, int(os.getenv("REQUEST_TIMEOUT", "10")))