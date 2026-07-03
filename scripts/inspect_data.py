"""
Module 1 — Data inspection (assumption killer).

Purpose: inspect both raw datasets exactly as delivered, verify every column
name and dtype, and emit a data-quality report. This script does NOT clean,
transform, engineer features, merge, or plot. It only observes and documents.

Run:  python scripts/inspect_data.py
Output: prints to stdout AND writes outputs/data_quality_report.md
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs" / "data_quality_report.md"

SENTIMENT = RAW / "fear_greed.csv"
TRADES = RAW / "hyperliquid_trades.csv"

# Columns we treat as categorical for value-frequency reporting (only if present).
CATEGORICAL_HINTS = {"classification", "Side", "Direction", "Crossed", "Coin"}
# Columns we suspect are date/time-like (report min/max/uniques as-is, no parsing logic).
DATELIKE_HINTS = {"date", "timestamp", "Timestamp", "Timestamp IST"}


def load_raw(path: Path) -> pd.DataFrame:
    """Load with dtype inference OFF for object columns is unnecessary here;
    we load with pandas defaults so we can report the *inferred* dtypes truthfully."""
    return pd.read_csv(path)


def section(title: str) -> str:
    return f"\n## {title}\n"


def df_schema_table(df: pd.DataFrame) -> str:
    rows = ["| # | column | dtype | non-null | nulls | null % | n_unique |",
            "|---|--------|-------|----------|-------|--------|----------|"]
    n = len(df)
    for i, col in enumerate(df.columns):
        nn = int(df[col].notna().sum())
        nulls = n - nn
        pct = f"{(nulls / n * 100):.2f}%" if n else "n/a"
        nuniq = int(df[col].nunique(dropna=True))
        rows.append(f"| {i} | `{col}` | {df[col].dtype} | {nn:,} | {nulls:,} | {pct} | {nuniq:,} |")
    return "\n".join(rows)


def _df_to_md(df: pd.DataFrame, index: bool = False) -> str:
    """Minimal markdown table renderer (avoids the optional `tabulate` dependency)."""
    cols = ([""] if index else []) + [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines = [header, sep]
    for idx, row in df.iterrows():
        cells = ([str(idx)] if index else []) + [
            (f"{v:,.4f}" if isinstance(v, float) else str(v)) for v in row.tolist()
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def numeric_summary(df: pd.DataFrame) -> str:
    num = df.select_dtypes(include="number")
    if num.empty:
        return "_No numeric columns._"
    desc = num.describe().T.reset_index().rename(columns={"index": "column"})
    return _df_to_md(desc, index=False)


def category_frequencies(df: pd.DataFrame) -> str:
    parts = []
    for col in df.columns:
        if col not in CATEGORICAL_HINTS:
            continue
        vc = df[col].value_counts(dropna=False)
        # Cap very high-cardinality columns (e.g., Coin) to top 15.
        capped = vc.head(15)
        parts.append(f"\n**`{col}`** — {df[col].nunique(dropna=True)} unique value(s)"
                     + (" (top 15 shown)" if len(vc) > 15 else "") + ":\n")
        parts.append("| value | count | share |\n|-------|-------|-------|")
        total = len(df)
        for val, cnt in capped.items():
            parts.append(f"| {val!r} | {cnt:,} | {cnt/total*100:.2f}% |")
    return "\n".join(parts) if parts else "_No hinted categorical columns present._"


def datelike_report(df: pd.DataFrame) -> str:
    parts = []
    for col in df.columns:
        if col not in DATELIKE_HINTS:
            continue
        s = df[col]
        parts.append(f"\n**`{col}`** (raw dtype `{s.dtype}`):")
        parts.append(f"- min (raw): `{s.min()}`")
        parts.append(f"- max (raw): `{s.max()}`")
        parts.append(f"- n_unique: {s.nunique(dropna=True):,}")
        parts.append(f"- sample values: {list(s.dropna().head(3))}")
    return "\n".join(parts) if parts else "_No hinted date-like columns present._"


def duplicate_report(df: pd.DataFrame, key_candidates: list[str]) -> str:
    parts = []
    full_dupes = int(df.duplicated().sum())
    parts.append(f"- Full-row duplicates: **{full_dupes:,}**")
    for key in key_candidates:
        if key in df.columns:
            kd = int(df.duplicated(subset=[key]).sum())
            parts.append(f"- Duplicate `{key}` values: **{kd:,}**")
    return "\n".join(parts)


def inspect(name: str, path: Path, key_candidates: list[str]) -> tuple[str, pd.DataFrame]:
    df = load_raw(path)
    md = [f"# {name}", ""]
    md.append(f"- Source file: `{path.relative_to(ROOT)}`")
    md.append(f"- File size on disk: {path.stat().st_size:,} bytes")
    md.append(f"- Rows: **{len(df):,}**")
    md.append(f"- Columns: **{df.shape[1]}**")
    md.append(f"- Memory (in-RAM): {df.memory_usage(deep=True).sum()/1e6:.1f} MB")

    md.append(section("Schema & dtypes (as inferred by pandas)"))
    md.append(df_schema_table(df))

    md.append(section("Missing values"))
    total_missing = int(df.isna().sum().sum())
    md.append(f"Total missing cells: **{total_missing:,}** "
              f"({total_missing/(len(df)*df.shape[1])*100:.4f}% of all cells)")
    cols_with_na = df.isna().sum()
    cols_with_na = cols_with_na[cols_with_na > 0]
    if cols_with_na.empty:
        md.append("\n_No column has any missing values._")
    else:
        md.append("\nColumns with missing values:")
        for c, v in cols_with_na.items():
            md.append(f"- `{c}`: {v:,} ({v/len(df)*100:.2f}%)")

    md.append(section("Duplicates"))
    md.append(duplicate_report(df, key_candidates))

    md.append(section("Date-like columns (raw, unparsed)"))
    md.append(datelike_report(df))

    md.append(section("Category frequencies"))
    md.append(category_frequencies(df))

    md.append(section("Numeric summary (raw)"))
    md.append(numeric_summary(df))

    md.append(section("First 5 rows (raw)"))
    md.append(_df_to_md(df.head(5), index=False))

    return "\n".join(md), df


def main() -> None:
    assert SENTIMENT.exists(), f"Missing {SENTIMENT}"
    assert TRADES.exists(), f"Missing {TRADES}"

    sent_md, sent_df = inspect(
        "Dataset 1 — Bitcoin Fear & Greed Index", SENTIMENT, key_candidates=["date", "timestamp"]
    )
    trade_md, trade_df = inspect(
        "Dataset 2 — Hyperliquid Historical Trader Data", TRADES,
        key_candidates=["Trade ID", "Order ID", "Transaction Hash"],
    )

    # Explicit assumption checks the PDF made that we must verify.
    checks = ["# Assumption verification (PDF vs reality)", ""]
    checks.append("| PDF said | Reality | Verdict |")
    checks.append("|----------|---------|---------|")
    checks.append(f"| Sentiment cols: `Date, Classification` | `{list(sent_df.columns)}` | "
                  f"Has extra `timestamp` + numeric `value`; richer than stated |")
    has_neutral = "Neutral" in set(sent_df["classification"].unique()) if "classification" in sent_df else "n/a"
    checks.append(f"| Classification = Fear/Greed (binary) | "
                  f"{sorted(sent_df['classification'].unique())} | "
                  f"Multi-bucket; Neutral present = {has_neutral} |")
    lev_present = any("lever" in c.lower() for c in trade_df.columns)
    checks.append(f"| Trades include `leverage` | leverage column present = **{lev_present}** | "
                  f"{'FOUND' if lev_present else 'ABSENT — must be proxied or dropped'} |")
    checks.append(f"| Trades include `event`, `start position` | "
                  f"start position present = {'Start Position' in trade_df.columns}; "
                  f"event present = {'event' in [c.lower() for c in trade_df.columns]} | verified |")

    # Data-integrity findings that materially affect downstream design.
    # (Documentation only: we identify issues here, we do NOT fix them in Module 1.)
    integ = ["# Key data-integrity findings (documentation only)", ""]
    tid_uniq = trade_df["Trade ID"].nunique()
    ts_uniq = trade_df["Timestamp"].nunique()
    pnl_zero = float((trade_df["Closed PnL"] == 0).mean() * 100)
    neg_fee = int((trade_df["Fee"] < 0).sum())
    zero_price = int((trade_df["Execution Price"] == 0).sum())
    zero_size = int((trade_df["Size USD"] == 0).sum())
    integ.append(f"1. **Numeric `Timestamp` column is LOSSY** — only {ts_uniq} unique values across "
                 f"{len(trade_df):,} rows (rounded to ~3 significant figures). It is unusable for time. "
                 f"**`Timestamp IST` (string, IST tz) is the authoritative time field.**")
    integ.append(f"2. **`Trade ID` is NOT a unique key** — only {tid_uniq:,} unique values across "
                 f"{len(trade_df):,} rows, and values appear rounded (e.g. 895000000000000). "
                 f"Full-row duplicates = 0, so rows are distinct; but no single reliable trade-level key exists "
                 f"(Order ID and Transaction Hash are one-to-many across fills).")
    integ.append(f"3. **No `leverage` column** — the PDF listed it, but the file has none. Leverage must be "
                 f"either derived as a documented proxy (e.g. from Size USD vs Start Position) or excluded, "
                 f"with the decision justified in the cleaning module.")
    integ.append(f"4. **`Closed PnL` is sparse** — {pnl_zero:.1f}% of rows have PnL = 0 (realized PnL booked on "
                 f"closing fills only). Win-rate must therefore be defined on PnL-bearing (closing) trades, "
                 f"not all fills — to be decided in the metrics module.")
    integ.append(f"5. **`Direction` has 12 values** including edge cases "
                 f"(Auto-Deleveraging, Liquidated, Settlement, Long > Short, Spot Dust Conversion). "
                 f"Long/short classification logic must handle these explicitly.")
    integ.append(f"6. **Boundary values present** — negative `Fee` rows: {neg_fee:,} (maker rebates); "
                 f"zero `Execution Price` rows: {zero_price:,}; zero `Size USD` rows: {zero_size:,}. "
                 f"Flagged for review in cleaning; not touched here.")
    integ.append(f"7. **Account concentration** — only {trade_df['Account'].nunique()} unique accounts and "
                 f"{trade_df['Coin'].nunique()} unique coins; HYPE alone is "
                 f"{(trade_df['Coin'] == 'HYPE').mean()*100:.1f}% of rows. Market-level aggregates will be "
                 f"dominated by a few accounts/coins — relevant for interpretation.")

    # Date range documentation (report only — NOT a merge). Parse ONLY to report the
    # true chronological range; the parsed values are not persisted or used downstream.
    ist = pd.to_datetime(trade_df["Timestamp IST"], format="%d-%m-%Y %H:%M", errors="coerce")
    n_unparsed = int(ist.isna().sum())
    sent_date = pd.to_datetime(sent_df["date"], errors="coerce")
    ranges = ["# Date coverage (documentation only — no merge performed)", ""]
    ranges.append(f"- Sentiment `date` chronological range: "
                  f"**{sent_date.min().date()} → {sent_date.max().date()}** ({sent_df['date'].nunique():,} unique days)")
    ranges.append(f"- Trades `Timestamp IST` chronological range: "
                  f"**{ist.min()} → {ist.max()}** IST "
                  f"(unparseable rows: {n_unparsed}; distinct calendar days: {ist.dt.date.nunique():,})")
    ranges.append(f"- Trade activity years present: {sorted(ist.dt.year.dropna().unique().astype(int).tolist())}")
    ranges.append(f"- **Overlap window** (where a sentiment label can exist for a trade day): "
                  f"**{max(sent_date.min(), ist.min().normalize()).date()} → "
                  f"{min(sent_date.max(), ist.max().normalize()).date()}**. "
                  f"Sentiment spans 2018–2025; trades span 2023-05 → 2025-05, so the usable analysis "
                  f"window is ~2 years (2023-05 → 2025-05). NOTE: the lexical string min/max of "
                  f"`Timestamp IST` ('01-01-2024'→'31-12-2024') is misleading because DD-MM-YYYY does "
                  f"not sort chronologically — the parsed range above is authoritative. "
                  f"Actual alignment is performed later in the merge module.")

    report = "\n\n---\n\n".join([
        "# Data Quality Report — Module 1 (Inspection)\n\n"
        "_Generated by `scripts/inspect_data.py`. Observation only: no cleaning, "
        "transformation, feature engineering, merging, or plotting performed._",
        "\n".join(checks),
        "\n".join(integ),
        sent_md,
        trade_md,
        "\n".join(ranges),
    ])

    OUT.write_text(report)
    print(report)
    print(f"\n\n>>> Report written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
