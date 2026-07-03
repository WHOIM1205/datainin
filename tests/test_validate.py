"""Unit tests for src.validate — the Module 2 checks catch what they claim to guard.

Strategy: build small synthetic frames (valid, then deliberately broken) and assert
that each rule flips to FAIL/WARN on the corresponding defect. This keeps the module
independently testable without loading the 47 MB raw file.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import validate as V


def _status(results, check_substr):
    """Return the status of the first check whose name contains check_substr."""
    for r in results:
        if check_substr in r.check:
            return r.status
    raise AssertionError(f"check matching {check_substr!r} not found")


# ---------- helpers ----------
def test_norm_dtype_maps_object_and_string_to_str():
    assert V._norm_dtype("object") == "str"
    assert V._norm_dtype("string") == "str"
    assert V._norm_dtype("int64") == "int64"


# ---------- sentiment ----------
def _valid_sentiment():
    return pd.DataFrame({
        "timestamp": [1, 2, 3],
        "value": [10, 50, 80],
        "classification": ["Extreme Fear", "Neutral", "Extreme Greed"],
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
    })


def test_sentiment_unknown_classification_fails():
    df = _valid_sentiment()
    df.loc[0, "classification"] = "Euphoria"  # not in the frozen 5-bucket domain
    res = V.validate_sentiment(df)
    assert _status(res, "classification in known") == "FAIL"


def test_sentiment_value_out_of_range_fails():
    df = _valid_sentiment()
    df.loc[0, "value"] = 250
    res = V.validate_sentiment(df)
    assert _status(res, "value within") == "FAIL"


def test_sentiment_duplicate_date_fails():
    df = _valid_sentiment()
    df.loc[2, "date"] = "2024-01-01"
    res = V.validate_sentiment(df)
    assert _status(res, "duplicate dates") == "FAIL"


# ---------- trades ----------
def _valid_trades():
    return pd.DataFrame({
        "Account": ["a", "a"], "Coin": ["BTC", "ETH"],
        "Execution Price": [10.0, 20.0], "Size Tokens": [2.0, 3.0],
        "Size USD": [20.0, 60.0], "Side": ["BUY", "SELL"],
        "Timestamp IST": ["01-06-2024 10:00", "02-06-2024 11:00"],
        "Start Position": [0.0, 0.0], "Direction": ["Open Long", "Close Long"],
        "Closed PnL": [0.0, 5.0], "Transaction Hash": ["0x1", "0x2"],
        "Order ID": [1, 2], "Crossed": [True, False],
        "Fee": [0.1, -0.05], "Trade ID": [1.0, 2.0], "Timestamp": [1.7e12, 1.7e12],
    })


def test_trades_unknown_side_fails():
    df = _valid_trades()
    df.loc[0, "Side"] = "HOLD"
    res = V.validate_trades(df)
    assert _status(res, "Side in {BUY,SELL}") == "FAIL"


def test_trades_unknown_direction_fails():
    df = _valid_trades()
    df.loc[0, "Direction"] = "Teleport"
    res = V.validate_trades(df)
    assert _status(res, "Direction in known") == "FAIL"


def test_trades_leverage_column_fails():
    df = _valid_trades()
    df["leverage"] = 5
    res = V.validate_trades(df)
    assert _status(res, "no leverage column") == "FAIL"


def test_trades_direction_side_mismatch_warns():
    df = _valid_trades()
    df.loc[0, "Side"] = "SELL"  # Open Long should be BUY
    res = V.validate_trades(df)
    assert _status(res, "Direction↔Side consistent") == "WARN"


def test_trades_zero_size_warns():
    df = _valid_trades()
    df.loc[0, "Size USD"] = 0.0
    res = V.validate_trades(df)
    assert _status(res, "Size USD >= 0") == "WARN"


def test_trades_valid_frame_has_no_failures_on_domain_checks():
    # Domain/consistency checks should pass on a clean frame (row-count check is
    # expected to fail because this fixture isn't the full 211k dataset — so we
    # assert specifically on the content checks, not the count).
    res = V.validate_trades(_valid_trades())
    for name in ["Side in {BUY,SELL}", "Direction in known", "no leverage column",
                 "Direction↔Side consistent", "Crossed is boolean"]:
        assert _status(res, name) == "PASS", name
