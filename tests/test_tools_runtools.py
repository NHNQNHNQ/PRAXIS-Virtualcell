from praxis2.core.seams import AllowAllPermission
from praxis2.core.state import State
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import (
    TOOL_RESULT_MAX_CHARS,
    SerialToolRunner,
    apply_tool_result_budget,
    placeholder_results,
)


class Echo(Tool):
    name = "echo"

    def input_schema(self):
        return {"type": "object", "properties": {"t": {"type": "string"}}}

    async def run(self, payload):
        return ToolResult(ok=True, value=payload["t"])


class Boom(Tool):
    name = "boom"

    def input_schema(self):
        return {"type": "object", "properties": {}}

    async def run(self, payload):
        return ToolResult(ok=False, error="炸了:依赖 X 缺失", recovery_hint="装 X 后重试")


def _registry():
    r = ToolRegistry()
    r.register(Echo())
    r.register(Boom())
    return r


def test_apply_tool_result_budget_truncates():
    big = "z" * (TOOL_RESULT_MAX_CHARS + 5000)
    out = apply_tool_result_budget(big)
    assert len(out) < len(big)
    assert "截断" in out
    small = "ok"
    assert apply_tool_result_budget(small) == "ok"  # 不超不动


async def test_ok_tool_result_shape():
    runner = SerialToolRunner(_registry(), recovery_budget=3, permission=AllowAllPermission())
    st = State()
    results = await runner.run_turn(
        [{"id": "tu1", "name": "echo", "input": {"t": "hi"}}], st
    )
    assert results == [
        {"type": "tool_result", "tool_use_id": "tu1", "is_error": False, "content": "hi"}
    ]
    assert st.recovery_attempts == 0


async def test_failing_tool_returns_structured_is_error_and_counts_recovery():
    runner = SerialToolRunner(_registry(), recovery_budget=3, permission=AllowAllPermission())
    st = State()
    results = await runner.run_turn([{"id": "tu9", "name": "boom", "input": {}}], st)
    r = results[0]
    assert r["type"] == "tool_result" and r["tool_use_id"] == "tu9"
    assert r["is_error"] is True
    assert "炸了" in r["content"]
    assert r["diagnostics"] is None  # M5 才填
    assert r["recovery_hint"] == "装 X 后重试"
    assert r["recovery_budget_remaining"] == 2  # 3 - 1
    assert st.recovery_attempts == 1


async def test_unknown_tool_is_structured_error():
    runner = SerialToolRunner(_registry(), recovery_budget=3, permission=AllowAllPermission())
    st = State()
    results = await runner.run_turn([{"id": "x", "name": "nope", "input": {}}], st)
    assert results[0]["is_error"] is True
    assert "未注册" in results[0]["content"]
    assert st.recovery_attempts == 1


async def test_abort_get_remaining_results_pairs_all_unrun():
    # §7.1.5:中断后未执行的 tool_use 必须配平占位 tool_result,杜绝孤儿
    # 直接测纯函数 placeholder_results(即 get_remaining_results 的底层, self._remaining)
    blocks = [
        {"id": "a", "name": "echo", "input": {"t": "1"}},
        {"id": "b", "name": "echo", "input": {"t": "2"}},
    ]
    placeholders = placeholder_results(blocks)
    assert [p["tool_use_id"] for p in placeholders] == ["a", "b"]
    assert all(p["is_error"] and p["type"] == "tool_result" for p in placeholders)
