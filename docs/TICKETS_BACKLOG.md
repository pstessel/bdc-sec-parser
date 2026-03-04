# BDC Ticket Backlog (Initial Batch)

Status legend: `todo | in-progress | blocked | done`

## BDC-001 — ARCC 10-Q primary layout mapping (cost/fair value/rate/maturity)
- **Type:** layout
- **Priority:** p0
- **Status:** todo
- **Scope:** Implement layout rule for dominant ARCC 10-Q unknown bucket and map canonical fields.
- **Acceptance criteria:**
  - [ ] `issuer_name`, `business_description`, `cost_estimate`, `fair_value_estimate`, `rate_spread_pik`, `maturity_date` extracted for mapped rows
  - [ ] Unknown rows reduced for ARCC 10-Q segment by measurable amount
  - [ ] Regression fixture added

## BDC-002 — ARCC 10-K primary layout mapping
- **Type:** layout
- **Priority:** p0
- **Status:** todo
- **Scope:** Add ARCC 10-K variant mapping (annual structure differs from quarterly rows).
- **Acceptance criteria:**
  - [ ] Canonical field mapping works on representative accessions
  - [ ] Unknown rows reduced for ARCC 10-K
  - [ ] No degradation in existing mapped layouts

## BDC-003 — MAIN 10-Q primary layout mapping
- **Type:** layout
- **Priority:** p0
- **Status:** todo
- **Scope:** Map MAIN quarterly layout and parse embedded investment text fields.
- **Acceptance criteria:**
  - [ ] `issuer_name`, `business_description`, `instrument_text`, `rate_spread_pik`, `cost`, `fair_value` captured
  - [ ] Unknown rows reduced for MAIN 10-Q
  - [ ] Added fixture + validation evidence

## BDC-004 — MAIN 10-K primary layout mapping
- **Type:** layout
- **Priority:** p1
- **Status:** todo
- **Scope:** Add MAIN annual layout rule and test against top unknown annual bucket.
- **Acceptance criteria:**
  - [ ] Stable mapping across at least 2 representative filings
  - [ ] Unknown annual rows reduced
  - [ ] QA report does not regress

## BDC-005 — OCSL layout family (10-Q/10-K)
- **Type:** layout
- **Priority:** p1
- **Status:** todo
- **Scope:** Add rules for OCSL quarterly and annual layout families.
- **Acceptance criteria:**
  - [ ] 10-Q and 10-K layouts mapped separately
  - [ ] Period semantics retained (`current/prior/comparative`)
  - [ ] Unknown OCSL rows reduced

## BDC-006 — Capture sector sub-headers as `industry_group`
- **Type:** task
- **Priority:** p0
- **Status:** todo
- **Scope:** Promote rows like “Software & Services” from header context into normalized `industry_group` field for following holdings until next group boundary.
- **Acceptance criteria:**
  - [ ] New normalized field `industry_group`
  - [ ] Propagation logic validated on ARCC sample filing
  - [ ] No contamination across group boundaries

## BDC-007 — Capture `business_description` as first-class normalized field
- **Type:** task
- **Priority:** p0
- **Status:** todo
- **Scope:** Extract and store business description column when present.
- **Acceptance criteria:**
  - [ ] New normalized field `business_description`
  - [ ] Populated for mapped layouts where description column exists
  - [ ] Empty only where truly unavailable

## BDC-008 — Comparative-period guardrails
- **Type:** bug
- **Priority:** p0
- **Status:** todo
- **Scope:** Prevent current/prior comparative values from being mixed in primary valuation columns.
- **Acceptance criteria:**
  - [ ] Period-aware mapping support added
  - [ ] `period_focus` and comparative flags preserved
  - [ ] Tests confirm no silent current/prior mixing

## BDC-009 — Unknown-layout diagnostics v2
- **Type:** task
- **Priority:** p1
- **Status:** in-progress
- **Scope:** Improve unknown-layout hint generation with richer signatures and top sample extraction.
- **Acceptance criteria:**
  - [ ] Diagnostic output includes representative header rows
  - [ ] Includes column-count + token signature
  - [ ] Supports direct ticket creation input
  - [ ] Mapping worksheet includes stable table-identification fields (`source_file`, `table_index`, `table_signature`, `table_preview`)
  - [ ] Add `page_number` when detectable from source
  - [ ] Table order ambiguity documented and reduced for human labeling workflows

## BDC-010 — Quality gate dashboard for layout progress
- **Type:** task
- **Priority:** p1
- **Status:** todo
- **Scope:** Add simple report that tracks `sched_unknown` over time by ticker/form.
- **Acceptance criteria:**
  - [ ] Snapshot report written each run
  - [ ] Includes total rows, unknown rows, unknown % by ticker/form
  - [ ] PM update can reference trend automatically

## BDC-011 — Multi-issuer accuracy benchmark (gold set + scorecard)
- **Type:** task
- **Priority:** p0
- **Status:** todo
- **Scope:** Create a ground-truth benchmark across multiple BDC issuers and filings to measure numeric extraction accuracy explicitly (not just schema validity).
- **Definition (plain English):**
  - Build a labeled "answer key" dataset (gold set), run parser output against it, and report exact hit/miss rates per field.
- **Milestone shape (phase 1):**
  - 5 issuers × 2 filings each (mix of 10-Q / 10-K) as initial benchmark cohort
  - Label core fields: `issuer_name`, `principal_estimate`, `cost_estimate`, `fair_value_estimate`, `business_description`, `industry_group`, `period_focus`
- **Acceptance criteria:**
  - [ ] Gold-set folder committed with labeling guide + labeled reference CSV/JSON
  - [ ] Scoring script implemented (`precision/recall` for categorical fields, numeric match/error metrics for amounts)
  - [ ] Output scorecard generated with per-field metrics and overall pass/fail thresholds
  - [ ] CI/test hook fails when benchmark falls below thresholds
  - [ ] README updated with how to run and interpret benchmark
  - [ ] Initial baseline report attached (so future changes can be compared)

## BDC-012 — Terminology cleanup: replace “heuristics” with “rule-based extraction” in user-facing docs
- **Type:** task
- **Priority:** p2
- **Status:** todo
- **Scope:** Update user-facing wording to avoid implying guesswork where deterministic rules are used.
- **Acceptance criteria:**
  - [ ] README and docs replace ambiguous wording where appropriate
  - [ ] One short section explains limits clearly: deterministic rules + measured benchmark accuracy

## BDC-013 — Expand benchmark + extraction coverage for investment/instrument fields
- **Type:** task
- **Priority:** p0
- **Status:** todo
- **Scope:** Capture and score investment-type text fields (for example ARCC `Investment` values like “First Lien Senior Secured Loan”) so subscriber-facing reports include richer instrument detail with measured accuracy.
- **Why:** Current phase-1 benchmark scores 7 core fields but does not yet quantify instrument/investment text quality.
- **Acceptance criteria:**
  - [ ] Normalized output includes first-class `instrument_text` field (or equivalent canonical field) where available
  - [ ] Benchmark gold schema extended with `instrument_text` and scoring logic added
  - [ ] Baseline score reported for `instrument_text` (exact + normalized text match policy documented)
  - [ ] Optional normalized derivatives defined and tested (`lien_rank`, `security_type`, `secured_flag`)
  - [ ] At least 3 issuers validated for instrument/investment extraction quality
  - [ ] Reporting docs updated to show how this field is used in subscriber outputs
