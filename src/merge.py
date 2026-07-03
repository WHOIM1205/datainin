"""
Module 9 — sentiment merge (the statistically critical step).

Left-joins the Fear & Greed sentiment and the in-sample BTC market context proxy
onto the daily aggregated tables. Design guarantees:
  - Left join: unmatched daily rows are KEPT (flagged has_sentiment=False), never dropped.
  - validate="m:1": guards against duplicate joins (sentiment/context have unique dates).
  - Additive flags only: has_sentiment, has_market_proxy, in_effective_window — nothing removed.

Resolves D8 (timezone) and D10 (analysis window) with the evidence gathered in the
runner (see outputs/merge_report.md). Methodology is fixed here BEFORE any hypothesis
testing (no optimizing the merge toward significance).

Reminder for downstream use: the BTC market context is an IN-SAMPLE PROXY reconstructed
from observed BTC-perpetual executions (~60% day coverage, D11) — not an official price.
"""
from __future__ import annotations

import pandas as pd

# First active day after the 217-day inactivity gap (E2): objective "effective window" start.
EFFECTIVE_START = pd.Timestamp("2023-12-01")

_SENT_RENAME = {"value": "sentiment_value", "classification": "sentiment_class"}


def _side_by_date(sentiment: pd.DataFrame) -> pd.Series:
    idx = pd.to_datetime(sentiment["date_key"]).dt.normalize()
    return pd.Series(sentiment["sentiment_side"].values, index=idx)


def merge_daily(daily: pd.DataFrame, sentiment: pd.DataFrame, market_ctx: pd.DataFrame,
                date_col: str, effective_start: pd.Timestamp = EFFECTIVE_START) -> tuple[pd.DataFrame, dict]:
    """Join sentiment + market-context proxy onto a daily table. Returns (merged, audit)."""
    n_before = len(daily)
    d = daily.copy()
    d[date_col] = pd.to_datetime(d[date_col]).dt.normalize()

    s = sentiment[["date_key", "value", "classification", "sentiment_side"]].rename(
        columns={"date_key": date_col, **_SENT_RENAME})
    s[date_col] = pd.to_datetime(s[date_col]).dt.normalize()

    mc = market_ctx.copy()
    mc[date_col] = pd.to_datetime(mc[date_col]).dt.normalize()

    merged = d.merge(s, on=date_col, how="left", validate="m:1")     # m:1 guards duplicate joins
    merged = merged.merge(mc, on=date_col, how="left", validate="m:1", suffixes=("", "_ctx"))

    merged["has_sentiment"] = merged["sentiment_side"].notna()
    merged["has_market_proxy"] = merged["btc_return"].notna()
    merged["in_effective_window"] = merged[date_col] >= effective_start

    matched = int(merged["has_sentiment"].sum())
    audit = {
        "merge_key": date_col,
        "rows_before": n_before,
        "rows_after": len(merged),
        "duplicate_joins": len(merged) - n_before,          # 0 by construction (m:1)
        "matched_rows": matched,
        "unmatched_rows": n_before - matched,
        "pct_matched": round(matched / n_before * 100, 2),
        "sentiment_nulls_introduced": n_before - matched,
        "market_proxy_nulls_introduced": int((~merged["has_market_proxy"]).sum()),
    }
    return merged, audit


def evaluate_tz(md_utc: pd.DataFrame, md_ist: pd.DataFrame, sentiment: pd.DataFrame,
                feats: pd.DataFrame) -> dict:
    """Objective comparison of UTC vs IST merge (no hypothesis testing)."""
    side = _side_by_date(sentiment)

    def match(md, dc):
        dd = pd.to_datetime(md[dc]).dt.normalize()
        m = dd.isin(side.index)
        return {"market_days": len(md), "matched": int(m.sum()), "unmatched": int((~m).sum()),
                "pct_matched": round(m.mean() * 100, 2),
                "unmatched_dates": sorted(dd[~m].dt.date.astype(str).unique())}

    tu = feats["trade_date_utc"].dt.normalize().map(side)
    ti = feats["trade_date_ist"].dt.normalize().map(side)
    boundary = feats["trade_date_utc"].dt.normalize() != feats["trade_date_ist"].dt.normalize()
    side_differs = (tu != ti) & tu.notna() & ti.notna()
    return {
        "utc": match(md_utc, "trade_date_utc"),
        "ist": match(md_ist, "trade_date_ist"),
        "trades_crossing_boundary_pct": round(boundary.mean() * 100, 2),
        "trades_regime_differs_pct": round(side_differs.mean() * 100, 2),
    }


def evaluate_window(md: pd.DataFrame, sentiment: pd.DataFrame, date_col: str,
                    effective_start: pd.Timestamp = EFFECTIVE_START) -> dict:
    """Full vs effective-window comparison: day counts and regime balance."""
    side = _side_by_date(sentiment)
    d = pd.to_datetime(md[date_col]).dt.normalize()

    def balance(mask):
        dd = d[mask]
        return {"market_days": int(mask.sum()),
                "regime_balance": dd.map(side).value_counts().to_dict()}

    return {"full": balance(d >= d.min()),
            "effective": balance(d >= effective_start)}
