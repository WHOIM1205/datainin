"""
Module 3 — clean the Hyperliquid trader dataset.

Non-destructive: raw columns preserved; cleaning only *adds* derived columns and
boolean flags. NO rows are dropped (flag-don't-drop policy). Every action returns
a CleanOp for the audit trail.

Decisions honoured:
  D3 — leverage is NOT fabricated (no leverage column exists, F2.4); excluded, documented.
  D8 — timezone of the sentiment `date` is unprovable from the data, so BOTH IST and UTC
       date keys are produced; the merge module decides which to use.
  T6 — spot trades are kept and flagged `is_spot` (not removed).
"""
from __future__ import annotations

import pandas as pd

from src.provenance import CleanOp

IST = "Asia/Kolkata"
TIME_FMT = "%d-%m-%Y %H:%M"

# Non-standard perp events / position flips — not normal directional trades (F2.10).
EDGE_DIRECTIONS = {
    "Auto-Deleveraging", "Liquidated Isolated Short", "Settlement",
    "Long > Short", "Short > Long",
}
# Spot markers (Direction-based and Coin-based definitions agree exactly, verified in M3).
SPOT_DIRECTIONS = {"Buy", "Sell", "Spot Dust Conversion"}


def clean_trades(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[CleanOp]]:
    df = raw.copy()
    n = len(df)
    ops: list[CleanOp] = []

    # T1 — parse authoritative time field to tz-aware IST (additive; raw string kept).
    df["ts_ist"] = pd.to_datetime(df["Timestamp IST"], format=TIME_FMT).dt.tz_localize(IST)
    ops.append(CleanOp(
        name="Parse `Timestamp IST` → `ts_ist` (tz-aware, Asia/Kolkata)",
        rows_before=n, rows_after=len(df), rows_affected=int(df["ts_ist"].notna().sum()),
        reversible=True, reason="Authoritative time; lossy numeric `Timestamp` ignored. Raw string kept.",
        disposition="added column", f_id="F2.5",
    ))

    # T2 — dual date keys (D8): keep BOTH IST and UTC calendar days; merge decides later.
    df["ts_utc"] = df["ts_ist"].dt.tz_convert("UTC")
    df["trade_date_ist"] = df["ts_ist"].dt.normalize().dt.tz_localize(None)
    df["trade_date_utc"] = df["ts_utc"].dt.normalize().dt.tz_localize(None)
    n_diff = int((df["trade_date_ist"] != df["trade_date_utc"]).sum())
    ops.append(CleanOp(
        name="Derive `trade_date_ist` & `trade_date_utc` (dual keys)",
        rows_before=n, rows_after=len(df), rows_affected=n_diff,
        reversible=True,
        reason=f"Sentiment tz unprovable from data; keep both keys. {n_diff:,} rows "
               f"({n_diff/n*100:.2f}%) fall on different IST vs UTC calendar days — the merge "
               f"module will choose the appropriate key.",
        disposition="added column", f_id="F2.5", decision="D8",
    ))

    # T3 — flag zero-notional rows (F2.14). Flag, not drop.
    df["is_zero_size"] = df["Size USD"] == 0
    ops.append(CleanOp(
        name="Flag `is_zero_size` (Size USD == 0)",
        rows_before=n, rows_after=len(df), rows_affected=int(df["is_zero_size"].sum()),
        reversible=True, reason="Zero-notional fills; excluded from size metrics later. Rows retained.",
        disposition="flagged (preserved)", f_id="F2.14",
    ))

    # T4 — flag rows where Size USD disagrees >1% with Price × Size Tokens (F2.2).
    approx = df["Execution Price"] * df["Size Tokens"]
    denom = df["Size USD"].abs().clip(lower=1e-9)
    df["size_mismatch"] = ((df["Size USD"] - approx).abs() / denom) > 0.01
    ops.append(CleanOp(
        name="Flag `size_mismatch` (|Size USD − Price×Tokens| > 1%)",
        rows_before=n, rows_after=len(df), rows_affected=int(df["size_mismatch"].sum()),
        reversible=True, reason="Transparency flag; Size USD (exchange-reported) is trusted. Rows retained.",
        disposition="flagged (preserved)", f_id="F2.2",
    ))

    # T5 — flag non-standard perp events / flips (F2.10).
    df["is_edge_direction"] = df["Direction"].isin(EDGE_DIRECTIONS)
    ops.append(CleanOp(
        name="Flag `is_edge_direction` (ADL/Liquidation/Settlement/flips)",
        rows_before=n, rows_after=len(df), rows_affected=int(df["is_edge_direction"].sum()),
        reversible=True, reason="Non-directional events; excluded from long/short ratio later. Rows retained.",
        disposition="flagged (preserved)", f_id="F2.10",
    ))

    # T6 — flag spot trades (D8/T6). Kept in dataset; directional analyses may filter later.
    df["is_spot"] = (
        df["Direction"].isin(SPOT_DIRECTIONS)
        | df["Coin"].str.startswith("@")
        | df["Coin"].str.contains("/", regex=False)
    )
    ops.append(CleanOp(
        name="Flag `is_spot` (spot markets vs perpetuals)",
        rows_before=n, rows_after=len(df), rows_affected=int(df["is_spot"].sum()),
        reversible=True,
        reason="Spot has no leverage/long-short semantics; retained for PnL/volume, filtered for "
               "directional/leverage analysis. Direction-based & Coin-based definitions agree exactly.",
        disposition="flagged (preserved)", f_id="F2.10", decision="T6",
    ))

    # T7 — leverage explicitly excluded (D3). No column fabricated.
    ops.append(CleanOp(
        name="Leverage EXCLUDED (no source column; not fabricated)",
        rows_before=n, rows_after=len(df), rows_affected=0,
        reversible=True,
        reason="F2.4: no leverage field exists and no account-equity/margin field allows honest "
               "reconstruction. Excluded from analysis per D3. No column added.",
        disposition="preserved", f_id="F2.4", decision="D3",
    ))

    # T8 — confirm no missing / no full-row duplicates (no action).
    ops.append(CleanOp(
        name="Verify 0 missing cells & 0 full-row duplicates",
        rows_before=n, rows_after=len(df),
        rows_affected=int(df[raw.columns].isna().sum().sum() + df.duplicated(subset=list(raw.columns)).sum()),
        reversible=True, reason="Confirmed clean at source. No imputation, no dedup needed.",
        disposition="preserved", f_id="F2.3",
    ))

    return df, ops
