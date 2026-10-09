"""Inject retrieved evidence, shared rules, skill summaries, and memory into prompts."""

from typing import Any

from praxis2.core.prompt import SYSTEM_PROMPT_DYNAMIC_BOUNDARY, Section


def _join_docs(docs: list[Any]) -> str:
    return "\n\n".join(
        f"### {getattr(d, 'kind', '?')}/{getattr(d, 'stem', '?')}\n"
        f"{getattr(d, 'text', '')}"
        for d in docs
    )


def assemble_agent_sections(
    selection: Any,
    *,
    retrieval: Any,
    common_docs: list[Any],
    skill_summary: str,
    memory_text: str,
) -> list[Section]:

    secs: list[Section] = []


    secs.append(Section(
        "current_turn_focus",
        (
            '# Current turn priority\nAnswer the latest user i'
            'ntent. Treat unrelated messages as new topics; c'
            'ontinue earlier work when explicitly requested.'
        ),
    ))

    if common_docs:
        secs.append(Section(
            "brain_common_rules",
            "# Shared rules (_common, RMCP and safety)\n"
            + _join_docs(common_docs),
        ))

    if not getattr(retrieval, "degraded_to_bare", True) and retrieval.hits:
        secs.append(Section(
            "brain_domain_hits",
            "# Retrieved domain evidence\n"
            + _join_docs(retrieval.hits),
        ))
    else:

        secs.append(Section(
            "retrieval_degraded",
            (
                '# Retrieval fallback\nNo domain evidence was retr'
                'ieved; use bare mode with shared rules only. Rea'
                'son:'
                f"{getattr(retrieval, 'reason', '')}"
            ),
        ))
    if skill_summary.strip():
        secs.append(Section(
            "skill_disclosure",
            "# Available skills\n" + skill_summary,
        ))
    if memory_text.strip():
        secs.append(Section(
            "memory_index",
            "# Merged MEMORY.md index\n" + memory_text,
        ))

    secs.append(Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""))
    return secs
