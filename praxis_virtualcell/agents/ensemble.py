"""只汇总 success 结果(rejected/failed 不进 ensemble)。Coordinator 仅通讯+汇总。
另算 model disagreement(pairwise cosine distance,§8.3),供 ReliabilityAgent 降级/abstain。"""
from __future__ import annotations

import itertools
import math

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _disagreement(vecs: list) -> dict:
    """多 predictor delta 向量的分歧度:mean pairwise (1-cos)/2 ∈ [0,1](0=同向, 0.5=正交, 1=反向)。
    cosine 尺度不变(只看方向),阈值跨 bench 稳定。零向量对记中性 0.5 且单列 n_zero_vector_pairs 便于审计
    (避免如 MockLinear 恒零产生的伪分歧被误读为真方向冲突)。注:1 维 delta 下只能检符号翻转,幅度分歧不可见。"""
    k = len(vecs)
    if k < 2:
        return {"score": None, "metric": "pairwise_cosine_distance", "n_models": k, "reason": "single_model"}
    length = min(len(v) for v in vecs)
    pairs, n_zero = [], 0
    for a, b in itertools.combinations(vecs, 2):
        va, vb = a[:length], b[:length]
        na = math.sqrt(sum(x * x for x in va))
        nb = math.sqrt(sum(y * y for y in vb))
        if na == 0.0 or nb == 0.0:
            pairs.append(0.5)
            n_zero += 1
        else:
            cos = max(-1.0, min(1.0, sum(x * y for x, y in zip(va, vb)) / (na * nb)))
            pairs.append((1.0 - cos) / 2.0)
    return {"score": sum(pairs) / len(pairs), "metric": "pairwise_cosine_distance",
            "n_models": k, "n_pairs": len(pairs), "dims": length, "n_zero_vector_pairs": n_zero}


class EnsembleCoordinatorAgent(BaseAgent):
    name = "EnsembleCoordinator"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        results = message.payload["results"]
        ok = [r for r in results if r["status"] == "success"]
        used = [r["agent_name"] for r in ok]
        rejected = [r["agent_name"] for r in results if r["status"] != "success"]  # 含 failed,保 test 断言
        failed = [r["agent_name"] for r in results if r["status"] == "failed"]
        ensemble = None
        vecs = [r["prediction"]["delta"] for r in ok if r.get("prediction")]
        if vecs:
            n = max((len(v) for v in vecs), default=0)
            ensemble = {"delta": [sum(v[i] for v in vecs) / len(vecs) for i in range(n)]} if n else None
        disagreement = _disagreement(vecs) if vecs else {
            "score": None, "metric": "pairwise_cosine_distance", "n_models": 0, "reason": "no_models"}
        bus.send(AgentMessage(message.message_id + ":ens", self.name, "Reliability",
            "ensemble_done", {**message.payload, "models_used": used, "models_rejected": rejected,
            "models_failed": failed, "ensemble": ensemble, "disagreement": disagreement},
            message.timestamp, message.message_id))
