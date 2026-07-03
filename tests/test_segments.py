"""Unit tests for src.segments — deterministic quantile/rule segments & balance."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.segments import (LONG_HI, LONG_LO, SEGMENT_COLS, assign_segments,
                          segment_balance)


def _metrics(n=12):
    rng = np.arange(n)
    return pd.DataFrame({
        "Account": [f"acc{i}" for i in rng],
        "avg_trades_per_active_day": rng + 1.0,
        "pct_profitable_days": (rng + 1) / (n + 1),
        "median_trade_size_usd": (rng + 1) * 100.0,
        "roi_on_notional": (rng - n / 2) / 100.0,
        "long_ratio": np.linspace(0.2, 0.8, n),
        "n_active_days": np.full(n, 30),
    })


def test_all_segment_columns_added():
    seg = assign_segments(_metrics())
    for c in SEGMENT_COLS + ["is_low_activity"]:
        assert c in seg.columns


def test_quantile_segments_balanced():
    seg = assign_segments(_metrics(12))
    assert seg["frequency_segment"].value_counts().to_dict() == {"Infrequent": 6, "Frequent": 6}
    assert seg["size_segment"].value_counts().to_dict() == {"Small": 6, "Large": 6}
    # tertiles of 12 -> 4/4/4
    assert set(seg["performance_segment"].value_counts().values) == {4}


def test_frequency_orders_correctly():
    seg = assign_segments(_metrics(12))
    # lowest intensity -> Infrequent, highest -> Frequent
    assert seg.sort_values("avg_trades_per_active_day").iloc[0]["frequency_segment"] == "Infrequent"
    assert seg.sort_values("avg_trades_per_active_day").iloc[-1]["frequency_segment"] == "Frequent"


def test_directional_rule_thresholds():
    seg = assign_segments(_metrics(12))
    for _, r in seg.iterrows():
        if r["long_ratio"] > LONG_HI:
            assert r["directional_segment"] == "Long-biased"
        elif r["long_ratio"] < LONG_LO:
            assert r["directional_segment"] == "Short-biased"
        else:
            assert r["directional_segment"] == "Balanced"


def test_deterministic():
    m = _metrics()
    a = assign_segments(m)[SEGMENT_COLS].astype(str)
    b = assign_segments(m)[SEGMENT_COLS].astype(str)
    assert a.equals(b)   # no randomness


def test_low_activity_flag():
    m = _metrics(12)
    m.loc[0, "n_active_days"] = 3
    seg = assign_segments(m)
    assert bool(seg.loc[0, "is_low_activity"]) is True
    assert bool(seg.loc[1, "is_low_activity"]) is False
