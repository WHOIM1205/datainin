"""
Module 7 runner — build account-day & market-day tables (both tz keys) and the report.

Outputs (data/interim/, git-ignored):
  account_day_utc.parquet   market_day_utc.parquet
  account_day_ist.parquet   market_day_ist.parquet
Report:
  outputs/aggregation_report.md   (every metric: grain, function, type, rationale)

Run:  python scripts/build_aggregates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.aggregate import METRIC_DOCS, aggregate_account_day, aggregate_market_day  # noqa: E402
from src.config import resolve  # noqa: E402
from src.io_utils import load_parquet, save_parquet  # noqa: E402

REPORT = resolve("outputs/aggregation_report.md")


def _report(built: dict) -> str:
    L = ["# Aggregation Report — Module 7",
         "",
         "_The analytical foundation: trade-level features collapsed to two strictly-separated "
         "daily grains. Rates/ratios are rebuilt from summed counts/notional (weighted), never "
         "averaged; heavy-tailed quantities use median (robust). Built for both tz keys because the "
         "sentiment timezone is unresolved (D8/D10); the merge module selects one._",
         ""]
    L.append("## Tables produced")
    L.append("| Table | Grain | Rows | Columns |")
    L.append("|---|---|---|---|")
    for name, (df, grain) in built.items():
        L.append(f"| `{name}.parquet` | {grain} | {len(df):,} | {df.shape[1]} |")
    L.append("")
    L.append("## Observation-count columns (sample sizes for later statistics)")
    L.append("- **account-day**: `trade_count`, `pnl_trade_count`, `perp_trade_count`, "
             "`valid_observation_count` (= trade_count). `account_count` ≡ 1 by construction.")
    L.append("- **market-day**: `trade_count`, `pnl_trade_count`, `account_count` (active accounts), "
             "`valid_observation_count` (= account_count).")
    L.append("")
    for grain in ["account-day", "market-day"]:
        L.append(f"## Metric dictionary — {grain}")
        L.append("| Column | Source grain | Function | Type | Rationale |")
        L.append("|---|---|---|---|---|")
        for col, g, src, func, typ, why in METRIC_DOCS:
            if g == grain:
                L.append(f"| `{col}` | {src} | {func} | {typ} | {why} |")
        L.append("")
    L.append("## Aggregation-type legend")
    L.append("- **count** — preserved observation count (sample size).")
    L.append("- **additive** — a sum of an extensive quantity (PnL, notional, fees).")
    L.append("- **median (robust)** — central tendency for heavy-tailed quantities (E1/E6).")
    L.append("- **weighted / derived-from-counts** — a rate or ratio rebuilt from summed "
             "counts/notional, NOT a mean of per-trade rates (avoids whale/minnow mis-averaging).")
    return "\n".join(L)


def main() -> int:
    feats = load_parquet(resolve("data/interim/trades_features.parquet"))
    built = {}
    for tz, date_col in [("utc", "trade_date_utc"), ("ist", "trade_date_ist")]:
        ad = aggregate_account_day(feats, date_col)
        md = aggregate_market_day(ad, feats, date_col)
        save_parquet(ad, resolve(f"data/interim/account_day_{tz}.parquet"))
        save_parquet(md, resolve(f"data/interim/market_day_{tz}.parquet"))
        built[f"account_day_{tz}"] = (ad, "account-day")
        built[f"market_day_{tz}"] = (md, "market-day")
        # reconciliation print
        print(f"[{tz.upper()}] account-day rows={len(ad):,} | market-day rows={len(md):,} | "
              f"Σ account-day trade_count={int(ad['trade_count'].sum()):,} "
              f"(raw trades={len(feats):,}) | "
              f"Σ market-day trade_count={int(md['trade_count'].sum()):,}")
    REPORT.write_text(_report(built))
    print(f"\n>>> Report written to {REPORT.relative_to(resolve('.'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
