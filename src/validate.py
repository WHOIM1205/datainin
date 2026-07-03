"""
Module 2 — Validation.

Turns Module 1's verified observations into enforced, rule-based checks. Every
check references the frozen fact (F-id) in ASSUMPTIONS_LOG.md that it guards.

Semantics:
  PASS  — the frozen fact holds; safe to build on.
  WARN  — a known, expected condition that cleaning must handle (not a failure).
  FAIL  — a frozen fact is violated: the raw data changed or an assumption is
          wrong. A FAIL must halt the pipeline (and, per governance, trigger a
          CHANGE entry in ASSUMPTIONS_LOG.md before proceeding).

This module validates. It does NOT clean, transform, engineer, merge, or plot.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# ---- Frozen baselines from Module 1 (see ASSUMPTIONS_LOG.md Part A) ----
SENTIMENT_EXPECTED_DTYPES = {
    "timestamp": "int64", "value": "int64", "classification": "str", "date": "str",
}  # F1.2
SENTIMENT_ROWS = 2644            # F1.1
CLASSIFICATION_DOMAIN = {"Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"}  # F1.4
VALUE_MIN, VALUE_MAX = 0, 100    # F1.5
SENTIMENT_DATE_RANGE = ("2018-02-01", "2025-05-02")  # F1.6

TRADES_EXPECTED_DTYPES = {
    "Account": "str", "Coin": "str", "Execution Price": "float64", "Size Tokens": "float64",
    "Size USD": "float64", "Side": "str", "Timestamp IST": "str", "Start Position": "float64",
    "Direction": "str", "Closed PnL": "float64", "Transaction Hash": "str", "Order ID": "int64",
    "Crossed": "bool", "Fee": "float64", "Trade ID": "float64", "Timestamp": "float64",
}  # F2.2
TRADES_ROWS = 211224             # F2.1
SIDE_DOMAIN = {"BUY", "SELL"}    # F2.10
DIRECTION_DOMAIN = {             # F2.10 (the 12 values observed in Module 1)
    "Open Long", "Close Long", "Open Short", "Close Short", "Sell", "Buy",
    "Spot Dust Conversion", "Short > Long", "Long > Short", "Auto-Deleveraging",
    "Liquidated Isolated Short", "Settlement",
}
TRADES_TIME_FMT = "%d-%m-%Y %H:%M"                      # F2.5
TRADES_DATE_RANGE = ("2023-05-01", "2025-05-01")       # F2.12
N_ACCOUNTS, N_COINS = 32, 246                          # F2.13
# Directions with an unambiguous side, used for the Direction<->Side consistency check (D7).
DIRECTION_TO_SIDE = {
    "Open Long": "BUY", "Close Short": "BUY", "Buy": "BUY",
    "Open Short": "SELL", "Close Long": "SELL", "Sell": "SELL",
}


@dataclass
class CheckResult:
    check: str
    ref: str      # F-id guarded
    status: str   # PASS / WARN / FAIL
    detail: str


def _norm_dtype(dtype) -> str:
    """Normalise a pandas dtype to the vocabulary used in config/frozen facts."""
    s = str(dtype)
    if s.startswith("string") or s == "object":
        return "str"
    return s


def _dtypes_check(df: pd.DataFrame, expected: dict, ref: str) -> CheckResult:
    mismatches = {
        c: (_norm_dtype(df[c].dtype), exp)
        for c, exp in expected.items()
        if c in df.columns and _norm_dtype(df[c].dtype) != exp
    }
    if mismatches:
        return CheckResult("dtypes match Module 1", ref, "FAIL", f"mismatches: {mismatches}")
    return CheckResult("dtypes match Module 1", ref, "PASS", "all dtypes as frozen")


def _schema_check(df: pd.DataFrame, expected_cols, ref: str) -> CheckResult:
    actual = list(df.columns)
    if actual != list(expected_cols):
        missing = set(expected_cols) - set(actual)
        extra = set(actual) - set(expected_cols)
        return CheckResult("column set & order", ref, "FAIL",
                           f"missing={missing or '{}'}, extra={extra or '{}'}, order_ok={actual == list(expected_cols)}")
    return CheckResult("column set & order", ref, "PASS", f"{len(actual)} columns exactly as frozen")


def validate_sentiment(df: pd.DataFrame) -> list[CheckResult]:
    r: list[CheckResult] = []
    r.append(CheckResult("row count", "F1.1", "PASS" if len(df) == SENTIMENT_ROWS else "FAIL",
                         f"{len(df):,} (expected {SENTIMENT_ROWS:,})"))
    r.append(_schema_check(df, SENTIMENT_EXPECTED_DTYPES.keys(), "F1.2"))
    r.append(_dtypes_check(df, SENTIMENT_EXPECTED_DTYPES, "F1.2"))

    n_missing = int(df.isna().sum().sum())
    r.append(CheckResult("no missing cells", "F1.3", "PASS" if n_missing == 0 else "FAIL",
                         f"{n_missing} missing"))
    dup_dates = int(df["date"].duplicated().sum())
    r.append(CheckResult("no duplicate dates (one row/day)", "F1.3", "PASS" if dup_dates == 0 else "FAIL",
                         f"{dup_dates} duplicate dates"))

    unknown = set(df["classification"].unique()) - CLASSIFICATION_DOMAIN
    r.append(CheckResult("classification in known 5-bucket domain", "F1.4",
                         "PASS" if not unknown else "FAIL", f"unknown values: {unknown or '{}'}"))

    out_of_range = int(((df["value"] < VALUE_MIN) | (df["value"] > VALUE_MAX)).sum())
    r.append(CheckResult("value within [0,100]", "F1.5", "PASS" if out_of_range == 0 else "FAIL",
                         f"{out_of_range} out-of-range; observed [{df['value'].min()},{df['value'].max()}]"))

    parsed = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    n_bad = int(parsed.isna().sum())
    in_range = (str(parsed.min().date()) >= SENTIMENT_DATE_RANGE[0]
                and str(parsed.max().date()) <= SENTIMENT_DATE_RANGE[1])
    r.append(CheckResult("date parseable YYYY-MM-DD & within frozen range", "F1.6",
                         "PASS" if n_bad == 0 and in_range else "FAIL",
                         f"unparseable={n_bad}; range {parsed.min().date()}→{parsed.max().date()}"))

    # Internal consistency: does classification map to a contiguous, non-overlapping value band?
    # Robust to subsets: only consider buckets actually present, in canonical order.
    order = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
    bands = df.groupby("classification")["value"].agg(["min", "max"])
    bands = bands.reindex([b for b in order if b in bands.index])
    overlaps = []
    prev_max = -1
    for name, row in bands.iterrows():
        if row["min"] <= prev_max:
            overlaps.append(name)
        prev_max = row["max"]
    detail = "; ".join(f"{n}:[{int(v['min'])},{int(v['max'])}]" for n, v in bands.iterrows())
    r.append(CheckResult("classification↔value bands are ordered & non-overlapping", "F1.4/F1.5",
                         "PASS" if not overlaps else "WARN",
                         (f"overlaps at {overlaps}; " if overlaps else "") + detail))
    return r


def validate_trades(df: pd.DataFrame) -> list[CheckResult]:
    r: list[CheckResult] = []
    r.append(CheckResult("row count", "F2.1", "PASS" if len(df) == TRADES_ROWS else "FAIL",
                         f"{len(df):,} (expected {TRADES_ROWS:,})"))
    r.append(_schema_check(df, TRADES_EXPECTED_DTYPES.keys(), "F2.2"))
    r.append(_dtypes_check(df, TRADES_EXPECTED_DTYPES, "F2.2"))

    n_missing = int(df.isna().sum().sum())
    r.append(CheckResult("no missing cells", "F2.3", "PASS" if n_missing == 0 else "FAIL",
                         f"{n_missing} missing"))
    dup_full = int(df.duplicated().sum())
    r.append(CheckResult("no full-row duplicates", "F2.3", "PASS" if dup_full == 0 else "FAIL",
                         f"{dup_full} full-row duplicates"))

    r.append(CheckResult("no leverage column", "F2.4",
                         "PASS" if not any("lever" in c.lower() for c in df.columns) else "FAIL",
                         "leverage absent as frozen"))

    parsed = pd.to_datetime(df["Timestamp IST"], format=TRADES_TIME_FMT, errors="coerce")
    n_bad = int(parsed.isna().sum())
    r.append(CheckResult("Timestamp IST fully parseable (DD-MM-YYYY HH:MM)", "F2.5",
                         "PASS" if n_bad == 0 else "FAIL", f"{n_bad} unparseable"))
    in_range = (str(parsed.min().date()) >= TRADES_DATE_RANGE[0]
                and str(parsed.max().date()) <= TRADES_DATE_RANGE[1])
    r.append(CheckResult("trade dates within frozen range", "F2.12",
                         "PASS" if in_range else "FAIL",
                         f"{parsed.min().date()}→{parsed.max().date()}"))

    # Lossy columns must STAY lossy (so downstream keeps ignoring them).
    ts_uniq = df["Timestamp"].nunique()
    r.append(CheckResult("numeric Timestamp confirmed lossy (do not use)", "F2.6",
                         "PASS" if ts_uniq < 100 else "FAIL", f"{ts_uniq} unique values"))
    tid_uniq = df["Trade ID"].nunique()
    r.append(CheckResult("Trade ID confirmed not a unique key (do not use)", "F2.7",
                         "PASS" if tid_uniq < len(df) * 0.5 else "FAIL",
                         f"{tid_uniq:,} unique / {len(df):,} rows"))

    bad_side = set(df["Side"].unique()) - SIDE_DOMAIN
    r.append(CheckResult("Side in {BUY,SELL}", "F2.10", "PASS" if not bad_side else "FAIL",
                         f"unexpected: {bad_side or '{}'}"))
    bad_dir = set(df["Direction"].unique()) - DIRECTION_DOMAIN
    r.append(CheckResult("Direction in known 12-value domain", "F2.10",
                         "PASS" if not bad_dir else "FAIL", f"unexpected: {bad_dir or '{}'}"))

    r.append(CheckResult("Crossed is boolean", "F2.11",
                         "PASS" if _norm_dtype(df["Crossed"].dtype) == "bool" else "FAIL",
                         str(df["Crossed"].dtype)))

    r.append(CheckResult("account/coin cardinality stable", "F2.13",
                         "PASS" if df["Account"].nunique() == N_ACCOUNTS and df["Coin"].nunique() == N_COINS
                         else "WARN",
                         f"accounts={df['Account'].nunique()} (exp {N_ACCOUNTS}), "
                         f"coins={df['Coin'].nunique()} (exp {N_COINS})"))

    # Range/sign sanity (WARN, not FAIL: these are known boundary rows for cleaning, F2.14).
    neg_price = int((df["Execution Price"] < 0).sum())
    r.append(CheckResult("Execution Price >= 0", "F2.14", "PASS" if neg_price == 0 else "FAIL",
                         f"{neg_price} negative"))
    neg_size = int((df["Size USD"] < 0).sum())
    zero_size = int((df["Size USD"] == 0).sum())
    r.append(CheckResult("Size USD >= 0 (zeros flagged for cleaning)", "F2.14",
                         "PASS" if neg_size == 0 and zero_size == 0 else ("FAIL" if neg_size else "WARN"),
                         f"{neg_size} negative, {zero_size} zero"))

    # Internal consistency: Size USD ~= Execution Price * Size Tokens (which size field to trust).
    approx = (df["Execution Price"] * df["Size Tokens"])
    denom = df["Size USD"].abs().clip(lower=1e-9)
    rel_err = (df["Size USD"] - approx).abs() / denom
    n_off = int((rel_err > 0.01).sum())  # >1% discrepancy
    r.append(CheckResult("Size USD ≈ Price × Size Tokens (±1%)", "F2.2",
                         "PASS" if n_off == 0 else "WARN",
                         f"{n_off:,} rows ({n_off/len(df)*100:.2f}%) differ >1%"))

    # Internal consistency: unambiguous Directions agree with Side (supports D7).
    clear = df[df["Direction"].isin(DIRECTION_TO_SIDE)]
    expected_side = clear["Direction"].map(DIRECTION_TO_SIDE)
    n_mismatch = int((clear["Side"] != expected_side).sum())
    r.append(CheckResult("Direction↔Side consistent for unambiguous directions", "F2.10",
                         "PASS" if n_mismatch == 0 else "WARN",
                         f"{n_mismatch:,} mismatches over {len(clear):,} unambiguous rows"))
    return r


def summarize(results: list[CheckResult]) -> dict:
    out = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for r in results:
        out[r.status] += 1
    return out
