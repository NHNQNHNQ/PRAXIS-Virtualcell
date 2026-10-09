"""Assemble stable agent instructions, task prompts, and dynamic context."""

import hashlib
from dataclasses import dataclass

from praxis2.core.state import State

SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "\x00__PRAXIS2_DYNAMIC_BOUNDARY__\x00"


@dataclass
class Section:
    name: str
    text: str
    cache_break: bool = False


def get_default_system_prompt() -> list[Section]:

    return [
        Section("identity", "You are the kernel assistant of the PRAXIS VirtualCell agent framework."),
        Section("safety", "Retrieve scientific evidence before execution. Do not invent DOI citations or sources."),
        Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
    ]


def build_effective_system_prompt(
    *,
    override: list[Section] | None = None,
    coordinator: list[Section] | None = None,
    agent: list[Section] | None = None,
    custom: list[Section] | None = None,
    default: list[Section] | None = None,
    append: list[Section] | None = None,
) -> list[Section]:
    """Combine stable instructions with task-specific prompts and retrieved context."""
    if override is not None:
        base = override
    elif coordinator is not None:
        base = coordinator
    elif agent is not None:
        base = agent
    elif custom is not None:
        base = custom
    elif default is not None:
        base = default
    else:
        base = get_default_system_prompt()
    return [*base, *(append or [])]


class SectionCache:
    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def render(self, section: Section) -> str:
        if section.cache_break:
            return section.text
        if section.name not in self._cache:
            self._cache[section.name] = section.text
        return self._cache[section.name]

    def invalidate(self) -> None:
        self._cache.clear()


def to_api_system(sections: list[Section]) -> list[dict]:

    static_parts: list[str] = []
    dynamic_parts: list[str] = []
    seen_boundary = False
    for s in sections:
        if s.name == SYSTEM_PROMPT_DYNAMIC_BOUNDARY:
            seen_boundary = True
            continue
        if not s.text:
            continue
        (dynamic_parts if seen_boundary else static_parts).append(s.text)
    blocks: list[dict] = []
    if static_parts:
        blocks.append(
            {
                "type": "text",
                "text": "\n\n".join(static_parts),
                "cache_control": {"type": "ephemeral"},
            }
        )
    if dynamic_parts:
        blocks.append({"type": "text", "text": "\n\n".join(dynamic_parts)})
    return blocks


def get_user_context(
    *,
    claude_md: str | None = None,
    agents_md: str | None = None,
    today: str | None = None,
) -> str | None:

    parts: list[str] = []
    if today:
        parts.append(f"Current date:{today}")
    if claude_md:
        parts.append(f"<project-instructions>\n{claude_md}\n</project-instructions>")
    if agents_md:
        parts.append(f"<agents-md>\n{agents_md}\n</agents-md>")
    return "\n\n".join(parts) if parts else None


def prepend_user_context(messages: list[dict], user_context: str | None) -> list[dict]:

    if not user_context:
        return list(messages)
    return [{"role": "user", "content": user_context}, *messages]


def get_system_context(*, git_status: str | None = None, cache_breaker: str | None = None) -> str | None:

    parts: list[str] = []
    if git_status:
        parts.append(f"<git-status>\n{git_status}\n</git-status>")
    if cache_breaker:
        parts.append(f"<cache-breaker>{cache_breaker}</cache-breaker>")
    return "\n\n".join(parts) if parts else None


def append_system_context(sections: list[Section], system_context: str | None) -> list[Section]:

    if not system_context:
        return list(sections)
    return [*sections, Section("system_context", system_context, cache_break=True)]


SPECIALIZED_PROMPTS: dict[str, str] = {
    "compact": "Compact the conversation while preserving key facts and unresolved tasks. Return only the summary.",
    "memory-extract": "Extract durable facts. Return only a structured fact list.",
    "memory-update": (
        "Maintain the MEMORY index. Return only updated index lines with filenames and one-line descriptions."
    ),
    "route": "Select an agent. Return only its identifier.",
}


def get_specialized_prompt(name: str) -> str:

    return SPECIALIZED_PROMPTS[name]


def section_hash(sections: list[Section]) -> str:

    h = hashlib.sha256()
    for s in sections:
        h.update(s.name.encode())
        h.update(b"\x1f")
        h.update(s.text.encode())
        h.update(b"\x1e")
    return h.hexdigest()


def render_and_persist(state: State, sections: list[Section]) -> list[dict]:

    api_system = to_api_system(sections)
    state.tool_use_context["rendered_system_prompt"] = api_system
    state.tool_use_context["system_prompt_hash"] = section_hash(sections)
    return api_system
