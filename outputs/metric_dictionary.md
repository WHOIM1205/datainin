# Metric Dictionary — Module 10

_Trader-level (per-account) metrics. Every metric measures **profitability, risk, consistency, or trading behaviour**; near-duplicates were pruned to the strongest representative. No hypothesis testing or conclusions — definitions and computation only._

**Grain:** one row per account (32 accounts). **Source:** merged daily + trade features (UTC, D8). **Realized PnL** on closing trades only (D6/F2.9).

## Profitability
| Metric | Formula | Interpretation | Assumptions | Limitations | Better |
|---|---|---|---|---|---|
| `total_pnl` | Σ Closed PnL over all trades | Absolute net profit (USD) the account realized. | PnL is additive and correctly signed (F2.9). | Scale-dependent — whales dominate; not comparable across account sizes. | higher |
| `expectancy_per_trade` | total_pnl / pnl_trade_count | Average realized edge per closing trade (USD). | Realized PnL booked on closing fills only (D6). | Ignores trade size; a large-size trader can have high expectancy but poor efficiency. | higher |
| `roi_on_notional` | total_pnl / Σ(Size USD on closing trades) | Return on capital-at-risk (profit per $ of notional traded). | Notional (Size USD) approximates capital at risk (F2.2). | Notional ≠ margin (no leverage/equity data, D3); it is turnover-weighted, not held capital. | higher |
| `profit_factor` | Σ gross_profit / |Σ gross_loss| | Dollars won per dollar lost; >1 is profitable. | Wins and losses both present. | Undefined with zero losses (→ NaN); insensitive to trade frequency. | higher |

## Risk-Adjusted
| Metric | Formula | Interpretation | Assumptions | Limitations | Better |
|---|---|---|---|---|---|
| `sharpe_proxy` | mean(daily_pnl) / std(daily_pnl) | Risk-adjusted return: mean daily PnL per unit of daily-PnL volatility. | Daily PnL is the return series; no risk-free rate; NOT annualized (hence 'proxy'). | Assumes stable variance; unstable for accounts with few active days; not comparable to a true annualized Sharpe. | higher |

## Risk
| Metric | Formula | Interpretation | Assumptions | Limitations | Better |
|---|---|---|---|---|---|
| `max_drawdown` | min(cumsum(daily_pnl) − cummax(cumsum(daily_pnl))) | Worst peak-to-trough decline of cumulative PnL (USD) — a drawdown proxy. | Cumulative daily PnL ordered by date approximates the equity path. | Path uses realized daily PnL only (no intraday/unrealized); scale-dependent (USD). | higher (closer to 0) |
| `cvar_5` | mean(daily_pnl | daily_pnl ≤ 5th percentile) | Expected shortfall: average PnL on the worst 5% of days (tail risk). | Enough active days for a meaningful 5% tail. | Unstable below ~20 active days; scale-dependent (USD). | higher (closer to 0) |

## Consistency
| Metric | Formula | Interpretation | Assumptions | Limitations | Better |
|---|---|---|---|---|---|
| `win_rate` | win_count / pnl_trade_count | Share of closing trades that are profitable (trade grain). | Closing trades only (D6). | Says nothing about win/loss magnitude — high win rate can still lose money. | higher |
| `pct_profitable_days` | mean(daily_pnl > 0) over active days | Share of active days that end net-positive (day grain). | Daily grain, UTC days (D8). | Day-level, so differs from win_rate; sensitive to how PnL clusters within a day. | higher |

## Behaviour
| Metric | Formula | Interpretation | Assumptions | Limitations | Better |
|---|---|---|---|---|---|
| `n_active_days` | count of distinct active days | Engagement span — how many days the account traded. | Active day = ≥1 trade that UTC day. | Does not capture intensity; a proxy for tenure/engagement, not calendar tenure. | neutral (segmenting) |
| `avg_trades_per_active_day` | total_trades / n_active_days | Trading intensity / frequency on days the account is active. | — | Averages over active days only (ignores idle days). | neutral (segmenting) |
| `median_trade_size_usd` | median(Size USD) over trades with Size USD > 0 | Typical position size (USD). | Size USD trusted (F2.2); zero-size rows excluded (F2.14). | Median hides the heavy right tail of sizes (E6). | neutral (segmenting) |
| `long_ratio` | long_count / (long_count + short_count), perp only | Directional bias: 0.5 = balanced, >0.5 = net long. | Perpetual Long/Short only; spot & edge excluded (T6/F2.10). | Counts opens+closes equally; not exposure- or time-weighted. | neutral (segmenting) |

## Deliberately excluded (redundancy discipline)
- **Value-at-Risk (VaR)** — dropped in favour of `cvar_5`; CVaR is coherent and averages the whole tail rather than a single quantile.
- **Symmetric PnL volatility (std)** — not a headline metric; downside risk (`max_drawdown`, `cvar_5`) is more decision-relevant. It survives only inside the `sharpe_proxy` denominator.
- **Raw total trade count** — folded into `avg_trades_per_active_day` (intensity) + `n_active_days` (engagement); the product adds no independent information.

## Intentionally retained near-neighbours (distinct information)
- `win_rate` (trade grain) vs `pct_profitable_days` (day grain) — a trader can win most trades yet lose on many days.
- `expectancy_per_trade` ($/trade) vs `roi_on_notional` ($/$) vs `profit_factor` (win/loss asymmetry) vs `total_pnl` (absolute) — four distinct profitability facets.
- `max_drawdown` (cumulative-path, sequence-dependent worst streak) vs `cvar_5` (single-day expected shortfall) — the only pair with |Spearman| > 0.9 (**0.929**). Both are kept because they answer different risk questions (worst *streak* vs typical *bad day*); their high rank-correlation is largely a shared **USD scale effect** (bigger accounts have bigger both) and they would diverge under different PnL clustering. Segmentation (M11) can scale-normalize if needed.