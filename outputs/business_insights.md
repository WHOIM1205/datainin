# Business Insights & Strategy Recommendations
### Trader Behaviour vs Bitcoin Market Sentiment (Hyperliquid)

*Prepared from the merged, quality-controlled dataset (32 accounts, 211,224 trades, May-2023 → May-2025) and the seven pre-registered statistical tests in `statistical_analysis.md`. Every statement below traces to a research question (RQ1–RQ7) or a frozen data finding (E1–E6). Claims not supported by the evidence are not made.*

---

## Executive summary

Market sentiment (Fear vs Greed) has a **limited and mostly indirect** relationship with trader performance in this dataset. The apparent "traders earn more on Greed days" pattern **does not survive controlling for the underlying Bitcoin price move** (RQ1 vs RQ7): it is largely a market-direction artifact, not an independent sentiment edge. The clearest behavioural signal is **position sizing** — traders tend to take **larger positions on Greed days** (RQ4, large effect) — but this result is **under-powered** (20 qualifying traders) and should be treated as *likely*, not confirmed. Sentiment's association with trade *direction* is **statistically real but small** (RQ6), and there is **no detectable difference** in per-trader PnL or trading frequency between regimes (RQ2, RQ5). The practical conclusion is that sentiment is more useful for **risk monitoring** (position-size behaviour) than for **alpha generation**.

---

## How to read the confidence tiers

| Tier | Meaning |
|------|---------|
| **Confirmed** | Statistically significant after FDR correction **and** the direction is consistent with the effect size; robust to the design. |
| **Likely** | A non-trivial effect size, but not significant after correction (under-powered) — directional, not proven. |
| **Exploratory** | Weak/small effect, not significant; suggestive only. |
| **No evidence** | Effect size small and CI spans zero; the data do not support a difference. |

---

## Findings

### Confirmed

**C1 — The Greed-day PnL "advantage" is a market-direction artifact, not a sentiment edge.**
- **Evidence:** Unconditionally, the typical account's daily PnL is modestly higher on Greed days (RQ1: median Greed−Fear ≈ **+179 USD/day**, CI [50, 308]; Cliff's δ 0.13 = *negligible*; FDR p=0.099 — not significant). After controlling for the BTC market move (return + volatility), the Greed effect collapses to **+65 USD/day with CI [−349, 480]** spanning zero (RQ7, FDR p=0.76).
- **Interpretation:** Fear/Greed is *derived from* price action; Greed days coincide with rising prices, and directional traders profit from the move — not from the sentiment label itself.
- **Business implication:** Sentiment alone is **not** a reliable performance or timing signal. Any backtest that appears to profit from "trade the Greed regime" is likely capturing beta to Bitcoin, not a sentiment effect.

**C2 — Sentiment is associated with trade direction, but the association is weak.**
- **Evidence:** RQ6 — sentiment × (Long/Short) on 139,786 perpetual trades is statistically significant (FDR p≈0) but **Cramér's V = 0.19 (*small*)**.
- **Interpretation:** The huge trade count makes even a faint association significant; the *magnitude* shows sentiment shifts the long/short mix only slightly from the baseline tilt (E5: ~57% long).
- **Business implication:** Do not expect sentiment to strongly predict whether the crowd is long or short; it nudges, it does not drive.

### Likely

**L1 — Traders increase position size on Greed days ("risk-on" sizing).**
- **Evidence:** RQ4 (per-trader paired) — median perp trade size is **+107 USD higher on Greed vs Fear days** (CI [6, 508]); matched-pairs rank-biserial **0.57 = *large***; but FDR p=0.084 (**not** significant) and only **20 traders** qualified (≥5 days per regime). See figure SF2.
- **Interpretation:** The effect is sizeable and consistent in direction (most traders size up in Greed), but the small qualifying sample means it is under-powered — directional, not conclusive.
- **Business implication:** Greed regimes plausibly coincide with elevated risk-taking (bigger positions). This is a **risk-management** signal, not a profit signal — larger size in a euphoric regime is exactly when tail losses are most damaging.

### Exploratory

**E-1 — Win rate may be marginally higher on Greed days.** RQ3: rank-biserial 0.30 (*small*), median Greed−Fear +1.6pp, CI [−2.4pp, +5.8pp], FDR p=0.34 — suggestive, not significant.
**E-2 — Market-level daily PnL is marginally higher on Greed days.** RQ1 (see C1) — negligible effect, and explained away by C1's market control.

### No evidence of an effect

**N-1 — No detectable difference in per-trader daily PnL between regimes** (RQ2: small effect, CI [−248, +83] spans zero, FDR p=0.51).
**N-2 — No detectable difference in trading frequency between regimes** (RQ5: small effect, CI spans zero, FDR p=0.56).

---

## Strategy recommendations

Two rules of thumb follow from the evidence. Each is stated with its support, expected benefit, limitations, and a confidence level. Neither is offered as a guaranteed edge.

### R1 — Apply regime-aware position-size discipline during Greed
- **Recommendation:** Treat Greed regimes as elevated-risk-taking periods: monitor, and where appropriate cap, position-size inflation — prioritising the accounts that up-size most (the Large-size / High-frequency segments from `segmentation_report.md`).
- **Supporting evidence:** RQ4 (larger positions on Greed days, large effect; SF2); consistent with C1 (the extra Greed PnL is beta, so bigger size mostly buys more market exposure, not more skill).
- **Expected benefit:** Reduced tail-loss exposure when the crowd is most risk-on — the regime where oversized positions are most dangerous.
- **Limitations:** Under-powered (20 traders, FDR p=0.084); **no leverage/margin data exists** (D3), so "size" is notional, not leverage; sizing has **not** been shown to harm performance here — this is a prudential, not a proven-profit, rule.
- **Confidence:** **Low–Medium.**

### R2 — Do not use Fear/Greed as a standalone performance or timing signal
- **Recommendation:** Exclude raw sentiment as a primary driver of entry/exit or performance expectations; if used at all, use it only *conditioned on* a price/volatility model, never on its own.
- **Supporting evidence:** RQ1 + RQ7 (the PnL gap is a market-direction artifact; C1), RQ2 (no per-trader PnL difference), RQ6 (only a small directional association).
- **Expected benefit:** Avoids deploying a spurious signal and the false confidence of a beta-driven backtest; redirects modelling effort to price/volatility features that actually carry the effect.
- **Limitations:** The market control uses an **in-sample BTC proxy reconstructed from observed BTC-perpetual executions, covering ~60% of active days** (D11) — a true external benchmark could sharpen the estimate; conclusions are at the daily grain.
- **Confidence:** **Medium–High** (a well-supported null after control, consistent across three RQs).

---

## What this analysis cannot conclude

- **Causality.** All results are associational. We cannot say sentiment *causes* behaviour; sentiment, price, and behaviour move together.
- **Leverage effects.** The dataset has **no leverage or account-equity field** (D3/F2.4). "Position size" is notional USD, not leverage; risk-taking conclusions are bounded by this.
- **Whether sizing-up hurts or helps.** RQ4 shows *that* traders size up in Greed, not whether it improves or damages their returns.
- **Generalisation.** Only **32 accounts**, and activity is **heavily concentrated** (top-5 accounts = 50% of trades, Gini 0.57 — E3) and **temporally concentrated** (92% of trades in the final 6 months — E2). Findings describe *these* traders in *this* window, not Hyperliquid or crypto traders broadly.
- **Fear-regime precision.** Only 103 Fear market-days vs 309 Greed (E4); Fear-day estimates are the least powered.
- **Sub-period stability.** We did not confirm the results hold identically inside the dense final-6-month sub-window vs the full span (flagged for robustness, D10).
- **Intraday / holding-period behaviour.** The analysis is at the daily grain; entry-to-exit holding times were not reconstructable from the available fields.

---

## Future work (requires additional data)

- **Account equity / margin data** → compute *true leverage* and test the risk-taking hypothesis directly (currently impossible, D3).
- **An external BTC price benchmark** (exchange OHLC) → replace the ~60%-coverage in-sample proxy (D11) and strengthen the confounder control (RQ7).
- **More accounts and a longer *dense* history** → raise power for the paired tests (RQ2–RQ5), especially the under-powered position-size result (RQ4) and Fear-day estimates.
- **Transaction-level entry/exit linkage** → holding-period and round-trip PnL, enabling drawdown-by-regime and holding-behaviour analyses not possible here.
- **Per-symbol and volatility-regime conditioning** → test whether the sentiment–behaviour link differs across assets and volatility states.
- **A pre-registered out-of-sample test** of R1 (does capping Greed-day size reduce realised tail loss?) on new data before any deployment.

---

*All figures referenced (SF1–SF3) are in `outputs/figures/`; underlying evidence in `outputs/statistical_analysis.md`; data-quality and methodology trail in `ASSUMPTIONS_LOG.md`.*
