import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def test_export_trace_writes_json(tmp_path):
    bus = MessageBus()
    bus.send(AgentMessage("m1", "A", "B", "ping", {"k": "v"}, "t0001"))
    p = tmp_path / "trace.json"
    bus.export_trace(str(p))
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data[0]["message_id"] == "m1" and data[0]["payload"]["k"] == "v"
