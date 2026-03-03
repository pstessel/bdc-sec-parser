# Ticketing System (BDC SEC Parser)

This project now uses a lightweight formal ticketing workflow to improve speed, quality, and traceability.

## Why this system

After reviewing common community practices (especially GitHub’s issue/PR template guidance and structured issue-form usage), the most effective pattern is:

1. **Structured intake** (required fields)
2. **Clear acceptance criteria** (pass/fail)
3. **Evidence + reproducibility**
4. **Small scoped tickets with explicit dependencies**

Reference used:
- GitHub Docs: *Using templates to encourage useful issues and pull requests*
  - https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests

## Ticket types

Use the issue forms in `.github/ISSUE_TEMPLATE/`:

- **Bug report** (`bug_report.yml`)
  - For reproducible defects.
  - Requires reproduction steps + expected/actual + acceptance criteria.

- **Layout mapping ticket** (`layout_mapping.yml`)
  - For schedule-layout-specific extraction work.
  - Requires explicit column mapping and period semantics.

- **Task** (`task.yml`)
  - For roadmap work not tied to a single defect.

## Label taxonomy

Recommended labels:
- `type:bug`
- `type:layout`
- `type:task`
- `quality`
- `triage`
- `blocked`
- `priority:p0`, `priority:p1`, `priority:p2`

## Workflow

1. **Intake**
   - Open ticket with required fields complete.
2. **Triage**
   - Assign `priority:*`, owner, and milestone.
3. **Implement**
   - Keep PR scope aligned to one ticket.
4. **Validate**
   - Run parser/normalizer/QA checks and attach evidence.
5. **Close**
   - Only close when acceptance criteria are satisfied.

## Definition of Done (DoD)

A ticket is done only if:
- Acceptance criteria are fully checked off.
- Reproducibility artifacts are attached.
- No schema/QA regressions introduced.
- Docs/roadmap updated if behavior changed.

## BDC-specific guidance

For layout mapping tickets, always capture:
- `industry_group` sub-headers (e.g., "Software & Services")
- `business_description`
- explicit current/prior/comparative handling

This prevents silent mixing of periods and preserves context needed for analysis.
