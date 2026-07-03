"""Unit tests for Module 3 cleaners — correctness of derived columns & flags,
non-destructiveness (no dropped rows, raw cols preserved), and Parquet round-trip
dtype preservation (tz-aware datetimes)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.clean_sentiment import clean_sentiment
from src.clean_trades import clean_trades
from src.io_utils import load_parquet, save_parquet


def _sentiment():
    return pd.DataFrame({
        "timestamp": [1, 2, 3, 4, 5],
        "value": [10, 30, 50, 70, 90],
        "classification": ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"],
        "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
    })


def _trades():
    return pd.DataFrame({
        "Account": ["a"] * 5, "Coin": ["BTC", "@107", "PURR/USDC", "ETH", "SOL"],
        "Execution Price": [10.0, 5.0, 1.0, 20.0, 2.0],
        "Size Tokens": [2.0, 4.0, 0.0, 3.0, 100.0],
        "Size USD": [20.0, 20.0, 0.0, 60.0, 200.0],
        "Side": ["BUY", "BUY", "SELL", "SELL", "BUY"],
        # row 4 (index 4) crosses the IST/UTC day boundary: 03:00 IST = prev-day 21:30 UTC
        "Timestamp IST": ["01-06-2024 10:00", "01-06-2024 12:00", "02-06-2024 09:00",
                          "02-06-2024 15:00", "01-06-2024 03:00"],
        "Start Position": [0.0, 0.0, 0.0, 0.0, 0.0],
        "Direction": ["Open Long", "Buy", "Sell", "Close Short", "Auto-Deleveraging"],
        "Closed PnL": [0.0, 0.0, 1.0, 5.0, -3.0],
        "Transaction Hash": [f"0x{i}" for i in range(5)],
        "Order ID": list(range(5)), "Crossed": [True] * 5,
        "Fee": [0.1] * 5, "Trade ID": [1.0] * 5, "Timestamp": [1.7e12] * 5,
    })


# ---------- sentiment ----------
def test_sentiment_non_destructive_and_derived():
    raw = _sentiment()
    clean, ops = clean_sentiment(raw)
    assert len(clean) == len(raw)                       # no rows dropped
    assert all(c in clean.columns for c in raw.columns)  # raw preserved
    assert "date_key" in clean.columns and "sentiment_side" in clean.columns
    assert str(clean["date_key"].dtype).startswith("datetime64")


def test_sentiment_side_mapping_and_neutral_kept():
    clean, _ = clean_sentiment(_sentiment())
    got = dict(zip(clean["classification"], clean["sentiment_side"]))
    assert got == {"Extreme Fear": "Fear", "Fear": "Fear", "Neutral": "Neutral",
                   "Greed": "Greed", "Extreme Greed": "Greed"}
    assert (clean["sentiment_side"] == "Neutral").sum() == 1  # Neutral retained first-class


# ---------- trades ----------
def test_trades_non_destructive():
    raw = _trades()
    clean, _ = clean_trades(raw)
    assert len(clean) == len(raw)
    assert all(c in clean.columns for c in raw.columns)


def test_trades_flags_correct():
    clean, _ = clean_trades(_trades())
    assert clean["is_zero_size"].tolist() == [False, False, True, False, False]
    # spot: @107 (idx1), PURR/USDC (idx2), Direction Buy (idx1), Direction Sell (idx2)
    assert clean["is_spot"].tolist() == [False, True, True, False, False]
    # edge: Auto-Deleveraging (idx4)
    assert clean["is_edge_direction"].tolist() == [False, False, False, False, True]


def test_trades_dual_date_keys_and_boundary():
    clean, _ = clean_trades(_trades())
    assert str(clean["ts_ist"].dtype).endswith("Asia/Kolkata]")
    # boundary row (idx4): 01-06 03:00 IST -> 31-05 21:30 UTC
    assert clean.loc[4, "trade_date_ist"] == pd.Timestamp("2024-06-01")
    assert clean.loc[4, "trade_date_utc"] == pd.Timestamp("2024-05-31")
    # non-boundary row (idx0): same day both zones
    assert clean.loc[0, "trade_date_ist"] == clean.loc[0, "trade_date_utc"]


def test_no_leverage_column_added():
    clean, _ = clean_trades(_trades())
    assert not any("lever" in c.lower() for c in clean.columns)


# ---------- parquet round-trip ----------
def test_parquet_roundtrip_preserves_tz(tmp_path):
    clean, _ = clean_trades(_trades())
    p = tmp_path / "t.parquet"
    save_parquet(clean, p)
    back = load_parquet(p)
    assert str(back["ts_ist"].dtype).endswith("Asia/Kolkata]")   # tz preserved
    assert back["is_spot"].dtype == bool
    assert len(back) == len(clean)
