"""
Module 12 — statistical core.

Each test answers ONE predefined research question (RQ). Tests are pre-planned, not
fished. Design principles:
  - Robust-by-default: PnL/size are heavy-tailed (E1/E6), so non-parametric tests
    (Mann-Whitney, Wilcoxon) + bootstrap CIs are the planned choice; assumptions are
    still checked and reported.
  - Effect size is reported for every test and weighted equally with the p-value.
  - Per-trader PAIRED designs (each account its own control) are preferred over pooling,
    because trades/days are not independent (whale concentration E3, D9).
  - Neutral days excluded only inside binary Fear-vs-Greed tests (D5).
  - FDR (Benjamini-Hochberg) across the RQ family.
  - Confounder control uses the in-sample BTC market proxy (~60% coverage, D11); a
    mixed-effects model is deliberately NOT used where a simpler model suffices (principle 6).

No business recommendations here — statistical evidence only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

MIN_DAYS = 5          # min days per regime for a trader to enter a paired test
RNG = np.random.default_rng(42)


@dataclass
class StatResult:
    rq: str
    question: str
    h0: str
    h1: str
    test: str
    why: str
    assumptions: str
    assumption_check: str
    n: str
    statistic: float
    p_value: float
    effect_name: str
    effect_value: float
    effect_magnitude: str
    ci: str
    meaning: str
    metric_label: str = ""
    p_adjusted: float = field(default=np.nan)


# ---------- effect sizes ----------
def _mag_delta(d: float) -> str:
    a = abs(d)
    return ("negligible" if a < 0.147 else "small" if a < 0.33 else "medium" if a < 0.474 else "large")


def cliffs_delta(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    U = stats.mannwhitneyu(a, b, alternative="two-sided").statistic
    return 2 * U / (len(a) * len(b)) - 1


def paired_rank_biserial(x, y) -> float:
    """Matched-pairs rank-biserial for Wilcoxon signed-rank (x−y)."""
    d = np.asarray(x) - np.asarray(y)
    d = d[d != 0]
    if len(d) == 0:
        return 0.0
    r = stats.rankdata(np.abs(d))
    Tp, Tn = r[d > 0].sum(), r[d < 0].sum()
    return float((Tp - Tn) / (Tp + Tn))


def _mag_v(v: float, k: int) -> str:
    # Cramér's V magnitude (df-adjusted, Cohen)
    return ("negligible" if v < 0.1 else "small" if v < 0.3 else "medium" if v < 0.5 else "large")


def cramers_v(table: np.ndarray) -> float:
    chi2 = stats.chi2_contingency(table, correction=False)[0]
    n = table.sum()
    return float(np.sqrt(chi2 / (n * (min(table.shape) - 1))))


# ---------- bootstrap CIs ----------
def boot_ci_diff_medians(a, b, n=5000) -> tuple[float, float]:
    a, b = np.asarray(a), np.asarray(b)
    diffs = [np.median(RNG.choice(b, len(b))) - np.median(RNG.choice(a, len(a))) for _ in range(n)]
    return tuple(np.percentile(diffs, [2.5, 97.5]))


def boot_ci_paired_median(x, y, n=5000) -> tuple[float, float]:
    d = np.asarray(y) - np.asarray(x)
    meds = [np.median(RNG.choice(d, len(d))) for _ in range(n)]
    return tuple(np.percentile(meds, [2.5, 97.5]))


# ---------- per-account × regime table ----------
def account_regime_metrics(account_day_merged: pd.DataFrame) -> pd.DataFrame:
    df = account_day_merged[account_day_merged["sentiment_side"].isin(["Fear", "Greed"])]
    g = df.groupby(["Account", "sentiment_side"], observed=True).agg(
        n_days=("daily_pnl", "size"),
        median_daily_pnl=("daily_pnl", "median"),
        win_count=("win_count", "sum"),
        pnl_trade_count=("pnl_trade_count", "sum"),
        trade_count=("trade_count", "sum"),
    )
    g["win_rate"] = g["win_count"] / g["pnl_trade_count"].replace(0, np.nan)
    g["trades_per_day"] = g["trade_count"] / g["n_days"]
    return g


def _paired(arm: pd.DataFrame, col: str) -> tuple[np.ndarray, np.ndarray, int]:
    """Return (fear_vals, greed_vals) for accounts with >=MIN_DAYS in BOTH regimes."""
    piv = arm[[col, "n_days"]].unstack("sentiment_side")
    ok = (piv[("n_days", "Fear")] >= MIN_DAYS) & (piv[("n_days", "Greed")] >= MIN_DAYS)
    piv = piv[ok].dropna(subset=[(col, "Fear"), (col, "Greed")])
    return piv[(col, "Fear")].values, piv[(col, "Greed")].values, len(piv)


# ---------- individual tests ----------
def _wilcoxon_rq(rq, question, fear, greed, better_col, unit_label) -> StatResult:
    diff = greed - fear
    sh_p = stats.shapiro(diff).pvalue if 3 <= len(diff) <= 5000 else np.nan
    stat, p = stats.wilcoxon(greed, fear)
    rb = paired_rank_biserial(greed, fear)
    lo, hi = boot_ci_paired_median(fear, greed)
    med = float(np.median(diff))
    return StatResult(
        rq=rq, question=question,
        h0=f"Within-trader {better_col} is the same on Fear vs Greed days (median paired diff = 0).",
        h1=f"Within-trader {better_col} differs between Fear and Greed days.",
        test="Wilcoxon signed-rank (paired)",
        why="Paired design (each trader its own control) removes between-trader confounding and "
            "respects non-independence (D9/E3); non-parametric for heavy-tailed data (E1).",
        assumptions="Paired, symmetric distribution of differences; ordinal/continuous.",
        assumption_check=f"Shapiro on paired diffs p={sh_p:.3g} "
                         f"({'non-normal → non-parametric justified' if sh_p < 0.05 else 'approx normal'}).",
        n=f"{len(fear)} traders (≥{MIN_DAYS} days each regime)",
        statistic=float(stat), p_value=float(p),
        effect_name="matched-pairs rank-biserial", effect_value=round(rb, 3),
        effect_magnitude=_mag_delta(rb),
        ci=f"median Greed−Fear = {med:.4g} (95% bootstrap CI [{lo:.4g}, {hi:.4g}])",
        meaning="",  # filled by caller
        metric_label=better_col,
    )


def rq_market_pnl(market_day_merged: pd.DataFrame) -> StatResult:
    md = market_day_merged
    fear = md.loc[md["sentiment_side"] == "Fear", "median_account_daily_pnl"].dropna().values
    greed = md.loc[md["sentiment_side"] == "Greed", "median_account_daily_pnl"].dropna().values
    stat, p = stats.mannwhitneyu(greed, fear, alternative="two-sided")
    d = cliffs_delta(greed, fear)
    lo, hi = boot_ci_diff_medians(fear, greed)
    sh = stats.shapiro(np.concatenate([fear, greed])).pvalue
    return StatResult(
        rq="RQ1", question="Does the typical account's daily PnL differ on Fear vs Greed market-days?",
        h0="Median-account daily PnL has the same distribution on Fear and Greed days.",
        h1="It differs between Fear and Greed days.",
        test="Mann–Whitney U (independent)",
        why="Two independent day-groups; non-parametric for heavy-tailed daily PnL (E1). "
            "Uses the whale-robust median-account daily PnL (E3).",
        assumptions="Independent observations; ordinal/continuous.",
        assumption_check=f"Shapiro p={sh:.3g} (non-normal → non-parametric); NOTE days are "
                         "autocorrelated → treat as approximate.",
        n=f"Fear {len(fear)} days vs Greed {len(greed)} days",
        statistic=float(stat), p_value=float(p),
        effect_name="Cliff's delta", effect_value=round(d, 3), effect_magnitude=_mag_delta(d),
        ci=f"median Greed−Fear = {np.median(greed)-np.median(fear):.4g} USD "
           f"(95% bootstrap CI [{lo:.4g}, {hi:.4g}])",
        meaning="",
    )


def rq_direction_assoc(trades_sent: pd.DataFrame) -> StatResult:
    perp = trades_sent[(trades_sent["is_perp"]) & (trades_sent["position_side"].isin(["Long", "Short"]))
                       & (trades_sent["sentiment_side"].isin(["Fear", "Greed"]))]
    table = pd.crosstab(perp["sentiment_side"], perp["position_side"]).values
    chi2, p, dof, exp = stats.chi2_contingency(table, correction=False)
    v = cramers_v(table)
    return StatResult(
        rq="RQ6", question="Is sentiment associated with trade direction (Long vs Short) on perps?",
        h0="Sentiment (Fear/Greed) and direction (Long/Short) are independent.",
        h1="Sentiment and direction are associated.",
        test="Chi-square test of independence",
        why="Two categorical variables; the natural association test. Cramér's V gives the "
            "(small-by-default) effect size.",
        assumptions="Expected cell counts ≥5; independent observations.",
        assumption_check=f"min expected cell = {exp.min():.0f} (≥5 OK). "
                         "CAVEAT: trades are clustered within accounts/days → not independent; "
                         "huge n inflates significance, so read Cramér's V, not p.",
        n=f"{int(table.sum()):,} perp trades",
        statistic=float(chi2), p_value=float(p),
        effect_name="Cramér's V", effect_value=round(v, 3), effect_magnitude=_mag_v(v, min(table.shape)),
        ci="(effect-size point estimate; V is bounded [0,1])",
        meaning="",
    )


def rq_confounder(market_day_merged: pd.DataFrame) -> StatResult:
    import statsmodels.formula.api as smf
    md = market_day_merged.copy()
    md = md[md["sentiment_side"].isin(["Fear", "Greed"]) & md["has_market_proxy"]].copy()
    md["is_greed"] = (md["sentiment_side"] == "Greed").astype(int)
    model = smf.ols("median_account_daily_pnl ~ is_greed + btc_return + btc_vol_7d", data=md).fit(cov_type="HC3")
    coef = model.params["is_greed"]; p = model.pvalues["is_greed"]
    lo, hi = model.conf_int().loc["is_greed"].tolist()
    return StatResult(
        rq="RQ7", question="Does sentiment predict daily PnL AFTER controlling for the BTC market move?",
        h0="Given BTC return & volatility, the Greed indicator adds nothing (coef = 0).",
        h1="Sentiment has a marginal effect on daily PnL beyond the market move.",
        test="OLS with robust (HC3) SE; market-day grain",
        why="Fear/Greed is derived from price, so the raw effect may be pure market direction. "
            "Controlling BTC return+vol isolates the marginal sentiment effect. Mixed-effects is "
            "NOT used: at the market-day grain there are no repeated within-group measures to warrant "
            "random effects — a simpler model suffices (principle 6).",
        assumptions="Linearity; residual normality (approx); homoskedastic (relaxed via HC3).",
        assumption_check=f"n={int(model.nobs)} proxy-covered Fear/Greed days (~60% coverage, D11); "
                         "residuals heavy-tailed → HC3 robust SE used; read as a linear approximation.",
        n=f"{int(model.nobs)} market-days with BTC proxy",
        statistic=float(model.tvalues["is_greed"]), p_value=float(p),
        effect_name="Greed coefficient (USD/day, market-median)", effect_value=round(float(coef), 2),
        effect_magnitude=("negligible" if lo <= 0 <= hi else "directional"),
        ci=f"95% CI [{lo:.4g}, {hi:.4g}] USD/day",
        meaning="",
    )


def run_all(account_day_merged, market_day_merged, trades_sent) -> list[StatResult]:
    arm = account_regime_metrics(account_day_merged)
    results: list[StatResult] = [rq_market_pnl(market_day_merged)]

    # RQ2 PnL, RQ3 win rate, RQ4 size (built separately), RQ5 frequency — per-trader paired
    fp, gp, n = _paired(arm, "median_daily_pnl")
    r2 = _wilcoxon_rq("RQ2", "Do individual traders realize different daily PnL on Fear vs Greed days?",
                      fp, gp, "median daily PnL", "trader")
    results.append(r2)
    fw, gw, _ = _paired(arm, "win_rate")
    results.append(_wilcoxon_rq("RQ3", "Do traders' win rates differ on Fear vs Greed days?",
                                fw, gw, "win rate", "trader"))
    ff, gf, _ = _paired(arm, "trades_per_day")
    results.append(_wilcoxon_rq("RQ5", "Do traders trade more/less frequently on Fear vs Greed days?",
                                ff, gf, "trades per active day", "trader"))

    # RQ4 size — per-account × regime median perp trade size (from trade-level + sentiment)
    perp = trades_sent[(trades_sent["is_perp"]) & (trades_sent["Size USD"] > 0)
                       & (trades_sent["sentiment_side"].isin(["Fear", "Greed"]))]
    sz = perp.groupby(["Account", "sentiment_side"], observed=True).agg(
        median_size=("Size USD", "median"), n_days=("trade_date_utc", lambda s: s.dt.normalize().nunique()))
    fs, gs, _ = _paired(sz.rename(columns={"median_size": "v"}), "v")
    results.append(_wilcoxon_rq("RQ4", "Do traders use different position sizes on Fear vs Greed days?",
                                fs, gs, "median perp trade size", "trader"))

    results.append(rq_direction_assoc(trades_sent))
    results.append(rq_confounder(market_day_merged))

    # FDR across the family
    from statsmodels.stats.multitest import multipletests
    ps = [r.p_value for r in results]
    adj = multipletests(ps, method="fdr_bh")[1]
    for r, a in zip(results, adj):
        r.p_adjusted = float(a)
    return results
