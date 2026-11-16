"""Read the raw NHS England files into DuckDB, unchanged apart from column names."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import config


def read_month(path: Path, month: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, skip_blank_lines=True)
    df.columns = [c.strip() for c in df.columns]
    unknown = set(df.columns) - set(config.COLUMNS)
    missing = set(config.COLUMNS) - set(df.columns)
    if unknown or missing:
        raise ValueError(f"{path.name}: header changed. Missing {sorted(missing)}, unexpected {sorted(unknown)}")
    df = df.rename(columns=config.COLUMNS)
    df = df[df.org_code.str.strip() != ""]
    df.insert(0, "month", month)
    df.insert(1, "source_file", path.name)
    return df


def load_raw(raw_dir: Path = config.RAW, sources: Path = config.SOURCES) -> pd.DataFrame:
    months = pd.read_csv(sources).month
    frames = [read_month(raw_dir / f"ae_{m.replace('-', '_')}.csv", m) for m in months]
    return pd.concat(frames, ignore_index=True)
