"""Shared settings for the NHS A&E performance pipeline."""
from pathlib import Path

import pandas as pd

try:  # keep classic object strings so DuckDB reads pandas frames on pandas 2.x and 3.x
    pd.set_option("future.infer_string", False)
except (KeyError, ValueError):
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
SOURCES = DATA / "sources.csv"
OUTPUTS = ROOT / "outputs"
DOCS = ROOT / "docs"
IMAGES = DOCS / "images"
DB_PATH = DATA / "ae.duckdb"

REGION = "NHS ENGLAND NORTH WEST"
REGION_LABEL = "North West"

# Operational standards from NHS England planning guidance
TARGETS = [
    {"label": "78% by March 2026 (2025/26 plan)", "value": 78.0, "from": "2025-04", "to": "2026-03"},
    {"label": "82% by March 2027 (2026/27 plan)", "value": 82.0, "from": "2026-04", "to": "2027-03"},
]
CONSTITUTIONAL_STANDARD = 95.0

# A trust is shown in the league table only if it runs a major (Type 1) emergency department
MIN_TYPE1_ATTENDANCES = 1000

# Column names exactly as published by NHS England (Monthly A&E CSV)
COLUMNS = {
    "Period": "period",
    "Org Code": "org_code",
    "Parent Org": "parent_org",
    "Org name": "org_name",
    "A&E attendances Type 1": "att_type1",
    "A&E attendances Type 2": "att_type2",
    "A&E attendances Other A&E Department": "att_other",
    "A&E attendances Booked Appointments Type 1": "att_booked_type1",
    "A&E attendances Booked Appointments Type 2": "att_booked_type2",
    "A&E attendances Booked Appointments Other Department": "att_booked_other",
    "Attendances over 4hrs Type 1": "over4_type1",
    "Attendances over 4hrs Type 2": "over4_type2",
    "Attendances over 4hrs Other Department": "over4_other",
    "Attendances over 4hrs Booked Appointments Type 1": "over4_booked_type1",
    "Attendances over 4hrs Booked Appointments Type 2": "over4_booked_type2",
    "Attendances over 4hrs Booked Appointments Other Department": "over4_booked_other",
    "Patients who have waited 4-12 hs from DTA to admission": "dta_4_12h",
    "Patients who have waited 12+ hrs from DTA to admission": "dta_12h_plus",
    "Emergency admissions via A&E - Type 1": "adm_type1",
    "Emergency admissions via A&E - Type 2": "adm_type2",
    "Emergency admissions via A&E - Other A&E department": "adm_other",
    "Other emergency admissions": "adm_other_emergency",
}
NUMERIC = [c for c in COLUMNS.values() if c not in ("period", "org_code", "parent_org", "org_name")]
