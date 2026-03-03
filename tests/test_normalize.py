import pandas as pd

from bdc_sched.normalize.investments import normalize_rows_to_investments


def test_normalize_basic():
    df = pd.DataFrame(
        [
            {
                "ticker": "ARCC",
                "cik": "0001287750",
                "accessionNo": "a1",
                "filingDate": "2025-01-01",
                "form": "10-Q",
                "source_file": "x",
                "table_index": 0,
                "row_index": 1,
                "raw_row_text": "ABC Corp (a) | 1,000 | 900 | 950",
                "cells_json": '["ABC Corp (a)","1,000","900","950"]',
                "numeric_count": 3,
                "numeric_1": 1000,
                "numeric_2": 900,
                "numeric_3": 950,
            }
        ]
    )

    out = normalize_rows_to_investments(df)
    assert len(out) == 1
    assert out.iloc[0]["issuer_name"] == "ABC Corp (a)"
    assert float(out.iloc[0]["fair_value_estimate"]) == 950.0
    assert out.iloc[0]["footnote_refs"] == "a"
