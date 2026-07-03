# Segmentation Report — Module 11

_Trader segments defined on 32 accounts. Priority: rule-based > quantile-based > clustering. Every segment is interpretable, reproducible (deterministic — no random seeds), and stable. No hypothesis testing and no recommendations here — definitions only._

**Population:** 32 accounts. **Low-activity caveat:** 0 account(s) have <10 active days (metrics noisier — flagged `is_low_activity`, not dropped).

## Adopted segments (rule / quantile)
| Segment | Method | Metric | Rationale | Balance | Strengths | Weaknesses |
|---|---|---|---|---|---|---|
| `frequency_segment` | quantile (median split) | `avg_trades_per_active_day` | How intensively an account trades on active days. | {'Infrequent': 16, 'Frequent': 16} | balanced by construction; deterministic; interpretable | cut point is relative (sample-dependent); ignores gap size |
| `consistency_segment` | quantile (median split) | `pct_profitable_days` | How often an account's days end net-positive. | {'Inconsistent': 16, 'Consistent': 16} | balanced by construction; deterministic; interpretable | cut point is relative (sample-dependent); ignores gap size |
| `size_segment` | quantile (median split) | `median_trade_size_usd` | Typical position size. | {'Small': 16, 'Large': 16} | balanced by construction; deterministic; interpretable | cut point is relative (sample-dependent); ignores gap size |
| `performance_segment` | quantile (tertiles) | `roi_on_notional` | Capital efficiency (scale-free return on notional). | {'Bottom': 11, 'Mid': 10, 'Top': 11} | balanced thirds; separates high/low; deterministic | small per-group n (~10-11); relative cut |
| `directional_segment` | rule-based (long_ratio >0.55 / <0.45) | `long_ratio` | Directional style: net long, balanced, or net short. | {'Balanced': 2, 'Long-biased': 16, 'Short-biased': 14} | fixed business thresholds; directly interpretable | thresholds are judgement; groups can be imbalanced |

## Sample sizes & balance (for downstream power awareness)
Median/tertile splits give balanced groups (16/16 or ~11/10/11); the rule-based directional split reflects the real long tilt (E5) and is intentionally allowed to be imbalanced. With only 32 accounts, per-segment n is small — a constraint for later per-account tests.

## Clustering evaluation (why it was NOT adopted)
KMeans on standardized behaviour/performance metrics (roi, intensity, consistency, size, long-ratio):
- Silhouette by k: {2: 0.218, 3: 0.219, 4: 0.25, 5: 0.256} → best k=5 (silhouette **0.256**).
- Seed stability (mean ARI over 10 seeds) at best k: **0.83** (reproducible convergence only — NOT evidence of meaningful structure, given the weak silhouette).
- Overlap with the quantile performance segment (ARI): **0.06**.

**Decision: clustering NOT adopted.** Justification:
1. **n = 32 is too small** for stable clusters; KMeans (Euclidean, standardized) was chosen as the simplest baseline and even it is fragile here.
2. **Weak separation** — best silhouette 0.256 indicates no clean cluster structure (values ≲0.5 are weak/overlapping).
3. **Not clearly better than quantiles** — clusters largely recapitulate the interpretable axes without adding a distinct, nameable archetype, and lose the direct business meaning of rule/quantile labels.
Per the rule 'if clustering is not clearly better, do not use it', the quantile/rule segments are the project's segmentation. Clustering remains available as an exploratory cross-check only.
