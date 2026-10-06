"""Provider-private reasoning survives real HTTP/SSE tool continuations."""
from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import respx

from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State
from praxis2.llm.client import LLMClient
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner


class Evidence(Tool):
    name = "evidence"

    def __init__(self):
        self.records = []

    def input_schema(self):
        return {"type": "object", "properties": {"record": {"type": "string"}},
                "required": ["record"]}

    async def run(self, payload):
        self.records.append(payload["record"])
        return ToolResult(ok=True, value=f"verified {payload['record']}")


def _sse(*deltas, finish="stop"):
    packets = [{"choices": [{"index": 0, "delta": delta}]} for delta in deltas]
    packets.append({"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})
    return "".join(f"data: {json.dumps(packet)}\n\n" for packet in packets) + "data: [DONE]\n\n"


def _tool_turn(number):
    return _sse(
        {"reasoning_content": f"private plan {number}: "},
        {"reasoning_content": "retrieve evidence"},
        {"content": f"Checking record R{number}."},
        {"tool_calls": [{"index": 0, "id": f"call-{number}", "type": "function",
                         "function": {"name": "evidence", "arguments": '{"record":'}}]},
        {"tool_calls": [{"index": 0, "function": {"arguments": f'"R{number}"}}'}}]},
        finish="tool_calls",
    )


@respx.mock
async def test_multiple_tool_turns_and_next_user_turn_keep_all_reasoning_on_wire():
    requests = []
    responses = [
        _tool_turn(1), _tool_turn(2),
        _sse({"reasoning_content": "private final interpretation"}, {"content": "Evidence summary."}),
        _sse({"reasoning_content": ""}, {"content": "Follow-up summary."}),
    ]

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, text=responses[len(requests) - 1],
                              headers={"content-type": "text/event-stream"})

    respx.post("https://up.example/v1/chat/completions").mock(side_effect=respond)
    evidence = Evidence()
    registry = ToolRegistry()
    registry.register(evidence)
    runner = SerialToolRunner(registry, recovery_budget=3, permission=AllowAllPermission())
    settings = SimpleNamespace(model="test-model", max_tokens=512, max_turns=5,
                               recovery_budget=3, max_output_recovery=0)
    state = State(messages=[{"role": "user", "content": "Compare records R1 and R2."}])
    client = LLMClient(api_key="test-only", base_url="https://up.example")
    kwargs = dict(client=client, registry=registry, runner=runner, settings=settings,
                  compactor=MinimalCompactor(), thinking={"type": "enabled"}, reasoning_effort="high")
    try:
        events = [event async for event in query(state, **kwargs)]
        assert events[-1] == {"type": "end", "reason": "stop"}
        state.messages.append({"role": "user", "content": "Explain the evidence again."})
        followup_events = [event async for event in query(state, **kwargs)]
    finally:
        await client.aclose()

    assert followup_events[-1] == {"type": "end", "reason": "stop"}
    assert evidence.records == ["R1", "R2"]
    assert len(requests) == 4
    for payload in requests:
        assert payload["thinking"] == {"type": "enabled"}
        assert payload["reasoning_effort"] == "high"

    expected_reasoning = ["private plan 1: retrieve evidence", "private plan 2: retrieve evidence"]
    third_history = requests[2]["messages"]
    tool_assistants = [message for message in third_history if message["role"] == "assistant"]
    assert [message["reasoning_content"] for message in tool_assistants] == expected_reasoning
    assert [message["content"] for message in tool_assistants] == ["Checking record R1.", "Checking record R2."]
    for number, message in enumerate(tool_assistants, 1):
        call = message["tool_calls"][0]
        assert call["id"] == f"call-{number}"
        assert json.loads(call["function"]["arguments"]) == {"record": f"R{number}"}
    assert [(message["tool_call_id"], message["content"]) for message in third_history
            if message["role"] == "tool"] == [("call-1", "verified R1"), ("call-2", "verified R2")]
    assert [message["reasoning_content"] for message in requests[3]["messages"]
            if message["role"] == "assistant"] == expected_reasoning + ["private final interpretation"]
    assert state.messages[-1] == {"role": "assistant", "content": "Follow-up summary.", "reasoning_content": ""}
    assert [event["type"] for event in events].count("tool_result") == 2
    assert not any(event["type"] == "thinking" or "private" in str(event)
                   for event in events + followup_events)
