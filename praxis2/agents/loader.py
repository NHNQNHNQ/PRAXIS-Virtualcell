"""Resolve agent modes and select brain documents with deterministic keyword routing."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from praxis2.brains.migrate import DISCIPLINE_SLUGS

_ONE_ABOVE_ALL_MAX_TURNS = 5
_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")


_SLUG_KEYWORDS: dict[str, set[str]] = {
    "virtualcell": {
        "virtualcell",
        "perturbation",
        "knockout",
        "transcriptome",
        "scrna",
        "growth",
        "essentiality",
        "cross-species",
        "abstain",
        "norman",
        "replogle",
    },
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
    brain_slugs: list[str]
    is_discipline: bool = False  # §7.5.4 → disallowed_tools:[AgentTool]
    readonly: bool = False
    max_turns: int | None = None
    route_reason: str = ""
    scores: dict[str, int] = field(default_factory=dict)


def _tokens(s: str) -> list[str]:
    return _TOKEN_RE.findall(s.lower())


def _score_slugs(query: str) -> dict[str, int]:

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

    spec_norm = (spec or "").strip().lower()
    if spec_norm in DISCIPLINE_SLUGS:
        return AgentSelection(
            mode=AgentMode.DISCIPLINE,
            brain_slugs=["_common", spec_norm],
            is_discipline=True,
        )
    if spec_norm == "general":
        return AgentSelection(
            mode=AgentMode.GENERAL,
            brain_slugs=["_common", "general"],
        )
    if spec_norm == "bare":
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
        if transcript_sink is not None:
            transcript_sink(
                {
                    "type": "agent_route",
                    "chosen": chosen,
                    "fallback": fallback,
                    "score": scores.get(chosen, 0),
                    "all_scores": scores,
                }
            )
        return AgentSelection(
            mode=AgentMode.ONE_ABOVE_ALL,
            brain_slugs=slugs,
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
            mode=AgentMode.YOURSELF,
            brain_slugs=slugs,
            readonly=True,
            scores=scores,
        )
    raise ValueError(
        f"Unknown agent selection {spec!r}(choose virtualcell / general / one-above-all / yourself / bare)"
    )
