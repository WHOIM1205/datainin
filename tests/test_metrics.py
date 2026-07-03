"""Unit tests for src.metrics — trader-level metric formulas & edge cases."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.metrics import DATE_COL, METRIC_NAMES, trader_metrics


def _features():
    rows = [
        # A: win +10, loss -4 (both perp Long), then non-bearing 0
        ("A", 10.0, True, True, 100.0, "Long"),
        ("A", -4.0, True, True, 100.0, "Long"),
        ("A", 0.0, False, True, 50.0, "Long"),
        # B: perp Short, with a big losing day
        ("B", 10.0, True, True, 200.0, "Short"),
        ("B", -30.0, True, True, 200.0, "Short"),
        ("B", 5.0, True, True, 200.0, "Short"),
        # C: single winning trade (no losses -> profit_factor undefined)
        ("C", 5.0, True, True, 300.0, "Long"),
    ]
    return pd.DataFrame(rows, columns=[
        "Account", "Closed PnL", "pnl_bearing", "is_perp", "Size USD", "position_side"])


def _account_day():
    rows = [
        ("A", "2024-01-01", 6.0), ("A", "2024-01-02", 0.0),
        ("B", "2024-01-01", 10.0), ("B", "2024-01-02", -30.0), ("B", "2024-01-03", 5.0),
        ("C", "2024-01-01", 5.0),
    ]
    df = pd.DataFrame(rows, columns=["Account", DATE_COL, "daily_pnl"])
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    return df


def _row(m, acc):
    return m[m["Account"] == acc].iloc[0]


def test_all_metrics_present():
    m = trader_metrics(_features(), _account_day())
    assert list(m.columns) == ["Account"] + METRIC_NAMES


def test_profitability_metrics_account_A():
    a = _row(trader_metrics(_features(), _account_day()), "A")
    assert a["total_pnl"] == 6.0
    assert a["expectancy_per_trade"] == 3.0            # 6 / 2 bearing
    assert abs(a["roi_on_notional"] - 6.0 / 200.0) < 1e-9
    assert abs(a["profit_factor"] - 10.0 / 4.0) < 1e-9
    assert a["win_rate"] == 0.5                        # 1 win / 2 bearing
    assert a["long_ratio"] == 1.0                      # all perp Long
    assert a["median_trade_size_usd"] == 100.0


def test_risk_and_consistency_account_A():
    a = _row(trader_metrics(_features(), _account_day()), "A")
    assert a["n_active_days"] == 2
    assert a["pct_profitable_days"] == 0.5
    assert abs(a["sharpe_proxy"] - 3.0 / np.std([6.0, 0.0], ddof=1)) < 1e-9
    assert a["max_drawdown"] == 0.0                    # cumulative never declines
    assert a["avg_trades_per_active_day"] == 1.5       # 3 trades / 2 days


def test_drawdown_and_short_bias_account_B():
    b = _row(trader_metrics(_features(), _account_day()), "B")
    assert b["max_drawdown"] == -30.0                  # 10 -> -20 trough, peak 10
    assert b["long_ratio"] == 0.0                      # all short
    assert abs(b["win_rate"] - 2.0 / 3.0) < 1e-9


def test_undefined_metrics_account_C():
    c = _row(trader_metrics(_features(), _account_day()), "C")
    assert pd.isna(c["profit_factor"])                 # no losses -> NaN, not inf
    assert pd.isna(c["sharpe_proxy"])                  # single day -> std NaN
