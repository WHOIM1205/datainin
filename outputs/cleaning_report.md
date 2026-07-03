# Cleaning Report — Module 3 (Audit Trail)

_Non-destructive cleaning: raw files untouched, no rows dropped, cleaning only adds derived columns and boolean flags. Every operation is logged with full provenance._

**Overall reconciliation: ✅ EXACT — no data loss**

## Dataset 1 — Bitcoin Fear & Greed → `data/interim/sentiment_clean.parquet`
| Operation | F-id | Decision | Rows before | Rows after | Rows affected | % affected | Reversible | Disposition | Reason |
|---|---|---|---|---|---|---|---|---|---|
| Parse `date` → `date_key` (datetime, calendar day) | F1.6 | — | 2,644 | 2,644 | 2,644 | 100.000% | yes | added column | Typed join key; raw string `date` preserved for provenance. |
| Verify `classification` in known 5-bucket domain | F1.4 | — | 2,644 | 2,644 | 0 | 0.000% | yes | preserved | Domain clean; unknown values={}. No change. |
| Add `sentiment_side` ∈ {Fear, Greed, Neutral} | F1.4 | D4/D5 | 2,644 | 2,644 | 2,644 | 100.000% | yes | added column | Coarse regime for Fear-vs-Greed analysis; Neutral retained as first-class (excluded only within specific binary tests, not here). |
| Verify 0 missing cells & 0 duplicate dates | F1.3 | — | 2,644 | 2,644 | 0 | 0.000% | yes | preserved | Confirmed clean at source. No imputation, no dedup needed. |

**Reconciliation**
- Rows raw → clean: **2,644 → 2,644** (dropped: 0)
- All 4 raw columns preserved: **True**
- Derived columns added (2): `date_key`, `sentiment_side`
- Reconciliation: **✅ EXACT**

**Cleaned schema**
| column | dtype | origin |
|---|---|---|
| `timestamp` | int64 | raw |
| `value` | int64 | raw |
| `classification` | str | raw |
| `date` | str | raw |
| `date_key` | datetime64[us] | **derived** |
| `sentiment_side` | str | **derived** |

## Dataset 2 — Hyperliquid Trades → `data/interim/trades_clean.parquet`
| Operation | F-id | Decision | Rows before | Rows after | Rows affected | % affected | Reversible | Disposition | Reason |
|---|---|---|---|---|---|---|---|---|---|
| Parse `Timestamp IST` → `ts_ist` (tz-aware, Asia/Kolkata) | F2.5 | — | 211,224 | 211,224 | 211,224 | 100.000% | yes | added column | Authoritative time; lossy numeric `Timestamp` ignored. Raw string kept. |
| Derive `trade_date_ist` & `trade_date_utc` (dual keys) | F2.5 | D8 | 211,224 | 211,224 | 53,322 | 25.244% | yes | added column | Sentiment tz unprovable from data; keep both keys. 53,322 rows (25.24%) fall on different IST vs UTC calendar days — the merge module will choose the appropriate key. |
| Flag `is_zero_size` (Size USD == 0) | F2.14 | — | 211,224 | 211,224 | 43 | 0.020% | yes | flagged (preserved) | Zero-notional fills; excluded from size metrics later. Rows retained. |
| Flag `size_mismatch` (|Size USD − Price×Tokens| > 1%) | F2.2 | — | 211,224 | 211,224 | 209 | 0.099% | yes | flagged (preserved) | Transparency flag; Size USD (exchange-reported) is trusted. Rows retained. |
| Flag `is_edge_direction` (ADL/Liquidation/Settlement/flips) | F2.10 | — | 211,224 | 211,224 | 137 | 0.065% | yes | flagged (preserved) | Non-directional events; excluded from long/short ratio later. Rows retained. |
| Flag `is_spot` (spot markets vs perpetuals) | F2.10 | T6 | 211,224 | 211,224 | 36,760 | 17.403% | yes | flagged (preserved) | Spot has no leverage/long-short semantics; retained for PnL/volume, filtered for directional/leverage analysis. Direction-based & Coin-based definitions agree exactly. |
| Leverage EXCLUDED (no source column; not fabricated) | F2.4 | D3 | 211,224 | 211,224 | 0 | 0.000% | yes | preserved | F2.4: no leverage field exists and no account-equity/margin field allows honest reconstruction. Excluded from analysis per D3. No column added. |
| Verify 0 missing cells & 0 full-row duplicates | F2.3 | — | 211,224 | 211,224 | 0 | 0.000% | yes | preserved | Confirmed clean at source. No imputation, no dedup needed. |

**Reconciliation**
- Rows raw → clean: **211,224 → 211,224** (dropped: 0)
- All 16 raw columns preserved: **True**
- Derived columns added (8): `ts_ist`, `ts_utc`, `trade_date_ist`, `trade_date_utc`, `is_zero_size`, `size_mismatch`, `is_edge_direction`, `is_spot`
- Reconciliation: **✅ EXACT**

**Cleaned schema**
| column | dtype | origin |
|---|---|---|
| `Account` | str | raw |
| `Coin` | str | raw |
| `Execution Price` | float64 | raw |
| `Size Tokens` | float64 | raw |
| `Size USD` | float64 | raw |
| `Side` | str | raw |
| `Timestamp IST` | str | raw |
| `Start Position` | float64 | raw |
| `Direction` | str | raw |
| `Closed PnL` | float64 | raw |
| `Transaction Hash` | str | raw |
| `Order ID` | int64 | raw |
| `Crossed` | bool | raw |
| `Fee` | float64 | raw |
| `Trade ID` | float64 | raw |
| `Timestamp` | float64 | raw |
| `ts_ist` | datetime64[us, Asia/Kolkata] | **derived** |
| `ts_utc` | datetime64[us, UTC] | **derived** |
| `trade_date_ist` | datetime64[us] | **derived** |
| `trade_date_utc` | datetime64[us] | **derived** |
| `is_zero_size` | bool | **derived** |
| `size_mismatch` | bool | **derived** |
| `is_edge_direction` | bool | **derived** |
| `is_spot` | bool | **derived** |

## Notes
- **No imputation performed** — both datasets had 0 missing cells (F1.3 / F2.3).
- **No rows removed** — all quality issues handled by additive flags (fully reversible).
- **Leverage excluded** (D3): not fabricated; no honest reconstruction is possible (F2.4).
- **Dual date keys retained** (D8): sentiment timezone is unprovable from the data (all sentiment timestamps sit at 05:30 UTC / 11:00 IST, landing on the same calendar day in both zones); the merge module will choose IST vs UTC.