from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from pandas.api import types as pdt

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

# Logical type checks for required columns.
# These guard against silent schema drift where columns exist but carry unexpected types.
SCHEMA_TYPES: dict[str, dict[str, str]] = {
    "parsed": {
        "ticker": "string",
        "accessionNo": "string",
        "table_index": "int",
        "row_index": "int",
        "raw_row_text": "string",
        "cells_json": "string",
        "numeric_count": "int",
    },
    "normalized": {
        "ticker": "string",
        "accessionNo": "string",
        "table_index": "int",
        "row_index": "int",
        "issuer_name": "string",
        "numeric_count": "int",
        "principal_estimate": "number",
        "cost_estimate": "number",
        "fair_value_estimate": "number",
        "is_total_row": "bool",
        "is_header_like": "bool",
        "confidence": "number",
    },
}


def _column_matches_type(series: pd.Series, expected: str) -> bool:
    if expected == "string":
        return pdt.is_string_dtype(series.dtype) or pdt.is_object_dtype(series.dtype)
    if expected == "int":
        return pdt.is_integer_dtype(series.dtype)
    if expected == "number":
        return pdt.is_numeric_dtype(series.dtype)
    if expected == "bool":
        return pdt.is_bool_dtype(series.dtype)
    return False


def validate_dataframe(df: pd.DataFrame, kind: str) -> dict[str, Any]:
    if kind not in SCHEMAS:
        return {
            "status": "error",
            "error": f"unknown schema kind: {kind}",
            "kind": kind,
            "rows": int(len(df)),
            "missing_columns": [],
            "type_mismatches": {},
        }

    required = SCHEMAS[kind]
    missing = [c for c in required if c not in df.columns]

    type_mismatches: dict[str, dict[str, str]] = {}
    if not missing:
        expected_types = SCHEMA_TYPES.get(kind, {})
        for col, expected in expected_types.items():
            if col not in df.columns:
                continue
            if not _column_matches_type(df[col], expected):
                type_mismatches[col] = {
                    "expected": expected,
                    "actual": str(df[col].dtype),
                }

    return {
        "status": "ok" if not missing and not type_mismatches else "error",
        "kind": kind,
        "rows": int(len(df)),
        "missing_columns": missing,
        "type_mismatches": type_mismatches,
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
            "type_mismatches": {},
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
            "type_mismatches": {},
        }

    report = validate_dataframe(df, kind)
    report["path"] = str(p)
    return report
