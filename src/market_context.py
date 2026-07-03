"""
Module 5 — market-context (confounder) features.

Fear/Greed is derived from price action, so a raw "sentiment → PnL" effect can be
pure market direction. To later isolate the *marginal* sentiment effect, we build a
daily BTC market-context series (return, volatility, up/down) as a control.

The series is derived from the provided trade data itself (BTC perpetual execution
prices) — no external data — so the project stays self-contained. The derived daily
price tracks real BTC history closely (validated in Module 5); median and volume-
weighted price agree at r≈0.9998, so the robust median is used.

Coverage limitation (honest): market context exists only on days with BTC perp
trades (~60% of active trading days); other days get NaN context and are simply
un-controlled at merge time.

Timezone: computed for whichever date key is passed (`trade_date_utc` or
`trade_date_ist`), because the sentiment tz is unresolved (D8/D10) — the merge
module picks the key and uses the matching context table.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MAX_GAP_DAYS = 5          # don't compute a "daily" return across a gap longer than this
VOL_SHORT, VOL_LONG = 7, 30


def compute_market_context(trades: pd.DataFrame, date_col: str, coin: str = "BTC") -> pd.DataFrame:
    """Daily BTC market-context features keyed on `date_col` (a normalized date column).

    Returns one row per BTC-active day with columns:
      <date_col>, btc_price, btc_n_trades, btc_return, btc_log_return,
      btc_vol_7d, btc_vol_30d, btc_abs_return, btc_up_day
    """
    btc = trades[(trades["Coin"] == coin) & (~trades["is_spot"]) & (~trades["is_edge_direction"])]
    daily = (btc.groupby(date_col)
             .agg(btc_price=("Execution Price", "median"),
                  btc_n_trades=("Execution Price", "size"))
             .sort_index())

    # Returns over consecutive available days, masked across long gaps (no spurious jumps).
    gap_days = daily.index.to_series().diff().dt.days
    across_gap = gap_days > MAX_GAP_DAYS
    daily["btc_return"] = daily["btc_price"].pct_change().mask(across_gap)
    daily["btc_log_return"] = np.log(daily["btc_price"]).diff().mask(across_gap)

    # Realized volatility = rolling std of daily returns (short and long windows).
    daily["btc_vol_7d"] = daily["btc_return"].rolling(VOL_SHORT, min_periods=3).std()
    daily["btc_vol_30d"] = daily["btc_return"].rolling(VOL_LONG, min_periods=10).std()

    daily["btc_abs_return"] = daily["btc_return"].abs()
    daily["btc_up_day"] = (daily["btc_return"] > 0).astype("boolean").mask(daily["btc_return"].isna())

    return daily.reset_index()


def coverage(context: pd.DataFrame, trades: pd.DataFrame, date_col: str) -> dict:
    """Diagnostic: how much of the active trading window has market context."""
    active_days = trades[date_col].nunique()
    ctx_days = context[date_col].nunique()
    ret_days = int(context["btc_return"].notna().sum())
    return {
        "active_trading_days": int(active_days),
        "btc_context_days": int(ctx_days),
        "coverage_pct": round(ctx_days / active_days * 100, 1),
        "days_with_return": ret_days,
        "price_min": round(float(context["btc_price"].min()), 0),
        "price_max": round(float(context["btc_price"].max()), 0),
    }
