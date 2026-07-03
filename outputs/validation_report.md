# Validation Report — Module 2

_Rule-based checks enforcing the frozen facts in `ASSUMPTIONS_LOG.md`._
_PASS = fact holds · WARN = known condition for cleaning to handle · FAIL = fact violated (halt)._

**Overall: ⚠️ PASS WITH WARNINGS** — 25 passed, 2 warnings, 0 failed (of 27 checks).

## Dataset 1 — Bitcoin Fear & Greed Index
| Status | Check | Guards | Detail |
|--------|-------|--------|--------|
| ✅ PASS | row count | `F1.1` | 2,644 (expected 2,644) |
| ✅ PASS | column set & order | `F1.2` | 4 columns exactly as frozen |
| ✅ PASS | dtypes match Module 1 | `F1.2` | all dtypes as frozen |
| ✅ PASS | no missing cells | `F1.3` | 0 missing |
| ✅ PASS | no duplicate dates (one row/day) | `F1.3` | 0 duplicate dates |
| ✅ PASS | classification in known 5-bucket domain | `F1.4` | unknown values: {} |
| ✅ PASS | value within [0,100] | `F1.5` | 0 out-of-range; observed [5,95] |
| ✅ PASS | date parseable YYYY-MM-DD & within frozen range | `F1.6` | unparseable=0; range 2018-02-01→2025-05-02 |
| ✅ PASS | classification↔value bands are ordered & non-overlapping | `F1.4/F1.5` | Extreme Fear:[5,24]; Fear:[25,44]; Neutral:[45,54]; Greed:[55,74]; Extreme Greed:[75,95] |

## Dataset 2 — Hyperliquid Historical Trader Data
| Status | Check | Guards | Detail |
|--------|-------|--------|--------|
| ✅ PASS | row count | `F2.1` | 211,224 (expected 211,224) |
| ✅ PASS | column set & order | `F2.2` | 16 columns exactly as frozen |
| ✅ PASS | dtypes match Module 1 | `F2.2` | all dtypes as frozen |
| ✅ PASS | no missing cells | `F2.3` | 0 missing |
| ✅ PASS | no full-row duplicates | `F2.3` | 0 full-row duplicates |
| ✅ PASS | no leverage column | `F2.4` | leverage absent as frozen |
| ✅ PASS | Timestamp IST fully parseable (DD-MM-YYYY HH:MM) | `F2.5` | 0 unparseable |
| ✅ PASS | trade dates within frozen range | `F2.12` | 2023-05-01→2025-05-01 |
| ✅ PASS | numeric Timestamp confirmed lossy (do not use) | `F2.6` | 7 unique values |
| ✅ PASS | Trade ID confirmed not a unique key (do not use) | `F2.7` | 2,810 unique / 211,224 rows |
| ✅ PASS | Side in {BUY,SELL} | `F2.10` | unexpected: {} |
| ✅ PASS | Direction in known 12-value domain | `F2.10` | unexpected: {} |
| ✅ PASS | Crossed is boolean | `F2.11` | bool |
| ✅ PASS | account/coin cardinality stable | `F2.13` | accounts=32 (exp 32), coins=246 (exp 246) |
| ✅ PASS | Execution Price >= 0 | `F2.14` | 0 negative |
| ⚠️ WARN | Size USD >= 0 (zeros flagged for cleaning) | `F2.14` | 0 negative, 43 zero |
| ⚠️ WARN | Size USD ≈ Price × Size Tokens (±1%) | `F2.2` | 209 rows (0.10%) differ >1% |
| ✅ PASS | Direction↔Side consistent for unambiguous directions | `F2.10` | 0 mismatches over 210,945 unambiguous rows |

## Warnings carried into cleaning (Module 3)
- **Size USD >= 0 (zeros flagged for cleaning)** (`F2.14`): 0 negative, 43 zero
- **Size USD ≈ Price × Size Tokens (±1%)** (`F2.2`): 209 rows (0.10%) differ >1%