#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

STAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
BUNDLE_DIR="reports/accuracy/handoff_${STAMP}_${SHA}"
mkdir -p "$BUNDLE_DIR"

# Pick newest evidence markdown and evidence artifact folder if they exist.
LATEST_EVIDENCE_MD="$(ls -1t reports/accuracy/evidence_*.md 2>/dev/null | head -n1 || true)"
LATEST_EVIDENCE_DIR="$(ls -1dt reports/accuracy/evidence_* 2>/dev/null | grep -v '\.md$' | head -n1 || true)"

# Core files (copy if present).
copy_if_exists () {
  local src="$1"
  local dst="$2"
  if [[ -e "$src" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp -R "$src" "$dst"
  fi
}

copy_if_exists "docs/ACCURACY_PLAYBOOK.md" "$BUNDLE_DIR/docs/ACCURACY_PLAYBOOK.md"
copy_if_exists "out/parsed/parse_run_manifest.json" "$BUNDLE_DIR/out/parsed/parse_run_manifest.json"
copy_if_exists "out/normalized/normalize_run_manifest.json" "$BUNDLE_DIR/out/normalized/normalize_run_manifest.json"
copy_if_exists "out/parsed/qa_report.json" "$BUNDLE_DIR/out/parsed/qa_report.json"

if [[ -n "$LATEST_EVIDENCE_MD" ]]; then
  copy_if_exists "$LATEST_EVIDENCE_MD" "$BUNDLE_DIR/reports/accuracy/$(basename "$LATEST_EVIDENCE_MD")"
fi
if [[ -n "$LATEST_EVIDENCE_DIR" ]]; then
  copy_if_exists "$LATEST_EVIDENCE_DIR" "$BUNDLE_DIR/reports/accuracy/$(basename "$LATEST_EVIDENCE_DIR")"
fi

# Copy gold-set/benchmark assets if present (future-proof for BDC-011).
copy_if_exists "benchmarks" "$BUNDLE_DIR/benchmarks"
copy_if_exists "gold_set" "$BUNDLE_DIR/gold_set"

cat > "$BUNDLE_DIR/HANDOFF_PROMPT.txt" <<'TXT'
You are an independent auditor for BDC extraction quality.

Given this repository state and evidence bundle:
1) Verify reproducibility commands and environment assumptions.
2) Re-run programmatic gates (tests + schema/type validation) where possible.
3) Validate run-manifest consistency (run_id/generated_at/parser_version propagation).
4) If benchmark assets are present, run benchmark scoring and report per-field metrics.
5) Produce an audit report with:
   - pass/fail by gate
   - per-field metrics (when benchmark present)
   - observed failure modes
   - reproducibility commands used
   - confidence level and limitations

Do not modify business logic. Evaluate and report only.
TXT

cat > "$BUNDLE_DIR/MANIFEST.json" <<JSON
{
  "created_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "repo": "bdc-sec-parser",
  "git_sha": "$SHA",
  "bundle_dir": "$BUNDLE_DIR",
  "included": {
    "accuracy_playbook": $( [[ -f docs/ACCURACY_PLAYBOOK.md ]] && echo true || echo false ),
    "parse_run_manifest": $( [[ -f out/parsed/parse_run_manifest.json ]] && echo true || echo false ),
    "normalize_run_manifest": $( [[ -f out/normalized/normalize_run_manifest.json ]] && echo true || echo false ),
    "qa_report": $( [[ -f out/parsed/qa_report.json ]] && echo true || echo false ),
    "latest_evidence_markdown": $( [[ -n "$LATEST_EVIDENCE_MD" ]] && echo true || echo false ),
    "latest_evidence_artifacts": $( [[ -n "$LATEST_EVIDENCE_DIR" ]] && echo true || echo false ),
    "benchmarks_dir": $( [[ -d benchmarks ]] && echo true || echo false ),
    "gold_set_dir": $( [[ -d gold_set ]] && echo true || echo false )
  }
}
JSON

# Create zip for easy handoff
ZIP_PATH="${BUNDLE_DIR}.zip"
( cd "$(dirname "$BUNDLE_DIR")" && zip -qr "$(basename "$ZIP_PATH")" "$(basename "$BUNDLE_DIR")" )

echo "Bundle directory: $BUNDLE_DIR"
echo "Bundle zip: $ZIP_PATH"
echo "Included latest evidence markdown: ${LATEST_EVIDENCE_MD:-none}"
echo "Included latest evidence artifacts dir: ${LATEST_EVIDENCE_DIR:-none}"
