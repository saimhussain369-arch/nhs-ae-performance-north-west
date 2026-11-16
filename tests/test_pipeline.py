"""Tests run against small files in the exact NHS England layout, built here so every answer is known."""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import config  # noqa: E402
import pipeline  # noqa: E402

HEADER = list(config.COLUMNS)

# org_code, region, name, type1 att, other att, booked type1, type1 over4, other over4, booked type1 over4, dta12, adm type1
PROVIDERS = [
    ("RW6", "NHS ENGLAND NORTH WEST", "PENNINE ACUTE HOSPITALS NHS TRUST", 10000, 2000, 500, 3500, 100, 50, 300, 2500),
    ("RJR", "NHS ENGLAND NORTH WEST", "COUNTESS OF CHESTER HOSPITAL NHS FOUNDATION TRUST", 6000, 2500, 0, 3000, 400, 0, 700, 2000),
    ("NQT5F", "NHS ENGLAND NORTH WEST", "SKELMERSDALE WALK IN CENTRE", 0, 1700, 0, 0, 20, 0, 0, 0),
    ("RAL", "NHS ENGLAND LONDON", "ROYAL FREE LONDON NHS FOUNDATION TRUST, HAMPSTEAD", 12000, 5000, 0, 4000, 200, 0, 900, 3000),
]


def provider_row(period, p):
    code, region, name, t1, oth, b1, o1, ooth, ob1, dta12, adm1 = p
    vals = [t1, 0, oth, b1, 0, 0, o1, 0, ooth, ob1, 0, 0, 0, dta12, adm1, 0, 0, 0]
    return [period, code, region, name] + vals


def write_month(raw: Path, month: str, period: str, providers=PROVIDERS, total_override=None):
    rows = [provider_row(period, p) for p in providers]
    total = [sum(r[i] for r in rows) for i in range(4, 22)]
    if total_override:
        total = total_override(total)
    with open(raw / f"ae_{month.replace('-', '_')}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
        w.writerow(["TOTAL"] * 4 + total)


@pytest.fixture
def data_dir(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (tmp_path / "sources.csv").write_text("month,url\n2026-09,x\n2026-10,y\n")
    write_month(raw, "2026-09", "MSitAE-SEPTEMBER-2026")
    write_month(raw, "2026-10", "MSitAE-OCTOBER-2026")
    return tmp_path


def run(data_dir):
    return pipeline.run(data_dir / "t.duckdb", data_dir / "raw", data_dir / "sources.csv")


def test_four_hour_percentage_matches_hand_calculation(data_dir):
    con = run(data_dir)
    att = 10000 + 2000 + 500 + 6000 + 2500 + 1700 + 12000 + 5000
    over = 3500 + 100 + 50 + 3000 + 400 + 20 + 4000 + 200
    eng = con.sql("SELECT pct_within_4h FROM area_month WHERE area = 'England' AND month = DATE '2026-10-01'").fetchone()[0]
    assert eng == round(100 * (1 - over / att), 1)

    nw_att = 10000 + 2000 + 500 + 6000 + 2500 + 1700
    nw_over = 3500 + 100 + 50 + 3000 + 400 + 20
    nw = con.sql("SELECT pct_within_4h FROM area_month WHERE area = 'North West' AND month = DATE '2026-10-01'").fetchone()[0]
    assert nw == round(100 * (1 - nw_over / nw_att), 1)


def test_type1_rate_uses_booked_type1_too(data_dir):
    con = run(data_dir)
    got = con.sql("SELECT pct_within_4h_type1 FROM trust_month WHERE org_code = 'RW6' LIMIT 1").fetchone()[0]
    assert got == round(100 * (1 - (3500 + 50) / (10000 + 500)), 1)


def test_league_table_only_includes_major_eds_in_region(data_dir):
    con = run(data_dir)
    codes = {r[0] for r in con.sql("SELECT org_code FROM trust_latest_quarter").fetchall()}
    assert codes == {"RW6", "RJR"}  # walk-in centre and London trust excluded


def test_clean_files_pass_every_check(data_dir):
    con = run(data_dir)
    assert con.sql("SELECT count(*) FROM dq_failures").fetchone()[0] == 0
    assert {r[0] for r in con.sql("SELECT status FROM dq_summary").fetchall()} == {"Pass"}


def test_reconciliation_catches_a_total_that_does_not_add_up(data_dir):
    write_month(data_dir / "raw", "2026-10", "MSitAE-OCTOBER-2026", total_override=lambda t: [t[0] + 5] + t[1:])
    con = run(data_dir)
    fails = con.sql("SELECT check_name FROM dq_failures").fetchall()
    assert ("providers_reconcile_to_published_total",) in fails


def test_wrong_period_and_impossible_counts_are_caught(data_dir):
    bad = list(PROVIDERS)
    bad[1] = ("RJR", "NHS ENGLAND NORTH WEST", "COUNTESS", 100, 0, 0, 500, 0, 0, 0, 0)  # 500 over 4h out of 100
    write_month(data_dir / "raw", "2026-10", "MSitAE-SEPTEMBER-2026", providers=bad)
    con = run(data_dir)
    fails = {r[0] for r in con.sql("SELECT check_name FROM dq_failures").fetchall()}
    assert {"period_matches_file", "over_4h_not_above_attendances"} <= fails


def test_changed_header_stops_the_load(data_dir):
    path = data_dir / "raw" / "ae_2026_10.csv"
    path.write_text(path.read_text().replace("Org name", "Organisation Name", 1))
    with pytest.raises(ValueError, match="header changed"):
        run(data_dir)
