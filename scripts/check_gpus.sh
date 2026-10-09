#!/usr/bin/env bash
# GPU 节点 = 提交端 (单 host) — 本机直接 nvidia-smi, 不 ssh-loop.
# 部署: scp scripts/check_gpus.sh 10.102.106.53:~/check_gpus.sh && ssh 10.102.106.53 'chmod +x ~/check_gpus.sh'
# 老 ssh-loop 版本: git log -- scripts/check_gpus.sh
set -euo pipefail
HOST=$(hostname -s)
python3 - "$HOST" <<'PY'
import json, subprocess, sys
host = sys.argv[1]
try:
    out = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"],
        text=True, timeout=10,
    )
except subprocess.SubprocessError as e:
    print(json.dumps({"total_slots": 0, "busy_slots": 0, "free_slots": 0,
                      "hosts": [host], "gpus": [],
                      "error": f"nvidia-smi failed: {e}"}))
    sys.exit(0)

gpus = []
for line in out.strip().splitlines():
    idx, name, mem_used, mem_total, util = [s.strip() for s in line.split(",")]
    busy = int(util) > 5 or int(mem_used) > 500
    gpus.append({
        "host": host, "gpu_id": int(idx), "name": name,
        "mem_mb": f"{mem_used}/{mem_total}",
        "util_pct": int(util),
        "busy": busy, "busy_label": None if not busy else "in_use",
    })
busy_n = sum(1 for g in gpus if g["busy"])
print(json.dumps({
    "total_slots": len(gpus),
    "busy_slots": busy_n,
    "free_slots": len(gpus) - busy_n,
    "hosts": [host],
    "gpus": gpus,
}))
PY
