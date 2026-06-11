"""大脑检索 retrieve-first 端到端编排(总纲 §3 step2.5 / §7.3.7 / §5④#1)。

检索 = RMCP「retrieve 先行」:命中 → 推进 RETRIEVE 相位(复用 M3
core/rmcp.advance_phase + hooks/builtin.advance_phase_on_retrieve 体例:
已在 RETRIEVE 则跳过,守 S7 无 RETRIEVE→RETRIEVE 边)→ 后续 execute 类
被 PhaseAwarePermission 放行(§7.3.7 M3 已落地)。检索为空不推进相位
(execute 仍被拒,科学严谨不失守),显式记降级(不静默,§3 step2.5)。"""

from dataclasses import dataclass
from typing import Any

from praxis2.brains.inject import assemble_agent_sections
from praxis2.brains.retrieve import retrieve_brain
from praxis2.core.prompt import Section
from praxis2.core.rmcp import Phase, advance_phase, get_phase
from praxis2.core.state import State


@dataclass
class RetrieveFirstResult:
    sections: list[Section]
    degraded_to_bare: bool
    reason: str = ""


def retrieve_first(
    state: State,
    selection: Any,
    *,
    domain_docs: list[Any],
    common_docs: list[Any],
    user_query: str,
    skill_summary: str = "",
    memory_text: str = "",
    top_k: int = 3,
) -> RetrieveFirstResult:
    r = retrieve_brain(domain_docs, user_query, top_k=top_k)
    if not r.degraded_to_bare and r.hits:
        # S7 守卫:转移表无 RETRIEVE→RETRIEVE 边,已在 RETRIEVE 则跳过
        # (体例同 M3 hooks/builtin.advance_phase_on_retrieve)
        if get_phase(state) is not Phase.RETRIEVE:
            advance_phase(state, Phase.RETRIEVE)
    secs = assemble_agent_sections(
        selection, retrieval=r, common_docs=common_docs,
        skill_summary=skill_summary, memory_text=memory_text,
    )
    return RetrieveFirstResult(
        sections=secs, degraded_to_bare=r.degraded_to_bare, reason=r.reason,
    )
