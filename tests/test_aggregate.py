"""Unit tests for src.aggregate — grain integrity, count preservation, and that
rates/ratios are rebuilt from counts (not averaged)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.aggregate import aggregate_account_day, aggregate_market_day

DATE = "trade_date_utc"


def _feats():
    rows = [
        # Account A, day1: win +10 (Long), loss -5 (Short)
        ("A", "2024-01-01", 10.0, True, True, False, "Long", 100.0, 0.10, 0.1, 0.0, False),
        ("A", "2024-01-01", -5.0, True, True, False, "Short", 200.0, -0.025, 0.2, 1.0, False),
        # Account A, day2: non-bearing Long
        ("A", "2024-01-02", 0.0, False, True, False, "Long", 50.0, np.nan, 0.05, 0.0, False),
        # Account B, day1: spot win +3
        ("B", "2024-01-01", 3.0, True, False, True, "Spot", 500.0, 0.006, 0.5, 0.0, False),
    ]
    cols = ["Account", DATE, "Closed PnL", "pnl_bearing", "is_perp", "is_spot",
            "position_side", "Size USD", "pnl_per_notional", "Fee", "size_z", "is_large_trade"]
    df = pd.DataFrame(rows, columns=cols)
    df[DATE] = pd.to_datetime(df[DATE])
    df["is_large_trade"] = df["is_large_trade"].astype("boolean")
    return df


def test_account_day_grain_and_counts():
    ad = aggregate_account_day(_feats(), DATE)
    assert ad.duplicated(["Account", DATE]).sum() == 0            # unique grain
    assert ad["trade_count"].sum() == 4                            # count preserved
    assert (ad["valid_observation_count"] == ad["trade_count"]).all()


def test_account_day_pnl_and_rates_from_counts():
    ad = aggregate_account_day(_feats(), DATE).set_index(["Account", pd.to_datetime("2024-01-01")]) \
        if False else aggregate_account_day(_feats(), DATE)
    a1 = ad[(ad["Account"] == "A") & (ad[DATE] == pd.Timestamp("2024-01-01"))].iloc[0]
    assert a1["daily_pnl"] == 5.0                                  # additive
    assert a1["pnl_trade_count"] == 2 and a1["win_count"] == 1
    assert a1["win_rate"] == 0.5                                   # from counts
    assert a1["long_count"] == 1 and a1["short_count"] == 1
    assert a1["long_short_ratio"] == 1.0
    assert abs(a1["fee_bps_weighted"] - (0.3 / 300 * 1e4)) < 1e-9  # weighted, not mean
    assert abs(a1["ret_on_notional_weighted"] - (5.0 / 300.0)) < 1e-9


def test_rate_nan_when_denominator_zero():
    ad = aggregate_account_day(_feats(), DATE)
    a2 = ad[(ad["Account"] == "A") & (ad[DATE] == pd.Timestamp("2024-01-02"))].iloc[0]
    assert a2["pnl_trade_count"] == 0
    assert pd.isna(a2["win_rate"])          # 0/0 -> NaN, not 0
    assert pd.isna(a2["long_short_ratio"])  # short_count 0 -> NaN


def test_market_day_grain_and_weighted_rate():
    feats = _feats()
    ad = aggregate_account_day(feats, DATE)
    md = aggregate_market_day(ad, feats, DATE)
    assert md[DATE].duplicated().sum() == 0
    m1 = md[md[DATE] == pd.Timestamp("2024-01-01")].iloc[0]
    assert m1["account_count"] == 2                    # A and B
    assert m1["valid_observation_count"] == 2
    assert m1["trade_count"] == 3
    assert m1["pnl_trade_count"] == 3 and m1["win_count"] == 2
    assert abs(m1["market_win_rate"] - 2 / 3) < 1e-9   # pooled from counts
    assert m1["market_daily_pnl"] == 8.0               # 10 -5 +3


def test_market_day_account_grain_median_separate():
    feats = _feats()
    ad = aggregate_account_day(feats, DATE)
    md = aggregate_market_day(ad, feats, DATE)
    m1 = md[md[DATE] == pd.Timestamp("2024-01-01")].iloc[0]
    # median across accounts of daily_pnl: A=5, B=3 -> median 4
    assert m1["median_account_daily_pnl"] == 4.0
