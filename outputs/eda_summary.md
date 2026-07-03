# EDA Summary — Module 4

_Six curated figures on the cleaned, un-merged data. Each answers a question and feeds the statistical analysis (Modules 10–12). Numbers are computed by `scripts/run_eda.py`._

**Analysis window (trades):** 2023-04-30 → 2025-05-01

> Not charted (would be decorative): missing-value & duplicate plots (0 of each — F1.3/F2.3); leverage distribution (excluded, D3/F2.4); trade-level correlation heatmap (mechanical — deferred to post-metrics viz, M13).

## V1. Fear & Greed over time (trade window shaded)

- **Question:** Which sentiment regimes occur, and how much of each falls inside the trade window?
- **Visualization:** Index time series with the 2023-05→2025-05 trade window shaded and regime thresholds marked — `figures/v1_sentiment_timeline_with_trade_window.png` · `figures/v1_sentiment_timeline_with_trade_window.svg`
- **Key observation:** In-window: 732 sentiment-days, side balance {'Greed': 411, 'Neutral': 177, 'Fear': 144}, mean index 58.2. 5-bucket balance {'Greed': 295, 'Neutral': 177, 'Fear': 129, 'Extreme Greed': 116, 'Extreme Fear': 15}.
- **Business implication:** The tradable period spans multiple regimes, so a Fear-vs-Greed contrast is supported in-window; class balance shows how much statistical support each regime has.
- **Statistical implication:** Per-regime sample sizes are adequate but imbalanced → use tests robust to unequal n; Neutral is retained as its own group (D5), excluded only in strict binary tests.
- **Next-module dependency:** Merge (M9) joins sentiment onto trades within exactly this window.

## V2. Realized PnL distribution (closing trades)

- **Question:** What is the shape of realized PnL — symmetric or heavy-tailed?
- **Visualization:** Log-count histogram of Closed PnL over PnL-bearing trades, median & mean marked — `figures/v2_realized_pnl_distribution.png` · `figures/v2_realized_pnl_distribution.svg`
- **Key observation:** 104,408 PnL-bearing trades; median 6.06 vs mean 98.62 (mean ≫ median → right pull); skew 21.6, excess kurtosis 3163.5; range [-117,990, 135,329]; win rate 83.2%.
- **Business implication:** PnL is dominated by rare extreme outcomes — averages are misleading; report medians and tail risk, not just mean PnL.
- **Statistical implication:** Heavy tails + high kurtosis ⇒ **non-parametric tests (Mann-Whitney / permutation) and effect sizes**, not t-tests on raw PnL; consider winsorized/median summaries. (D6, F2.9)
- **Next-module dependency:** Metrics (M10) define win-rate/PnL on this PnL-bearing subset; stats (M12) pick tests from this shape.

## V3. Trade size distribution — perp vs spot

- **Question:** How wide is the position-size range, and do spot and perp differ?
- **Visualization:** Overlaid log10(Size USD) histograms for perpetual vs spot trades — `figures/v3_trade_size_distribution_perp_vs_spot.png` · `figures/v3_trade_size_distribution_perp_vs_spot.svg`
- **Key observation:** Sizes span 0.01 → 3,921,431 USD (many orders of magnitude); median perp 649 vs spot 393.
- **Business implication:** Position sizing is highly heterogeneous; a few very large trades can dominate any size-weighted metric.
- **Statistical implication:** Size is heavy-tailed → compare **medians / log-sizes**, not means; motivates size-based segmentation later.
- **Next-module dependency:** Metrics (M10) use median/relative sizing; segmentation (M11) may split by size tier.

## V4. Account activity concentration (Lorenz)

- **Question:** How concentrated is activity — do a few accounts dominate?
- **Visualization:** Lorenz curve of trades per account with Gini — `figures/v4_account_activity_concentration_lorenz.png` · `figures/v4_account_activity_concentration_lorenz.svg`
- **Key observation:** 32 accounts; Gini 0.57; top account = 19.0% of all trades, top 5 = 50.5%.
- **Business implication:** Market-level aggregates are driven by a handful of accounts — 'the market' ≈ a few whales; conclusions must be reported per-account, not just pooled.
- **Statistical implication:** Pooling all trades violates independence (repeated-measures per account) → prefer **per-account paired tests** and cluster-aware analysis. (D9)
- **Next-module dependency:** Aggregation (M8) builds per-account daily tables; stats (M12) use per-account designs.

## V5. Long / Short / Spot baseline composition

- **Question:** What is the baseline directional mix before any sentiment conditioning?
- **Visualization:** Bar chart of trade counts by Long / Short / Spot / Edge — `figures/v5_long_short_spot_baseline.png` · `figures/v5_long_short_spot_baseline.svg`
- **Key observation:** Composition {'Long': 98573, 'Short': 75754, 'Spot': 36760, 'Edge': 137}; perpetual long/short ratio = 1.3 (slight long tilt).
- **Business implication:** Establishes the reference distribution: any Fear-vs-Greed directional shift must be judged against this baseline, not zero.
- **Statistical implication:** Baseline proportions are the null for the later **chi-square** on sentiment × direction; spot/edge excluded from directional tests (T6/F2.10).
- **Next-module dependency:** Merge+metrics (M9–M10) compute regime-conditional long/short vs this baseline.

## V6. Trading activity over time

- **Question:** How does trading activity evolve — inactive periods, bursts, uneven sampling?
- **Visualization:** Daily trade count with a 7-day moving average — `figures/v6_trading_activity_over_time.png` · `figures/v6_trading_activity_over_time.svg`
- **Key observation:** 476/733 days active (64.9% coverage); mean 288/day; peak 7,454 on 2025-02-24; longest zero-activity gap 217 days. **Volume is heavily back-loaded: only 0.2% of trades occur in 2023, while 92.2% fall in the final 6 months (Nov-2024 → Apr-2025).**
- **Business implication:** The effective dataset is really late-2024→2025, not the full 2-year span; any 'overall' conclusion is dominated by that recent, high-activity period.
- **Statistical implication:** Severe temporal imbalance ⇒ a Fear-vs-Greed difference could be a proxy for *when* trading happened. **Mitigation: report the effective active window, and stratify / robustness-check on the high-activity sub-period** so regime effects aren't confounded with sampling. (feeds a merge-window decision in M9)
- **Next-module dependency:** Stats interpretation (M12) must confirm Fear/Greed differences aren't artifacts of activity timing; M9 decides whether to restrict/annotate the analysis window.
