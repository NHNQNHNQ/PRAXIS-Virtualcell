"""P1 架构契约：critic 必须审 rule-first 融合后的最终 SIR 裁决。"""

from __future__ import annotations

import hashlib
import json

from praxis_virtualcell.mdr_gnb.predictors.registry import PredictorRegistry, PredictorSpec
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query


def _registry_with_non_resistant_model_result() -> PredictorRegistry:
    registry = PredictorRegistry()

    def _predict(_context):
        return {
            "abstained": False,
            "output_kind": "sir_class",
            "sir": "S",
            "sir_prob": {"S": 0.9, "I": 0.0, "R": 0.1},
        }

    registry.register(PredictorSpec(
        name="test_sir",
        version="test",
        species=["escherichia_coli"],
        drug_class=["carbapenems"],
        output_kind="sir_class",
        artifact_path="test://sir.joblib",
        predict=_predict,
    ))
    return registry


def test_critic_receives_rule_first_final_sir_and_trace_orders_it(monkeypatch):
    """融合把 S 改为 R 后，critic 必须用 R 做不变量审计，而非融合前空字典。"""
    from praxis_virtualcell.mdr_gnb.coordinator import fusion

    def _force_rule_first_r(result, **_kwargs):
        return {
            **result,
            "sir": "R",
            "fusion": {
                "method": "test_rule_first_fusion",
                "rule_pred": "R",
                "ml_sir": result["sir"],
                "evidence_tier": "strong",
            },
        }

    monkeypatch.setattr(fusion, "fuse_sir", _force_rule_first_r)

    out = run_mdr_query({
        "species": "escherichia_coli",
        "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
        "requested_outputs": ["SIR"],
        # 空 genotype 与最终 R 结论是 critic #5 的生产反例。
        "amr_profile": {},
    }, seed_task_id="critic-final-fusion", registry=_registry_with_non_resistant_model_result())

    assert out["report"]["sir"] == "R"
    assert "genotype_conclusion_contradiction" in out["report"]["critic_violations"]

    trace_types = [message.message_type for message in out["trace"]]
    assert trace_types.index("rule_fusion_done") < trace_types.index("critic_checked")
    assert trace_types.index("critic_checked") < trace_types.index("final_decision_resolved")
    assert trace_types.index("final_decision_resolved") < trace_types.index("report_built")

    trace_by_type = {message.message_type: message for message in out["trace"]}
    assert trace_by_type["critic_checked"].payload["conclusion_sir"] == {"meropenem": "R"}
    final_decision = trace_by_type["final_decision_resolved"]
    assert final_decision.parent_message_id == trace_by_type["critic_checked"].message_id
    assert final_decision.payload == {
        "schema_version": "mdr-final-decision-v1",
        "preliminary_abstained": False,
        "preliminary_abstain_reasons": [],
        "final_abstained": False,
        "final_abstain_reasons": [],
        "final_output_kind": "sir_class",
        "final_sir": "R",
        "critic_policy_version": "mdr-critic-v2-final-fusion",
        "critic_action": "record_only",
        "critic_violations": ["genotype_conclusion_contradiction"],
        "report_sha256": hashlib.sha256(
            json.dumps(
                out["report"], sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest(),
    }
    assert trace_by_type["report_built"].parent_message_id == final_decision.message_id

    seen_message_ids: set[str] = set()
    for message in out["trace"]:
        if message.parent_message_id is not None:
            assert message.parent_message_id in seen_message_ids
        seen_message_ids.add(message.message_id)

    report_blob = json.dumps(out["report"], sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")
    assert trace_by_type["report_built"].payload["report_sha256"] == hashlib.sha256(report_blob).hexdigest()
