from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _m(mid, sender, receiver, mtype):
    return AgentMessage(mid, sender, receiver, mtype, {}, "t0001")


def test_send_routes_to_receiver_inbox():
    bus = MessageBus()
    bus.send(_m("m1", "A", "B", "ping"))
    assert [m.message_id for m in bus.get_messages("B")] == ["m1"]
    assert bus.get_messages("C") == []


def test_trace_records_all_in_order():
    bus = MessageBus()
    bus.send(_m("m1", "A", "B", "ping"))
    bus.send(_m("m2", "B", "A", "pong"))
    assert [m.message_id for m in bus.trace] == ["m1", "m2"]


def test_has_message_type_and_latest():
    bus = MessageBus()
    bus.send(_m("m1", "A", "B", "brain_retrieved"))
    assert bus.has_message_type("brain_retrieved") is True
    assert bus.has_message_type("nope") is False
    assert bus.latest("brain_retrieved").message_id == "m1"
    assert bus.latest("nope") is None
