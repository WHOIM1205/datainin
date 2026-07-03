"""
Module 5 runner — build daily BTC market-context tables (confounder controls).

Produces one table per date-key convention (tz choice deferred to merge, D8/D10):
  data/interim/market_context_utc.parquet   (keyed on trade_date_utc)
  data/interim/market_context_ist.parquet   (keyed on trade_date_ist)

Run:  python scripts/build_market_context.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import resolve  # noqa: E402
from src.io_utils import load_parquet, save_parquet  # noqa: E402
from src.market_context import compute_market_context, coverage  # noqa: E402


def main() -> int:
    trades = load_parquet(resolve("data/interim/trades_clean.parquet"))
    for tz, date_col in [("utc", "trade_date_utc"), ("ist", "trade_date_ist")]:
        ctx = compute_market_context(trades, date_col)
        out = resolve(f"data/interim/market_context_{tz}.parquet")
        save_parquet(ctx, out)
        cov = coverage(ctx, trades, date_col)
        print(f"[{tz.upper()}] {out.name}: {len(ctx)} rows | "
              f"coverage {cov['coverage_pct']}% of {cov['active_trading_days']} active days | "
              f"returns on {cov['days_with_return']} days | "
              f"BTC price {cov['price_min']:,.0f}→{cov['price_max']:,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
