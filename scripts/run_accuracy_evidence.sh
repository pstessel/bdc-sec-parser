#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

mkdir -p reports/accuracy

STAMP_FILE="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
ISO_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUT_MD="reports/accuracy/evidence_${STAMP_FILE}.md"
OUT_DIR="reports/accuracy/evidence_${STAMP_FILE}"
mkdir -p "$OUT_DIR"

SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
PYVER="$(python -V 2>&1 || echo unknown)"
HOST="$(hostname 2>/dev/null || echo unknown-host)"

PYTEST_LOG="$OUT_DIR/pytest.txt"
VALIDATE_PARSED_JSON="$OUT_DIR/validate_parsed.json"
VALIDATE_NORM_JSON="$OUT_DIR/validate_normalized.json"
QA_COPY_JSON="$OUT_DIR/qa_report.json"

PARSED_CSV="out/parsed/all_rows.csv"
NORM_CSV="out/normalized/investments.csv"
QA_JSON="out/parsed/qa_report.json"
PARSE_MANIFEST="out/parsed/parse_run_manifest.json"
NORM_MANIFEST="out/normalized/normalize_run_manifest.json"

# 1) Run pytest
set +e
python -m pytest -q > "$PYTEST_LOG" 2>&1
PYTEST_RC=$?
set -e

# 2) Validate parsed (if present)
if [[ -f "$PARSED_CSV" ]]; then
  bdc-sched validate --kind parsed --input "$PARSED_CSV" --out "$VALIDATE_PARSED_JSON" > "$OUT_DIR/validate_parsed.txt" 2>&1 || true
else
  cat > "$VALIDATE_PARSED_JSON" <<'JSON'
{"status":"error","error":"parsed csv not found"}
JSON
fi

# 3) Validate normalized (if present)
if [[ -f "$NORM_CSV" ]]; then
  bdc-sched validate --kind normalized --input "$NORM_CSV" --out "$VALIDATE_NORM_JSON" > "$OUT_DIR/validate_normalized.txt" 2>&1 || true
else
  cat > "$VALIDATE_NORM_JSON" <<'JSON'
{"status":"error","error":"normalized csv not found"}
JSON
fi

# 4) Copy QA report if present
if [[ -f "$QA_JSON" ]]; then
  cp "$QA_JSON" "$QA_COPY_JSON"
else
  cat > "$QA_COPY_JSON" <<'JSON'
{"status":"error","error":"qa report not found"}
JSON
fi

export ISO_TS SHA HOST PYVER OUT_MD OUT_DIR PYTEST_LOG VALIDATE_PARSED_JSON VALIDATE_NORM_JSON QA_COPY_JSON PARSE_MANIFEST NORM_MANIFEST PYTEST_RC

python - <<'PY'
import json
import os
from pathlib import Path

out_md = Path(os.environ["OUT_MD"])
out_dir = os.environ["OUT_DIR"]
pytest_log = Path(os.environ["PYTEST_LOG"])
parsed = json.loads(Path(os.environ["VALIDATE_PARSED_JSON"]).read_text())
norm = json.loads(Path(os.environ["VALIDATE_NORM_JSON"]).read_text())
qa = json.loads(Path(os.environ["QA_COPY_JSON"]).read_text())
parse_manifest = os.environ["PARSE_MANIFEST"]
norm_manifest = os.environ["NORM_MANIFEST"]
pytest_rc = int(os.environ["PYTEST_RC"])

pytest_text = pytest_log.read_text(errors="ignore").strip().splitlines()
pytest_summary = pytest_text[-1] if pytest_text else "no pytest output"

qa_summary = qa.get("summary", {}) if isinstance(qa, dict) else {}

lines = []
lines.append("# Accuracy Evidence Log")
lines.append("")
lines.append(f"- **Run timestamp (UTC):** {os.environ['ISO_TS']}")
lines.append(f"- **Git commit SHA:** {os.environ['SHA']}")
lines.append("- **Operator:** OpenClaw assistant (automated)")
lines.append(f"- **Environment:** {os.environ['HOST']}, {os.environ['PYVER']}")
lines.append("")
lines.append("## Scope")
lines.append("- **Issuers:** from current out/manifests and outputs")
lines.append("- **Filings:** from current output artifacts")
lines.append("- **Pipeline commands run:**")
lines.append("  1. `python -m pytest -q`")
lines.append("  2. `bdc-sched validate --kind parsed --input out/parsed/all_rows.csv --out <path>`")
lines.append("  3. `bdc-sched validate --kind normalized --input out/normalized/investments.csv --out <path>`")
lines.append("")
lines.append("## Programmatic Gates")
lines.append(f"- **Pytest:** {'pass' if pytest_rc == 0 else 'fail'} ({pytest_summary})")
lines.append(f"- **Parsed schema validation:** {parsed.get('status', 'error')}")
lines.append(f"  - missing_columns: {parsed.get('missing_columns', [])}")
lines.append(f"  - type_mismatches: {parsed.get('type_mismatches', {})}")
lines.append(f"- **Normalized schema validation:** {norm.get('status', 'error')}")
lines.append(f"  - missing_columns: {norm.get('missing_columns', [])}")
lines.append(f"  - type_mismatches: {norm.get('type_mismatches', {})}")
lines.append("- **QA summary:**")
lines.append(f"  - rows: {qa_summary.get('total_rows', 'n/a')}")
lines.append(f"  - filings: {qa_summary.get('total_filings', 'n/a')}")
lines.append(f"  - empty_raw_pct: {qa_summary.get('empty_raw_pct', 'n/a')}")
lines.append(f"  - numeric_count_zero_pct: {qa_summary.get('numeric_count_zero_pct', 'n/a')}")
lines.append(f"  - duplicate_key_rows: {qa_summary.get('duplicate_key_rows', 'n/a')}")
lines.append(f"  - flagged_filings: {qa_summary.get('flagged_filings', 'n/a')}")
lines.append("")
lines.append("## Run Artifacts")
lines.append(f"- **Parse run manifest:** {parse_manifest if Path(parse_manifest).exists() else 'missing'}")
lines.append(f"- **Normalize run manifest:** {norm_manifest if Path(norm_manifest).exists() else 'missing'}")
lines.append(f"- **Parsed validate report:** {os.environ['VALIDATE_PARSED_JSON']}")
lines.append(f"- **Normalized validate report:** {os.environ['VALIDATE_NORM_JSON']}")
lines.append(f"- **QA report copy:** {os.environ['QA_COPY_JSON']}")
lines.append(f"- **Raw logs folder:** {out_dir}")
lines.append("")
lines.append("## Manual Review (sampled rows)")
lines.append("- **Status:** pending (manual protocol in docs/ACCURACY_PLAYBOOK.md)")
lines.append("")
lines.append("## Independent Verification Handoff")
lines.append("- **Status:** pending")
lines.append("- **Suggested input bundle:** repo SHA + this evidence folder + manifests + validate reports")
lines.append("")
lines.append("## Known Limitations / Risks")
lines.append("- Automated checks confirm structure and test stability, not full cross-issuer numeric truth.")
lines.append("")
lines.append("## Go/No-Go Summary")
if pytest_rc == 0 and parsed.get("status") == "ok" and norm.get("status") == "ok":
    lines.append("- **Result:** GO (programmatic gates passed)")
else:
    lines.append("- **Result:** NO-GO (one or more programmatic gates failed)")

out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Created evidence log: {out_md}")
PY

echo "Artifacts directory: $OUT_DIR"
