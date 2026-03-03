# BDC SEC Parser Roadmap (PM/Project Plan)

## Objective
Ship a reliable, auditable extraction pipeline for BDC Schedule of Investments tables.

## Current State (done)
- Fetch/download/parse pipeline implemented.
- QA and normalize commands implemented.
- Initial XML/HTML parser hardening done.

## Milestone 1 — Data Contracts & Regression Safety (in progress)
**Goal:** Prevent silent schema drift and breakage.

### Deliverables
- [x] Schema contract validation module (`parsed`, `normalized`)
- [x] CLI `validate` command
- [x] Basic regression tests for schema checks
- [ ] Expand fixtures + parser edge-case tests

### Acceptance Criteria
- `bdc-sched validate --kind parsed` fails on missing required columns.
- `bdc-sched validate --kind normalized` fails on missing required columns.
- Tests cover pass/fail scenarios.

## Milestone 2 — Extraction Quality
**Goal:** Improve field-level correctness and confidence scoring.

### Deliverables
- Gold-set of representative filings.
- Precision/recall scoring by field.
- Parser heuristics tuned from top failure modes.
- [ ] Capture sector/sub-header hierarchy (e.g., `Software & Services`) as first-class `industry_group` field.
- [ ] Capture `Business Description` as first-class normalized field (`business_description`) with layout-specific mapping rules.

## Milestone 3 — Operational Reliability
**Goal:** Make runs reproducible and observable.

### Deliverables
- Run manifest with parser version + timestamp.
- Lineage from raw filing -> parsed row -> normalized row.
- Alerting thresholds from QA report.

## Next 3 tasks (execution order)
1. Add fixture-based parser regression tests (merged headers, sparse numeric rows, footnotes).
2. Add strict type checks to validation (not just columns).
3. Add run metadata artifact (`run_id`, `generated_at`, `parser_version`) to outputs.
