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
- `qa`:
  - JSON report: `out/parsed/qa_report.json`
  - summary printed: empty-row %, numeric-zero %, duplicate key count, flagged filings
- `normalize`:
  - normalized CSV: `out/normalized/investments.csv`
  - optional parquet: `out/normalized/investments.parquet`
  - defaults: `--min-confidence 0.4 --drop-headers`
  - pipe-delimited cell artifacts are split/cleaned into normalized cell arrays
  - emits `layout_id`, `period_focus`, `has_pipe_artifacts`, `clean_row_text`
- `validate`:
  - schema check for parsed/normalized outputs
  - optional JSON output report via `--out`
- `profile-layouts`:
  - layout summary CSV: `out/normalized/layout_profile.csv`
  - groups by `ticker/form/layout_id/period_focus` with row counts and confidence stats

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
