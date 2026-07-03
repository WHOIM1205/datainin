# Merge Report — Module 9

_The statistically critical join of Fear & Greed sentiment (and the in-sample BTC market context proxy) onto the daily tables. Methodology was chosen on the evidence below BEFORE any hypothesis testing — the merge was never tuned toward significant results. No hypothesis tests, significance interpretation, or business conclusions are produced here._

## 1. Timezone strategy — UTC vs IST (D8)
| Strategy | Market-days | Matched | Unmatched | % matched | Unmatched dates |
|---|---|---|---|---|---|
| **UTC (chosen)** | 476 | 476 | 0 | 100.0% | — |
| IST (rejected) | 480 | 479 | 1 | 99.79% | ['2024-10-26'] |

- **tz sensitivity:** 25.24% of trades cross the IST/UTC day boundary, but only **6.57% are assigned a different sentiment regime** under UTC vs IST — i.e. 93%+ of trades are tz-robust.

**Decision: UTC.** Evidence, not preference:
1. The sentiment series is anchored to a **fixed UTC instant** (every timestamp is 05:30:00 UTC — established in M3/M5); the '11:00 IST' appearance is merely that same UTC instant expressed in IST, an artifact of the trade data's display tz — not evidence the index is IST-native.
2. The Bitcoin Fear & Greed index and crypto markets conventionally operate on **UTC days**.
3. **Completeness:** UTC matches 100% of market-days (0 unmatched); IST leaves 1 unmatched day (2024-10-26, a date absent from the sentiment series).
**Why IST was rejected:** no evidence the index is IST-native; IST bucketing relies on the exchange's *display* timezone (which describes trade display, not the sentiment's native day) and introduces an unmatched day. Residual uncertainty (6.57% tz-sensitive trades) is small and can be robustness-checked under IST in M12 if needed.

## 2. Analysis window — Full vs Effective (D10)
| Window | Market-days | Regime balance (Fear / Greed / Neutral) | Trades retained |
|---|---|---|---|
| **Full (chosen)** | 476 | 103 / 309 / 64 | 211,224 (100%) |
| Effective (≥2023-12-01) | 475 | 103 / 308 / 64 | 211,221 (100.00%) |

- The effective (post-gap) window removes only the isolated pre-gap fragment: **1 market-day and 3 trades**. Sample size (476→475), regime balance, and therefore statistical power are **essentially unchanged**.

**Decision: FULL dataset (default).** Because the effective window changes sample size/balance negligibly, discarding data is unjustified. The genuine concern from E2 (92% of trades in the final 6 months) is a **volume-concentration** issue, not a day-count issue: at the daily grain each day is one observation, so concentration does not shrink daily-grain n. It is retained as the `in_effective_window` flag (no rows dropped) so M12 can robustness-check any trade-pooled / volume-weighted statistic on the dense sub-period.

## 3. Merge audit (chosen methodology: UTC, full)
**account_day_merged.parquet**
- Merge key / tz convention: `trade_date_utc` (UTC)
- Rows before → after: **2,343 → 2,343**
- Duplicate joins: **0** (m:1 join — none possible)
- Matched rows: **2,343** (100.0%)
- Unmatched rows (kept, flagged `has_sentiment=False`): **0**
- Sentiment nulls introduced: **0**
- BTC-proxy nulls introduced (~60% coverage, D11): **352**

**market_day_merged.parquet**
- Merge key / tz convention: `trade_date_utc` (UTC)
- Rows before → after: **476 → 476**
- Duplicate joins: **0** (m:1 join — none possible)
- Matched rows: **476** (100.0%)
- Unmatched rows (kept, flagged `has_sentiment=False`): **0**
- Sentiment nulls introduced: **0**
- BTC-proxy nulls introduced (~60% coverage, D11): **199**

## 4. Sentiment sample sizes at the merged grain (for downstream power awareness)
Market-day regime balance is **Greed-tilted** (Greed 309 / Fear 103 / Neutral 64 days), so Fear-day power is the binding constraint. Neutral is retained (D5) and excluded only inside specific binary tests (M12). BTC market-context proxy covers ~60% of days (D11) — that caveat must accompany any confounder-controlled result.

## 5. Guardrail
Methodology (tz + window) was fixed above **before** running any hypothesis test (requirement 5). No significance was consulted in choosing it.
