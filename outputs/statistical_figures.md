# Statistical Figures — Module 13

_Each figure communicates a Module-12 statistical result (effect size, CI, paired structure, or regression coefficient) — not EDA. Every figure references its research question._

## SF1 · Effect-size forest — `figures/sf1_effect_size_forest.png`
- **Research question(s):** RQ1–RQ6 (overview).
- **Statistical result referenced:** Cliff's δ (RQ1), matched-pairs rank-biserial (RQ2–RQ5), Cramér's V (RQ6), with 95% bootstrap CIs and FDR significance.
- **Interpretation:** All performance/behaviour effects sit in the negligible–small band except RQ4 (position size, large). RQ6 is significant but small.
- **Key takeaway:** Sentiment's measurable footprint on traders is mostly small; the one sizeable effect is **position sizing**, and even it has a wide CI (few traders qualify).

## SF2 · RQ4 paired position size — `figures/sf2_rq4_position_size_dumbbell.png`
- **Research question:** RQ4 — do traders size differently on Fear vs Greed days?
- **Statistical result referenced:** Wilcoxon signed-rank, rank-biserial 0.57 (large), median Greed−Fear +107 USD (95% CI [6, 508]); FDR p=0.084.
- **Interpretation:** Most traders' dots move right from Fear (red) to Greed (green) — position sizes are systematically larger on Greed days.
- **Key takeaway:** A consistent **risk-on sizing** pattern in Greed; large but under-powered (n=20 qualifying traders), so directional-but-not-yet-conclusive.

## SF3 · RQ1→RQ7 confounder — `figures/sf3_rq7_confounder_coefficient.png`
- **Research question:** RQ1 (raw PnL gap) vs RQ7 (gap after controlling the BTC market move).
- **Statistical result referenced:** raw median gap +178 USD/day (CI excludes 0) vs OLS Greed coefficient +65 USD/day (95% CI [-350, 480], crosses 0).
- **Interpretation:** The apparent Greed-day PnL advantage shrinks toward zero and its CI widens across zero once BTC return & volatility are controlled.
- **Key takeaway:** The Fear/Greed PnL gap is **largely a market-direction artifact**, not an independent sentiment edge (reminder: BTC context is an in-sample proxy, ~60% coverage).
