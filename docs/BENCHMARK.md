# Benchmarking Accuracy (BDC-011 Phase 1)

This benchmark measures extraction quality against a labeled gold set.

## Files

- Gold set template: `benchmarks/gold_set_phase1_template.csv`
- Scoring script: `scripts/score_gold_set.py`
- Output report (generated): `reports/accuracy/benchmark_<timestamp>.json`

## Phase 1 scope

Start small and concrete:
- 5 issuers × 2 filings each
- Label these fields:
  - `issuer_name`
  - `principal_estimate`
  - `cost_estimate`
  - `fair_value_estimate`
  - `business_description`
  - `industry_group`
  - `period_focus`

## Gold set requirements

Each row must include primary keys:
- `ticker`
- `accessionNo`
- `table_index`
- `row_index`

And expected values for the fields above.

## Run scoring

```bash
python scripts/score_gold_set.py \
  --pred out/normalized/investments.csv \
  --gold benchmarks/gold_set_phase1_template.csv \
  --out reports/accuracy/benchmark_phase1.json
```

## What the report contains

- row-level match counts (`matched_rows`, `missing_in_pred`, `extra_in_pred`)
- per-field metrics:
  - numeric: MAE, exact-match rate (within tolerance)
  - categorical/text: exact-match rate (case-insensitive)

## Notes

- This is phase-1 baseline scoring.
- Use results to prioritize mapping work by worst fields and issuers.
