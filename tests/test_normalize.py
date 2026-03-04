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
                "row_index": 0,
                "raw_row_text": "Portfolio Company | Business Description | Type of Investment | Amortized Cost | Fair Value",
                "cells_json": '["Portfolio Company","Business Description","Type of Investment","Amortized Cost","Fair Value"]',
                "numeric_count": 0,
            },
            {
                "ticker": "ARCC",
                "cik": "0001287750",
                "accessionNo": "a1",
                "filingDate": "2025-01-01",
                "form": "10-Q",
                "source_file": "x",
                "table_index": 0,
                "row_index": 1,
                "raw_row_text": "ABC Corp (a) | Software Company | First Lien Senior Secured Loan | 900 | 950",
                "cells_json": '["ABC Corp (a)","Software Company","First Lien Senior Secured Loan","900","950"]',
                "numeric_count": 2,
                "numeric_1": 900,
                "numeric_2": 950,
            },
        ]
    )

    out = normalize_rows_to_investments(df)
    row = out[out["row_index"] == 1].iloc[0]
    assert row["issuer_name"] == "ABC Corp (a)"
    assert float(row["fair_value_estimate"]) == 950.0
    assert row["footnote_refs"] == "a"
    assert row["instrument_text"] == "First Lien Senior Secured Loan"
