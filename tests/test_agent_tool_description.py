from praxis2.agents.agent_tool import AgentTool


def test_agent_tool_description_warns_not_auto_fork():
    """风险点①:run() 只构 spawn 描述符恒 ok=True。描述须显式声明
    '只返回描述符/不代表子 agent 已完成',防模型把'已构造'当'已完成分析'转述。"""
    d = AgentTool.description
    assert "不代表" in d and "完成" in d
    assert "描述符" in d
