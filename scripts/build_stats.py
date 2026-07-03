"""
Module 12 runner — run the predefined statistical tests and write the report.

Outputs:
  outputs/statistical_analysis.md
  data/processed/stat_results.parquet   (machine-readable results)

Run:  python scripts/build_stats.py
"""
from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.config import resolve  # noqa: E402
from src.io_utils import load_parquet, save_parquet  # noqa: E402
from src.stats import run_all  # noqa: E402

REPORT = resolve("outputs/statistical_analysis.md")
ALPHA = 0.05


def _trades_sent(features: pd.DataFrame, sentiment: pd.DataFrame) -> pd.DataFrame:
    s = sentiment[["date_key", "sentiment_side"]].rename(columns={"date_key": "trade_date_utc"})
    s["trade_date_utc"] = pd.to_datetime(s["trade_date_utc"]).dt.normalize()
    f = features.copy()
    f["trade_date_utc"] = pd.to_datetime(f["trade_date_utc"]).dt.normalize()
    return f.merge(s, on="trade_date_utc", how="left")


def _meaning(r) -> str:
    sig = r.p_adjusted < ALPHA
    practical = r.effect_magnitude not in ("negligible", "directional")
    if r.rq == "RQ6":
        d = f"sentiment and direction are {'associated' if sig else 'not meaningfully associated'}"
        return (f"On perps, {d}, but the association is **{r.effect_magnitude}** (Cramér's V "
                f"{r.effect_value}) — sentiment barely shifts whether traders go long or short.")
    if r.rq == "RQ7":
        surv = "survives" if (sig and r.effect_magnitude == "directional") else "does NOT survive"
        return (f"After controlling for the BTC market move, the sentiment effect **{surv}** "
                f"(Greed coef {r.effect_value} USD/day, {r.ci}) — i.e. any raw Fear/Greed PnL gap is "
                f"{'partly independent of' if surv=='survives' else 'largely explained by'} market direction.")
    direction = "higher" if r.effect_value > 0 else "lower" if r.effect_value < 0 else "no different"
    sig_txt = "statistically significant after FDR" if sig else "not statistically significant after FDR"
    powered = "" if sig or r.effect_magnitude in ("negligible",) else \
        " — a non-trivial effect that is under-powered here, not proven absent"
    return (f"On Greed vs Fear days, traders' **{r.metric_label}** tends to be **{direction}**; the effect "
            f"is **{r.effect_magnitude}** ({r.effect_name} {r.effect_value}) and {sig_txt}{powered}.")


def main() -> int:
    adm = load_parquet(resolve("data/processed/account_day_merged.parquet"))
    mdm = load_parquet(resolve("data/processed/market_day_merged.parquet"))
    feats = load_parquet(resolve("data/interim/trades_features.parquet"))
    sentiment = load_parquet(resolve("data/interim/sentiment_clean.parquet"))
    trades_sent = _trades_sent(feats, sentiment)

    results = run_all(adm, mdm, trades_sent)
    for r in results:
        r.meaning = _meaning(r)

    save_parquet(pd.DataFrame([asdict(r) for r in results]), resolve("data/processed/stat_results.parquet"))

    L = ["# Statistical Analysis — Module 12",
         "",
         "_Seven predefined research questions, one test each (not fished). Robust-by-default "
         "(non-parametric + bootstrap) given heavy-tailed data (E1/E6); per-trader paired designs "
         "respect non-independence (E3/D9). Effect size is weighted equally with the p-value; p-values "
         "are FDR-adjusted (Benjamini–Hochberg). Neutral days excluded only in binary tests (D5). The "
         "BTC market context is an IN-SAMPLE PROXY (~60% coverage, D11). No business recommendations — "
         "evidence only._",
         "",
         "## Summary",
         "| RQ | Test | p (raw) | p (FDR) | Sig? | Effect | Magnitude |",
         "|---|---|---|---|---|---|---|"]
    for r in results:
        sig = "✅" if r.p_adjusted < ALPHA else "—"
        L.append(f"| {r.rq} | {r.test.split('(')[0].strip()} | {r.p_value:.3g} | {r.p_adjusted:.3g} | "
                 f"{sig} | {r.effect_name} {r.effect_value} | {r.effect_magnitude} |")
    L += ["",
          "> **Statistical vs practical significance.** ✅ marks FDR-significant results only. A ✅ with a "
          "*negligible/small* effect is statistically detectable but of little practical importance "
          "(often driven by large n); a large effect that is not ✅ is under-powered, not absent. Both "
          "columns must be read together.",
          ""]

    for r in results:
        L += [f"## {r.rq} — {r.question}",
              f"- **H0:** {r.h0}",
              f"- **H1:** {r.h1}",
              f"- **Test:** {r.test}",
              f"- **Why this test:** {r.why}",
              f"- **Assumptions:** {r.assumptions}",
              f"- **Assumption check:** {r.assumption_check}",
              f"- **Sample size:** {r.n}",
              f"- **Statistic / p-value:** {r.statistic:.4g} / p={r.p_value:.3g} → "
              f"**FDR-adjusted p={r.p_adjusted:.3g}** ({'significant' if r.p_adjusted<ALPHA else 'not significant'} at α={ALPHA})",
              f"- **Effect size:** {r.effect_name} = **{r.effect_value}** ({r.effect_magnitude})",
              f"- **Confidence interval:** {r.ci}",
              f"- **What this means for trader behaviour:** {r.meaning}",
              ""]
    REPORT.write_text("\n".join(L))
    print("\n".join(L))
    print(f"\n>>> report: {REPORT.relative_to(resolve('.'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
