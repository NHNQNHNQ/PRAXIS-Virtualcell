"""perturbation_predict skill runner(stdin JSON → stdout JSON)。

bootstrap 占位:真实预测逻辑随 Week 3/4 接入 Coordinator + PredictorRegistry。
契约:从 stdin 读 inputs JSON,向 stdout 写单行 result JSON。
"""
from __future__ import annotations

import json
import sys


def main() -> None:
    raw = sys.stdin.read() or "{}"
    inputs = json.loads(raw)
    result = {
        "skill_id": "perturbation_predict",
        "ok": True,
        "simulated": bool(inputs.get("simulate", False)),
        "inputs": inputs,
    }
    sys.stdout.write(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
