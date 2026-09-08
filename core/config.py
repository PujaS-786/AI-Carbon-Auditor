import os
from pathlib import Path

# Base directory for the AI Carbon Auditor
BASE_DIR = Path(__file__).resolve().parent.parent

# Storage Paths
STORAGE_DIR = BASE_DIR / "storage"
RAW_DIR = STORAGE_DIR / "raw"
RAW_INVOICES_DIR = RAW_DIR / "invoices"
RAW_ERP_DIR = RAW_DIR / "erp"
RAW_UTILITY_DIR = RAW_DIR / "utility"
PROCESSED_DIR = STORAGE_DIR / "processed"
LEDGER_DIR = STORAGE_DIR / "ledger"
REPORTS_DIR = STORAGE_DIR / "reports"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

# File paths
LEDGER_FILE = LEDGER_DIR / "audit_ledger.jsonl"
HITL_RESOLUTIONS_FILE = PROCESSED_DIR / "hitl_resolutions.jsonl"
REPORTS_OUTPUT_JSON = REPORTS_DIR / "latest_disclosure.json"
REPORTS_OUTPUT_CSV = REPORTS_DIR / "latest_disclosure.csv"

# Auditor Configuration
CONFIDENCE_THRESHOLD = 0.85
OUTLIER_THRESHOLD_MULTIPLIER = 5.0
GENESIS_PREVIOUS_HASH = "0" * 64

# Ensure storage directories exist
for folder in [
    RAW_DIR, RAW_INVOICES_DIR, RAW_ERP_DIR, RAW_UTILITY_DIR,
    PROCESSED_DIR, LEDGER_DIR, REPORTS_DIR, SAMPLE_DATA_DIR
]:
    folder.mkdir(parents=True, exist_ok=True)
