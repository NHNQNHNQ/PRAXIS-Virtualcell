"""读 brains/virtualcell/<species>/ 的 yaml,产出 brain_context(检索先行的标记)。"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage


def _load_yaml(p: Path) -> dict:
    if not p.is_file():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


class SpeciesBrainAgent(BaseAgent):
    name = "SpeciesBrain"

    def __init__(self, config: RuntimeConfig) -> None:
        self.root = Path(config.brains_root)

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload["request"]
        species = req.get("species", "")
        sp_dir = self.root / species
        supported = sp_dir.is_dir()
        brain_context = {
            "species": species,
            "species_supported": supported,
            "generic": {
                "task_schema": _load_yaml(self.root / "generic" / "task_schema.yaml"),
                "default_abstain_rules": _load_yaml(self.root / "generic" / "default_abstain_rules.yaml"),
                "negative_transfer": _load_yaml(self.root / "generic" / "general_negative_transfer.yaml"),
            },
            "model_applicability": _load_yaml(sp_dir / "model_applicability.yaml"),
            "object_vocabulary": _load_yaml(sp_dir / "object_vocabulary.yaml"),
            "rules_referenced": ([f"brains/virtualcell/{species}/model_applicability.yaml"] if supported else [])
                                + ["brains/virtualcell/generic/general_negative_transfer.yaml"],
        }
        bus.send(AgentMessage(
            message_id=message.message_id + ":brain",
            sender=self.name, receiver="ModelApplicability",
            message_type="brain_retrieved",
            payload={"request": req, "brain_context": brain_context},
            timestamp=message.timestamp, parent_message_id=message.message_id,
        ))
