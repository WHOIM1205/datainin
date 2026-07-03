"""
Module 3 runner — clean both datasets, persist to Parquet, emit the audit trail.

Outputs:
  data/interim/sentiment_clean.parquet
  data/interim/trades_clean.parquet
  outputs/cleaning_report.md   (complete provenance / audit trail)

Guarantees: raw is never modified; no rows are dropped; row counts reconcile exactly.

Run:  python scripts/clean_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.clean_sentiment import clean_sentiment  # noqa: E402
from src.clean_trades import clean_trades  # noqa: E402
from src.config import load_config, resolve  # noqa: E402
from src.io_utils import save_parquet  # noqa: E402
from src.provenance import CleanOp, report_table  # noqa: E402

REPORT = resolve("outputs/cleaning_report.md")


def _schema_block(df: pd.DataFrame, raw_cols: list[str]) -> str:
    lines = ["| column | dtype | origin |", "|---|---|---|"]
    for c in df.columns:
        origin = "raw" if c in raw_cols else "**derived**"
        lines.append(f"| `{c}` | {df[c].dtype} | {origin} |")
    return "\n".join(lines)


def _reconcile(name: str, raw: pd.DataFrame, clean: pd.DataFrame, ops: list[CleanOp]) -> tuple[str, bool]:
    dropped = len(raw) - len(clean)
    added_cols = [c for c in clean.columns if c not in raw.columns]
    raw_preserved = all(c in clean.columns for c in raw.columns)
    ok = (dropped == 0) and raw_preserved
    block = [
        f"- Rows raw → clean: **{len(raw):,} → {len(clean):,}** (dropped: {dropped})",
        f"- All {len(raw.columns)} raw columns preserved: **{raw_preserved}**",
        f"- Derived columns added ({len(added_cols)}): {', '.join(f'`{c}`' for c in added_cols)}",
        f"- Reconciliation: **{'✅ EXACT' if ok else '❌ MISMATCH'}**",
    ]
    return "\n".join(block), ok


def main() -> int:
    cfg = load_config()
    raw_sent = pd.read_csv(resolve(cfg["paths"]["raw_sentiment"]))
    raw_trades = pd.read_csv(resolve(cfg["paths"]["raw_trades"]))

    sent_clean, sent_ops = clean_sentiment(raw_sent)
    trades_clean, trades_ops = clean_trades(raw_trades)

    save_parquet(sent_clean, resolve("data/interim/sentiment_clean.parquet"))
    save_parquet(trades_clean, resolve("data/interim/trades_clean.parquet"))

    sent_recon, sent_ok = _reconcile("sentiment", raw_sent, sent_clean, sent_ops)
    trades_recon, trades_ok = _reconcile("trades", raw_trades, trades_clean, trades_ops)
    all_ok = sent_ok and trades_ok

    report = "\n".join([
        "# Cleaning Report — Module 3 (Audit Trail)",
        "",
        "_Non-destructive cleaning: raw files untouched, no rows dropped, cleaning only adds "
        "derived columns and boolean flags. Every operation is logged with full provenance._",
        "",
        f"**Overall reconciliation: {'✅ EXACT — no data loss' if all_ok else '❌ MISMATCH'}**",
        "",
        "## Dataset 1 — Bitcoin Fear & Greed → `data/interim/sentiment_clean.parquet`",
        report_table(sent_ops),
        "",
        "**Reconciliation**",
        sent_recon,
        "",
        "**Cleaned schema**",
        _schema_block(sent_clean, list(raw_sent.columns)),
        "",
        "## Dataset 2 — Hyperliquid Trades → `data/interim/trades_clean.parquet`",
        report_table(trades_ops),
        "",
        "**Reconciliation**",
        trades_recon,
        "",
        "**Cleaned schema**",
        _schema_block(trades_clean, list(raw_trades.columns)),
        "",
        "## Notes",
        "- **No imputation performed** — both datasets had 0 missing cells (F1.3 / F2.3).",
        "- **No rows removed** — all quality issues handled by additive flags (fully reversible).",
        "- **Leverage excluded** (D3): not fabricated; no honest reconstruction is possible (F2.4).",
        "- **Dual date keys retained** (D8): sentiment timezone is unprovable from the data "
        "(all sentiment timestamps sit at 05:30 UTC / 11:00 IST, landing on the same calendar day "
        "in both zones); the merge module will choose IST vs UTC.",
    ])
    REPORT.write_text(report)
    print(report)
    print(f"\n>>> Report written to {REPORT.relative_to(resolve('.'))}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
