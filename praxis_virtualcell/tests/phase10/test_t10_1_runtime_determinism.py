from dataclasses import asdict

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
