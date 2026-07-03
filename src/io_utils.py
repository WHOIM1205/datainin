"""Parquet-first IO (Module 3+). Preserves dtypes and tz-aware datetimes."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_parquet(df: pd.DataFrame, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, engine="pyarrow", index=False)
    return path


def load_parquet(path: Path | str) -> pd.DataFrame:
    return pd.read_parquet(path, engine="pyarrow")
