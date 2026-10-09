#!/usr/bin/env bash
# refresh_all.sh — 一键闭环:.53 装 P0 → 重采 host inventory → 拷回 Mac → 本地重跑对账。
#
# 前置:Mac → 53 ssh 免密;Mac 端 conda /python3 可用。
# 用法:
#   bash refresh_all.sh dry-run    # .53 只 dry-run 安装,但 host 采集真跑
#   bash refresh_all.sh run        # 真装真采
#
# 本脚本只读 brains/(用于本地 extract_brain_deps),修改:
#   .53:conda env(install_p0_packages)
#   Mac:_audit/host_raw.txt, host_inventory.json, brains_deps_inventory.tsv,
#         parity_matrix.tsv, parity_summary.json, green_skills.json

set -uo pipefail   # 单节失败不阻塞

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
MODE="${1:-dry-run}"
SSH_HOST="zkyd@10.102.106.53"

if [[ "$MODE" != "dry-run" && "$MODE" != "run" ]]; then
  echo "Usage: $0 {dry-run|run}" >&2
  exit 2
fi

echo "=== refresh_all · mode=$MODE · repo=$REPO ==="

# ---- 1. .53 装 P0 (gnina/dssp/mmseqs2/praxis-pharma) ----
echo
echo "--- [1/4] ssh .53 install_p0_packages.sh $MODE ---"
ssh "$SSH_HOST" "bash -s $MODE" < "$REPO/scripts/audit/install_p0_packages.sh"

# ---- 2. .53 重采 host inventory ----
echo
echo "--- [2/4] ssh .53 collect_host.sh > _audit/host_raw.txt ---"
ssh "$SSH_HOST" 'bash -s' < "$REPO/scripts/audit/collect_host.sh" > "$REPO/_audit/host_raw.txt"
ls -lh "$REPO/_audit/host_raw.txt"

# ---- 3. 本地 parse → host_inventory.json ----
echo
echo "--- [3/4] parse_host.py → host_inventory.json ---"
python3 "$REPO/scripts/audit/parse_host.py" "$REPO/_audit/host_raw.txt" "$REPO/_audit/host_inventory.json"

# ---- 4. 重跑 extract + parity + 主路径名单 ----
echo
echo "--- [4/4] extract_brain_deps + parity + green list ---"
cd "$REPO"
python3 scripts/audit/extract_brain_deps.py
python3 scripts/audit/parity.py

# 同时刷新 green_skills.json(主路径名单,system_prompt 过滤参考的真值)
python3 << 'PY'
import csv, json
from collections import defaultdict
from pathlib import Path
ROOT = Path("/Volumes/T7/clade-learn/PRAXIS-2")
status = defaultdict(lambda: {"green": 0, "red": 0})
with (ROOT / "_audit/parity_matrix.tsv").open() as f:
    r = csv.DictReader(f, delimiter="\t")
    for row in r:
        k = (row["brain"], row["skill"])
        status[k]["green" if row["gap_kind"] == "green" else "red"] += 1
ag = sorted(k for k, v in status.items() if v["red"] == 0)
by_brain = defaultdict(list)
for b, s in ag:
    by_brain[b].append(s)
(ROOT / "_audit/green_skills.json").write_text(
    json.dumps({b: sorted(s) for b, s in by_brain.items()}, indent=2, ensure_ascii=False)
)
print(f"green skills: {len(ag)} (by brain: { {b: len(s) for b, s in by_brain.items()} })")
PY

echo
echo "=== Done. ==="
echo "下一步:"
echo "  - 重启 PRAXIS-2 backend(让 build_chat_system_prompt 的 host_envs_cache 重读)"
echo "  - 或者本地 python3 -c \"from praxis2.brains import system_prompt; system_prompt._host_envs_cache=None; print(len(system_prompt._host_envs()))\""
