from praxis2.server.chat_registry import build_chat_registry


def test_bash_isolation_passed_to_tool(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path), bash_isolation=True)
    tool = reg.get("Bash")
    assert tool is not None
    assert tool._isolation is True


def test_bash_no_isolation_default(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path))
    tool = reg.get("Bash")
    assert tool._isolation is False


def test_no_bash_when_sandbox_root_none():

    reg = build_chat_registry(bash_sandbox_root=None)
    assert reg.get("Bash") is None


def test_bash_cgroup_passed_to_tool(tmp_path):
    reg = build_chat_registry(
        bash_sandbox_root=str(tmp_path),
        bash_cgroup=True,
        bash_cgroup_mem_mb=512,
        bash_cgroup_cpu_pct=200,
    )
    tool = reg.get("Bash")
    assert tool._cgroup is True
    assert tool._cgroup_mem_mb == 512
    assert tool._cgroup_cpu_pct == 200


def test_bash_cgroup_default_off(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path))
    assert reg.get("Bash")._cgroup is False


def test_bash_netns_passed_to_tool(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path), bash_netns=True)
    assert reg.get("Bash")._netns is True


def test_bash_netns_default_off(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path))
    assert reg.get("Bash")._netns is False
