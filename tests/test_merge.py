"""Unit tests for src.merge — no row multiplication, unmatched rows kept, flags & audit."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.merge import EFFECTIVE_START, merge_daily

DC = "trade_date_utc"


def _daily():
    # two accounts, two days: 2024-06-01 (in sentiment) and 2023-01-01 (NOT in sentiment)
    return pd.DataFrame({
        "Account": ["A", "B", "A"],
        DC: pd.to_datetime(["2024-06-01", "2024-06-01", "2023-01-01"]),
        "daily_pnl": [10.0, -5.0, 3.0],
    })


def _sentiment():
    return pd.DataFrame({
        "date_key": pd.to_datetime(["2024-06-01", "2024-06-02"]),
        "value": [60, 40],
        "classification": ["Greed", "Fear"],
        "sentiment_side": ["Greed", "Fear"],
    })


def _ctx():
    return pd.DataFrame({
        DC: pd.to_datetime(["2024-06-01"]),
        "btc_return": [0.02], "btc_vol_7d": [0.03], "btc_up_day": [True],
    })


def test_no_row_multiplication_and_unmatched_kept():
    merged, audit = merge_daily(_daily(), _sentiment(), _ctx(), DC)
    assert len(merged) == 3                       # left join, no multiplication
    assert audit["duplicate_joins"] == 0
    assert audit["matched_rows"] == 2             # two 2024-06-01 rows matched
    assert audit["unmatched_rows"] == 1           # 2023-01-01 kept but unmatched
    # unmatched row is still present
    assert (merged[DC] == pd.Timestamp("2023-01-01")).sum() == 1


def test_flags_correct():
    merged, _ = merge_daily(_daily(), _sentiment(), _ctx(), DC)
    m = merged.set_index([merged["Account"], merged[DC]])
    assert merged.loc[merged[DC] == "2024-06-01", "has_sentiment"].all()
    assert not merged.loc[merged[DC] == "2023-01-01", "has_sentiment"].any()
    # market proxy only on 2024-06-01
    assert merged.loc[merged[DC] == "2024-06-01", "has_market_proxy"].all()
    assert not merged.loc[merged[DC] == "2023-01-01", "has_market_proxy"].any()
    # effective window: 2024-06-01 >= EFFECTIVE_START, 2023-01-01 < it
    assert merged.loc[merged[DC] == "2024-06-01", "in_effective_window"].all()
    assert not merged.loc[merged[DC] == "2023-01-01", "in_effective_window"].any()


def test_sentiment_values_attached():
    merged, _ = merge_daily(_daily(), _sentiment(), _ctx(), DC)
    row = merged[(merged["Account"] == "A") & (merged[DC] == "2024-06-01")].iloc[0]
    assert row["sentiment_side"] == "Greed"
    assert row["sentiment_value"] == 60


def test_duplicate_sentiment_dates_raise():
    dup = pd.concat([_sentiment(), _sentiment().iloc[[0]]])  # duplicate 2024-06-01
    with pytest.raises(Exception):
        merge_daily(_daily(), dup, _ctx(), DC)   # validate="m:1" must reject


def test_effective_start_is_post_gap():
    assert EFFECTIVE_START == pd.Timestamp("2023-12-01")
