#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

KEYS = ["ticker", "accessionNo", "table_index", "row_index"]
FIELDS = [
    "issuer_name",
    "principal_estimate",
    "cost_estimate",
    "fair_value_estimate",
    "business_description",
    "instrument_text",
    "industry_group",
    "period_focus",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.inp, low_memory=False)
    cols = [c for c in KEYS + FIELDS if c in df.columns]
    df = df[cols].copy()

    for f in FIELDS:
        if f in df.columns:
            df[f"pred_{f}"] = df[f]
            df[f"gold_{f}"] = df[f]  # prefill; reviewer edits mismatches
            df.drop(columns=[f], inplace=True)

    df["review_status"] = "pending"
    df["review_notes"] = ""

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
