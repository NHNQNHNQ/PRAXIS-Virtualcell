"""只汇总 success 结果(rejected/failed 不进 ensemble)。Coordinator 仅通讯+汇总。
另算 model disagreement(pairwise cosine distance,§8.3),供 ReliabilityAgent 降级/abstain。"""
from __future__ import annotations

import itertools
import json
import math

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.adapter_sdk import (
    DEFAULT_ADAPTER_REGISTRY,
    AdapterOutputEnvelope,
    AdapterRegistry,
)


def _disagreement(vecs: list) -> dict:
    """多 predictor delta 向量的分歧度:mean pairwise (1-cos)/2 ∈ [0,1](0=同向, 0.5=正交, 1=反向)。
    cosine 尺度不变(只看方向),阈值跨 bench 稳定。零向量对记中性 0.5 且单列 n_zero_vector_pairs 便于审计
    (避免如 MockLinear 恒零产生的伪分歧被误读为真方向冲突)。注:1 维 delta 下只能检符号翻转,幅度分歧不可见。"""
    k = len(vecs)
    if k < 2:
        return {"score": None, "metric": "pairwise_cosine_distance", "n_models": k,
                "reason": "no_models" if k == 0 else "single_model"}
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
            cos = max(-1.0, min(1.0, sum(x * y for x, y in zip(va, vb)) / (na * nb)))  # noqa: B905
            pairs.append((1.0 - cos) / 2.0)
    return {"score": sum(pairs) / len(pairs), "metric": "pairwise_cosine_distance",
            "n_models": k, "n_pairs": len(pairs), "dims": length, "n_zero_vector_pairs": n_zero}


def _flat_values(values) -> list[float]:
    return [item for value in values for item in (
        _flat_values(value) if isinstance(value, (list, tuple)) else [value]
    )]


class EnsembleCoordinatorAgent(BaseAgent):
    name = "EnsembleCoordinator"

    def __init__(self, *, adapter_registry: AdapterRegistry | None = None) -> None:
        self._adapter_registry = (
            DEFAULT_ADAPTER_REGISTRY
            if adapter_registry is None
            else adapter_registry
        )

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        results = message.payload["results"]
        ok = [r for r in results if r["status"] == "success"]
        used = [r["agent_name"] for r in ok]
        rejected = [r["agent_name"] for r in results if r["status"] != "success"]  # 含 failed,保 test 断言
        failed = [r["agent_name"] for r in results if r["status"] == "failed"]
        ensemble = None
        adapter_output = None
        strict = [
            (r, (r.get("provenance") or {}).get("adapter_output"))
            for r in ok
            if (r.get("provenance") or {}).get("adapter_output") is not None
        ]
        if not strict:
            vecs = [r["prediction"]["delta"] for r in ok if r.get("prediction")]
            if vecs:
                n = max((len(v) for v in vecs), default=0)
                ensemble = {"delta": [sum(v[i] for v in vecs) / len(vecs) for i in range(n)]} if n else None
                if ensemble is not None and len(vecs) == 1:
                    prediction = next(r["prediction"] for r in ok if r.get("prediction"))
                    for key in (
                        "baseline",
                        "feature_ids_sha256",
                        "n_features",
                        "value_type",
                        "unseen_train_targets",
                    ):
                        if key in prediction:
                            ensemble[key] = prediction[key]
        else:
            vecs = []
            try:
                if len(strict) != len(ok):
                    raise ValueError("mixed legacy and adapter outputs")
                envelopes = tuple(
                    AdapterOutputEnvelope.model_validate_json(
                        json.dumps(raw, sort_keys=True, allow_nan=False)
                    )
                    for _, raw in strict
                )
                fingerprints = {
                    envelope.provenance.adapter_fingerprint for envelope in envelopes
                }
                if len(fingerprints) != 1:
                    raise ValueError("adapter output fingerprints differ")
                adapter = self._adapter_registry.resolve_fingerprint(fingerprints.pop())
                envelopes = tuple(
                    adapter.validate_envelope(envelope) for envelope in envelopes
                )
                combined = adapter.validate_envelope(adapter.aggregate(envelopes))
                ensemble = adapter.validate_projection(adapter.project_output(combined))
                adapter_output = combined.to_dict()
                vecs = [_flat_values(envelope.values) for envelope in envelopes]
            except Exception:  # noqa: BLE001 — adapter boundary is fail-closed and fault-isolated
                used = []
                rejected = list(dict.fromkeys([*rejected, *(r["agent_name"] for r in ok)]))
        disagreement = _disagreement(vecs) if vecs else {
            "score": None, "metric": "pairwise_cosine_distance", "n_models": 0, "reason": "no_models"}
        # per-predictor caution(如机制模型 disposition=caution/abstain 的 caution_flags)表面化,
        # 不参与裁决(ensemble 不在红线上),只为 provenance 如实透传。
        model_cautions = {r["agent_name"]: r["uncertainty"]["caution_flags"]
                          for r in results
                          if (r.get("uncertainty") or {}).get("caution_flags")}
        payload = {**message.payload, "models_used": used, "models_rejected": rejected,
                   "models_failed": failed, "ensemble": ensemble, "disagreement": disagreement,
                   "model_cautions": model_cautions}
        if adapter_output is not None:
            payload["adapter_output"] = adapter_output
        bus.send(AgentMessage(message.message_id + ":ens", self.name, "Reliability",
            "ensemble_done", payload, message.timestamp, message.message_id))
