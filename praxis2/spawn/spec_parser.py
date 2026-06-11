"""v0.15.0:auto 模式下,从 chat 末尾 assistant 文本提取 EXECUTABLE SPEC。

设计契约见 tests/test_spawn_spec_parser.py。保守提取:
- 必须含 'EXECUTABLE SPEC' 字样(case-insensitive)
- 取最长 fenced code block 作为 spawn prompt
- 任一条件不满足 → None(调用方 push spawn_skipped)
"""
from __future__ import annotations

import re

# fenced code block:三反引号 + 可选语言标识 + 内容 + 三反引号。
# 用非贪婪 + DOTALL 让 \n 可入 . 内容。
_FENCE_RE = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)


def parse_executable_spec(text: str) -> str | None:
    """提取 EXECUTABLE SPEC 的 prompt 体。返回 None = skip spawn。"""
    if "executable spec" not in text.lower():
        return None
    blocks = _FENCE_RE.findall(text)
    if not blocks:
        return None
    # 取最长(主体代码 vs 示例 import / 元数据块)
    longest = max(blocks, key=len).strip()
    if not longest:
        return None
    return longest
