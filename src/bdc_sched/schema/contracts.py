from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

PARSED_REQUIRED_COLUMNS = [
    "ticker",
    "accessionNo",
    "table_index",
    "row_index",
    "raw_row_text",
    "cells_json",
    "numeric_count",
]

NORMALIZED_REQUIRED_COLUMNS = [
    "ticker",
    "accessionNo",
    "table_index",
    "row_index",
    "issuer_name",
    "numeric_count",
    "principal_estimate",
    "cost_estimate",
    "fair_value_estimate",
    "is_total_row",
    "is_header_like",
    "confidence",
]


SCHEMAS: dict[str, list[str]] = {
    "parsed": PARSED_REQUIRED_COLUMNS,
    "normalized": NORMALIZED_REQUIRED_COLUMNS,
}


def validate_dataframe(df: pd.DataFrame, kind: str) -> dict[str, Any]:
    if kind not in SCHEMAS:
        return {
            "status": "error",
            "error": f"unknown schema kind: {kind}",
            "kind": kind,
            "rows": int(len(df)),
            "missing_columns": [],
        }

    required = SCHEMAS[kind]
    missing = [c for c in required if c not in df.columns]

    return {
        "status": "ok" if not missing else "error",
        "kind": kind,
        "rows": int(len(df)),
        "missing_columns": missing,
    }


def validate_csv(path: str | Path, kind: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {
            "status": "error",
            "error": f"file not found: {p}",
            "kind": kind,
            "rows": 0,
            "missing_columns": [],
        }

    try:
        df = pd.read_csv(p)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"failed reading csv: {exc}",
            "kind": kind,
            "rows": 0,
            "missing_columns": [],
        }

    report = validate_dataframe(df, kind)
    report["path"] = str(p)
    return report
