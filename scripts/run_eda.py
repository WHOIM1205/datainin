"""
Module 4 runner — Exploratory Data Analysis.

Generates 6 curated figures (PNG+SVG, high-DPI) on the CLEANED, un-merged data and
writes outputs/eda_summary.md. Each chart answers a specific question and feeds the
later statistical analysis. Numbers in the summary are computed here (reproducible),
not hand-typed.

Run:  python scripts/run_eda.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt  # noqa: E402

from src.config import resolve  # noqa: E402
from src.io_utils import load_parquet  # noqa: E402
from src.viz import INK, PALETTE, apply_style, save_fig  # noqa: E402

FIG = resolve("outputs/figures")
SUMMARY = resolve("outputs/eda_summary.md")

LONG_DIRS = {"Open Long", "Close Long"}
SHORT_DIRS = {"Open Short", "Close Short"}


def prep(trades: pd.DataFrame) -> pd.DataFrame:
    df = trades.copy()
    df["pnl_bearing"] = df["Closed PnL"] != 0
    df["is_perp"] = ~df["is_spot"] & ~df["is_edge_direction"]
    cat = np.where(df["Direction"].isin(LONG_DIRS), "Long",
          np.where(df["Direction"].isin(SHORT_DIRS), "Short",
          np.where(df["is_spot"], "Spot", "Edge")))
    df["direction_cat"] = cat
    return df


# ---------------- V1 ----------------
def v1_sentiment_timeline(sent, w_start, w_end):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(sent["date_key"], sent["value"], color=PALETTE["primary"], lw=1.4)
    ax.axvspan(w_start, w_end, color=PALETTE["accent"], alpha=0.10, lw=0)
    for edge, lbl in [(25, "Fear"), (45, "Neutral"), (55, "Greed"), (75, "Extreme Greed")]:
        ax.axhline(edge, color=INK["grid"], lw=0.8, ls="--", zorder=0)
    ax.set_title("V1 · Fear & Greed index over time (trade window shaded)")
    ax.set_ylabel("Index value (0–100)"); ax.set_xlabel("")
    ax.set_ylim(0, 100)
    ax.annotate("trade-data window\n(2023-05 → 2025-05)",
                xy=(w_start + (w_end - w_start) / 2, 92), ha="center", va="top",
                color=INK["secondary"], fontsize=9)
    files = save_fig(fig, FIG, "v1_sentiment_timeline_with_trade_window")

    inw = sent[(sent["date_key"] >= w_start) & (sent["date_key"] <= w_end)]
    return files, {
        "n_inwindow_days": len(inw),
        "side_balance": inw["sentiment_side"].value_counts().to_dict(),
        "bucket_balance": inw["classification"].value_counts().to_dict(),
        "mean_value_inwindow": round(float(inw["value"].mean()), 1),
    }


# ---------------- V2 ----------------
def v2_pnl_distribution(df):
    pnl = df.loc[df["pnl_bearing"], "Closed PnL"]
    lo, hi = pnl.quantile(0.005), pnl.quantile(0.995)
    n_below, n_above = int((pnl < lo).sum()), int((pnl > hi).sum())
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.hist(pnl, bins=120, range=(lo, hi), color=PALETTE["primary"], log=True)
    ax.axvline(pnl.median(), color=INK["primary"], lw=1.6, label=f"median = {pnl.median():.2f}")
    ax.axvline(pnl.mean(), color=PALETTE["accent"], lw=1.6, ls="--", label=f"mean = {pnl.mean():.2f}")
    ax.axvline(0, color=INK["axis"], lw=1.0, zorder=0)
    ax.set_title("V2 · Realized PnL distribution (closing trades) — log-count")
    ax.set_xlabel("Closed PnL (USD, winsorized 0.5–99.5%)"); ax.set_ylabel("Trades (log scale)")
    ax.legend(loc="upper right")
    ax.annotate(f"{n_below:,} extreme losses < {lo:,.0f}   |   {n_above:,} extreme gains > {hi:,.0f}",
                xy=(0.5, -0.28), xycoords="axes fraction", ha="center",
                color=INK["secondary"], fontsize=9)
    files = save_fig(fig, FIG, "v2_realized_pnl_distribution")
    return files, {
        "n_pnl_bearing": int(len(pnl)),
        "win_rate": round(float((pnl > 0).mean()) * 100, 1),
        "median": round(float(pnl.median()), 2), "mean": round(float(pnl.mean()), 2),
        "skew": round(float(pnl.skew()), 1), "kurtosis": round(float(pnl.kurt()), 1),
        "min": round(float(pnl.min()), 0), "max": round(float(pnl.max()), 0),
    }


# ---------------- V3 ----------------
def v3_size_distribution(df):
    d = df[df["Size USD"] > 0]
    perp = np.log10(d.loc[d["is_perp"], "Size USD"])
    spot = np.log10(d.loc[d["is_spot"], "Size USD"])
    bins = np.linspace(min(perp.min(), spot.min()), max(perp.max(), spot.max()), 60)
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.hist(perp, bins=bins, color=PALETTE["Long"], alpha=0.75, label="Perpetual")
    ax.hist(spot, bins=bins, color=PALETTE["Spot"], alpha=0.65, label="Spot")
    ax.set_title("V3 · Trade size distribution (log10 USD) — perp vs spot")
    ax.set_xlabel("log10(Size USD)"); ax.set_ylabel("Trades")
    ax.legend(loc="upper right")
    files = save_fig(fig, FIG, "v3_trade_size_distribution_perp_vs_spot")
    return files, {
        "perp_median": round(float(10 ** perp.median()), 0),
        "spot_median": round(float(10 ** spot.median()), 0),
        "overall_min": round(float(d["Size USD"].min()), 2),
        "overall_max": round(float(d["Size USD"].max()), 0),
    }


# ---------------- V4 ----------------
def lorenz_gini(counts: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Return Lorenz curve (x, y) and the Gini coefficient for non-negative counts."""
    c = np.sort(np.asarray(counts, dtype=float))
    cum = np.cumsum(c) / c.sum()
    x = np.arange(1, len(c) + 1) / len(c)
    lx = np.concatenate([[0], x]); ly = np.concatenate([[0], cum])
    gini = 1 - 2 * np.trapezoid(ly, lx)
    return lx, ly, float(gini)


def v4_activity_concentration(df):
    per_acct = df.groupby("Account").size().sort_values()
    lorenz_x, lorenz_y, gini = lorenz_gini(per_acct.values)
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    ax.plot(lorenz_x, lorenz_y, color=PALETTE["primary"], lw=2.2, label="Observed")
    ax.plot([0, 1], [0, 1], color=INK["muted"], lw=1.2, ls="--", label="Perfect equality")
    ax.fill_between(lorenz_x, lorenz_y, lorenz_x, color=PALETTE["primary"], alpha=0.08)
    ax.set_title("V4 · Account activity concentration (Lorenz)")
    ax.set_xlabel("Cumulative share of accounts"); ax.set_ylabel("Cumulative share of trades")
    ax.legend(loc="upper left")
    ax.annotate(f"Gini = {gini:.2f}", xy=(0.62, 0.18), color=INK["primary"], fontweight="bold")
    files = save_fig(fig, FIG, "v4_account_activity_concentration_lorenz")
    top1 = per_acct.iloc[-1] / per_acct.sum() * 100
    top5 = per_acct.iloc[-5:].sum() / per_acct.sum() * 100
    return files, {"gini": round(float(gini), 2), "n_accounts": int(len(per_acct)),
                   "top1_share": round(float(top1), 1), "top5_share": round(float(top5), 1)}


# ---------------- V5 ----------------
def v5_direction_baseline(df):
    order = ["Long", "Short", "Spot", "Edge"]
    counts = df["direction_cat"].value_counts().reindex(order).fillna(0).astype(int)
    colors = [PALETTE["Long"], PALETTE["Short"], PALETTE["Spot"], PALETTE["Neutral"]]
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    bars = ax.bar(order, counts.values, color=colors, width=0.66)
    total = counts.sum()
    for b, c in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, c, f"{c:,}\n({c/total*100:.1f}%)",
                ha="center", va="bottom", color=INK["secondary"], fontsize=9)
    ax.set_title("V5 · Trade composition baseline (Long / Short / Spot / Edge)")
    ax.set_ylabel("Trades"); ax.set_ylim(0, counts.max() * 1.15)
    files = save_fig(fig, FIG, "v5_long_short_spot_baseline")
    ls_ratio = counts["Long"] / counts["Short"] if counts["Short"] else float("nan")
    return files, {"counts": counts.to_dict(), "long_short_ratio": round(float(ls_ratio), 2)}


# ---------------- V6 ----------------
def v6_activity_over_time(df, w_start, w_end):
    daily = df.groupby("trade_date_utc").size()
    full = pd.date_range(w_start, w_end, freq="D")
    daily = daily.reindex(full, fill_value=0)
    ma = daily.rolling(7, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(daily.index, daily.values, color=PALETTE["primary"], lw=0.7, alpha=0.45, label="Daily trade count")
    ax.plot(ma.index, ma.values, color=PALETTE["accent"], lw=2.0, label="7-day moving average")
    ax.set_title("V6 · Trading activity over time (daily count + 7-day MA)")
    ax.set_ylabel("Trades per day"); ax.set_xlabel("")
    ax.legend(loc="upper left")
    files = save_fig(fig, FIG, "v6_trading_activity_over_time")
    zero_days = int((daily == 0).sum())
    # longest run of zero-activity days
    z = (daily == 0).astype(int).values
    longest_gap, run = 0, 0
    for v in z:
        run = run + 1 if v else 0
        longest_gap = max(longest_gap, run)
    # temporal concentration of volume (the key sampling caveat)
    total = len(df)
    pct_2023 = (df["trade_date_utc"] < "2024-01-01").mean() * 100
    pct_last6mo = (df["trade_date_utc"] >= "2024-11-01").mean() * 100
    return files, {
        "span_days": len(daily), "active_days": int((daily > 0).sum()),
        "zero_days": zero_days, "coverage_pct": round((daily > 0).mean() * 100, 1),
        "max_daily": int(daily.max()), "max_daily_date": str(daily.idxmax().date()),
        "mean_daily": round(float(daily.mean()), 0), "longest_zero_gap": longest_gap,
        "pct_2023": round(float(pct_2023), 1), "pct_last6mo": round(float(pct_last6mo), 1),
    }


def main() -> int:
    apply_style()
    sent = load_parquet(resolve("data/interim/sentiment_clean.parquet"))
    trades = prep(load_parquet(resolve("data/interim/trades_clean.parquet")))
    w_start = min(trades["trade_date_utc"].min(), trades["trade_date_ist"].min())
    w_end = max(trades["trade_date_utc"].max(), trades["trade_date_ist"].max())

    f1, s1 = v1_sentiment_timeline(sent, w_start, w_end)
    f2, s2 = v2_pnl_distribution(trades)
    f3, s3 = v3_size_distribution(trades)
    f4, s4 = v4_activity_concentration(trades)
    f5, s5 = v5_direction_baseline(trades)
    f6, s6 = v6_activity_over_time(trades, w_start, w_end)

    md = _summary(w_start, w_end, [(f1, s1), (f2, s2), (f3, s3), (f4, s4), (f5, s5), (f6, s6)])
    SUMMARY.write_text(md)
    print(md)
    print(f"\n>>> Summary written to {SUMMARY.relative_to(resolve('.'))}")
    print(f">>> {len(list(FIG.glob('*.png')))} PNG + {len(list(FIG.glob('*.svg')))} SVG in {FIG.relative_to(resolve('.'))}")
    return 0


def _fig_links(files):
    stem = files["png"].stem
    return f"`figures/{stem}.png` · `figures/{stem}.svg`"


def _summary(w_start, w_end, results):
    (f1, s1), (f2, s2), (f3, s3), (f4, s4), (f5, s5), (f6, s6) = results
    L = ["# EDA Summary — Module 4",
         "",
         "_Six curated figures on the cleaned, un-merged data. Each answers a question and feeds "
         "the statistical analysis (Modules 10–12). Numbers are computed by `scripts/run_eda.py`._",
         f"\n**Analysis window (trades):** {w_start.date()} → {w_end.date()}",
         "",
         "> Not charted (would be decorative): missing-value & duplicate plots (0 of each — F1.3/F2.3); "
         "leverage distribution (excluded, D3/F2.4); trade-level correlation heatmap (mechanical — "
         "deferred to post-metrics viz, M13).",
         ""]

    def block(n, title, files, question, viz, obs, biz, stat, dep):
        L.extend([f"## {n}. {title}", "",
                  f"- **Question:** {question}",
                  f"- **Visualization:** {viz} — {_fig_links(files)}",
                  f"- **Key observation:** {obs}",
                  f"- **Business implication:** {biz}",
                  f"- **Statistical implication:** {stat}",
                  f"- **Next-module dependency:** {dep}", ""])

    block("V1", "Fear & Greed over time (trade window shaded)", f1,
          "Which sentiment regimes occur, and how much of each falls inside the trade window?",
          "Index time series with the 2023-05→2025-05 trade window shaded and regime thresholds marked",
          f"In-window: {s1['n_inwindow_days']} sentiment-days, side balance {s1['side_balance']}, "
          f"mean index {s1['mean_value_inwindow']}. 5-bucket balance {s1['bucket_balance']}.",
          "The tradable period spans multiple regimes, so a Fear-vs-Greed contrast is supported "
          "in-window; class balance shows how much statistical support each regime has.",
          "Per-regime sample sizes are adequate but imbalanced → use tests robust to unequal n; "
          "Neutral is retained as its own group (D5), excluded only in strict binary tests.",
          "Merge (M9) joins sentiment onto trades within exactly this window.")

    block("V2", "Realized PnL distribution (closing trades)", f2,
          "What is the shape of realized PnL — symmetric or heavy-tailed?",
          "Log-count histogram of Closed PnL over PnL-bearing trades, median & mean marked",
          f"{s2['n_pnl_bearing']:,} PnL-bearing trades; median {s2['median']} vs mean {s2['mean']} "
          f"(mean ≫ median → right pull); skew {s2['skew']}, excess kurtosis {s2['kurtosis']}; "
          f"range [{s2['min']:,.0f}, {s2['max']:,.0f}]; win rate {s2['win_rate']}%.",
          "PnL is dominated by rare extreme outcomes — averages are misleading; report medians and "
          "tail risk, not just mean PnL.",
          "Heavy tails + high kurtosis ⇒ **non-parametric tests (Mann-Whitney / permutation) and "
          "effect sizes**, not t-tests on raw PnL; consider winsorized/median summaries. (D6, F2.9)",
          "Metrics (M10) define win-rate/PnL on this PnL-bearing subset; stats (M12) pick tests from this shape.")

    block("V3", "Trade size distribution — perp vs spot", f3,
          "How wide is the position-size range, and do spot and perp differ?",
          "Overlaid log10(Size USD) histograms for perpetual vs spot trades",
          f"Sizes span {s3['overall_min']:,} → {s3['overall_max']:,.0f} USD (many orders of magnitude); "
          f"median perp {s3['perp_median']:,.0f} vs spot {s3['spot_median']:,.0f}.",
          "Position sizing is highly heterogeneous; a few very large trades can dominate any "
          "size-weighted metric.",
          "Size is heavy-tailed → compare **medians / log-sizes**, not means; motivates size-based "
          "segmentation later.",
          "Metrics (M10) use median/relative sizing; segmentation (M11) may split by size tier.")

    block("V4", "Account activity concentration (Lorenz)", f4,
          "How concentrated is activity — do a few accounts dominate?",
          "Lorenz curve of trades per account with Gini",
          f"{s4['n_accounts']} accounts; Gini {s4['gini']}; top account = {s4['top1_share']}% of all "
          f"trades, top 5 = {s4['top5_share']}%.",
          "Market-level aggregates are driven by a handful of accounts — 'the market' ≈ a few whales; "
          "conclusions must be reported per-account, not just pooled.",
          "Pooling all trades violates independence (repeated-measures per account) → prefer "
          "**per-account paired tests** and cluster-aware analysis. (D9)",
          "Aggregation (M8) builds per-account daily tables; stats (M12) use per-account designs.")

    block("V5", "Long / Short / Spot baseline composition", f5,
          "What is the baseline directional mix before any sentiment conditioning?",
          "Bar chart of trade counts by Long / Short / Spot / Edge",
          f"Composition {s5['counts']}; perpetual long/short ratio = {s5['long_short_ratio']} "
          "(slight long tilt).",
          "Establishes the reference distribution: any Fear-vs-Greed directional shift must be judged "
          "against this baseline, not zero.",
          "Baseline proportions are the null for the later **chi-square** on sentiment × direction; "
          "spot/edge excluded from directional tests (T6/F2.10).",
          "Merge+metrics (M9–M10) compute regime-conditional long/short vs this baseline.")

    block("V6", "Trading activity over time", f6,
          "How does trading activity evolve — inactive periods, bursts, uneven sampling?",
          "Daily trade count with a 7-day moving average",
          f"{s6['active_days']}/{s6['span_days']} days active ({s6['coverage_pct']}% coverage); "
          f"mean {s6['mean_daily']:,.0f}/day; peak {s6['max_daily']:,} on {s6['max_daily_date']}; "
          f"longest zero-activity gap {s6['longest_zero_gap']} days. **Volume is heavily "
          f"back-loaded: only {s6['pct_2023']}% of trades occur in 2023, while {s6['pct_last6mo']}% "
          f"fall in the final 6 months (Nov-2024 → Apr-2025).**",
          "The effective dataset is really late-2024→2025, not the full 2-year span; any 'overall' "
          "conclusion is dominated by that recent, high-activity period.",
          "Severe temporal imbalance ⇒ a Fear-vs-Greed difference could be a proxy for *when* trading "
          "happened. **Mitigation: report the effective active window, and stratify / robustness-check "
          "on the high-activity sub-period** so regime effects aren't confounded with sampling. (feeds a "
          "merge-window decision in M9)",
          "Stats interpretation (M12) must confirm Fear/Greed differences aren't artifacts of activity timing; "
          "M9 decides whether to restrict/annotate the analysis window.")

    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
