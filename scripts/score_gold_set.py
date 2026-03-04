#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

KEYS = ["ticker", "accessionNo", "table_index", "row_index"]
NUM_FIELDS = ["principal_estimate", "cost_estimate", "fair_value_estimate"]
TXT_FIELDS = ["issuer_name", "business_description", "instrument_text", "industry_group", "period_focus"]


def norm_text(v) -> str:
    if pd.isna(v):
        return ""
    return " ".join(str(v).strip().lower().split())


def score_numeric(g: pd.Series, p: pd.Series, tol: float) -> dict:
    g_num = pd.to_numeric(g, errors="coerce")
    p_num = pd.to_numeric(p, errors="coerce")
    both = g_num.notna() & p_num.notna()
    if both.sum() == 0:
        return {"pairs": 0, "mae": None, "within_tolerance_rate": None}
    diff = (g_num[both] - p_num[both]).abs()
    return {
        "pairs": int(both.sum()),
        "mae": float(diff.mean()),
        "within_tolerance_rate": float((diff <= tol).mean()),
    }


def score_text(g: pd.Series, p: pd.Series) -> dict:
    g_txt = g.map(norm_text)
    p_txt = p.map(norm_text)
    both = (g_txt != "") & (p_txt != "")
    if both.sum() == 0:
        return {"pairs": 0, "exact_rate": None}
    return {
        "pairs": int(both.sum()),
        "exact_rate": float((g_txt[both] == p_txt[both]).mean()),
    }


def main():
    ap = argparse.ArgumentParser("score_gold_set")
    ap.add_argument("--pred", required=True, help="normalized predictions csv")
    ap.add_argument("--gold", required=True, help="gold set csv")
    ap.add_argument("--out", required=True, help="output json report")
    ap.add_argument("--numeric-tol", type=float, default=1.0, help="absolute tolerance for numeric exact-rate")
    args = ap.parse_args()

    pred = pd.read_csv(args.pred)
    gold = pd.read_csv(args.gold)

    missing_pred_keys = [k for k in KEYS if k not in pred.columns]
    missing_gold_keys = [k for k in KEYS if k not in gold.columns]
    if missing_pred_keys or missing_gold_keys:
        raise SystemExit(f"Missing key columns: pred={missing_pred_keys}, gold={missing_gold_keys}")

    pred_idx = pred.set_index(KEYS, drop=False)
    gold_idx = gold.set_index(KEYS, drop=False)

    common_idx = gold_idx.index.intersection(pred_idx.index)
    gold_only = gold_idx.index.difference(pred_idx.index)
    pred_only = pred_idx.index.difference(gold_idx.index)

    g = gold_idx.loc[common_idx].copy()
    p = pred_idx.loc[common_idx].copy()

    field_scores = {}
    for f in NUM_FIELDS:
        if f in g.columns and f in p.columns:
            field_scores[f] = score_numeric(g[f], p[f], tol=args.numeric_tol)
    for f in TXT_FIELDS:
        if f in g.columns and f in p.columns:
            field_scores[f] = score_text(g[f], p[f])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {"pred": args.pred, "gold": args.gold},
        "keys": KEYS,
        "row_reconciliation": {
            "gold_rows": int(len(gold_idx)),
            "pred_rows": int(len(pred_idx)),
            "matched_rows": int(len(common_idx)),
            "missing_in_pred": int(len(gold_only)),
            "extra_in_pred": int(len(pred_only)),
        },
        "numeric_tolerance": args.numeric_tol,
        "field_scores": field_scores,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote benchmark report: {out}")


if __name__ == "__main__":
    main()
