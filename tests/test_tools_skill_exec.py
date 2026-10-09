from __future__ import annotations

import asyncio

from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.skill_exec import SkillExecTool


def _run(coro):
    return (
        asyncio.get_event_loop().run_until_complete(coro)
        if not asyncio.get_event_loop().is_running()
        else asyncio.run(coro)
    )  # noqa: E501


def test_skill_exec_registered_in_chat_registry():

    sel_disc = resolve_agent("virtualcell", user_query="hi")
    reg_disc = build_chat_registry(selection=sel_disc)
    names = [t["name"] for t in reg_disc.anthropic_tools()]
    assert "SkillExec" in names

    sel_gen = resolve_agent("general", user_query="hi")
    reg_gen = build_chat_registry(selection=sel_gen)
    names_gen = [t["name"] for t in reg_gen.anthropic_tools()]
    assert "SkillExec" in names_gen

    assert "AgentTool" in names_gen

    assert "AgentTool" not in names


def test_skill_exec_returns_to_execute_for_real_skill():

    t = SkillExecTool()
    r = asyncio.run(
        t.run(
            {
                "name": "perturbation_predict",
                "brain": "virtualcell",
                "inputs": {"perturbation": "GENE_KO", "cell_type": "K562"},
            }
        )
    )
    assert r.ok
    plan = r.value["execution_plan"]
    assert plan["brain"] == "virtualcell"
    assert plan["skill"] == "perturbation_predict"
    assert plan["host_env"] == "praxis-virtualcell"
    assert r.value["sop_excerpt"]
    assert "conda activate praxis-virtualcell" in r.value["ssh_command_template"]


def test_skill_exec_unknown_skill_returns_error():
    t = SkillExecTool()
    r = asyncio.run(t.run({"name": "this_skill_does_not_exist_xyz"}))
    assert not r.ok
    assert "not found" in (r.error or "")


def test_skill_exec_finds_skill_without_brain_hint():

    t = SkillExecTool()
    r = asyncio.run(t.run({"name": "perturbation_predict"}))
    assert r.ok
    assert r.value["execution_plan"]["brain"] == "virtualcell"


def test_skill_exec_rmcp_op_declared():

    t = SkillExecTool()
    assert t.rmcp_op == "call_skill"


def test_skill_exec_degrades_when_no_ssh_env(monkeypatch):

    for k in ("PRAXIS_SKILL_SSH_HOST", "PRAXIS_SKILL_REMOTE_BRAINS", "PRAXIS_SKILL_CONDA_INIT"):
        monkeypatch.delenv(k, raising=False)
    t = SkillExecTool()
    r = asyncio.run(
        t.run(
            {
                "name": "perturbation_predict",
                "brain": "virtualcell",
                "inputs": {"perturbation": "GENE_KO", "simulate": True},
            }
        )
    )
    assert r.ok
    assert r.value["exec_via"] == "manual (no auto-exec)"
    assert "PRAXIS_SKILL_SSH_HOST" in r.value["why_not_executed"]
    assert "conda activate praxis-virtualcell" in r.value["ssh_command_template"]


def test_skill_exec_input_schema_complete():
    t = SkillExecTool()
    schema = t.input_schema()
    assert schema["required"] == ["name"]
    assert "name" in schema["properties"]
    assert "brain" in schema["properties"]
    assert "inputs" in schema["properties"]


async def _fake_proc_factory(stdout: bytes, stderr: bytes = b"", rc: int = 0):

    class FakeProc:
        returncode = rc

        async def communicate(self, _stdin):
            return stdout, stderr

        async def wait(self):
            return rc

        def kill(self):
            pass

    return FakeProc()


def test_skill_exec_real_ssh_when_env_set(monkeypatch):

    import asyncio as _aio

    from praxis2.tools import skill_exec as mod

    monkeypatch.setenv("PRAXIS_SKILL_SSH_HOST", "researcher@example.invalid")
    monkeypatch.setenv("PRAXIS_SKILL_REMOTE_BRAINS", "/srv/praxis/brains")
    monkeypatch.setenv("PRAXIS_SKILL_CONDA_INIT", "/opt/conda/etc/profile.d/conda.sh")

    expected_payload = {
        "skill_id": "boltz_structure_predict",
        "ok": True,
        "pdb_path": "out/sim.pdb",
        "confidence": 0.87,
    }
    captured_argv: list = []

    async def fake_create_subprocess_exec(*argv, **kwargs):
        captured_argv.extend(argv)
        import json as _json

        return await _fake_proc_factory(_json.dumps(expected_payload).encode("utf-8"))

    monkeypatch.setattr(mod.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    t = mod.SkillExecTool()
    r = _aio.run(
        t.run(
            {
                "name": "perturbation_predict",
                "brain": "virtualcell",
                "inputs": {"seed": 42, "simulate": True},
            }
        )
    )
    assert r.ok, f"Expected successful execution; error={r.error}"
    assert r.value["execution_plan"]["exec_via"].startswith("ssh ")
    assert r.value["result"] == expected_payload

    assert captured_argv[0] == "ssh"
    assert "researcher@example.invalid" in captured_argv
    assert "bash" in captured_argv and "-lc" in captured_argv


def test_skill_exec_ssh_exec_nonzero_rc_returns_error(monkeypatch):

    import asyncio as _aio

    from praxis2.tools import skill_exec as mod

    monkeypatch.setenv("PRAXIS_SKILL_SSH_HOST", "researcher@example.invalid")
    monkeypatch.setenv("PRAXIS_SKILL_REMOTE_BRAINS", "/srv/praxis/brains")
    monkeypatch.setenv("PRAXIS_SKILL_CONDA_INIT", "/opt/conda/etc/profile.d/conda.sh")

    async def fake_create_subprocess_exec(*argv, **kwargs):
        return await _fake_proc_factory(b"", b"ModuleNotFoundError: no module 'boltz'", rc=1)

    monkeypatch.setattr(mod.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    t = mod.SkillExecTool()
    r = _aio.run(
        t.run(
            {
                "name": "perturbation_predict",
                "brain": "virtualcell",
                "inputs": {"simulate": True},
            }
        )
    )
    assert not r.ok
    assert "rc=1" in (r.error or "")
    assert r.value.get("stderr", "").startswith("ModuleNotFoundError")


def test_skill_exec_ssh_command_quotes_run_py_path_with_spaces(monkeypatch):

    import asyncio as _aio

    from praxis2.tools import skill_exec as mod

    monkeypatch.setenv("PRAXIS_SKILL_SSH_HOST", "researcher@example.invalid")
    monkeypatch.setenv("PRAXIS_SKILL_REMOTE_BRAINS", "/srv/praxis/brains")
    monkeypatch.setenv("PRAXIS_SKILL_CONDA_INIT", "/opt/conda/etc/profile.d/conda.sh")

    captured_remote_cmd: list[str] = []

    async def fake_create_subprocess_exec(*argv, **kwargs):

        captured_remote_cmd.append(argv[-1])
        import json as _json

        return await _fake_proc_factory(_json.dumps({"ok": True}).encode("utf-8"))

    monkeypatch.setattr(mod.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    t = mod.SkillExecTool()
    _ = _aio.run(
        t.run(
            {
                "name": "perturbation_predict",
                "brain": "virtualcell",
                "inputs": {},
            }
        )
    )
    cmd = captured_remote_cmd[0]

    assert "/run.py'" in cmd or '/run.py"' in cmd, (
        f"The complete rel/run.py path must be quoted; observed remote command: {cmd!r}"
    )

    assert "'/run.py" not in cmd, f"/run.py must remain inside the quoted path: {cmd!r}"


def test_skill_exec_ssh_exec_stdout_non_json_returns_error(monkeypatch):

    import asyncio as _aio

    from praxis2.tools import skill_exec as mod

    monkeypatch.setenv("PRAXIS_SKILL_SSH_HOST", "researcher@example.invalid")
    monkeypatch.setenv("PRAXIS_SKILL_REMOTE_BRAINS", "/srv/praxis/brains")
    monkeypatch.setenv("PRAXIS_SKILL_CONDA_INIT", "/opt/conda/etc/profile.d/conda.sh")

    async def fake_create_subprocess_exec(*argv, **kwargs):
        return await _fake_proc_factory(b"not a json output", b"")

    monkeypatch.setattr(mod.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    t = mod.SkillExecTool()
    r = _aio.run(
        t.run(
            {
                "name": "perturbation_predict",
                "brain": "virtualcell",
                "inputs": {},
            }
        )
    )
    assert not r.ok
    assert "\u975e JSON" in (r.error or "") or "JSON" in (r.error or "")
    assert "not a json output" in r.value.get("stdout_raw", "")


def test_skill_exec_rmcp_op_matches_execute_phase_whitelist():

    from praxis2.core.rmcp import ALLOWED_OPS, Phase
    from praxis2.tools.skill_exec import SkillExecTool

    assert SkillExecTool.rmcp_op == "call_skill"
    assert SkillExecTool.rmcp_op in ALLOWED_OPS[Phase.EXECUTE]
