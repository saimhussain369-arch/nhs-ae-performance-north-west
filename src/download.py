"""Download the official NHS England Monthly A&E CSV files listed in data/sources.csv.

Files are saved unchanged to data/raw/ae_YYYY_MM.csv, and a manifest records the
URL, size, row count and SHA-256 of each file so every figure can be traced back
to the exact file it came from.
"""
from __future__ import annotations

import hashlib
import sys
import time
import urllib.request

import pandas as pd

import config

HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio data pipeline; github.com/saimhussain369-arch)"}


def fetch(url: str, attempts: int = 3) -> bytes:
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # network hiccup: wait and retry
            if i == attempts - 1:
                raise RuntimeError(f"Could not download {url}: {exc}") from exc
            time.sleep(3 * (i + 1))
    raise AssertionError("unreachable")


def main(force: bool = False) -> pd.DataFrame:
    config.RAW.mkdir(parents=True, exist_ok=True)
    sources = pd.read_csv(config.SOURCES)
    rows = []
    for s in sources.itertuples():
        path = config.RAW / f"ae_{s.month.replace('-', '_')}.csv"
        if force or not path.exists():
            path.write_bytes(fetch(s.url))
            print(f"downloaded {s.month}")
        body = path.read_bytes()
        rows.append({
            "month": s.month, "file": path.name, "url": s.url, "bytes": len(body),
            "lines": body.count(b"\n"), "sha256": hashlib.sha256(body).hexdigest(),
        })
    manifest = pd.DataFrame(rows)
    manifest.to_csv(config.RAW / "manifest.csv", index=False)
    return manifest


if __name__ == "__main__":
    main(force="--force" in sys.argv)
