# Aggregation Report — Module 7

_The analytical foundation: trade-level features collapsed to two strictly-separated daily grains. Rates/ratios are rebuilt from summed counts/notional (weighted), never averaged; heavy-tailed quantities use median (robust). Built for both tz keys because the sentiment timezone is unresolved (D8/D10); the merge module selects one._

## Tables produced
| Table | Grain | Rows | Columns |
|---|---|---|---|
| `account_day_utc.parquet` | account-day | 2,343 | 25 |
| `market_day_utc.parquet` | market-day | 476 | 16 |
| `account_day_ist.parquet` | account-day | 2,341 | 25 |
| `market_day_ist.parquet` | market-day | 480 | 16 |

## Observation-count columns (sample sizes for later statistics)
- **account-day**: `trade_count`, `pnl_trade_count`, `perp_trade_count`, `valid_observation_count` (= trade_count). `account_count` ≡ 1 by construction.
- **market-day**: `trade_count`, `pnl_trade_count`, `account_count` (active accounts), `valid_observation_count` (= account_count).

## Metric dictionary — account-day
| Column | Source grain | Function | Type | Rationale |
|---|---|---|---|---|
| `trade_count` | trade | count of fills | count | Sample size: number of trades that account-day. |
| `pnl_trade_count` | trade | count where Closed PnL≠0 | count | Sample size for PnL/win metrics (realized only on closing fills, D6/F2.9). |
| `perp_trade_count` | trade | count where is_perp | count | Perp sample size (directional/leverage analysis is perp-only). |
| `valid_observation_count` | trade | = trade_count | count | Explicit sample size the row summarizes. |
| `daily_pnl` | trade | sum(Closed PnL) | additive | Total realized PnL that account-day; PnL is additive. |
| `gross_profit` | trade | sum(PnL where >0) | additive | Feeds profit factor later; additive. |
| `gross_loss` | trade | sum(PnL where <0) | additive | Feeds profit factor / drawdown; additive. |
| `win_count` | trade | count where PnL>0 | count | Numerator for win_rate (kept as a count so rate is reconstructable). |
| `win_rate` | trade | win_count / pnl_trade_count | weighted (derived-from-counts) | A RATE — rebuilt from counts, never averaged across trades. |
| `notional_sum` | trade | sum(Size USD) | additive | Gross traded volume; additive. |
| `notional_median` | trade | median(Size USD) | median (robust) | Typical trade size; median because size is heavy-tailed (E6), not mean. |
| `ret_on_notional_weighted` | trade | daily_pnl / bearing_notional | weighted | Notional-weighted return; a RATIO built from sums, not a mean of per-trade ratios. |
| `pnl_per_notional_median` | trade | median(pnl_per_notional) | median (robust) | Robust central tendency of per-trade return-on-notional. |
| `long_count` | trade | count perp Long | count | Numerator of long/short ratio (perp only). |
| `short_count` | trade | count perp Short | count | Denominator of long/short ratio (perp only). |
| `long_short_ratio` | trade | long_count / short_count | weighted (derived-from-counts) | A RATIO — from counts; NaN when short_count=0. |
| `long_notional` | trade | sum(Size USD where perp Long) | additive | Notional-weighted long exposure. |
| `short_notional` | trade | sum(Size USD where perp Short) | additive | Notional-weighted short exposure. |
| `net_directional_notional` | trade | long_notional − short_notional | additive | Signed net directional exposure (perp). |
| `fee_sum` | trade | sum(Fee) | additive | Total fees (negative = rebates, F2.14); additive. |
| `fee_bps_weighted` | trade | fee_sum / notional_sum × 1e4 | weighted | Cost RATE — total fees over total notional, not a mean of per-trade bps. |
| `size_z_median` | trade | median(size_z) | median (robust) | Typical self-normalized aggression that day (E3/E6). |
| `large_trade_count` | trade | count where is_large_trade | count | How many unusually-large-for-this-account trades. |

## Metric dictionary — market-day
| Column | Source grain | Function | Type | Rationale |
|---|---|---|---|---|
| `trade_count` | trade | count of fills | count | Market trade sample size. |
| `pnl_trade_count` | trade | count where PnL≠0 | count | Market PnL sample size. |
| `account_count` | account | distinct account-days | count | Number of accounts active that day (E3: few whales dominate). |
| `valid_observation_count` | account | = account_count | count | Sample size for cross-account daily statistics. |
| `market_daily_pnl` | trade | sum(Closed PnL) | additive | Total realized PnL across all accounts; additive. |
| `median_account_daily_pnl` | account | median(account-day daily_pnl) | median (robust) | Typical account's day — resists whale domination (E3). ACCOUNT grain, not trade. |
| `market_win_rate` | trade | Σwin_count / Σpnl_trade_count | weighted (derived-from-counts) | Pooled win RATE from counts, not a mean of account rates. |
| `total_notional` | trade | sum(Size USD) | additive | Total market volume. |
| `median_trade_size` | trade | median(Size USD) | median (robust) | Typical trade size market-wide (E6). |
| `market_long_short_ratio` | trade | Σlong_count / Σshort_count | weighted (derived-from-counts) | Pooled directional RATIO from counts. |
| `market_fee_bps_weighted` | trade | Σfee / Σnotional × 1e4 | weighted | Pooled cost rate. |

## Aggregation-type legend
- **count** — preserved observation count (sample size).
- **additive** — a sum of an extensive quantity (PnL, notional, fees).
- **median (robust)** — central tendency for heavy-tailed quantities (E1/E6).
- **weighted / derived-from-counts** — a rate or ratio rebuilt from summed counts/notional, NOT a mean of per-trade rates (avoids whale/minnow mis-averaging).