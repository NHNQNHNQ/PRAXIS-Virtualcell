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
