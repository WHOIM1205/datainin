"""
Module 2 runner — execute validation checks and emit outputs/validation_report.md.

Exit code is non-zero if any check FAILs, so the pipeline halts on a broken
assumption (governance rule: a FAIL requires a CHANGE entry before proceeding).

Run:  python scripts/validate_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config, resolve  # noqa: E402
from src.validate import (  # noqa: E402
    CheckResult, summarize, validate_sentiment, validate_trades,
)

OUT = resolve("outputs/validation_report.md")


def _table(results: list[CheckResult]) -> str:
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    lines = ["| Status | Check | Guards | Detail |", "|--------|-------|--------|--------|"]
    for r in results:
        lines.append(f"| {icon[r.status]} {r.status} | {r.check} | `{r.ref}` | {r.detail} |")
    return "\n".join(lines)


def main() -> int:
    cfg = load_config()
    sent = pd.read_csv(resolve(cfg["paths"]["raw_sentiment"]))
    trades = pd.read_csv(resolve(cfg["paths"]["raw_trades"]))

    sent_res = validate_sentiment(sent)
    trade_res = validate_trades(trades)
    all_res = sent_res + trade_res
    s = summarize(all_res)

    verdict = "❌ FAIL" if s["FAIL"] else ("⚠️ PASS WITH WARNINGS" if s["WARN"] else "✅ ALL PASS")
    report = "\n".join([
        "# Validation Report — Module 2",
        "",
        "_Rule-based checks enforcing the frozen facts in `ASSUMPTIONS_LOG.md`._",
        "_PASS = fact holds · WARN = known condition for cleaning to handle · FAIL = fact violated (halt)._",
        "",
        f"**Overall: {verdict}** — {s['PASS']} passed, {s['WARN']} warnings, {s['FAIL']} failed "
        f"(of {len(all_res)} checks).",
        "",
        "## Dataset 1 — Bitcoin Fear & Greed Index",
        _table(sent_res),
        "",
        "## Dataset 2 — Hyperliquid Historical Trader Data",
        _table(trade_res),
        "",
        "## Warnings carried into cleaning (Module 3)",
        _warn_notes(all_res),
    ])
    OUT.write_text(report)
    print(report)
    print(f"\n>>> Report written to {OUT.relative_to(resolve('.'))}")

    return 1 if s["FAIL"] else 0


def _warn_notes(results: list[CheckResult]) -> str:
    warns = [r for r in results if r.status == "WARN"]
    if not warns:
        return "_None._"
    return "\n".join(f"- **{r.check}** (`{r.ref}`): {r.detail}" for r in warns)


if __name__ == "__main__":
    raise SystemExit(main())
