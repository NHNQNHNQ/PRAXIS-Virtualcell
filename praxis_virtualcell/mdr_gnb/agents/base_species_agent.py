"""物种 agent 基类:经 bus 收 mdr_task → 检索 brain(retrieve-before-predict)→ 发
brain_retrieved(带 rules_referenced provenance)。时间戳/ID 一律经注入的 Clock/IdGen,
保证 trace 确定性 replay。子类只需声明 species 与 brain 目录名。"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.mdr_gnb.agents.brain_loader import load_species_brain


class BaseSpeciesAgent(BaseAgent):
    species: str = ""            # 子类必填,如 "escherichia_coli"
    receiver_next: str = "PredictorHub"

    def __init__(
        self,
        *,
        brain_root: Path,
        clock: Clock,
        idgen: IdGen,
        brain: Mapping[str, Any] | None = None,
        brain_available: bool | None = None,
        rules_referenced: list[str] | None = None,
    ) -> None:
        self.brain_root = Path(brain_root)
        self.clock = clock
        self.idgen = idgen
        # Production requests inject the execution-scoped, parsed brain here.
        # Keeping the fallback preserves the small agent's direct unit-test and
        # legacy use, while avoiding a second filesystem read on the API path.
        self._captured_brain = deepcopy(dict(brain)) if brain is not None else None
        self._brain_available = brain_available
        self._rules_referenced = list(rules_referenced) if rules_referenced else None

    def _brain_dir(self) -> Path:
        return self.brain_root / self.species / "brain"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload["request"]
        brain = (deepcopy(self._captured_brain)
                 if self._captured_brain is not None
                 else load_species_brain(self._brain_dir()))
        rel = f"praxis_virtualcell/mdr_gnb/agents/{self.species}/brain/rules.yaml"
        supported = (self._brain_available if self._brain_available is not None
                     else self._brain_dir().is_dir())
        brain_context = {
            "species": self.species,
            "species_supported": supported,
            "rules": brain["rules"],
            "resistance_mechanisms": brain["resistance_mechanisms"],
            "negative_cases": brain["negative_cases"],
            "assay_boundaries": brain["assay_boundaries"],
            "species_specific_breakpoints": brain["species_specific_breakpoints"],
            "rules_referenced": (
                list(self._rules_referenced)
                if self._rules_referenced is not None
                else ([rel] if supported else [])
            ),
        }
        bus.send(AgentMessage(
            message_id=self.idgen.next(),
            sender=self.name, receiver=self.receiver_next,
            message_type="brain_retrieved",
            payload={"request": req, "brain_context": brain_context},
            timestamp=self.clock.now(),
            parent_message_id=message.message_id,
        ))
