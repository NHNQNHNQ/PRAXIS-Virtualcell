from dataclasses import asdict

import pytest

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.exceptions import PraxisVCError, SchemaError
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.workflows.run_virtualcell_query import run_query


def test_schema_error_is_praxisvc_error():
    assert issubclass(SchemaError, PraxisVCError)


def test_agent_message_new_fields_defaults():
    m = AgentMessage("msg_0001", "A", "B", "ping", {"k": 1}, "t0001")
    assert m.schema_version == "vc.msg.v1"
    assert m.trace_id is None
    assert m.task_id is None
    d = asdict(m)
    assert {"schema_version", "trace_id", "task_id"} <= set(d)


def test_bus_backfills_trace_and_task_from_context():
    bus = MessageBus()
    bus.set_context(trace_id="trace_abc", task_id="task_xyz")
    bus.send(AgentMessage("msg_0001", "A", "B", "ping", {"k": 1}, "t0001"))
    m = bus.trace[0]
    assert m.trace_id == "trace_abc"
    assert m.task_id == "task_xyz"


def test_bus_backfills_deterministic_fallback_without_context():
    bus = MessageBus()  # 未 set_context
    bus.send(AgentMessage("msg_0007", "A", "B", "ping", {"k": 1}, "t0001"))
    m = bus.trace[0]
    assert m.trace_id == "trace_msg_0007"   # 确定性兜底,不 raise
    assert m.task_id == "task_msg_0007"


def test_bus_rejects_non_dict_payload():
    bus = MessageBus()
    bus.set_context(trace_id="trace_abc", task_id="task_xyz")
    bad = AgentMessage("msg_0001", "A", "B", "ping", "free text handoff", "t0001")  # payload 非 dict
    with pytest.raises(SchemaError):
        bus.send(bad)


def test_bus_rejects_missing_hard_field():
    bus = MessageBus()
    bus.set_context(trace_id="trace_abc", task_id="task_xyz")
    bad = AgentMessage("msg_0001", "", "B", "ping", {"k": 1}, "t0001")  # sender 空
    with pytest.raises(SchemaError):
        bus.send(bad)


def test_bus_accepts_valid_message():
    bus = MessageBus()
    bus.set_context(trace_id="trace_abc", task_id="task_xyz")
    bus.send(AgentMessage("msg_0001", "A", "B", "ping", {"k": 1}, "t0001"))
    assert len(bus.trace) == 1


_REQ = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
        "input_modality": "scRNA", "output_modality": "delta_expression",
        "task_type": "predict_delta_expression"}
_CFG = RuntimeConfig(mode=Mode.OFFLINE)


def _trace_ids(out):
    return {step.get("trace_id") for step in out["trace"] if isinstance(step, dict)}


def test_trace_id_is_per_run_consistent():
    out = run_query(dict(_REQ), config=_CFG)
    ids = _trace_ids(out)
    assert len(ids) == 1                 # 同一 run 所有 message 同一 trace_id
    assert None not in ids               # 已回填
    assert next(iter(ids)).startswith("trace_")


def test_trace_id_deterministic_across_runs():
    a = _trace_ids(run_query(dict(_REQ), config=_CFG))
    b = _trace_ids(run_query(dict(_REQ), config=_CFG))
    assert a == b                        # 两跑同 req → 同 trace_id


def _canon_hash(obj) -> str:
    import hashlib
    import json
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


_ACCEPT = dict(_REQ)
_ABSTAIN = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
            "input_modality": "scRNA", "output_modality": "delta_expression",
            "task_type": "predict_delta_expression"}


@pytest.mark.parametrize("req", [_ACCEPT, _ABSTAIN], ids=["accept", "abstain"])
def test_offline_rerun_byte_equal(req):
    outs = [run_query(dict(req), config=_CFG) for _ in range(3)]
    sr_hashes = {_canon_hash(o["structured_report"]) for o in outs}
    tr_hashes = {_canon_hash(o["trace"]) for o in outs}
    assert len(sr_hashes) == 1, "structured_report 三跑不一致"
    assert len(tr_hashes) == 1, "trace 三跑不一致"


def test_trace_messages_schema_compliant():
    out = run_query(dict(_ACCEPT), config=_CFG)
    for step in out["trace"]:
        assert isinstance(step, dict)
        for f in ("message_id", "sender", "receiver", "message_type", "timestamp",
                  "schema_version", "trace_id", "task_id"):
            assert step.get(f), f"trace message 缺 {f}: {step}"
        # 注:payload 不在对外 trace 摘要里(精简视图),其结构化(必为 dict)由 bus._validate
        # 在 send 时保证,已由 Task 5 的 test_bus_rejects_non_dict_payload 覆盖。


def test_offline_report_provenance_fields_present():
    out = run_query(dict(_ACCEPT), config=_CFG)
    prov = out["provenance"]
    for f in ("rules_referenced", "models_used", "n_messages"):
        assert f in prov, f"provenance 缺字段 {f}"
