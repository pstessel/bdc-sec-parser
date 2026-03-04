# Accuracy Playbook (Programmatic + Manual)

This document is the single source of truth for proving extraction quality.

## Purpose

1. Provide a repeatable test process we can run ourselves.
2. Provide a handoff package for an independent frontier model to validate results.
3. Track both automated and manual validation steps for audit + marketing evidence.

## Current status snapshot

- Pipeline stages: fetch → download → parse → qa → normalize → validate
- Regression tests: parser edge-cases (merged headers, sparse numeric rows, footnotes)
- Schema validation: required columns + strict type checks
- Run metadata: `run_id`, `generated_at`, `parser_version`
- Run manifests:
  - `out/parsed/parse_run_manifest.json`
  - `out/normalized/normalize_run_manifest.json`

---

## A) Programmatic validation checklist (must pass)

Run from repo root:

```bash
python -m pytest -q
bdc-sched validate --kind parsed --input out/parsed/all_rows.csv
bdc-sched validate --kind normalized --input out/normalized/investments.csv
```

Or use the one-shot evidence runner (auto-writes logs + summary markdown):

```bash
chmod +x scripts/run_accuracy_evidence.sh
./scripts/run_accuracy_evidence.sh
```

Expected:
- tests all green
- validate returns `schema ok`
- no `missing_columns`
- no `type_mismatches`

### Artifact capture

Save these files per run:
- parse manifest JSON
- normalize manifest JSON
- parsed/normalized validate reports (`--out` JSON)
- QA report JSON
- git commit SHA

---

## B) Manual validation checklist (human review)

For each sampled filing:

1. Open source filing HTML and parsed output side-by-side.
2. Verify at least 10 sampled rows across table sections.
3. Confirm:
   - issuer name matches source row
   - principal/cost/fair value are not shifted columns
   - totals/header rows flagged correctly
   - period semantics (current/prior/comparative) preserved
   - business_description and industry_group (if present) are not cross-row contaminated
4. Record pass/fail notes in a review log.

---

## C) Independent frontier-model testing handoff

## Goal
Provide a neutral second-opinion run that reproduces scoring without relying on this session.

### One-command handoff packaging

```bash
chmod +x scripts/package_independent_handoff.sh
./scripts/package_independent_handoff.sh
```

This creates:
- `reports/accuracy/handoff_<timestamp>_<sha>/`
- `reports/accuracy/handoff_<timestamp>_<sha>.zip`

with the latest evidence logs/artifacts, manifests, QA report, playbook, and a ready-to-use handoff prompt.

### Handoff package contents

- Repo URL + commit SHA
- Command list to run pipeline and tests
- Gold set reference files (once BDC-011 lands)
- Scoring script + expected metric schema
- A fixed output folder for generated evidence

### Suggested handoff prompt (template)

```text
You are an independent auditor for BDC extraction quality.

Given this repository at commit <SHA>, run the full verification workflow:
1) Install environment
2) Run test suite
3) Run schema/type validation on parsed + normalized outputs
4) Run benchmark scoring against gold set
5) Produce an audit report with:
   - pass/fail by gate
   - per-field metrics
   - observed failure modes
   - reproducibility commands used

Do not change business logic; only evaluate and report.
```

---

## D) Evidence log format (for marketing + audit)

Store a structured log per run, e.g. `reports/accuracy/evidence_<date>.md`:

- Date/time (UTC)
- commit SHA
- dataset scope (issuers/filings)
- test results
- schema validation results
- benchmark scores
- manual review summary
- known limitations

This gives a verifiable narrative: “what we tested, how, and what passed.”

---

## E) Known limitation (current)

Current tests prove stability and schema integrity, not universal per-field correctness across all BDC layouts. Multi-issuer benchmark ticket: **BDC-011**.
