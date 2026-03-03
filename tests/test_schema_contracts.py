from __future__ import annotations

import pandas as pd

from bdc_sched.schema.contracts import validate_dataframe


def test_validate_parsed_schema_ok():
    df = pd.DataFrame(
        [
            {
                "ticker": "ARCC",
                "accessionNo": "000000-00-000001",
                "table_index": 0,
                "row_index": 1,
                "raw_row_text": "Foo | 100 | 120",
                "cells_json": '["Foo","100","120"]',
                "numeric_count": 2,
            }
        ]
    )

    report = validate_dataframe(df, "parsed")
    assert report["status"] == "ok"
    assert report["missing_columns"] == []


def test_validate_normalized_schema_missing_confidence():
    df = pd.DataFrame(
        [
            {
                "ticker": "ARCC",
                "accessionNo": "000000-00-000001",
                "table_index": 0,
                "row_index": 1,
                "issuer_name": "Foo Co",
                "numeric_count": 2,
                "principal_estimate": 100.0,
                "cost_estimate": 110.0,
                "fair_value_estimate": 120.0,
                "is_total_row": False,
                "is_header_like": False,
            }
        ]
    )

    report = validate_dataframe(df, "normalized")
    assert report["status"] == "error"
    assert "confidence" in report["missing_columns"]
