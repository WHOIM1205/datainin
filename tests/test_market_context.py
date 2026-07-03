"""Unit tests for src.market_context — daily BTC context, gap masking, exclusions."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.market_context import MAX_GAP_DAYS, compute_market_context


def _trades():
    d = pd.to_datetime
    rows = [
        # day 1: two BTC perp trades -> median price 100
        ("BTC", 90.0, False, False, "2024-01-01"),
        ("BTC", 110.0, False, False, "2024-01-01"),
        # day 2 (consecutive): median 110 -> return +10%
        ("BTC", 110.0, False, False, "2024-01-02"),
        # day 20 (gap > MAX_GAP_DAYS): price 120 -> return must be NaN (no spurious jump)
        ("BTC", 120.0, False, False, "2024-01-20"),
        # noise that must be EXCLUDED:
        ("BTC", 999.0, True, False, "2024-01-02"),    # spot BTC
        ("BTC", 999.0, False, True, "2024-01-02"),    # edge direction
        ("ETH", 50.0, False, False, "2024-01-02"),    # non-BTC
    ]
    return pd.DataFrame({
        "Coin": [r[0] for r in rows],
        "Execution Price": [r[1] for r in rows],
        "is_spot": [r[2] for r in rows],
        "is_edge_direction": [r[3] for r in rows],
        "Size USD": [1.0] * len(rows),
        "d": pd.to_datetime([r[4] for r in rows]),
    })


def test_price_is_median_of_btc_perp_only():
    ctx = compute_market_context(_trades(), "d").set_index("d")
    assert ctx.loc["2024-01-01", "btc_price"] == 100.0   # median(90,110); 999s excluded
    assert ctx.loc["2024-01-01", "btc_n_trades"] == 2
    assert ctx.loc["2024-01-02", "btc_price"] == 110.0   # spot/edge/ETH excluded


def test_return_and_up_day():
    ctx = compute_market_context(_trades(), "d").set_index("d")
    assert abs(ctx.loc["2024-01-02", "btc_return"] - 0.10) < 1e-9
    assert ctx.loc["2024-01-02", "btc_up_day"] == True  # noqa: E712


def test_gap_masks_return():
    ctx = compute_market_context(_trades(), "d").set_index("d")
    # 2024-01-20 is >5 days after 2024-01-02 -> return NaN, up_day NA
    assert pd.isna(ctx.loc["2024-01-20", "btc_return"])
    assert pd.isna(ctx.loc["2024-01-20", "btc_up_day"])


def test_first_day_has_no_return():
    ctx = compute_market_context(_trades(), "d").set_index("d")
    assert pd.isna(ctx.loc["2024-01-01", "btc_return"])


def test_volatility_non_negative():
    ctx = compute_market_context(_trades(), "d")
    vol = ctx[["btc_vol_7d", "btc_vol_30d"]].dropna()
    assert (vol >= 0).all().all()


def test_max_gap_constant_reasonable():
    assert MAX_GAP_DAYS == 5
