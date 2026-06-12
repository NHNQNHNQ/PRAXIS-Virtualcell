"""五种 agent 模式解析(总纲 §7.5.0)。产「要检索注入的大脑集」喂 §3 step2.5。
所有模式共用同一 query()/build_effective_system_prompt 路径,区别仅在
注入哪些大脑(§7.5.0 末句:不产生第二条代码路径)。

路由打分:确定性词频(与 brains/retrieve 同口径,不引入重模型)。
one-above-all 路由依据写 transcript(§12 可观测)。"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from praxis2.brains.migrate import DISCIPLINE_SLUGS

_ONE_ABOVE_ALL_MAX_TURNS = 5  # §7.5.4 路由器 max_turns 上限
_TOKEN_RE = re.compile(r"[\w一-鿿]+")

# 学科关键词表(忠实 v1 §4.3 学科语义的最小确定性打分表;真实 agent
# 关键词/case 标题在运维灌入 brains 后可扩,M5 用最小可测表)。
# 值须全小写且为单 token(与 _tokens().lower() 同口径;含空格的多词短语
# 经 _tokens 分词后永不命中,故拆为单 token,如 force/forcefield)。
# B.3 校准:key lowercase 对齐 DISCIPLINE_SLUGS(真盘 namespace brain:<lower>);
# v2.0.2:Synth carry → 13(真盘 _brains/synth/ 已落地 + rsync 到 brains/synth/)。
_SLUG_KEYWORDS: dict[str, set[str]] = {
    "virtualcell": {"虚拟细胞", "virtualcell", "扰动", "perturbation", "敲除",
                    "转录组", "scrna", "生长", "必需基因", "essentiality",
                    "跨物种", "abstain", "norman", "replogle"},
}


class AgentMode(StrEnum):
    DISCIPLINE = "discipline"
    GENERAL = "general"
    ONE_ABOVE_ALL = "one-above-all"
    YOURSELF = "yourself"
    BARE = "bare"


@dataclass
class AgentSelection:
    mode: AgentMode
    brain_slugs: list[str]          # 要检索注入的大脑集(含 _common,除非 S13 裸跑)
    is_discipline: bool = False     # §7.5.4 → disallowed_tools:[AgentTool]
    readonly: bool = False          # yourself 合成视图不写回 brains
    max_turns: int | None = None    # one-above-all 路由器 max_turns≤5
    route_reason: str = ""
    scores: dict[str, int] = field(default_factory=dict)


def _tokens(s: str) -> list[str]:
    return _TOKEN_RE.findall(s.lower())


def _score_slugs(query: str) -> dict[str, int]:
    # 同分时下游 max()/sorted() 取 _SLUG_KEYWORDS 定义序首个(CPython dict
    # 插入序确定,与 §12 可复盘一致)
    toks = _tokens(query)
    out: dict[str, int] = {}
    for slug, kws in _SLUG_KEYWORDS.items():
        sc = sum(1 for t in toks if t in kws)
        if sc > 0:
            out[slug] = sc
    return out


def resolve_agent(
    spec: str,
    *,
    user_query: str,
    transcript_sink: Callable[[dict], None] | None = None,
) -> AgentSelection:
    # B.3:spec 入口大小写标准化(兼容历史 TitleCase 调用如 "Cryo"),
    # 内部统一 lowercase 以对齐真盘 namespace brain:<lower>;
    # 5 种保留模式(general/bare/one-above-all/yourself)同样大小写无关。
    spec_norm = (spec or "").strip().lower()
    if spec_norm in DISCIPLINE_SLUGS:
        return AgentSelection(
            mode=AgentMode.DISCIPLINE,
            brain_slugs=["_common", spec_norm], is_discipline=True,
        )
    if spec_norm == "general":
        return AgentSelection(
            mode=AgentMode.GENERAL, brain_slugs=["_common", "general"],
        )
    if spec_norm == "bare":
        # S13:bare 仍保留 _common(完全裸跑须显式开关且记审计,非本 spec)
        return AgentSelection(mode=AgentMode.BARE, brain_slugs=["_common"])
    if spec_norm == "one-above-all":
        scores = _score_slugs(user_query)
        if scores:
            chosen = max(scores, key=lambda k: scores[k])
            slugs = ["_common", chosen]
            fallback = False
        else:
            chosen = "general"
            slugs = ["_common", "general"]
            fallback = True
        if transcript_sink is not None:  # §12 路由依据可观测
            transcript_sink({
                "type": "agent_route", "chosen": chosen,
                "fallback": fallback, "score": scores.get(chosen, 0),
                "all_scores": scores,
            })
        return AgentSelection(
            mode=AgentMode.ONE_ABOVE_ALL, brain_slugs=slugs,
            is_discipline=(not fallback and chosen in DISCIPLINE_SLUGS),
            max_turns=_ONE_ABOVE_ALL_MAX_TURNS,
            route_reason=("fallback→general" if fallback else f"route→{chosen}"),
            scores=scores,
        )
    if spec_norm == "yourself":
        scores = _score_slugs(user_query)
        picked = sorted(scores, key=lambda k: scores[k], reverse=True)
        slugs = ["_common", *picked] if picked else ["_common", "general"]
        return AgentSelection(
            mode=AgentMode.YOURSELF, brain_slugs=slugs,
            readonly=True,  # 合成只读视图,不写回 brains(沉淀走 §7.4.2 审核)
            scores=scores,
        )
    raise ValueError(
        f"未知 agent 选择 {spec!r}(须为 12 学科 slug / general / "
        f"one-above-all / yourself / bare,§7.5.0 + B.3 校准)"
    )
