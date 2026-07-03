# Statistical Analysis — Module 12

_Seven predefined research questions, one test each (not fished). Robust-by-default (non-parametric + bootstrap) given heavy-tailed data (E1/E6); per-trader paired designs respect non-independence (E3/D9). Effect size is weighted equally with the p-value; p-values are FDR-adjusted (Benjamini–Hochberg). Neutral days excluded only in binary tests (D5). The BTC market context is an IN-SAMPLE PROXY (~60% coverage, D11). No business recommendations — evidence only._

## Summary
| RQ | Test | p (raw) | p (FDR) | Sig? | Effect | Magnitude |
|---|---|---|---|---|---|---|
| RQ1 | Mann–Whitney U | 0.0423 | 0.0987 | — | Cliff's delta 0.133 | negligible |
| RQ2 | Wilcoxon signed-rank | 0.361 | 0.505 | — | matched-pairs rank-biserial -0.213 | small |
| RQ3 | Wilcoxon signed-rank | 0.192 | 0.336 | — | matched-pairs rank-biserial 0.298 | small |
| RQ5 | Wilcoxon signed-rank | 0.481 | 0.561 | — | matched-pairs rank-biserial -0.154 | small |
| RQ4 | Wilcoxon signed-rank | 0.024 | 0.0838 | — | matched-pairs rank-biserial 0.571 | large |
| RQ6 | Chi-square test of independence | 0 | 0 | ✅ | Cramér's V 0.191 | small |
| RQ7 | OLS with robust | 0.757 | 0.757 | — | Greed coefficient (USD/day, market-median) 65.41 | negligible |

> **Statistical vs practical significance.** ✅ marks FDR-significant results only. A ✅ with a *negligible/small* effect is statistically detectable but of little practical importance (often driven by large n); a large effect that is not ✅ is under-powered, not absent. Both columns must be read together.

## RQ1 — Does the typical account's daily PnL differ on Fear vs Greed market-days?
- **H0:** Median-account daily PnL has the same distribution on Fear and Greed days.
- **H1:** It differs between Fear and Greed days.
- **Test:** Mann–Whitney U (independent)
- **Why this test:** Two independent day-groups; non-parametric for heavy-tailed daily PnL (E1). Uses the whale-robust median-account daily PnL (E3).
- **Assumptions:** Independent observations; ordinal/continuous.
- **Assumption check:** Shapiro p=3.46e-33 (non-normal → non-parametric); NOTE days are autocorrelated → treat as approximate.
- **Sample size:** Fear 103 days vs Greed 309 days
- **Statistic / p-value:** 1.803e+04 / p=0.0423 → **FDR-adjusted p=0.0987** (not significant at α=0.05)
- **Effect size:** Cliff's delta = **0.133** (negligible)
- **Confidence interval:** median Greed−Fear = 178.5 USD (95% bootstrap CI [50.23, 308.1])
- **What this means for trader behaviour:** On Greed vs Fear days, traders' **** tends to be **higher**; the effect is **negligible** (Cliff's delta 0.133) and not statistically significant after FDR.

## RQ2 — Do individual traders realize different daily PnL on Fear vs Greed days?
- **H0:** Within-trader median daily PnL is the same on Fear vs Greed days (median paired diff = 0).
- **H1:** Within-trader median daily PnL differs between Fear and Greed days.
- **Test:** Wilcoxon signed-rank (paired)
- **Why this test:** Paired design (each trader its own control) removes between-trader confounding and respects non-independence (D9/E3); non-parametric for heavy-tailed data (E1).
- **Assumptions:** Paired, symmetric distribution of differences; ordinal/continuous.
- **Assumption check:** Shapiro on paired diffs p=1.58e-09 (non-normal → non-parametric justified).
- **Sample size:** 29 traders (≥5 days each regime)
- **Statistic / p-value:** 118 / p=0.361 → **FDR-adjusted p=0.505** (not significant at α=0.05)
- **Effect size:** matched-pairs rank-biserial = **-0.213** (small)
- **Confidence interval:** median Greed−Fear = 0 (95% bootstrap CI [-248.1, 82.7])
- **What this means for trader behaviour:** On Greed vs Fear days, traders' **median daily PnL** tends to be **lower**; the effect is **small** (matched-pairs rank-biserial -0.213) and not statistically significant after FDR — a non-trivial effect that is under-powered here, not proven absent.

## RQ3 — Do traders' win rates differ on Fear vs Greed days?
- **H0:** Within-trader win rate is the same on Fear vs Greed days (median paired diff = 0).
- **H1:** Within-trader win rate differs between Fear and Greed days.
- **Test:** Wilcoxon signed-rank (paired)
- **Why this test:** Paired design (each trader its own control) removes between-trader confounding and respects non-independence (D9/E3); non-parametric for heavy-tailed data (E1).
- **Assumptions:** Paired, symmetric distribution of differences; ordinal/continuous.
- **Assumption check:** Shapiro on paired diffs p=0.002 (non-normal → non-parametric justified).
- **Sample size:** 29 traders (≥5 days each regime)
- **Statistic / p-value:** 114 / p=0.192 → **FDR-adjusted p=0.336** (not significant at α=0.05)
- **Effect size:** matched-pairs rank-biserial = **0.298** (small)
- **Confidence interval:** median Greed−Fear = 0.01601 (95% bootstrap CI [-0.02397, 0.058])
- **What this means for trader behaviour:** On Greed vs Fear days, traders' **win rate** tends to be **higher**; the effect is **small** (matched-pairs rank-biserial 0.298) and not statistically significant after FDR — a non-trivial effect that is under-powered here, not proven absent.

## RQ5 — Do traders trade more/less frequently on Fear vs Greed days?
- **H0:** Within-trader trades per active day is the same on Fear vs Greed days (median paired diff = 0).
- **H1:** Within-trader trades per active day differs between Fear and Greed days.
- **Test:** Wilcoxon signed-rank (paired)
- **Why this test:** Paired design (each trader its own control) removes between-trader confounding and respects non-independence (D9/E3); non-parametric for heavy-tailed data (E1).
- **Assumptions:** Paired, symmetric distribution of differences; ordinal/continuous.
- **Assumption check:** Shapiro on paired diffs p=4.08e-07 (non-normal → non-parametric justified).
- **Sample size:** 29 traders (≥5 days each regime)
- **Statistic / p-value:** 184 / p=0.481 → **FDR-adjusted p=0.561** (not significant at α=0.05)
- **Effect size:** matched-pairs rank-biserial = **-0.154** (small)
- **Confidence interval:** median Greed−Fear = -3.016 (95% bootstrap CI [-16.08, 6.985])
- **What this means for trader behaviour:** On Greed vs Fear days, traders' **trades per active day** tends to be **lower**; the effect is **small** (matched-pairs rank-biserial -0.154) and not statistically significant after FDR — a non-trivial effect that is under-powered here, not proven absent.

## RQ4 — Do traders use different position sizes on Fear vs Greed days?
- **H0:** Within-trader median perp trade size is the same on Fear vs Greed days (median paired diff = 0).
- **H1:** Within-trader median perp trade size differs between Fear and Greed days.
- **Test:** Wilcoxon signed-rank (paired)
- **Why this test:** Paired design (each trader its own control) removes between-trader confounding and respects non-independence (D9/E3); non-parametric for heavy-tailed data (E1).
- **Assumptions:** Paired, symmetric distribution of differences; ordinal/continuous.
- **Assumption check:** Shapiro on paired diffs p=3.64e-05 (non-normal → non-parametric justified).
- **Sample size:** 20 traders (≥5 days each regime)
- **Statistic / p-value:** 45 / p=0.024 → **FDR-adjusted p=0.0838** (not significant at α=0.05)
- **Effect size:** matched-pairs rank-biserial = **0.571** (large)
- **Confidence interval:** median Greed−Fear = 107.4 (95% bootstrap CI [6.22, 507.8])
- **What this means for trader behaviour:** On Greed vs Fear days, traders' **median perp trade size** tends to be **higher**; the effect is **large** (matched-pairs rank-biserial 0.571) and not statistically significant after FDR — a non-trivial effect that is under-powered here, not proven absent.

## RQ6 — Is sentiment associated with trade direction (Long vs Short) on perps?
- **H0:** Sentiment (Fear/Greed) and direction (Long/Short) are independent.
- **H1:** Sentiment and direction are associated.
- **Test:** Chi-square test of independence
- **Why this test:** Two categorical variables; the natural association test. Cramér's V gives the (small-by-default) effect size.
- **Assumptions:** Expected cell counts ≥5; independent observations.
- **Assumption check:** min expected cell = 29676 (≥5 OK). CAVEAT: trades are clustered within accounts/days → not independent; huge n inflates significance, so read Cramér's V, not p.
- **Sample size:** 139,786 perp trades
- **Statistic / p-value:** 5092 / p=0 → **FDR-adjusted p=0** (significant at α=0.05)
- **Effect size:** Cramér's V = **0.191** (small)
- **Confidence interval:** (effect-size point estimate; V is bounded [0,1])
- **What this means for trader behaviour:** On perps, sentiment and direction are associated, but the association is **small** (Cramér's V 0.191) — sentiment barely shifts whether traders go long or short.

## RQ7 — Does sentiment predict daily PnL AFTER controlling for the BTC market move?
- **H0:** Given BTC return & volatility, the Greed indicator adds nothing (coef = 0).
- **H1:** Sentiment has a marginal effect on daily PnL beyond the market move.
- **Test:** OLS with robust (HC3) SE; market-day grain
- **Why this test:** Fear/Greed is derived from price, so the raw effect may be pure market direction. Controlling BTC return+vol isolates the marginal sentiment effect. Mixed-effects is NOT used: at the market-day grain there are no repeated within-group measures to warrant random effects — a simpler model suffices (principle 6).
- **Assumptions:** Linearity; residual normality (approx); homoskedastic (relaxed via HC3).
- **Assumption check:** n=229 proxy-covered Fear/Greed days (~60% coverage, D11); residuals heavy-tailed → HC3 robust SE used; read as a linear approximation.
- **Sample size:** 229 market-days with BTC proxy
- **Statistic / p-value:** 0.309 / p=0.757 → **FDR-adjusted p=0.757** (not significant at α=0.05)
- **Effect size:** Greed coefficient (USD/day, market-median) = **65.41** (negligible)
- **Confidence interval:** 95% CI [-349.5, 480.3] USD/day
- **What this means for trader behaviour:** After controlling for the BTC market move, the sentiment effect **does NOT survive** (Greed coef 65.41 USD/day, 95% CI [-349.5, 480.3] USD/day) — i.e. any raw Fear/Greed PnL gap is largely explained by market direction.
