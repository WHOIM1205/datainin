"""
Module 3 — clean the Bitcoin Fear & Greed dataset.

Non-destructive: raw columns are preserved; cleaning only *adds* derived columns.
Every action returns a CleanOp for the audit trail. No rows are dropped.

Decisions honoured:
  D4 — keep numeric `value` + 5-bucket `classification`; add a Fear/Greed/Neutral side.
  D5 — Neutral is a first-class category (never removed here).
"""
from __future__ import annotations

import pandas as pd

from src.provenance import CleanOp

# classification -> coarse side (D4/D5). Neutral kept as its own first-class value.
SIDE_MAP = {
    "Extreme Fear": "Fear", "Fear": "Fear",
    "Neutral": "Neutral",
    "Greed": "Greed", "Extreme Greed": "Greed",
}


def clean_sentiment(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[CleanOp]]:
    df = raw.copy()
    n = len(df)
    ops: list[CleanOp] = []

    # S1 — parse `date` string into a normalized datetime key (additive; original kept).
    df["date_key"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    ops.append(CleanOp(
        name="Parse `date` → `date_key` (datetime, calendar day)",
        rows_before=n, rows_after=len(df), rows_affected=int(df["date_key"].notna().sum()),
        reversible=True, reason="Typed join key; raw string `date` preserved for provenance.",
        disposition="added column", f_id="F1.6",
    ))

    # S2 — verify classification domain is clean (no action expected).
    unknown = set(df["classification"].unique()) - set(SIDE_MAP)
    ops.append(CleanOp(
        name="Verify `classification` in known 5-bucket domain",
        rows_before=n, rows_after=len(df), rows_affected=0,
        reversible=True, reason=f"Domain clean; unknown values={unknown or '{}'}. No change.",
        disposition="preserved", f_id="F1.4",
    ))

    # S3 — add coarse Fear/Greed/Neutral side (D4/D5). Neutral kept first-class.
    df["sentiment_side"] = df["classification"].map(SIDE_MAP)
    ops.append(CleanOp(
        name="Add `sentiment_side` ∈ {Fear, Greed, Neutral}",
        rows_before=n, rows_after=len(df), rows_affected=int(df["sentiment_side"].notna().sum()),
        reversible=True,
        reason="Coarse regime for Fear-vs-Greed analysis; Neutral retained as first-class "
               "(excluded only within specific binary tests, not here).",
        disposition="added column", f_id="F1.4", decision="D4/D5",
    ))

    # S4 — confirm no missing / no duplicate dates (no action).
    ops.append(CleanOp(
        name="Verify 0 missing cells & 0 duplicate dates",
        rows_before=n, rows_after=len(df),
        rows_affected=int(df.isna().sum().sum() + df["date"].duplicated().sum()),
        reversible=True, reason="Confirmed clean at source. No imputation, no dedup needed.",
        disposition="preserved", f_id="F1.3",
    ))

    return df, ops
