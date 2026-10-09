"""Phase 5:ActiveLearningAgent(进 bus,产 learning_queue)。
红线:advisory 不碰裁决 —— 只读 report/evidence_level,只 emit learning_queue_ready,不改 report。
learning_queue 用 disagreement/OOD/evidence/module 弱支持排序(information gain 降序)。"""
from praxis_virtualcell.active_learning.active_learning_agent import ActiveLearningAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _module_plan(entries=None):
    entries = entries or [
        {"module": "genetic_hub", "role": "primary", "species_support": "strong",
         "verdict": "accept", "data_gated": False},
        {"module": "stress_processor", "role": "secondary", "species_support": "weak",
         "verdict": "caution", "data_gated": True},
    ]
    return {"species": "human", "primary": "genetic_hub",
            "secondary": ["stress_processor"], "overall_verdict": "caution", "entries": entries}


def _report(**kw):
    base = {"abstain": False, "reliability": "high", "prediction": {"delta": [0.3]},
            "models_used": ["MockLinear"], "abstain_reasons": [], "downgrade_reasons": [],
            "model_disagreement": {"score": 0.3, "triggered": False}, "caution_flags": {},
            "learned_reliability": None, "request": {"species": "human",
                                                     "perturbation_targets": ["AHR"]},
            "seen_in_train": True,
            "provenance": {"module_plan": _module_plan()}}
    base.update(kw)
    return base


def _run(report, evidence_level=None):
    bus = MessageBus()
    ActiveLearningAgent().handle(AgentMessage(
        message_id="c1", sender="EvidenceLevelAgent", receiver="ActiveLearningAgent",
        message_type="learning_queue_request",
        payload={"report": report, "evidence_level": evidence_level or {"level": "E3"}},
        timestamp="t1"), bus)
    return bus.latest("learning_queue_ready")


def test_emits_learning_queue_ready():
    msg = _run(_report())
    assert msg is not None
    assert msg.message_type == "learning_queue_ready"
    assert msg.receiver == "client"
    q = msg.payload["learning_queue"]
    assert "items" in q and "notes" in q


def test_weak_gated_module_ranks_higher():
    """弱支持 + data_gated 的 stress_processor 该排在 strong genetic_hub 之前(information gain 高)。"""
    msg = _run(_report())
    items = msg.payload["learning_queue"]["items"]
    mods = [it["module"] for it in items]
    assert "stress_processor" in mods and "genetic_hub" in mods
    assert mods.index("stress_processor") < mods.index("genetic_hub")


def test_does_not_mutate_report():
    """红线:AL 不碰裁决 —— 跑前后 report 逐键不变。"""
    r = _report()
    snap = {"abstain": r["abstain"], "reliability": r["reliability"],
            "prediction": dict(r["prediction"]), "provenance_keys": set(r["provenance"])}
    _run(r)
    assert r["abstain"] == snap["abstain"]
    assert r["reliability"] == snap["reliability"]
    assert r["prediction"] == snap["prediction"]
    assert set(r["provenance"]) == snap["provenance_keys"]   # AL 不往 report.provenance 塞键(由 runtime sidecar 挂)


def test_abstain_report_no_fabricated_accept():
    """abstain 请求:AL 可建议补数据(候选来自弱模块),但绝不把 abstain 改 accept。"""
    r = _report(abstain=True, prediction=None, models_used=[],
                abstain_reasons=["model_disagreement_too_high"])
    msg = _run(r, evidence_level={"level": "E1"})
    assert r["abstain"] is True            # 不被改
    q = msg.payload["learning_queue"]
    assert isinstance(q["items"], list)    # 空或含"补数据"候选,不虚构 accept


def test_no_module_plan_empty_queue_with_note():
    """无 module_plan(不可路由请求)→ 空队列 + note,不崩不虚构(红线 6)。"""
    r = _report(provenance={})
    msg = _run(r)
    q = msg.payload["learning_queue"]
    assert q["items"] == []
    assert q["notes"]                      # 有 note 说明为何空


def test_high_disagreement_drives_gain():
    """分歧触发 → 相关候选 information_gain 更高 + drivers 记 disagreement。"""
    msg = _run(_report(model_disagreement={"score": 0.95, "triggered": True},
                       reliability="medium",
                       downgrade_reasons=["downgrade:model_disagreement_too_high"]),
               evidence_level={"level": "E4"})
    items = msg.payload["learning_queue"]["items"]
    assert items                           # 有候选
    drivers = [d for it in items for d in it["drivers"]]
    assert any("disagreement" in d for d in drivers)


def test_no_llm_import_in_module():
    import praxis_virtualcell.active_learning.active_learning_agent as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_client" not in src
    assert "llm_orchestration" not in src
