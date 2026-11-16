"""Load the raw files into DuckDB and build the checked, reporting-ready tables."""
from __future__ import annotations

from pathlib import Path

import duckdb
from jinja2 import Template

import config
from load import load_raw

SQL = config.ROOT / "sql"


def render(name: str) -> str:
    return Template((SQL / name).read_text()).render(
        NUMERIC=config.NUMERIC, REGION=config.REGION, REGION_LABEL=config.REGION_LABEL,
        MIN_TYPE1_ATTENDANCES=config.MIN_TYPE1_ATTENDANCES,
    )


def run(db_path: Path = config.DB_PATH, raw_dir: Path = config.RAW,
        sources: Path = config.SOURCES) -> duckdb.DuckDBPyConnection:
    db_path.unlink(missing_ok=True)
    con = duckdb.connect(str(db_path))
    bronze = load_raw(raw_dir, sources)
    con.register("bronze_df", bronze)
    con.execute("CREATE TABLE bronze_ae AS SELECT * FROM bronze_df")
    for name in ("01_silver.sql", "02_dq_checks.sql", "03_gold.sql"):
        con.execute(render(name))
    return con


if __name__ == "__main__":
    c = run()
    print(c.sql("SELECT * FROM dq_summary"))
    print(c.sql("SELECT * FROM area_month WHERE month = (SELECT max(month) FROM area_month)"))
