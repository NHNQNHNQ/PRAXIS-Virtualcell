"""Parse free text into VirtualCellRequest JSON with DeepSeek json_mode, validate through from_dict, and emit
request_parsed. LLM, JSON, or validation failure emits llm_input_failed for runtime fallback.
"""
from __future__ import annotations

import json
from dataclasses import asdict

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request import VirtualCellRequest

_SYS = (

        "Parse the user's virtual cell experiment description into JSON. Fields: request_id, "
        'species, perturbation_type, perturbation_targets (array), input_modality, '
        'output_modality, task_type, cell_type. Convention: use lowercase English species '
        "names (human/mouse/bacteria/yeast); gene knockout implies perturbation_type='gene', "
        "input_modality='scRNA', output_modality='delta_expression', "
        "task_type='predict_delta_expression'.Omit fields that cannot be determined. Return "
        'only JSON, without explanation.'

)


class LLMInputInterpreterAgent(BaseAgent):
    name = "LLMInputInterpreter"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        text = message.payload["text"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS}, {"role": "user", "content": text}],
            json_mode=True)
        reason = res.get("error") or "llm_disabled"
        if res.get("content"):
            try:
                d = json.loads(res["content"])
                if not d.get("request_id"):
                    d["request_id"] = "llm-" + message.message_id
                for _k, _v in (("input_modality", "scRNA"),
                               ("output_modality", "delta_expression"),
                               ("task_type", "predict_delta_expression")):
                    if not d.get(_k):
                        d[_k] = _v
                req = VirtualCellRequest.from_dict(d)
                bus.send(AgentMessage(message.message_id + ":llmparsed", self.name,
                    "BioObjectNormalizer", "request_parsed", {"request": asdict(req)},
                    message.timestamp, message.message_id))
                return






            except (json.JSONDecodeError, InputValidationError, KeyError, TypeError,
                    AttributeError, RecursionError) as e:
                reason = f"llm_parse_invalid: {e}"
        bus.send(AgentMessage(message.message_id + ":llmfail", self.name, "client",
            "llm_input_failed", {"reason": reason, "text": text},
            message.timestamp, message.message_id))
