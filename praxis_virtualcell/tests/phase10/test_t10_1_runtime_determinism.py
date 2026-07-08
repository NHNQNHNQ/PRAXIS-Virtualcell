from dataclasses import asdict

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.exceptions import PraxisVCError, SchemaError
from praxis_virtualcell.core.message import AgentMessage


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
