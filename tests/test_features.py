"""Unit tests for src.features — per-trade feature correctness & non-destructiveness."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features import add_trade_features


def _trades():
    ts = pd.to_datetime([
        "2024-01-01 10:00", "2024-01-03 10:00", "2024-01-06 10:00",  # account A (3 trades)
        "2024-02-01 10:00",                                          # account B (1 trade)
    ]).tz_localize("Asia/Kolkata")
    return pd.DataFrame({
        "Account": ["A", "A", "A", "B"],
        "Coin": ["BTC", "BTC", "BTC", "ETH"],
        "Size USD": [100.0, 100.0, 10000.0, 500.0],
        "Closed PnL": [0.0, 5.0, -20.0, 10.0],
        "Fee": [0.05, 0.10, 2.0, 0.25],
        "Direction": ["Open Long", "Close Long", "Open Short", "Buy"],
        "is_spot": [False, False, False, True],
        "is_edge_direction": [False, False, False, False],
        "ts_ist": ts,
    })


def test_non_destructive():
    raw = _trades()
    out = add_trade_features(raw)
    assert len(out) == len(raw)
    assert all(c in out.columns for c in raw.columns)


def test_pnl_bearing_and_win():
    out = add_trade_features(_trades())
    assert out["pnl_bearing"].tolist() == [False, True, True, True]
    # is_win: NA for non-bearing, then True(5>0), False(-20), True(10)
    assert pd.isna(out.loc[0, "is_win"])
    assert out.loc[1, "is_win"] == True   # noqa: E712
    assert out.loc[2, "is_win"] == False  # noqa: E712


def test_position_side():
    out = add_trade_features(_trades())
    assert out["position_side"].tolist() == ["Long", "Long", "Short", "Spot"]


def test_pnl_per_notional_and_fee_bps():
    out = add_trade_features(_trades())
    assert pd.isna(out.loc[0, "pnl_per_notional"])          # non-bearing -> NaN
    assert abs(out.loc[1, "pnl_per_notional"] - 5.0 / 100.0) < 1e-9
    assert abs(out.loc[3, "fee_bps"] - (0.25 / 500.0 * 1e4)) < 1e-9


def test_size_z_uses_account_history():
    out = add_trade_features(_trades())
    # account A: the 10000 trade is far larger than its 100/100 -> positive z
    assert out.loc[2, "size_z"] > 0
    assert out.loc[0, "size_z"] < 0
    # account B has a single trade -> std undefined -> size_z NaN
    assert pd.isna(out.loc[3, "size_z"])


def test_account_tenure_days():
    out = add_trade_features(_trades())
    # account A first trade 2024-01-01; third trade 2024-01-06 -> 5 days
    assert out.loc[0, "account_tenure_days"] == 0
    assert out.loc[2, "account_tenure_days"] == 5
    assert out.loc[3, "account_tenure_days"] == 0   # B's only trade
