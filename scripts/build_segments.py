"""
Module 11 runner — define trader segments, evaluate clustering, write the report.

Outputs:
  data/processed/trader_segments.parquet   (metrics + segment labels)
  outputs/segmentation_report.md

Run:  python scripts/build_segments.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import resolve  # noqa: E402
from src.io_utils import load_parquet, save_parquet  # noqa: E402
from src.segments import (LONG_HI, LONG_LO, LOW_ACTIVITY_DAYS, SEGMENT_COLS,
                          assign_segments, evaluate_clustering, segment_balance)  # noqa: E402

REPORT = resolve("outputs/segmentation_report.md")
CLUSTER_FEATURES_STR = "behaviour/performance metrics (roi, intensity, consistency, size, long-ratio)"

SPEC = {
    "frequency_segment": ("quantile (median split)", "avg_trades_per_active_day",
                          "How intensively an account trades on active days."),
    "consistency_segment": ("quantile (median split)", "pct_profitable_days",
                            "How often an account's days end net-positive."),
    "size_segment": ("quantile (median split)", "median_trade_size_usd",
                     "Typical position size."),
    "performance_segment": ("quantile (tertiles)", "roi_on_notional",
                            "Capital efficiency (scale-free return on notional)."),
    "directional_segment": (f"rule-based (long_ratio >{LONG_HI} / <{LONG_LO})", "long_ratio",
                            "Directional style: net long, balanced, or net short."),
}


def main() -> int:
    m = load_parquet(resolve("data/processed/trader_metrics.parquet"))
    seg = assign_segments(m)
    save_parquet(seg, resolve("data/processed/trader_segments.parquet"))
    bal = segment_balance(seg)
    clu = evaluate_clustering(m)

    L = ["# Segmentation Report — Module 11",
         "",
         "_Trader segments defined on 32 accounts. Priority: rule-based > quantile-based > clustering. "
         "Every segment is interpretable, reproducible (deterministic — no random seeds), and stable. "
         "No hypothesis testing and no recommendations here — definitions only._",
         "",
         f"**Population:** {len(seg)} accounts. **Low-activity caveat:** "
         f"{int(seg['is_low_activity'].sum())} account(s) have <{LOW_ACTIVITY_DAYS} active days "
         "(metrics noisier — flagged `is_low_activity`, not dropped).",
         "",
         "## Adopted segments (rule / quantile)",
         "| Segment | Method | Metric | Rationale | Balance | Strengths | Weaknesses |",
         "|---|---|---|---|---|---|---|"]
    strengths = {
        "quantile (median split)": "balanced by construction; deterministic; interpretable",
        "quantile (tertiles)": "balanced thirds; separates high/low; deterministic",
        f"rule-based (long_ratio >{LONG_HI} / <{LONG_LO})": "fixed business thresholds; directly interpretable",
    }
    weaknesses = {
        "quantile (median split)": "cut point is relative (sample-dependent); ignores gap size",
        "quantile (tertiles)": "small per-group n (~10-11); relative cut",
        f"rule-based (long_ratio >{LONG_HI} / <{LONG_LO})": "thresholds are judgement; groups can be imbalanced",
    }
    for col in SEGMENT_COLS:
        method, metric, rationale = SPEC[col]
        L.append(f"| `{col}` | {method} | `{metric}` | {rationale} | {bal[col]} | "
                 f"{strengths[method]} | {weaknesses[method]} |")

    L += ["",
          "## Sample sizes & balance (for downstream power awareness)",
          "Median/tertile splits give balanced groups (16/16 or ~11/10/11); the rule-based directional "
          "split reflects the real long tilt (E5) and is intentionally allowed to be imbalanced. With "
          "only 32 accounts, per-segment n is small — a constraint for later per-account tests.",
          "",
          "## Clustering evaluation (why it was NOT adopted)",
          f"KMeans on standardized {CLUSTER_FEATURES_STR}:",
          f"- Silhouette by k: {clu['silhouette_by_k']} → best k={clu['best_k']} "
          f"(silhouette **{clu['best_silhouette']}**).",
          f"- Seed stability (mean ARI over 10 seeds) at best k: **{clu['seed_stability_ari']}** "
          "(reproducible convergence only — NOT evidence of meaningful structure, given the weak silhouette).",
          f"- Overlap with the quantile performance segment (ARI): **{clu['overlap_with_performance_ari']}**.",
          "",
          "**Decision: clustering NOT adopted.** Justification:",
          f"1. **n = {clu['n_accounts']} is too small** for stable clusters; KMeans (Euclidean, "
          "standardized) was chosen as the simplest baseline and even it is fragile here.",
          f"2. **Weak separation** — best silhouette {clu['best_silhouette']} indicates no clean cluster "
          "structure (values ≲0.5 are weak/overlapping).",
          "3. **Not clearly better than quantiles** — clusters largely recapitulate the interpretable "
          "axes without adding a distinct, nameable archetype, and lose the direct business meaning of "
          "rule/quantile labels.",
          "Per the rule 'if clustering is not clearly better, do not use it', the quantile/rule segments "
          "are the project's segmentation. Clustering remains available as an exploratory cross-check "
          "only.",
          ""]
    REPORT.write_text("\n".join(L))
    print(f"segments saved: {seg.shape} | low-activity accounts: {int(seg['is_low_activity'].sum())}")
    for c in SEGMENT_COLS:
        print(f"  {c:22s} {bal[c]}")
    print(f"\nclustering: {clu}")
    print(f">>> report: {REPORT.relative_to(resolve('.'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
