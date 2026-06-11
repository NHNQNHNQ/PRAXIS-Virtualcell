"""prompt 可观测(总纲 §7.2.8 / §12.4):--dump-prompts JSONL + /context 分段统计。
调试 prompt drift 必备。消费 core/prompt.py 产物,不参与组装(职责分离)。"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from praxis2.core.prompt import Section
from praxis2.llm.usage import estimate_tokens


def make_jsonl_recorder(path: str) -> Callable[[dict], None]:
    """§7.2.8 --dump-prompts 底座:返回 on_request(record) 回调,把每次 API 请求的
    完整 prompt 追加为一行 JSON(可逐行 diff 比对定位 drift)。字面 argv 标志在
    entry/cli.py 建成时(M6)绑定到本回调 + 配置项 dump_prompts。
    非并发安全:M6 多 worker 接入时须改为进程级锁或每 worker 独立文件。"""
    p = Path(path)

    def _record(record: dict) -> None:
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return _record


@dataclass
class ContextSegment:
    name: str
    tokens: int


def analyze_context(sections: list[Section]) -> list[ContextSegment]:
    """§7.2.8 /context 底座:把 effective system prompt 按 section 拆成命名段,
    逐段估 token(复用 llm.estimate_tokens 同一口径保持一致)。空 text 段跳过。
    注:每段独立包成单条 message 估算,绝对值含固定包裹开销(~8 tok/段),
    各段一致可比,用于相对占比展示;如需精确绝对值改为整体一次估算。"""
    out: list[ContextSegment] = []
    for s in sections:
        if not s.text:
            continue
        tokens, _ = estimate_tokens([{"role": "system", "content": s.text}], None, None)
        out.append(ContextSegment(name=s.name, tokens=tokens))
    return out
