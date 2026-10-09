from praxis2.agents.agent_tool import AgentTool


def test_agent_tool_description_warns_not_auto_fork():

    d = AgentTool.description
    assert "does not represent" in d and "completed" in d
    assert "descriptor" in d
