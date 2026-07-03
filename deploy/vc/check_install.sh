#!/usr/bin/env bash
# 安装自检:python 版本 + CLI 可用 + 一次 offline demo 产 report.md(无需 API key)。
set -euo pipefail
python3 -c 'import sys; assert sys.version_info >= (3, 11), "需 Python>=3.11"' && echo "[ok] python>=3.11"
praxis-vc --help >/dev/null && echo "[ok] praxis-vc CLI"
OUT="$(mktemp -d)/demo"
praxis-vc run --request examples/ahr_k562.json --mode offline --out "$OUT" >/dev/null
if [ -f "$OUT/report.md" ]; then
  echo "[ok] offline demo → report.md ($(grep -c '^## ' "$OUT/report.md") 段)"
else
  echo "[FAIL] 无 report.md"
  exit 1
fi
echo "check_install: ALL OK"
