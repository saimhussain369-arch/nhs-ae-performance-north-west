"""Run end to end: download -> load -> check -> report."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import download  # noqa: E402
import pipeline  # noqa: E402
import report  # noqa: E402


def main() -> None:
    print("1/3 downloading NHS England Monthly A&E files")
    download.main()
    print("2/3 loading and checking in DuckDB")
    con = pipeline.run()
    print(con.sql("SELECT check_name, status, failures FROM dq_summary"))
    failed = con.sql("SELECT count(*) FROM dq_summary WHERE status = 'Fail'").fetchone()[0]
    print("3/3 writing extracts, charts and summary")
    report.extracts(con)
    report.charts(con)
    report.summary(con)
    print(con.sql("SELECT * FROM area_month WHERE month = (SELECT max(month) FROM area_month)"))
    if failed:
        sys.exit(f"{failed} data quality check(s) failed - see outputs/dq_summary.csv")


if __name__ == "__main__":
    main()
