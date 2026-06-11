"""BrainQueryTool:模型可调用的"在本学科 brain 里检索"工具(v0.16.0 P0)。

回归:此前 chat_registry 只挂 AgentTool + SkillExec,system prompt 列出 13 学科
brain 的 case/rule/skill 名字,但没工具能"查"——模型只能纯文字回答(幻觉)。

本工具包装 brains/retrieve.py:retrieve_brain + brains/migrate.py:migrate_dir_tree。
不依赖 store / DB,直接读文件系统 brains/<slug>/。检索类工具不受相位门约束
(rmcp_op=None);否则 INIT 相位永远调不了 BrainQuery → 死锁。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis2.brains.migrate import DISCIPLINE_SLUGS, build_fixture_brain, migrate_dir_tree
from praxis2.brains.retrieve import retrieve_brain
from praxis2.tools.base import Tool, ToolResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BRAINS_ROOT_DEFAULT = _REPO_ROOT / "brains"

# excerpt 截断阈值:既要让模型读到关键证据,又要防止单次检索把 tool_result 撑爆
# (SerialToolRunner.TOOL_RESULT_MAX_CHARS = 20000,假设 top_k=5 → 单条 < 4000)
_EXCERPT_MAX_CHARS = 800


def _excerpt(text: str, max_chars: int = _EXCERPT_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n…[截断:原 {len(text)} 字符]"


class BrainQueryTool(Tool):
    """在指定学科 brain 里检索相关案例 / 规则 / 技能 / 反例。

    返回结构:{brain, query, hits: [{slug, kind, stem, excerpt, score}],
              degraded_to_bare, reason, total_docs}。
    """

    name = "BrainQuery"
    description = (
        "在指定学科 brain(cell/crispr/cryo/dock/drug/enzyme/immuno/md/"
        "microbiome/omics/pharma/protein/synth)里检索相关案例 / 规则 / 技能 / "
        "反例。返回命中文档的 stem + 摘录;0 命中显式 degraded_to_bare=True。"
        "kinds 可过滤 ['cases','rules','skills','neg_cases']。"
    )
    rmcp_op = None  # 检索类工具不受相位门(否则 INIT 永远调不了 → 死锁)
    # GAP-AH-1:本工具最近一次是否真命中(非 fixture/空/降级)。仅在 run() 返回 ok=True
    # 后有效;早退路径(缺参/未知 brain,ok=False)不重写本标记 → 消费方须先看 result.is_error/ok
    # 再读(post_hook advance_phase_on_real_retrieval 已先做 is_error 短路,故陈旧值不会被误读)。
    last_retrieval_real_hit = False

    def __init__(self, brains_root: Path | None = None) -> None:
        self._root = Path(brains_root) if brains_root else _BRAINS_ROOT_DEFAULT

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "brain": {
                    "type": "string",
                    "description": (
                        "学科 slug(小写),如 enzyme/dock/cell/crispr/cryo/"
                        "drug/immuno/md/microbiome/omics/pharma/protein/synth"
                    ),
                },
                "query": {
                    "type": "string",
                    "description": "检索关键词(中英文混合 OK,BM25-lite 关键词命中)",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回 top-k 条(默认 5,上限 20)",
                    "default": 5,
                },
                "kinds": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["cases", "rules", "skills", "neg_cases"],
                    },
                    "description": "(可选)限定 kinds,默认全部四类一起检索",
                },
            },
            "required": ["brain", "query"],
        }

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        brain = (payload.get("brain") or "").strip().lower()
        query = (payload.get("query") or "").strip()
        top_k = int(payload.get("top_k") or 5)
        top_k = max(1, min(top_k, 20))  # cap 1..20 防爆
        kinds_filter = payload.get("kinds")

        if not brain:
            return ToolResult(
                ok=False,
                error="缺 brain 参数(必填,例: enzyme)",
                recovery_hint=f"可选 brain:{', '.join(DISCIPLINE_SLUGS)}",
            )
        if not query:
            return ToolResult(
                ok=False,
                error="缺 query 参数(必填,例: 'Stiffler 2015 β-lactamase')",
            )

        brain_dir = self._root / brain
        if not brain_dir.is_dir():
            # fallback 1:_common 是 13 学科外的特殊 slug;允许检索
            # fallback 2:fixture brain(测试场景:用户传了合法 slug 但本地无文件)
            if brain in DISCIPLINE_SLUGS or brain == "_common":
                docs = build_fixture_brain(brain)
                source = "fixture"
            else:
                return ToolResult(
                    ok=False,
                    error=(
                        f"未知 brain '{brain}'。可选:{', '.join(DISCIPLINE_SLUGS)}"
                        f"(brains_root={self._root})"
                    ),
                )
        else:
            docs = migrate_dir_tree(brain_dir, brain)
            source = "filesystem"
            if not docs:
                # 真盘存在但 migrate 抽不到 → fallback fixture(保 tool_use 不空 return)
                docs = build_fixture_brain(brain)
                source = "fixture(empty real)"

        if kinds_filter:
            allowed = set(kinds_filter)
            docs = [d for d in docs if d.kind in allowed]

        result = retrieve_brain(docs, query, top_k=top_k)
        # v0.16.3:scores 与 hits 必须等长。retrieve_brain 降级(degraded_to_bare)
        # 时 hits=[] scores=[];命中时两者同长。若上游 bug 导致长度不一致,
        # 显式补齐到 hits 长度(score 缺失补 0.0),不再 silent 丢弃 hits
        # (strict=False 会丢多余 hit → 模型收到不完整检索结果)。
        hits = result.hits
        scores = result.scores or []
        if len(scores) < len(hits):
            scores = list(scores) + [0.0] * (len(hits) - len(scores))
        hits_view = [
            {
                "slug": d.slug,
                "kind": d.kind,
                "stem": d.stem,
                "excerpt": _excerpt(d.text),
                "score": round(float(s), 3),
            }
            for d, s in zip(hits, scores, strict=True)
        ]

        self.last_retrieval_real_hit = (
            source == "filesystem"
            and not result.degraded_to_bare
            and bool(hits_view)
        )
        return ToolResult(
            ok=True,
            value={
                "brain": brain,
                "query": query,
                "top_k": top_k,
                "hits": hits_view,
                "degraded_to_bare": result.degraded_to_bare,
                "reason": result.reason,
                "total_docs": len(docs),
                "source": source,
            },
        )
