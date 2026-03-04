# bdc-sec-parser

Pipeline to download SEC BDC filings (10-Q/10-K) and parse **Consolidated Schedule(s) of Investments** tables.

## Quickstart

1. Create virtualenv and install:
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -e .`
2. Copy `.env.example` to `.env` and set `SEC_USER_AGENT`.
3. Universe defaults to starter BDCs in `configs/universe.yml`:
   - ARCC, OCSL, MAIN

## Full run (default-safe)

```bash
bdc-sched fetch --years 5 --forms 10-Q,10-K --include-amendments
bdc-sched download
bdc-sched parse
bdc-sched qa
bdc-sched normalize
bdc-sched validate --kind parsed --input out/parsed/all_rows.csv
bdc-sched validate --kind normalized --input out/normalized/investments.csv
```

### What each command writes

- `fetch` → `out/manifests/*_recent.json`
  - Filters by filing date (`--years`, default `5`)
  - Includes amendments by default (`--include-amendments`, disable with `--no-include-amendments`)
- `download` → `out/raw_filings/<ticker>/<accession>.html`
- `parse`:
  - per filing CSV: `out/parsed/<ticker>/<accession>.csv`
  - consolidated CSV: `out/parsed/all_rows.csv`
  - optional parquet: `out/parsed/all_rows.parquet` (auto-skipped if parquet engine missing)
  - run manifest JSON: `out/parsed/parse_run_manifest.json`
  - adds run metadata columns to every row: `run_id`, `generated_at`, `parser_version`
- `qa`:
  - JSON report: `out/parsed/qa_report.json`
  - summary printed: empty-row %, numeric-zero %, duplicate key count, flagged filings
- `normalize`:
  - normalized CSV: `out/normalized/investments.csv`
  - optional parquet: `out/normalized/investments.parquet`
  - run manifest JSON: `out/normalized/normalize_run_manifest.json`
  - defaults: `--min-confidence 0.4 --drop-headers`
  - pipe-delimited cell artifacts are split/cleaned into normalized cell arrays
  - emits `layout_id`, `period_focus`, `has_pipe_artifacts`, `clean_row_text`
  - adds run metadata columns to every row: `run_id`, `generated_at`, `parser_version`
- `validate`:
  - schema check for parsed/normalized outputs
  - enforces both required columns and strict logical types
  - optional JSON output report via `--out`
  - failure output includes `missing_columns` and `type_mismatches`
- `profile-layouts`:
  - layout summary CSV: `out/normalized/layout_profile.csv`
  - groups by `ticker/form/layout_id/period_focus` with row counts and confidence stats

## Validation and run metadata quick examples

```bash
# Validate parsed output
bdc-sched validate --kind parsed --input out/parsed/all_rows.csv

# Validate normalized output and write machine-readable report
bdc-sched validate --kind normalized --input out/normalized/investments.csv --out out/normalized/schema_report.json
```

`validate` returns a summary with:
- `missing_columns`: required columns not found
- `type_mismatches`: columns present but wrong dtype (example: string in an int/bool field)

Run manifests:
- `out/parsed/parse_run_manifest.json`
- `out/normalized/normalize_run_manifest.json`

Each manifest includes `run_id`, `generated_at`, `parser_version`, plus input/output paths and row counts.

## Project management

- Ticketing workflow: `docs/TICKETING.md`
- Issue forms: `.github/ISSUE_TEMPLATE/`

## Parser notes

- Heading match: `Consolidated Schedule(s) of Investments`
- Uses nearby table(s) after heading as candidates
- Stores best-effort parsed rows with:
  - source metadata (`ticker,cik,accessionNo,filingDate,form,source_file`)
  - raw row text and normalized cell JSON
  - parsed numeric helper fields (`numeric_*`, `first_numeric`, `last_numeric`)
- Bad filings are logged and skipped without crashing the run.
