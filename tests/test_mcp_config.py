import pytest
from praxis2.mcp.config import MCPServerSpec, parse_mcp_servers


def test_parse_empty_returns_empty_list():
    assert parse_mcp_servers("") == []
    assert parse_mcp_servers("   ") == []


def test_parse_single_server():
    specs = parse_mcp_servers(
        '[{"name":"echo","command":"python","args":["-m","praxis2.mcp.echo_server"]}]'
    )
    assert len(specs) == 1
    s = specs[0]
    assert s.name == "echo"
    assert s.command == "python"
    assert s.args == ["-m", "praxis2.mcp.echo_server"]
    assert s.env == {}


def test_parse_with_env():
    specs = parse_mcp_servers(
        '[{"name":"fs","command":"node","args":["x.js"],"env":{"KEY":"v"}}]'
    )
    assert specs[0].env == {"KEY": "v"}


def test_parse_multiple_servers():
    specs = parse_mcp_servers(
        '[{"name":"a","command":"python","args":[]},'
        '{"name":"b","command":"node","args":["s.js"]}]'
    )
    assert [s.name for s in specs] == ["a", "b"]


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError, match="MCP.*JSON"):
        parse_mcp_servers("not json {[")


def test_parse_missing_name_raises():
    with pytest.raises(ValueError, match="name"):
        parse_mcp_servers('[{"command":"python","args":[]}]')


def test_parse_missing_command_raises():
    with pytest.raises(ValueError, match="command"):
        parse_mcp_servers('[{"name":"x","args":[]}]')


def test_parse_non_list_raises():
    with pytest.raises(ValueError, match="list"):
        parse_mcp_servers('{"name":"x"}')


def test_parse_args_defaults_to_empty():
    specs = parse_mcp_servers('[{"name":"x","command":"python"}]')
    assert specs[0].args == []


def test_parse_args_non_list_raises():
    import pytest
    with pytest.raises(ValueError, match="args 必须是 list"):
        parse_mcp_servers('[{"name":"x","command":"python","args":"oops"}]')


def test_parse_args_int_raises():
    import pytest
    with pytest.raises(ValueError, match="args 必须是 list"):
        parse_mcp_servers('[{"name":"x","command":"python","args":5}]')


def test_parse_env_non_dict_raises():
    import pytest
    with pytest.raises(ValueError, match="env 必须是 object"):
        parse_mcp_servers('[{"name":"x","command":"python","env":"oops"}]')
