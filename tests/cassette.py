"""cassette 加载工具(总纲 §5②)。回放优先;录制模式留待真实 key 时实现。

PRAXIS_RECORD=1 且配置了真实上游时,后续里程碑可在此实现「打真实 API 并落盘」;
M0 只提供确定性回放,避免 CI 依赖活 LLM。"""

import os
from pathlib import Path

CASSETTES = Path(__file__).parent / "cassettes"


def load(name: str) -> str:
    if os.environ.get("PRAXIS_RECORD") == "1":
        raise NotImplementedError(
            "录制模式在后续里程碑实现;M0 仅回放。请勿在 CI 设 PRAXIS_RECORD。"
        )
    return (CASSETTES / name).read_text()
