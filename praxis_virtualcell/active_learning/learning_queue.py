"""Serializable advisory queue of proposed next experiments, without LLM or bus dependencies. Sort by descending
information_gain and retain insertion order for ties. Empty candidates produce empty items and a note;
predictions, verdicts, and provenance remain unchanged.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class LearningQueueItem:
    candidate: str
    module: str
    information_gain: float
    drivers: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LearningQueue:
    items: list[LearningQueueItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:

        self.items = sorted(self.items, key=lambda it: it.information_gain, reverse=True)

    def to_dict(self) -> dict:
        return {"items": [it.to_dict() for it in self.items], "notes": list(self.notes)}
