#!/usr/bin/env bash
# Check Python, CLI availability, and one offline report without an API key.
set -euo pipefail
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python >=3.11 is required"' && echo "[ok] python>=3.11"
praxis-vc --help >/dev/null && echo "[ok] praxis-vc CLI"
OUT="$(mktemp -d)/demo"
praxis-vc run --request examples/ahr_k562.json --mode offline --out "$OUT" >/dev/null
if [ -f "$OUT/report.md" ]; then
  echo "[ok] offline demo → report.md ($(grep -c '^## ' "$OUT/report.md") sections)"
else
  echo "[FAIL] report.md was not produced"
  exit 1
fi
echo "check_install: ALL OK"
