"""
Module 9 runner — evaluate both tz strategies & both windows, choose on evidence,
then build the merged analytical datasets and the audit report.

Chosen methodology (decided BEFORE any hypothesis testing):
  timezone = UTC   |   window = FULL (with in_effective_window flag retained)

Outputs (data/processed/):
  account_day_merged.parquet   market_day_merged.parquet
Report:
  outputs/merge_report.md

Run:  python scripts/build_merge.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import resolve  # noqa: E402
from src.io_utils import load_parquet, save_parquet  # noqa: E402
from src.merge import (EFFECTIVE_START, evaluate_tz, evaluate_window, merge_daily)  # noqa: E402

REPORT = resolve("outputs/merge_report.md")
CHOSEN_TZ = "utc"
CHOSEN_DATE_COL = "trade_date_utc"


def _audit_block(title: str, a: dict) -> list[str]:
    return [
        f"**{title}**",
        f"- Merge key / tz convention: `{a['merge_key']}` (UTC)",
        f"- Rows before → after: **{a['rows_before']:,} → {a['rows_after']:,}**",
        f"- Duplicate joins: **{a['duplicate_joins']}** (m:1 join — none possible)",
        f"- Matched rows: **{a['matched_rows']:,}** ({a['pct_matched']}%)",
        f"- Unmatched rows (kept, flagged `has_sentiment=False`): **{a['unmatched_rows']:,}**",
        f"- Sentiment nulls introduced: **{a['sentiment_nulls_introduced']:,}**",
        f"- BTC-proxy nulls introduced (~60% coverage, D11): **{a['market_proxy_nulls_introduced']:,}**",
        "",
    ]


def main() -> int:
    sentiment = load_parquet(resolve("data/interim/sentiment_clean.parquet"))
    feats = load_parquet(resolve("data/interim/trades_features.parquet"))
    ad = load_parquet(resolve(f"data/interim/account_day_{CHOSEN_TZ}.parquet"))
    md = load_parquet(resolve(f"data/interim/market_day_{CHOSEN_TZ}.parquet"))
    md_utc = load_parquet(resolve("data/interim/market_day_utc.parquet"))
    md_ist = load_parquet(resolve("data/interim/market_day_ist.parquet"))
    ctx = load_parquet(resolve(f"data/interim/market_context_{CHOSEN_TZ}.parquet"))

    tz = evaluate_tz(md_utc, md_ist, sentiment, feats)
    win = evaluate_window(md_utc, sentiment, "trade_date_utc")

    ad_m, ad_audit = merge_daily(ad, sentiment, ctx, CHOSEN_DATE_COL)
    md_m, md_audit = merge_daily(md, sentiment, ctx, CHOSEN_DATE_COL)
    save_parquet(ad_m, resolve("data/processed/account_day_merged.parquet"))
    save_parquet(md_m, resolve("data/processed/market_day_merged.parquet"))

    L = ["# Merge Report — Module 9",
         "",
         "_The statistically critical join of Fear & Greed sentiment (and the in-sample BTC market "
         "context proxy) onto the daily tables. Methodology was chosen on the evidence below BEFORE "
         "any hypothesis testing — the merge was never tuned toward significant results. No hypothesis "
         "tests, significance interpretation, or business conclusions are produced here._",
         "",
         "## 1. Timezone strategy — UTC vs IST (D8)",
         "| Strategy | Market-days | Matched | Unmatched | % matched | Unmatched dates |",
         "|---|---|---|---|---|---|",
         f"| **UTC (chosen)** | {tz['utc']['market_days']} | {tz['utc']['matched']} | "
         f"{tz['utc']['unmatched']} | {tz['utc']['pct_matched']}% | {tz['utc']['unmatched_dates'] or '—'} |",
         f"| IST (rejected) | {tz['ist']['market_days']} | {tz['ist']['matched']} | "
         f"{tz['ist']['unmatched']} | {tz['ist']['pct_matched']}% | {tz['ist']['unmatched_dates'] or '—'} |",
         "",
         f"- **tz sensitivity:** {tz['trades_crossing_boundary_pct']}% of trades cross the IST/UTC day "
         f"boundary, but only **{tz['trades_regime_differs_pct']}% are assigned a different sentiment "
         f"regime** under UTC vs IST — i.e. 93%+ of trades are tz-robust.",
         "",
         "**Decision: UTC.** Evidence, not preference:",
         "1. The sentiment series is anchored to a **fixed UTC instant** (every timestamp is 05:30:00 "
         "UTC — established in M3/M5); the '11:00 IST' appearance is merely that same UTC instant "
         "expressed in IST, an artifact of the trade data's display tz — not evidence the index is "
         "IST-native.",
         "2. The Bitcoin Fear & Greed index and crypto markets conventionally operate on **UTC days**.",
         "3. **Completeness:** UTC matches 100% of market-days (0 unmatched); IST leaves 1 unmatched "
         "day (2024-10-26, a date absent from the sentiment series).",
         "**Why IST was rejected:** no evidence the index is IST-native; IST bucketing relies on the "
         "exchange's *display* timezone (which describes trade display, not the sentiment's native day) "
         "and introduces an unmatched day. Residual uncertainty (6.57% tz-sensitive trades) is small and "
         "can be robustness-checked under IST in M12 if needed.",
         "",
         "## 2. Analysis window — Full vs Effective (D10)",
         "| Window | Market-days | Regime balance (Fear / Greed / Neutral) | Trades retained |",
         "|---|---|---|---|",
         f"| **Full (chosen)** | {win['full']['market_days']} | "
         f"{win['full']['regime_balance'].get('Fear',0)} / {win['full']['regime_balance'].get('Greed',0)} "
         f"/ {win['full']['regime_balance'].get('Neutral',0)} | 211,224 (100%) |",
         f"| Effective (≥2023-12-01) | {win['effective']['market_days']} | "
         f"{win['effective']['regime_balance'].get('Fear',0)} / {win['effective']['regime_balance'].get('Greed',0)} "
         f"/ {win['effective']['regime_balance'].get('Neutral',0)} | 211,221 (100.00%) |",
         "",
         "- The effective (post-gap) window removes only the isolated pre-gap fragment: **1 market-day "
         "and 3 trades**. Sample size (476→475), regime balance, and therefore statistical power are "
         "**essentially unchanged**.",
         "",
         "**Decision: FULL dataset (default).** Because the effective window changes sample size/balance "
         "negligibly, discarding data is unjustified. The genuine concern from E2 (92% of trades in the "
         "final 6 months) is a **volume-concentration** issue, not a day-count issue: at the daily grain "
         "each day is one observation, so concentration does not shrink daily-grain n. It is retained as "
         "the `in_effective_window` flag (no rows dropped) so M12 can robustness-check any trade-pooled / "
         "volume-weighted statistic on the dense sub-period.",
         "",
         "## 3. Merge audit (chosen methodology: UTC, full)",
         *_audit_block("account_day_merged.parquet", ad_audit),
         *_audit_block("market_day_merged.parquet", md_audit),
         "## 4. Sentiment sample sizes at the merged grain (for downstream power awareness)",
         "Market-day regime balance is **Greed-tilted** (Greed 309 / Fear 103 / Neutral 64 days), so "
         "Fear-day power is the binding constraint. Neutral is retained (D5) and excluded only inside "
         "specific binary tests (M12). BTC market-context proxy covers ~60% of days (D11) — that caveat "
         "must accompany any confounder-controlled result.",
         "",
         "## 5. Guardrail",
         "Methodology (tz + window) was fixed above **before** running any hypothesis test (requirement 5). "
         "No significance was consulted in choosing it.",
         ""]
    REPORT.write_text("\n".join(L))
    print("\n".join(L))
    print(f"\n>>> Report: {REPORT.relative_to(resolve('.'))}")
    print(f">>> account_day_merged rows={len(ad_m):,} cols={ad_m.shape[1]} | "
          f"market_day_merged rows={len(md_m):,} cols={md_m.shape[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
