"""
Module 7 — daily aggregation (the analytical foundation).

Two strictly-separated grains:
  * account-day : one row per (Account, calendar day)
  * market-day  : one row per calendar day (across all accounts)

Aggregation principles enforced here:
  - Rates/ratios are NEVER averaged. Win rate, long/short ratio, return-on-notional
    and fee-bps are rebuilt from summed counts / summed notional (weighted), so a
    whale's day cannot be averaged on equal footing with a minnow's.
  - Heavy-tailed quantities (PnL, size — E1/E6) use median (robust), not mean.
  - Observation counts are preserved on every row (trade_count, pnl_trade_count,
    account_count where applicable, valid_observation_count) for later sample sizes.
  - Grains are never mixed: market-day columns record whether they came from the
    trade grain or the account grain (see METRIC_DOCS).

No sentiment join, no tests of significance, no conclusions — tables only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LONG, SHORT = "Long", "Short"

# ---- Metric documentation (single source for the aggregation report) ----
# (column, grain, source_grain, function, type, rationale)
METRIC_DOCS = [
    # account-day
    ("trade_count", "account-day", "trade", "count of fills", "count",
     "Sample size: number of trades that account-day."),
    ("pnl_trade_count", "account-day", "trade", "count where Closed PnL≠0", "count",
     "Sample size for PnL/win metrics (realized only on closing fills, D6/F2.9)."),
    ("perp_trade_count", "account-day", "trade", "count where is_perp", "count",
     "Perp sample size (directional/leverage analysis is perp-only)."),
    ("valid_observation_count", "account-day", "trade", "= trade_count", "count",
     "Explicit sample size the row summarizes."),
    ("daily_pnl", "account-day", "trade", "sum(Closed PnL)", "additive",
     "Total realized PnL that account-day; PnL is additive."),
    ("gross_profit", "account-day", "trade", "sum(PnL where >0)", "additive",
     "Feeds profit factor later; additive."),
    ("gross_loss", "account-day", "trade", "sum(PnL where <0)", "additive",
     "Feeds profit factor / drawdown; additive."),
    ("win_count", "account-day", "trade", "count where PnL>0", "count",
     "Numerator for win_rate (kept as a count so rate is reconstructable)."),
    ("win_rate", "account-day", "trade", "win_count / pnl_trade_count", "weighted (derived-from-counts)",
     "A RATE — rebuilt from counts, never averaged across trades."),
    ("notional_sum", "account-day", "trade", "sum(Size USD)", "additive",
     "Gross traded volume; additive."),
    ("notional_median", "account-day", "trade", "median(Size USD)", "median (robust)",
     "Typical trade size; median because size is heavy-tailed (E6), not mean."),
    ("ret_on_notional_weighted", "account-day", "trade", "daily_pnl / bearing_notional", "weighted",
     "Notional-weighted return; a RATIO built from sums, not a mean of per-trade ratios."),
    ("pnl_per_notional_median", "account-day", "trade", "median(pnl_per_notional)", "median (robust)",
     "Robust central tendency of per-trade return-on-notional."),
    ("long_count", "account-day", "trade", "count perp Long", "count",
     "Numerator of long/short ratio (perp only)."),
    ("short_count", "account-day", "trade", "count perp Short", "count",
     "Denominator of long/short ratio (perp only)."),
    ("long_short_ratio", "account-day", "trade", "long_count / short_count", "weighted (derived-from-counts)",
     "A RATIO — from counts; NaN when short_count=0."),
    ("long_notional", "account-day", "trade", "sum(Size USD where perp Long)", "additive",
     "Notional-weighted long exposure."),
    ("short_notional", "account-day", "trade", "sum(Size USD where perp Short)", "additive",
     "Notional-weighted short exposure."),
    ("net_directional_notional", "account-day", "trade", "long_notional − short_notional", "additive",
     "Signed net directional exposure (perp)."),
    ("fee_sum", "account-day", "trade", "sum(Fee)", "additive",
     "Total fees (negative = rebates, F2.14); additive."),
    ("fee_bps_weighted", "account-day", "trade", "fee_sum / notional_sum × 1e4", "weighted",
     "Cost RATE — total fees over total notional, not a mean of per-trade bps."),
    ("size_z_median", "account-day", "trade", "median(size_z)", "median (robust)",
     "Typical self-normalized aggression that day (E3/E6)."),
    ("large_trade_count", "account-day", "trade", "count where is_large_trade", "count",
     "How many unusually-large-for-this-account trades."),
    # market-day
    ("trade_count", "market-day", "trade", "count of fills", "count", "Market trade sample size."),
    ("pnl_trade_count", "market-day", "trade", "count where PnL≠0", "count", "Market PnL sample size."),
    ("account_count", "market-day", "account", "distinct account-days", "count",
     "Number of accounts active that day (E3: few whales dominate)."),
    ("valid_observation_count", "market-day", "account", "= account_count", "count",
     "Sample size for cross-account daily statistics."),
    ("market_daily_pnl", "market-day", "trade", "sum(Closed PnL)", "additive",
     "Total realized PnL across all accounts; additive."),
    ("median_account_daily_pnl", "market-day", "account", "median(account-day daily_pnl)", "median (robust)",
     "Typical account's day — resists whale domination (E3). ACCOUNT grain, not trade."),
    ("market_win_rate", "market-day", "trade", "Σwin_count / Σpnl_trade_count", "weighted (derived-from-counts)",
     "Pooled win RATE from counts, not a mean of account rates."),
    ("total_notional", "market-day", "trade", "sum(Size USD)", "additive", "Total market volume."),
    ("median_trade_size", "market-day", "trade", "median(Size USD)", "median (robust)",
     "Typical trade size market-wide (E6)."),
    ("market_long_short_ratio", "market-day", "trade", "Σlong_count / Σshort_count", "weighted (derived-from-counts)",
     "Pooled directional RATIO from counts."),
    ("market_fee_bps_weighted", "market-day", "trade", "Σfee / Σnotional × 1e4", "weighted",
     "Pooled cost rate."),
]


def _helpers(df: pd.DataFrame) -> pd.DataFrame:
    d = df
    pnl = d["Closed PnL"]
    perp = d["is_perp"]
    is_long = (d["position_side"] == LONG) & perp
    is_short = (d["position_side"] == SHORT) & perp
    return pd.DataFrame({
        "Account": d["Account"],
        "pnl": pnl,
        "win": (pnl > 0).astype(int),
        "bearing": d["pnl_bearing"].astype(int),
        "perp": perp.astype(int),
        "spot": d["is_spot"].astype(int),
        "gross_profit": pnl.clip(lower=0),
        "gross_loss": pnl.clip(upper=0),
        "notional": d["Size USD"],
        "bearing_notional": d["Size USD"].where(d["pnl_bearing"], 0.0),
        "pnl_per_notional": d["pnl_per_notional"],
        "long": is_long.astype(int),
        "short": is_short.astype(int),
        "long_notional": d["Size USD"].where(is_long, 0.0),
        "short_notional": d["Size USD"].where(is_short, 0.0),
        "fee": d["Fee"],
        "size_z": d["size_z"],
        "is_large": d["is_large_trade"].astype("boolean").fillna(False).astype(int),
    })


def aggregate_account_day(features: pd.DataFrame, date_col: str) -> pd.DataFrame:
    h = _helpers(features)
    h[date_col] = features[date_col].values
    g = h.groupby(["Account", date_col], observed=True)
    a = g.agg(
        trade_count=("pnl", "size"),
        pnl_trade_count=("bearing", "sum"),
        perp_trade_count=("perp", "sum"),
        daily_pnl=("pnl", "sum"),
        gross_profit=("gross_profit", "sum"),
        gross_loss=("gross_loss", "sum"),
        win_count=("win", "sum"),
        notional_sum=("notional", "sum"),
        notional_median=("notional", "median"),
        _bearing_notional=("bearing_notional", "sum"),
        pnl_per_notional_median=("pnl_per_notional", "median"),
        long_count=("long", "sum"),
        short_count=("short", "sum"),
        long_notional=("long_notional", "sum"),
        short_notional=("short_notional", "sum"),
        fee_sum=("fee", "sum"),
        size_z_median=("size_z", "median"),
        large_trade_count=("is_large", "sum"),
    ).reset_index()

    # rates/ratios rebuilt from counts/sums (never averaged)
    a["valid_observation_count"] = a["trade_count"]
    a["win_rate"] = a["win_count"] / a["pnl_trade_count"].replace(0, np.nan)
    a["ret_on_notional_weighted"] = a["daily_pnl"] / a["_bearing_notional"].replace(0, np.nan)
    a["long_short_ratio"] = a["long_count"] / a["short_count"].replace(0, np.nan)
    a["net_directional_notional"] = a["long_notional"] - a["short_notional"]
    a["fee_bps_weighted"] = a["fee_sum"] / a["notional_sum"].replace(0, np.nan) * 1e4
    return a.drop(columns=["_bearing_notional"])


def aggregate_market_day(account_day: pd.DataFrame, features: pd.DataFrame, date_col: str) -> pd.DataFrame:
    h = _helpers(features)
    h[date_col] = features[date_col].values
    t = h.groupby(date_col, observed=True).agg(
        trade_count=("pnl", "size"),
        pnl_trade_count=("bearing", "sum"),
        win_count=("win", "sum"),
        market_daily_pnl=("pnl", "sum"),
        total_notional=("notional", "sum"),
        median_trade_size=("notional", "median"),
        long_count=("long", "sum"),
        short_count=("short", "sum"),
        fee_sum=("fee", "sum"),
    )
    # account-grain aggregates (kept separate from the trade grain)
    ac = account_day.groupby(date_col, observed=True).agg(
        account_count=("daily_pnl", "size"),
        median_account_daily_pnl=("daily_pnl", "median"),
    )
    m = t.join(ac).reset_index()
    m["valid_observation_count"] = m["account_count"]
    m["market_win_rate"] = m["win_count"] / m["pnl_trade_count"].replace(0, np.nan)
    m["market_long_short_ratio"] = m["long_count"] / m["short_count"].replace(0, np.nan)
    m["market_fee_bps_weighted"] = m["fee_sum"] / m["total_notional"].replace(0, np.nan) * 1e4
    return m
