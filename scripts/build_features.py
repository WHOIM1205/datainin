"""
Module 6 runner — add per-trade features and persist.

Input:  data/interim/trades_clean.parquet
Output: data/interim/trades_features.parquet  (cleaned + per-trade features)

Run:  python scripts/build_features.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import resolve  # noqa: E402
from src.features import add_trade_features  # noqa: E402
from src.io_utils import load_parquet, save_parquet  # noqa: E402

NEW_COLS = ["pnl_bearing", "is_win", "is_perp", "position_side", "pnl_per_notional",
            "fee_bps", "fee_drag", "size_z", "is_large_trade", "account_tenure_days"]


def main() -> int:
    raw = load_parquet(resolve("data/interim/trades_clean.parquet"))
    feat = add_trade_features(raw)
    save_parquet(feat, resolve("data/interim/trades_features.parquet"))

    print(f"rows: {len(raw):,} -> {len(feat):,} (added {len(NEW_COLS)} feature columns)")
    print(f"raw columns preserved: {all(c in feat.columns for c in raw.columns)}")
    print("\nfeature coverage / sanity:")
    print(f"  pnl_bearing trades:      {feat['pnl_bearing'].sum():,} ({feat['pnl_bearing'].mean()*100:.1f}%)")
    print(f"  win rate (pnl-bearing):  {feat.loc[feat['pnl_bearing'],'is_win'].mean()*100:.1f}%")
    print(f"  position_side split:     {feat['position_side'].value_counts().to_dict()}")
    print(f"  pnl_per_notional median: {feat['pnl_per_notional'].median():.4f}  "
          f"(IQR {feat['pnl_per_notional'].quantile(.25):.4f}..{feat['pnl_per_notional'].quantile(.75):.4f})")
    print(f"  fee_bps median:          {feat['fee_bps'].median():.2f} bps  "
          f"(negative/rebate rows: {(feat['fee_bps']<0).sum():,})")
    print(f"  size_z defined:          {feat['size_z'].notna().sum():,}  "
          f"(large trades |z|>2: {feat['is_large_trade'].sum():,})")
    print(f"  account_tenure_days:     0..{int(feat['account_tenure_days'].max())} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
