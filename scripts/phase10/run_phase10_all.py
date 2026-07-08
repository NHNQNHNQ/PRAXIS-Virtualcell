"""Phase 10 全量测试驱动(骨架,真正实现见 P10.D)。"""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    """当前只跑 phase10 测试子集(占位)。P10.D 扩为全 T10.1-T10.7 编排 + 指标汇总。"""
    return subprocess.call(
        [sys.executable, "-m", "pytest", "praxis_virtualcell/tests/phase10", "-q"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
