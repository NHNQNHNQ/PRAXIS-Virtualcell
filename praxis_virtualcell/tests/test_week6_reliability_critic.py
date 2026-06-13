"""Week 6:reliability/abstain/critic 强化(GPT §8)。

⚠ 诚实记(对抗验证 verdict 要求):disagreement / core_predictor_failed / cell_type 三机制在**当前 mock e2e 流
永不触发**(三 mock 全单 target 正常 delta → score 0.333<0.5;run_prediction 不抛异常;请求 cell_type=None)。
故本测试用**手搓 payload/results 直接驱动 agent**证明机制非纸面、可被激活;真实 e2e 激活待未来真分歧/可失败
predictor 接入。1 维 delta 下 cosine 仅检符号翻转,幅度分歧不可见(已在 _disagreement docstring 标注)。"""
from praxis_virtualcell.agents.critic import CriticAgent
from praxis_virtualcell.agents.ensemble import _disagreement
from praxis_virtualcell.agents.reliability import ReliabilityAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _result(name, status, delta=None, sigma=0.2):
    return {"agent_name": name, "status": status,
            "prediction": {"delta": delta} if status == "success" else None,
            "uncertainty": {"sigma": sigma} if status == "success" else None,
            "applicability_score": 1.0, "evidence": [], "rejection_reason": None, "provenance": {}}


# --- model disagreement (§8.3) ---

def test_disagreement_score_direction_sensitive():
    assert _disagreement([[0.5], [0.5]])["score"] == 0.0       # 同向 → 0
    assert _disagreement([[0.5], [-0.5]])["score"] == 1.0      # 反向 → 1
    assert _disagreement([[0.5]])["score"] is None             # 单模型无法算分歧


def test_disagreement_zero_vector_audited():
    d = _disagreement([[0.0], [0.5]])
    assert d["n_zero_vector_pairs"] == 1                       # 零向量伪信号可审计(MockLinear 恒零)


def _rel(payload):
    bus = MessageBus()
    ReliabilityAgent().handle(AgentMessage("m", "X", "Reliability", "assess", payload, "t"), bus)
    return bus.latest("reliability_decided").payload["reliability_decision"]


def test_disagreement_high_abstains_when_rule_present():
    rd = _rel({"request": {"perturbation_targets": ["A"]}, "models_used": ["MockCPA", "MockGEARS"],
               "ensemble": {"delta": [0.05]}, "disagreement": {"score": 0.9},
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": ["model_disagreement_too_high"]}}}})
    assert rd["abstain"] is True and "model_disagreement_too_high" in rd["reasons"]
    assert rd["model_disagreement"]["triggered"] is True


def test_disagreement_high_downgrades_when_no_abstain_rule():
    rd = _rel({"request": {"perturbation_targets": ["A"]}, "models_used": ["MockCPA", "MockGEARS"],
               "ensemble": {"delta": [0.05]}, "disagreement": {"score": 0.9},
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": []}}}})
    assert rd["abstain"] is False and rd["reliability"] == "medium"   # high→medium(分歧高但 rule 未声明 abstain)
    assert "downgrade:model_disagreement_too_high" in rd["reasons"]   # 降级理由可追溯(§8.4)


# --- core_predictor_failed (§8.2) ---

def test_core_predictor_failed_abstains():
    rd = _rel({"request": {"perturbation_targets": ["A"]}, "models_used": ["MockGEARS"],
               "ensemble": {"delta": [0.1]},
               "results": [_result("MockCPA", "failed"), _result("MockGEARS", "success", [0.1])],
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": ["core_predictor_failed"]},
                                             "core_predictors": {"core": ["MockCPA"]}}}})
    assert rd["abstain"] is True and "core_predictor_failed" in rd["reasons"]


def test_non_core_failed_does_not_abstain():
    rd = _rel({"request": {"perturbation_targets": ["A"]}, "models_used": ["MockGEARS"],
               "ensemble": {"delta": [0.1]},
               "results": [_result("MockCPA", "failed"), _result("MockGEARS", "success", [0.1])],
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": ["core_predictor_failed"]},
                                             "core_predictors": {"core": []}}}})  # 无 core 声明
    assert rd["abstain"] is False


# --- cell_type 降级 ---

def test_cell_type_unsupported_lowers_reliability():
    rd = _rel({"request": {"perturbation_targets": ["A"], "cell_type": "Jurkat"},
               "models_used": ["MockCPA", "MockGEARS"], "ensemble": {"delta": [0.1]},
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": []}},
                                 "model_applicability": {"MockCPA": {"supported_cell_types": ["K562"]},
                                                         "MockGEARS": {"supported_cell_types": ["K562"]}}}})
    assert rd["abstain"] is False and rd["reliability"] == "medium"
    assert "downgrade:cell_type_not_supported" in rd["reasons"]


# --- critic 强化 (§8.4) ---

def _crit(payload, trace_types=("brain_retrieved", "predictor_result")):
    bus = MessageBus()
    for i, t in enumerate(trace_types):
        bus.send(AgentMessage(f"b{i}", "X", "Y", t, {}, "t"))
    CriticAgent().handle(AgentMessage("m", "X", "Critic", "review", payload, "t"), bus)
    return bus.latest("critic_done").payload["critic_violations"]


def test_critic_missing_provenance():
    v = _crit({"brain_context": {"rules_referenced": []}, "request": {"species": "human"},
               "reliability_decision": {"abstain": False}, "models_used": ["MockCPA"],
               "results": [_result("MockCPA", "success", [0.1])]})
    assert "missing_provenance" in v


def test_critic_missing_uncertainty():
    bad = _result("MockCPA", "success", [0.1])
    bad["uncertainty"] = None
    v = _crit({"brain_context": {"rules_referenced": ["x.yaml"]}, "request": {"species": "human"},
               "reliability_decision": {"abstain": False}, "models_used": ["MockCPA"], "results": [bad]})
    assert any(x.startswith("missing_uncertainty") for x in v)


def test_critic_abstain_inconsistent_with_prediction():
    v = _crit({"brain_context": {"rules_referenced": ["x.yaml"]}, "request": {"species": "human"},
               "reliability_decision": {"abstain": True}, "models_used": [], "ensemble": {"delta": [0.1]},
               "results": []})
    assert "abstain_inconsistent_with_prediction" in v


def test_critic_happy_no_violations():
    v = _crit({"brain_context": {"rules_referenced": ["x.yaml"],
                                 "model_applicability": {"MockCPA": {"supported_species": ["human"]}}},
               "request": {"species": "human"}, "reliability_decision": {"abstain": False},
               "models_used": ["MockCPA"], "ensemble": {"delta": [0.1]},
               "results": [_result("MockCPA", "success", [0.1])]})
    assert v == []


# --- report 拆分 abstain vs downgrade (§8.4 报告诚实性, e2e 激活 cell_type 路径) ---

def test_report_cell_type_downgrade_e2e():
    from praxis_virtualcell.workflows.predict_delta_expression import run_request
    # human + 不支持的 cell_type(Jurkat 不在任何 supported_cell_types) → 降级(非 abstain)
    r = run_request({"request_id": "r", "species": "human", "perturbation_type": "gene",
                     "perturbation_targets": ["AHR"], "input_modality": "scRNA",
                     "output_modality": "delta_expression", "task_type": "predict_delta_expression",
                     "cell_type": "Jurkat"})
    assert r["abstain"] is False
    assert r["abstain_reasons"] == []                                    # 非 abstain → 不携带 abstain_reasons
    assert "downgrade:cell_type_not_supported" in r["downgrade_reasons"]  # 降级单列
    assert "models_failed" in r and "model_disagreement" in r            # 契约字段齐
