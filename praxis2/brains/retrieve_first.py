

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


        if get_phase(state) is not Phase.RETRIEVE:
            advance_phase(state, Phase.RETRIEVE)
    secs = assemble_agent_sections(
        selection, retrieval=r, common_docs=common_docs,
        skill_summary=skill_summary, memory_text=memory_text,
    )
    return RetrieveFirstResult(
        sections=secs, degraded_to_bare=r.degraded_to_bare, reason=r.reason,
    )
