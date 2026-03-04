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
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only-reviewed", action="store_true", default=False)
    args = ap.parse_args()

    w = pd.read_csv(args.work, low_memory=False)
    if args.only_reviewed and "review_status" in w.columns:
        w = w[w["review_status"].str.lower() == "done"]

    out_df = pd.DataFrame()
    for k in KEYS:
        out_df[k] = w[k]
    for f in FIELDS:
        g = f"gold_{f}"
        if g in w.columns:
            out_df[f] = w[g]

    out_df = out_df.drop_duplicates(subset=KEYS, keep="last")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out, index=False)
    print(f"wrote {len(out_df)} rows -> {out}")


if __name__ == "__main__":
    main()
