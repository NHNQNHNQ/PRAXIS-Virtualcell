import pytest

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.exceptions import UnknownAgentError
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.runtime import AgentRuntime


class Echo(BaseAgent):
    name = "Echo"

    def handle(self, message, bus):
        bus.send(AgentMessage("e1", self.name, "client", "echoed",
                              {"got": message.payload}, "t0"))


def test_register_and_dispatch():
    rt = AgentRuntime(RuntimeConfig(), bus=MessageBus(), clock=Clock(), idgen=IdGen())
    rt.register_agent(Echo())
    m = rt.mk_message("client", "Echo", "ping", {"x": 1})
    rt.dispatch_message(m)
    assert rt.bus.latest("echoed").payload["got"] == {"x": 1}


def test_dispatch_unknown_agent_raises():
    rt = AgentRuntime(RuntimeConfig(), bus=MessageBus(), clock=Clock(), idgen=IdGen())
    with pytest.raises(UnknownAgentError):
        rt.dispatch_message(rt.mk_message("client", "Nope", "ping", {}))


def test_mk_message_uses_idgen_and_clock():
    rt = AgentRuntime(RuntimeConfig(), bus=MessageBus(), clock=Clock(), idgen=IdGen())
    m = rt.mk_message("a", "b", "t", {})
    assert m.message_id == "msg_0001" and m.timestamp == "t0001"
