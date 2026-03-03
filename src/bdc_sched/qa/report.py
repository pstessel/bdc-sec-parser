from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = [
    "ticker",
    "accessionNo",
    "table_index",
    "row_index",
    "raw_row_text",
    "numeric_count",
]


def _pct(part: int, total: int) -> float:
    return round((part / total) * 100.0, 3) if total else 0.0


def build_qa_report(df: pd.DataFrame) -> dict[str, Any]:
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        return {
            "status": "error",
            "error": f"missing required columns: {missing_cols}",
            "summary": {},
            "by_filing": [],
        }

    total_rows = int(len(df))
    empty_raw = int(df["raw_row_text"].fillna("").astype(str).str.strip().eq("").sum())
    numeric_zero = int(pd.to_numeric(df["numeric_count"], errors="coerce").fillna(0).eq(0).sum())
    duplicate_keys = int(df.duplicated(subset=["ticker", "accessionNo", "table_index", "row_index"]).sum())

    grouped = df.groupby(["ticker", "accessionNo"], dropna=False)
    by_filing: list[dict[str, Any]] = []
    for (ticker, accession), g in grouped:
        rows = int(len(g))
        empty = int(g["raw_row_text"].fillna("").astype(str).str.strip().eq("").sum())
        zero_num = int(pd.to_numeric(g["numeric_count"], errors="coerce").fillna(0).eq(0).sum())
        dup = int(g.duplicated(subset=["table_index", "row_index"]).sum())

        flags: list[str] = []
        low_rows = rows < 50
        zero_pct = _pct(zero_num, rows)

        # Avoid noisy false positives: low row count alone is common for some issuers/periods.
        # Flag only when low row count is accompanied by weak numeric signal.
        if low_rows and zero_pct > 40:
            flags.append("low_row_count_with_weak_numeric_signal")
        # Always flag extreme low-row extractions.
        if rows < 20:
            flags.append("very_low_row_count")
        if zero_pct > 70:
            flags.append("mostly_non_numeric_rows")
        if dup > 0:
            flags.append("duplicate_table_row_keys")

        by_filing.append(
            {
                "ticker": ticker,
                "accessionNo": accession,
                "rows": rows,
                "low_row_count": low_rows,
                "empty_raw_rows": empty,
                "empty_raw_pct": _pct(empty, rows),
                "numeric_count_zero_rows": zero_num,
                "numeric_count_zero_pct": zero_pct,
                "duplicate_table_row_keys": dup,
                "flags": flags,
            }
        )

    flagged = sum(1 for x in by_filing if x["flags"])

    return {
        "status": "ok",
        "summary": {
            "total_rows": total_rows,
            "total_filings": len(by_filing),
            "empty_raw_rows": empty_raw,
            "empty_raw_pct": _pct(empty_raw, total_rows),
            "numeric_count_zero_rows": numeric_zero,
            "numeric_count_zero_pct": _pct(numeric_zero, total_rows),
            "duplicate_key_rows": duplicate_keys,
            "flagged_filings": flagged,
        },
        "by_filing": by_filing,
    }


def write_qa_report(report: dict[str, Any], out_path: str | Path) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return p
