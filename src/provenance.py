"""Provenance record for cleaning operations (Module 3).

Every cleaning action returns a CleanOp so the audit trail in
outputs/cleaning_report.md is generated mechanically — not by hand — and the
row-count reconciliation is guaranteed to reflect what the code actually did.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CleanOp:
    name: str
    rows_before: int
    rows_after: int
    rows_affected: int
    reversible: bool
    reason: str
    disposition: str          # "preserved" | "flagged (preserved)" | "removed" | "added column"
    f_id: str = ""
    decision: str = ""

    @property
    def pct_affected(self) -> float:
        return (self.rows_affected / self.rows_before * 100) if self.rows_before else 0.0


def report_table(ops: list[CleanOp]) -> str:
    head = ("| Operation | F-id | Decision | Rows before | Rows after | Rows affected | "
            "% affected | Reversible | Disposition | Reason |")
    sep = "|---|---|---|---|---|---|---|---|---|---|"
    lines = [head, sep]
    for o in ops:
        lines.append(
            f"| {o.name} | {o.f_id or '—'} | {o.decision or '—'} | {o.rows_before:,} | "
            f"{o.rows_after:,} | {o.rows_affected:,} | {o.pct_affected:.3f}% | "
            f"{'yes' if o.reversible else 'NO'} | {o.disposition} | {o.reason} |"
        )
    return "\n".join(lines)
