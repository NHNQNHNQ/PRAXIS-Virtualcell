"""free-text → VirtualCellRequest JSON(DeepSeek json_mode)→ from_dict 校验 → request_parsed。
失败(LLM error / JSON / 校验)→ llm_input_failed(runtime fallback)。"""
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
    "你把用户的虚拟细胞实验描述解析成 JSON。字段:request_id, species, perturbation_type, "
    "perturbation_targets(数组), input_modality, output_modality, task_type, cell_type。"
    "约定:species 用小写英文(human/mouse/bacteria/yeast);基因敲除→perturbation_type='gene'、"
    "input_modality='scRNA'、output_modality='delta_expression'、task_type='predict_delta_expression'。"
    "无法判断的字段省略。只输出 JSON,不要解释。"
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
            # C3:补 AttributeError —— JSON 顶层非 object(如 "[1,2,3]")时 d.get 会抛,
            # 该 agent 直接处理用户自由文本是暴露面最大的一环,须优雅失败而非崩溃。
            # C4 修正 11:回填 RecursionError(五元组仍缺它;RuntimeError 子类,不在任一
            # 现有成员的继承链上)。机械枚举 7 处之一 —— 本处**可达性最弱**:agent 确被注册进
            # 生产 runtime(predict_delta_expression.py:55)、也确由 runtime.py:269 派发,
            # 但通往它的唯一方法 run_workflow_from_text **当前无生产调用点**(仅测试调用)。
            except (json.JSONDecodeError, InputValidationError, KeyError, TypeError,
                    AttributeError, RecursionError) as e:
                reason = f"llm_parse_invalid: {e}"
        bus.send(AgentMessage(message.message_id + ":llmfail", self.name, "client",
            "llm_input_failed", {"reason": reason, "text": text},
            message.timestamp, message.message_id))
