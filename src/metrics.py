"""
Module 10 — trader-level (per-account) analytical metrics.

Every metric measures profitability, risk, consistency, or trading behaviour — no
metric is included merely for finance convention. Near-duplicates are pruned to the
strongest representative:
  - CVaR (expected shortfall) kept; plain VaR dropped (CVaR is coherent & uses the
    whole tail).
  - Downside risk (max drawdown, CVaR) kept; symmetric PnL-volatility dropped as a
    headline (it survives only inside the Sharpe-proxy denominator).
  - avg trades/active-day kept; raw total_trades kept only as an exposure denominator,
    not as a separate "frequency" metric.

Definitions live in METRIC_DEFS (single source for outputs/metric_dictionary.md).
No hypothesis testing, significance, or conclusions here — computation only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DATE_COL = "trade_date_utc"
CVAR_Q = 0.05

# (name, category, formula, interpretation, assumptions, limitations, better)
METRIC_DEFS = [
    ("total_pnl", "profitability", "Σ Closed PnL over all trades",
     "Absolute net profit (USD) the account realized.",
     "PnL is additive and correctly signed (F2.9).",
     "Scale-dependent — whales dominate; not comparable across account sizes.", "higher"),
    ("expectancy_per_trade", "profitability", "total_pnl / pnl_trade_count",
     "Average realized edge per closing trade (USD).",
     "Realized PnL booked on closing fills only (D6).",
     "Ignores trade size; a large-size trader can have high expectancy but poor efficiency.", "higher"),
    ("roi_on_notional", "profitability", "total_pnl / Σ(Size USD on closing trades)",
     "Return on capital-at-risk (profit per $ of notional traded).",
     "Notional (Size USD) approximates capital at risk (F2.2).",
     "Notional ≠ margin (no leverage/equity data, D3); it is turnover-weighted, not held capital.", "higher"),
    ("profit_factor", "profitability", "Σ gross_profit / |Σ gross_loss|",
     "Dollars won per dollar lost; >1 is profitable.",
     "Wins and losses both present.",
     "Undefined with zero losses (→ NaN); insensitive to trade frequency.", "higher"),
    ("win_rate", "consistency", "win_count / pnl_trade_count",
     "Share of closing trades that are profitable (trade grain).",
     "Closing trades only (D6).",
     "Says nothing about win/loss magnitude — high win rate can still lose money.", "higher"),
    ("pct_profitable_days", "consistency", "mean(daily_pnl > 0) over active days",
     "Share of active days that end net-positive (day grain).",
     "Daily grain, UTC days (D8).",
     "Day-level, so differs from win_rate; sensitive to how PnL clusters within a day.", "higher"),
    ("sharpe_proxy", "risk-adjusted", "mean(daily_pnl) / std(daily_pnl)",
     "Risk-adjusted return: mean daily PnL per unit of daily-PnL volatility.",
     "Daily PnL is the return series; no risk-free rate; NOT annualized (hence 'proxy').",
     "Assumes stable variance; unstable for accounts with few active days; not comparable to a true annualized Sharpe.", "higher"),
    ("max_drawdown", "risk", "min(cumsum(daily_pnl) − cummax(cumsum(daily_pnl)))",
     "Worst peak-to-trough decline of cumulative PnL (USD) — a drawdown proxy.",
     "Cumulative daily PnL ordered by date approximates the equity path.",
     "Path uses realized daily PnL only (no intraday/unrealized); scale-dependent (USD).", "higher (closer to 0)"),
    ("cvar_5", "risk", "mean(daily_pnl | daily_pnl ≤ 5th percentile)",
     "Expected shortfall: average PnL on the worst 5% of days (tail risk).",
     "Enough active days for a meaningful 5% tail.",
     "Unstable below ~20 active days; scale-dependent (USD).", "higher (closer to 0)"),
    ("n_active_days", "behaviour", "count of distinct active days",
     "Engagement span — how many days the account traded.",
     "Active day = ≥1 trade that UTC day.",
     "Does not capture intensity; a proxy for tenure/engagement, not calendar tenure.", "neutral (segmenting)"),
    ("avg_trades_per_active_day", "behaviour", "total_trades / n_active_days",
     "Trading intensity / frequency on days the account is active.",
     "—",
     "Averages over active days only (ignores idle days).", "neutral (segmenting)"),
    ("median_trade_size_usd", "behaviour", "median(Size USD) over trades with Size USD > 0",
     "Typical position size (USD).",
     "Size USD trusted (F2.2); zero-size rows excluded (F2.14).",
     "Median hides the heavy right tail of sizes (E6).", "neutral (segmenting)"),
    ("long_ratio", "behaviour", "long_count / (long_count + short_count), perp only",
     "Directional bias: 0.5 = balanced, >0.5 = net long.",
     "Perpetual Long/Short only; spot & edge excluded (T6/F2.10).",
     "Counts opens+closes equally; not exposure- or time-weighted.", "neutral (segmenting)"),
]
METRIC_NAMES = [d[0] for d in METRIC_DEFS]


def _trade_aggregates(features: pd.DataFrame) -> pd.DataFrame:
    f = features
    perp = f["is_perp"]
    h = pd.DataFrame({
        "Account": f["Account"],
        "pnl": f["Closed PnL"],
        "bearing": f["pnl_bearing"].astype(int),
        "win": (f["Closed PnL"] > 0).astype(int),
        "gp": f["Closed PnL"].clip(lower=0),
        "gl": f["Closed PnL"].clip(upper=0),
        "bearing_notional": f["Size USD"].where(f["pnl_bearing"], 0.0),
        "size_pos": f["Size USD"].where(f["Size USD"] > 0),
        "long": ((f["position_side"] == "Long") & perp).astype(int),
        "short": ((f["position_side"] == "Short") & perp).astype(int),
    })
    g = h.groupby("Account")
    a = g.agg(
        total_pnl=("pnl", "sum"),
        total_trades=("pnl", "size"),
        pnl_trade_count=("bearing", "sum"),
        win_count=("win", "sum"),
        gross_profit=("gp", "sum"),
        gross_loss=("gl", "sum"),
        bearing_notional=("bearing_notional", "sum"),
        median_trade_size_usd=("size_pos", "median"),
        long_count=("long", "sum"),
        short_count=("short", "sum"),
    )
    a["expectancy_per_trade"] = a["total_pnl"] / a["pnl_trade_count"].replace(0, np.nan)
    a["win_rate"] = a["win_count"] / a["pnl_trade_count"].replace(0, np.nan)
    a["roi_on_notional"] = a["total_pnl"] / a["bearing_notional"].replace(0, np.nan)
    a["profit_factor"] = a["gross_profit"] / (-a["gross_loss"]).replace(0, np.nan)
    directional = (a["long_count"] + a["short_count"]).replace(0, np.nan)
    a["long_ratio"] = a["long_count"] / directional
    return a


def _daily_metrics(account_day: pd.DataFrame) -> pd.DataFrame:
    ad = account_day.sort_values(["Account", DATE_COL])
    g = ad.groupby("Account")["daily_pnl"]

    def cvar(s):
        thr = s.quantile(CVAR_Q)
        tail = s[s <= thr]
        return tail.mean() if len(tail) else np.nan

    def mdd(s):
        cum = s.cumsum()
        return float((cum - cum.cummax()).min())

    out = pd.DataFrame({
        "n_active_days": g.size(),
        "pct_profitable_days": ad.assign(_p=ad["daily_pnl"] > 0).groupby("Account")["_p"].mean(),
        "sharpe_proxy": g.mean() / g.std().replace(0, np.nan),
        "max_drawdown": g.apply(mdd),
        "cvar_5": g.apply(cvar),
    })
    return out


def trader_metrics(features: pd.DataFrame, account_day: pd.DataFrame) -> pd.DataFrame:
    """One row per account with all trader-level metrics (METRIC_NAMES)."""
    ta = _trade_aggregates(features)
    dm = _daily_metrics(account_day)
    m = ta.join(dm, how="outer")
    m["avg_trades_per_active_day"] = m["total_trades"] / m["n_active_days"].replace(0, np.nan)
    return m.reset_index()[["Account"] + METRIC_NAMES].copy()
