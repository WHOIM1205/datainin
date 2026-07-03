"""
Module 10 runner — compute trader-level metrics, save table, write metric dictionary.

Outputs:
  data/processed/trader_metrics.parquet
  outputs/metric_dictionary.md
Also prints a redundancy check (pairwise |Spearman| among metrics).

Run:  python scripts/build_metrics.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.config import resolve  # noqa: E402
from src.io_utils import load_parquet, save_parquet  # noqa: E402
from src.metrics import METRIC_DEFS, METRIC_NAMES, trader_metrics  # noqa: E402

DICT = resolve("outputs/metric_dictionary.md")


def _dictionary(m: pd.DataFrame) -> str:
    L = ["# Metric Dictionary — Module 10",
         "",
         "_Trader-level (per-account) metrics. Every metric measures **profitability, risk, "
         "consistency, or trading behaviour**; near-duplicates were pruned to the strongest "
         "representative. No hypothesis testing or conclusions — definitions and computation only._",
         "",
         f"**Grain:** one row per account ({len(m)} accounts). **Source:** merged daily + trade "
         "features (UTC, D8). **Realized PnL** on closing trades only (D6/F2.9).",
         ""]
    for cat in ["profitability", "risk-adjusted", "risk", "consistency", "behaviour"]:
        L.append(f"## {cat.title()}")
        L.append("| Metric | Formula | Interpretation | Assumptions | Limitations | Better |")
        L.append("|---|---|---|---|---|---|")
        for name, c, formula, interp, assum, limit, better in METRIC_DEFS:
            if c == cat:
                L.append(f"| `{name}` | {formula} | {interp} | {assum} | {limit} | {better} |")
        L.append("")
    L.append("## Deliberately excluded (redundancy discipline)")
    L.append("- **Value-at-Risk (VaR)** — dropped in favour of `cvar_5`; CVaR is coherent and "
             "averages the whole tail rather than a single quantile.")
    L.append("- **Symmetric PnL volatility (std)** — not a headline metric; downside risk "
             "(`max_drawdown`, `cvar_5`) is more decision-relevant. It survives only inside the "
             "`sharpe_proxy` denominator.")
    L.append("- **Raw total trade count** — folded into `avg_trades_per_active_day` (intensity) + "
             "`n_active_days` (engagement); the product adds no independent information.")
    L.append("")
    L.append("## Intentionally retained near-neighbours (distinct information)")
    L.append("- `win_rate` (trade grain) vs `pct_profitable_days` (day grain) — a trader can win most "
             "trades yet lose on many days.")
    L.append("- `expectancy_per_trade` ($/trade) vs `roi_on_notional` ($/$) vs `profit_factor` (win/loss "
             "asymmetry) vs `total_pnl` (absolute) — four distinct profitability facets.")
    L.append("- `max_drawdown` (cumulative-path, sequence-dependent worst streak) vs `cvar_5` "
             "(single-day expected shortfall) — the only pair with |Spearman| > 0.9 (**0.929**). Both are "
             "kept because they answer different risk questions (worst *streak* vs typical *bad day*); "
             "their high rank-correlation is largely a shared **USD scale effect** (bigger accounts have "
             "bigger both) and they would diverge under different PnL clustering. Segmentation (M11) can "
             "scale-normalize if needed.")
    return "\n".join(L)


def main() -> int:
    feats = load_parquet(resolve("data/interim/trades_features.parquet"))
    ad = load_parquet(resolve("data/processed/account_day_merged.parquet"))
    m = trader_metrics(feats, ad)
    save_parquet(m, resolve("data/processed/trader_metrics.parquet"))
    DICT.write_text(_dictionary(m))

    print(f"trader_metrics: {m.shape[0]} accounts × {len(METRIC_NAMES)} metrics")
    print("\nsanity (median across accounts):")
    for name in METRIC_NAMES:
        print(f"  {name:28s} median={m[name].median():.4f}  defined={m[name].notna().sum()}/{len(m)}")

    print("\nredundancy check — pairwise |Spearman| > 0.9 (excl. self):")
    corr = m[METRIC_NAMES].corr(method="spearman").abs()
    flagged = [(a, b, round(corr.loc[a, b], 3))
               for i, a in enumerate(METRIC_NAMES) for b in METRIC_NAMES[i + 1:]
               if corr.loc[a, b] > 0.9]
    print("  " + ("\n  ".join(f"{a} ~ {b}: {r}" for a, b, r in flagged) if flagged else "none — no metric pair exceeds 0.9"))
    print(f"\n>>> dictionary: {DICT.relative_to(resolve('.'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
