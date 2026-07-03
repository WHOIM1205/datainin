"""
Module 13 — statistical figures (communicate the Module 12 results; not EDA).

Three figures, each tied to specific research question(s):
  SF1  effect-size forest plot (RQ1-RQ6) with bootstrap 95% CIs + magnitude bands
  SF2  paired dumbbell for RQ4 (per-trader position size, Fear vs Greed)
  SF3  RQ1 vs RQ7 coefficient plot — raw PnL gap vs the market-controlled coefficient

Outputs: outputs/figures/sf*.{png,svg} and outputs/statistical_figures.md

Run:  python scripts/build_stat_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from src.config import resolve  # noqa: E402
from src.io_utils import load_parquet  # noqa: E402
from src.stats import (account_regime_metrics, cliffs_delta, paired_rank_biserial,  # noqa: E402
                       _paired, MIN_DAYS)
from src.viz import INK, PALETTE, apply_style, save_fig  # noqa: E402

FIG = resolve("outputs/figures")
DOC = resolve("outputs/statistical_figures.md")
BOOT = np.random.default_rng(7)
ALPHA = 0.05


def _boot_effect(fn, *arrays, n=3000):
    vals = []
    for _ in range(n):
        if len(arrays) == 2 and len(arrays[0]) == len(arrays[1]):  # paired
            idx = BOOT.integers(0, len(arrays[0]), len(arrays[0]))
            vals.append(fn(arrays[0][idx], arrays[1][idx]))
        else:  # independent
            a = BOOT.choice(arrays[0], len(arrays[0]))
            b = BOOT.choice(arrays[1], len(arrays[1]))
            vals.append(fn(a, b))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def _size_pivot(trades_sent):
    perp = trades_sent[(trades_sent["is_perp"]) & (trades_sent["Size USD"] > 0)
                       & (trades_sent["sentiment_side"].isin(["Fear", "Greed"]))]
    g = perp.groupby(["Account", "sentiment_side"], observed=True).agg(
        v=("Size USD", "median"),
        n_days=("trade_date_utc", lambda s: s.dt.normalize().nunique()))
    piv = g.unstack("sentiment_side")
    ok = (piv[("n_days", "Fear")] >= MIN_DAYS) & (piv[("n_days", "Greed")] >= MIN_DAYS)
    piv = piv[ok].dropna(subset=[("v", "Fear"), ("v", "Greed")])
    return piv[("v", "Fear")].values, piv[("v", "Greed")].values


def build_arrays(adm, mdm, trades_sent):
    arm = account_regime_metrics(adm)
    a = {}
    fe = mdm.loc[mdm["sentiment_side"] == "Fear", "median_account_daily_pnl"].dropna().values
    gr = mdm.loc[mdm["sentiment_side"] == "Greed", "median_account_daily_pnl"].dropna().values
    a["RQ1"] = ("independent", fe, gr)
    for rq, col in [("RQ2", "median_daily_pnl"), ("RQ3", "win_rate"), ("RQ5", "trades_per_day")]:
        f, g, _ = _paired(arm, col)
        a[rq] = ("paired", f, g)
    fs, gs = _size_pivot(trades_sent)
    a["RQ4"] = ("paired", fs, gs)
    return a


# ---------------- SF1 ----------------
def sf1_forest(results, arrays):
    order = ["RQ1", "RQ2", "RQ3", "RQ4", "RQ5", "RQ6"]
    labels = {"RQ1": "RQ1 market PnL", "RQ2": "RQ2 trader PnL", "RQ3": "RQ3 win rate",
              "RQ4": "RQ4 position size", "RQ5": "RQ5 frequency", "RQ6": "RQ6 direction (|V|)"}
    fig, ax = plt.subplots(figsize=(9, 4.6))
    # magnitude bands (|effect|): negligible/small/medium/large
    for x0, x1, c in [(0, .147, "#f2f2ef"), (.147, .33, "#e6e6e2"), (.33, .474, "#dadad4"), (.474, 1, "#cdcdc6")]:
        ax.axvspan(x0, x1, color=c, zorder=0); ax.axvspan(-x1, -x0, color=c, zorder=0)
    ax.axvline(0, color=INK["axis"], lw=1.2)
    for i, rq in enumerate(order):
        r = results[results["rq"] == rq].iloc[0]
        eff = r["effect_value"]
        sig = r["p_adjusted"] < ALPHA
        color = PALETTE["primary"] if sig else INK["muted"]
        if rq == "RQ6":
            ax.plot(eff, i, "D", color=color, ms=9)  # unsigned magnitude
        else:
            kind, f, g = arrays[rq]
            fn = cliffs_delta if kind == "independent" else paired_rank_biserial
            lo, hi = _boot_effect(fn, g, f) if kind == "paired" else _boot_effect(fn, g, f)
            ax.plot([lo, hi], [i, i], color=color, lw=2.4)
            ax.plot(eff, i, "o", color=color, ms=9)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([labels[o] for o in order])
    ax.invert_yaxis()
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Effect size  (Greed − Fear; signed for RQ1-5, |Cramér's V| for RQ6)")
    ax.set_title("SF1 · Effect sizes with 95% bootstrap CIs (bands: negligible→large)")
    ax.plot([], [], "o", color=PALETTE["primary"], label="FDR-significant")
    ax.plot([], [], "o", color=INK["muted"], label="not significant")
    ax.legend(loc="lower right")
    return save_fig(fig, FIG, "sf1_effect_size_forest")


# ---------------- SF2 ----------------
def sf2_dumbbell(arrays):
    _, fear, greed = arrays["RQ4"]
    order = np.argsort(fear)
    fear, greed = fear[order], greed[order]
    y = np.arange(len(fear))
    fig, ax = plt.subplots(figsize=(8, 5.2))
    for i in range(len(fear)):
        ax.plot([fear[i], greed[i]], [y[i], y[i]], color=INK["grid"], lw=1.6, zorder=1)
    ax.scatter(fear, y, color=PALETTE["Fear"], s=42, label="Fear days", zorder=2)
    ax.scatter(greed, y, color=PALETTE["Greed"], s=42, label="Greed days", zorder=2)
    ax.set_xscale("log")
    ax.set_xlabel("Median perp trade size (USD, log scale)")
    ax.set_ylabel("Traders (sorted by Fear-day size)")
    ax.set_yticks([])
    ax.set_title("SF2 · RQ4 — per-trader position size, Fear vs Greed (paired)")
    ax.legend(loc="lower right")
    return save_fig(fig, FIG, "sf2_rq4_position_size_dumbbell")


# ---------------- SF3 ----------------
def sf3_confounder(mdm):
    import statsmodels.formula.api as smf
    from src.stats import boot_ci_diff_medians
    md = mdm[mdm["sentiment_side"].isin(["Fear", "Greed"])].copy()
    fear = md.loc[md["sentiment_side"] == "Fear", "median_account_daily_pnl"].dropna().values
    greed = md.loc[md["sentiment_side"] == "Greed", "median_account_daily_pnl"].dropna().values
    raw = np.median(greed) - np.median(fear)
    raw_lo, raw_hi = boot_ci_diff_medians(fear, greed)

    sub = md[md["has_market_proxy"]].copy()
    sub["is_greed"] = (sub["sentiment_side"] == "Greed").astype(int)
    m = smf.ols("median_account_daily_pnl ~ is_greed + btc_return + btc_vol_7d", sub).fit(cov_type="HC3")
    coef = m.params["is_greed"]; clo, chi = m.conf_int().loc["is_greed"].tolist()

    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    pts = [("Raw Greed−Fear gap\n(RQ1, unconditional)", raw, raw_lo, raw_hi, PALETTE["accent"]),
           ("Greed effect controlling\nBTC move (RQ7)", coef, clo, chi, PALETTE["primary"])]
    for i, (lab, est, lo, hi, c) in enumerate(pts):
        ax.plot([lo, hi], [i, i], color=c, lw=2.6)
        ax.plot(est, i, "o", color=c, ms=11)
        ax.annotate(f"{est:.0f} USD/day  [{lo:.0f}, {hi:.0f}]", (est, i), textcoords="offset points",
                    xytext=(0, -16), ha="center", va="top", color=INK["secondary"], fontsize=9)
    ax.axvline(0, color=INK["axis"], lw=1.4)
    ax.set_ylim(1.6, -0.6)
    ax.set_yticks([0, 1]); ax.set_yticklabels([p[0] for p in pts])
    ax.set_xlabel("Effect on market-median daily PnL (USD/day)")
    ax.set_title("SF3 · RQ1→RQ7 — Fear/Greed PnL gap vs market-controlled effect", pad=14)
    return save_fig(fig, FIG, "sf3_rq7_confounder_coefficient")


def _doc(figs):
    return "\n".join([
        "# Statistical Figures — Module 13",
        "",
        "_Each figure communicates a Module-12 statistical result (effect size, CI, paired structure, "
        "or regression coefficient) — not EDA. Every figure references its research question._",
        "",
        "## SF1 · Effect-size forest — " + f"`figures/{figs['sf1']['png'].stem}.png`",
        "- **Research question(s):** RQ1–RQ6 (overview).",
        "- **Statistical result referenced:** Cliff's δ (RQ1), matched-pairs rank-biserial (RQ2–RQ5), "
        "Cramér's V (RQ6), with 95% bootstrap CIs and FDR significance.",
        "- **Interpretation:** All performance/behaviour effects sit in the negligible–small band except "
        "RQ4 (position size, large). RQ6 is significant but small.",
        "- **Key takeaway:** Sentiment's measurable footprint on traders is mostly small; the one "
        "sizeable effect is **position sizing**, and even it has a wide CI (few traders qualify).",
        "",
        "## SF2 · RQ4 paired position size — " + f"`figures/{figs['sf2']['png'].stem}.png`",
        "- **Research question:** RQ4 — do traders size differently on Fear vs Greed days?",
        "- **Statistical result referenced:** Wilcoxon signed-rank, rank-biserial 0.57 (large), "
        "median Greed−Fear +107 USD (95% CI [6, 508]); FDR p=0.084.",
        "- **Interpretation:** Most traders' dots move right from Fear (red) to Greed (green) — position "
        "sizes are systematically larger on Greed days.",
        "- **Key takeaway:** A consistent **risk-on sizing** pattern in Greed; large but under-powered "
        "(n=20 qualifying traders), so directional-but-not-yet-conclusive.",
        "",
        "## SF3 · RQ1→RQ7 confounder — " + f"`figures/{figs['sf3']['png'].stem}.png`",
        "- **Research question:** RQ1 (raw PnL gap) vs RQ7 (gap after controlling the BTC market move).",
        "- **Statistical result referenced:** raw median gap +178 USD/day (CI excludes 0) vs OLS Greed "
        "coefficient +65 USD/day (95% CI [-350, 480], crosses 0).",
        "- **Interpretation:** The apparent Greed-day PnL advantage shrinks toward zero and its CI widens "
        "across zero once BTC return & volatility are controlled.",
        "- **Key takeaway:** The Fear/Greed PnL gap is **largely a market-direction artifact**, not an "
        "independent sentiment edge (reminder: BTC context is an in-sample proxy, ~60% coverage).",
        "",
    ])


def main() -> int:
    apply_style()
    adm = load_parquet(resolve("data/processed/account_day_merged.parquet"))
    mdm = load_parquet(resolve("data/processed/market_day_merged.parquet"))
    feats = load_parquet(resolve("data/interim/trades_features.parquet"))
    sent = load_parquet(resolve("data/interim/sentiment_clean.parquet"))
    results = load_parquet(resolve("data/processed/stat_results.parquet"))

    s = sent[["date_key", "sentiment_side"]].rename(columns={"date_key": "trade_date_utc"})
    s["trade_date_utc"] = pd.to_datetime(s["trade_date_utc"]).dt.normalize()
    feats["trade_date_utc"] = pd.to_datetime(feats["trade_date_utc"]).dt.normalize()
    trades_sent = feats.merge(s, on="trade_date_utc", how="left")

    arrays = build_arrays(adm, mdm, trades_sent)
    figs = {"sf1": sf1_forest(results, arrays), "sf2": sf2_dumbbell(arrays), "sf3": sf3_confounder(mdm)}
    DOC.write_text(_doc(figs))
    print(f"built {len(figs)} figures ({len(list(FIG.glob('sf*.png')))} PNG + "
          f"{len(list(FIG.glob('sf*.svg')))} SVG); doc: {DOC.relative_to(resolve('.'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
