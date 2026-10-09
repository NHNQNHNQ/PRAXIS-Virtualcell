import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from praxis2.core.prompt import Section
from praxis2.llm.usage import estimate_tokens


def make_jsonl_recorder(path: str) -> Callable[[dict], None]:

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

    out: list[ContextSegment] = []
    for s in sections:
        if not s.text:
            continue
        tokens, _ = estimate_tokens([{"role": "system", "content": s.text}], None, None)
        out.append(ContextSegment(name=s.name, tokens=tokens))
    return out
