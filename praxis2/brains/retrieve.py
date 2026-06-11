"""大脑检索 retrieve-first(总纲 §3 step 2.5)。

M5 第一版:确定性可测的关键词/词频近似(BM25-lite),不引入向量库/
重模型(个人开发环境不 over-engineering;v2 可替换本单一函数,接口不变)。
检索为空显式记录降级 bare(不静默,§3 step 2.5)。"""

import re
from dataclasses import dataclass, field
from typing import Any

# 中文需空格分隔;无空格连续汉字视为单 token(BM25-lite 第一版局限,
# v2 真向量检索可绕开,见总纲校准②——接口不变,替换本单一函数即可)
_TOKEN_RE = re.compile(r"[\w一-鿿]+")


def _tokens(s: str) -> list[str]:
    return _TOKEN_RE.findall(s.lower())


@dataclass
class RetrievalResult:
    hits: list[Any]  # BrainDoc(命中,按分降序)
    degraded_to_bare: bool
    reason: str = ""
    scores: list[float] = field(default_factory=list)


def retrieve_brain(docs: list[Any], query: str, *, top_k: int) -> RetrievalResult:
    """对领域 docs 关键词/词频打分(BM25-lite:query token 在 doc 的命中
    词频之和,doc 越短同命中分越高的轻量近似)。无命中 → degraded_to_bare。"""
    q = set(_tokens(query))
    if not docs or not q:
        return RetrievalResult(
            hits=[], degraded_to_bare=True,
            reason="检索为空:无文档或空查询 → 降级 bare(显式记录,不静默)",
        )
    scored: list[tuple[float, Any]] = []
    for d in docs:
        toks = _tokens(getattr(d, "text", ""))
        if not toks:
            continue
        tf = sum(toks.count(w) for w in q)
        if tf <= 0:
            continue
        score = tf / (1.0 + 0.001 * len(toks))  # 轻量 tf 长度衰减(非完整 BM25-b;v2 换真向量检索)
        scored.append((score, d))
    if not scored:
        return RetrievalResult(
            hits=[], degraded_to_bare=True,
            reason="检索 0 命中 → 降级 bare(不注入领域大脑,显式记录,§3 step2.5)",
        )
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    return RetrievalResult(
        hits=[d for _, d in top], degraded_to_bare=False,
        scores=[s for s, _ in top],
    )
