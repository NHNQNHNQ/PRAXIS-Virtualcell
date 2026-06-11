from praxis2.tools.brain_query import BrainQueryTool


def _make_tool():
    return BrainQueryTool()


async def test_real_hit_flag_equals_derived_condition():
    """不可证伪化:flag 必须严格等于"真命中"判定(source=filesystem ∧ 非降级 ∧ 有命中)。
    任何环境都断言该等式——有真盘则 flag=True,fixture 兜底则 flag=False,均能证伪实现。"""
    tool = _make_tool()
    res = await tool.run({"brain": "enzyme", "query": "thermostability", "top_k": 3})
    assert res.ok
    expected = (
        res.value.get("source") == "filesystem"
        and not res.value.get("degraded_to_bare", False)
        and bool(res.value.get("hits"))
    )
    assert tool.last_retrieval_real_hit is expected


async def test_unknown_brain_flag_false():
    tool = _make_tool()
    res = await tool.run({"brain": "no_such_brain_xyz", "query": "x"})
    assert not res.ok  # 未知 brain
    assert tool.last_retrieval_real_hit is False


async def test_empty_query_keeps_flag_false():
    tool = _make_tool()
    await tool.run({"brain": "enzyme", "query": ""})
    assert tool.last_retrieval_real_hit is False
