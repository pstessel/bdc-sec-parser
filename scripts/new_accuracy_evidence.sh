#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

STAMP_FILE="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
ISO_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUT="reports/accuracy/evidence_${STAMP_FILE}.md"
SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
PYVER="$(python -V 2>&1 || echo unknown)"
HOST="$(hostname 2>/dev/null || echo unknown-host)"

cp reports/accuracy/evidence_TEMPLATE.md "$OUT"

python - <<PY
from pathlib import Path
p = Path("$OUT")
text = p.read_text(encoding="utf-8")
text = text.replace("<YYYY-MM-DDTHH:MM:SSZ>", "$ISO_TS")
text = text.replace("<sha>", "$SHA")
text = text.replace("<host + python version>", "$HOST, $PYVER")
p.write_text(text, encoding="utf-8")
PY

echo "Created: $OUT"
echo "Next: fill placeholders, then commit evidence log if needed."
