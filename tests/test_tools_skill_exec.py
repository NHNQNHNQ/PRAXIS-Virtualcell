"""SkillExecTool 单测:验证「智能体能调到 skill」这一闭环动作。

回归:此前 chat_registry 只挂 AgentTool,模型看到 system prompt 里的 skill 名
但没工具能"调用"。本工具补这一缝。
"""

from __future__ import annotations

import asyncio

from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.skill_exec import SkillExecTool


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if not asyncio.get_event_loop().is_running() else asyncio.run(coro)


def test_skill_exec_registered_in_chat_registry():
    """所有模式都应有 SkillExec(包括 discipline)。"""
    sel_disc = resolve_agent("virtualcell", user_query="hi")
    reg_disc = build_chat_registry(selection=sel_disc)
    names = [t["name"] for t in reg_disc.anthropic_tools()]
    assert "SkillExec" in names

    sel_gen = resolve_agent("general", user_query="hi")
    reg_gen = build_chat_registry(selection=sel_gen)
    names_gen = [t["name"] for t in reg_gen.anthropic_tools()]
    assert "SkillExec" in names_gen
    # general 同时有 AgentTool
    assert "AgentTool" in names_gen
    # discipline 无 AgentTool(§7.5.4)
    assert "AgentTool" not in names


def test_skill_exec_returns_to_execute_for_real_skill():
    """对真存在的 skill 返回 execution_plan + ssh 命令模板 + SOP 摘要。"""
    t = SkillExecTool()
    r = asyncio.run(t.run({
        "name": "perturbation_predict",
        "brain": "virtualcell",
        "inputs": {"perturbation": "GENE_KO", "cell_type": "K562"},
    }))
    assert r.ok
    plan = r.value["execution_plan"]
    assert plan["brain"] == "virtualcell"
    assert plan["skill"] == "perturbation_predict"
    assert plan["host_env"] == "praxis-virtualcell"
    assert r.value["sop_excerpt"]  # SOP 抓到了
    assert "conda activate praxis-virtualcell" in r.value["ssh_command_template"]


def test_skill_exec_unknown_skill_returns_error():
    t = SkillExecTool()
    r = asyncio.run(t.run({"name": "this_skill_does_not_exist_xyz"}))
    assert not r.ok
    assert "未找到" in (r.error or "")


def test_skill_exec_finds_skill_without_brain_hint():
    """传 name 不传 brain 也能找到(全 brain 搜)。"""
    t = SkillExecTool()
    r = asyncio.run(t.run({"name": "perturbation_predict"}))
    assert r.ok
    assert r.value["execution_plan"]["brain"] == "virtualcell"


def test_skill_exec_rmcp_op_declared():
    """§7.3.7:execute 类工具必须显式声明 rmcp_op,防相位门静默绕过。"""
    t = SkillExecTool()
    assert t.rmcp_op == "call_skill"


def test_skill_exec_degrades_when_no_ssh_env(monkeypatch):
    """无 ssh 环境变量 → 返回 SOP + 命令模板,不尝试自动执行。"""
    for k in ("PRAXIS_SKILL_SSH_HOST", "PRAXIS_SKILL_REMOTE_BRAINS", "PRAXIS_SKILL_CONDA_INIT"):
        monkeypatch.delenv(k, raising=False)
    t = SkillExecTool()
    r = asyncio.run(t.run({
        "name": "perturbation_predict", "brain": "virtualcell",
        "inputs": {"perturbation": "GENE_KO", "simulate": True},
    }))
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


# ============== v0.16.0 GA:env 齐时默认真 SSH exec(M7 真执行链)==============


async def _fake_proc_factory(stdout: bytes, stderr: bytes = b"", rc: int = 0):
    """构造一个 fake asyncio subprocess,communicate 返指定 stdout/stderr,returncode=rc。"""
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
    """v0.16.0 GA(M7 真执行链):3 env 齐 + skill 有 run.py → 走 _exec_via_ssh 真 exec。
    mock asyncio.create_subprocess_exec 返 stdout JSON,验 Tool 输出结构化 result。"""
    import asyncio as _aio

    from praxis2.tools import skill_exec as mod

    monkeypatch.setenv("PRAXIS_SKILL_SSH_HOST", "zkyd@10.102.106.53")
    monkeypatch.setenv("PRAXIS_SKILL_REMOTE_BRAINS", "/home/zkyd/data1/mzy/PRAXIS-2/brains")
    monkeypatch.setenv("PRAXIS_SKILL_CONDA_INIT", "/home/zkyd/software/miniconda3/etc/profile.d/conda.sh")

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
    r = _aio.run(t.run({
        "name": "perturbation_predict",
        "brain": "virtualcell",
        "inputs": {"seed": 42, "simulate": True},
    }))
    assert r.ok, f"应真 exec 成功,得到 error={r.error}"
    assert r.value["execution_plan"]["exec_via"].startswith("ssh ")
    assert r.value["result"] == expected_payload
    # 验真 SSH 命令拼接:ssh zkyd@.53 bash -lc '<remote_cmd>'
    assert captured_argv[0] == "ssh"
    assert "zkyd@10.102.106.53" in captured_argv
    assert "bash" in captured_argv and "-lc" in captured_argv


def test_skill_exec_ssh_exec_nonzero_rc_returns_error(monkeypatch):
    """远端命令 rc!=0 → ok=False,error 含 rc + stderr 摘要。"""
    import asyncio as _aio

    from praxis2.tools import skill_exec as mod

    monkeypatch.setenv("PRAXIS_SKILL_SSH_HOST", "zkyd@10.102.106.53")
    monkeypatch.setenv("PRAXIS_SKILL_REMOTE_BRAINS", "/home/zkyd/data1/mzy/PRAXIS-2/brains")
    monkeypatch.setenv("PRAXIS_SKILL_CONDA_INIT", "/home/zkyd/software/miniconda3/etc/profile.d/conda.sh")

    async def fake_create_subprocess_exec(*argv, **kwargs):
        return await _fake_proc_factory(b"", b"ModuleNotFoundError: no module 'boltz'", rc=1)

    monkeypatch.setattr(mod.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    t = mod.SkillExecTool()
    r = _aio.run(t.run({
        "name": "perturbation_predict",
        "brain": "virtualcell",
        "inputs": {"simulate": True},
    }))
    assert not r.ok
    assert "rc=1" in (r.error or "")
    assert r.value.get("stderr", "").startswith("ModuleNotFoundError")


def test_skill_exec_ssh_command_quotes_run_py_path_with_spaces(monkeypatch):
    """v0.16.2 patch:rel 路径含空格 / Unicode 时,`{quote(rel)}/run.py` 引号
    在 /run.py 前剥离会让 shell 把 /run.py 当独立参数。修复:quote 整个
    `rel/run.py` 路径。
    """
    import asyncio as _aio

    from praxis2.tools import skill_exec as mod

    monkeypatch.setenv("PRAXIS_SKILL_SSH_HOST", "zkyd@10.102.106.53")
    monkeypatch.setenv("PRAXIS_SKILL_REMOTE_BRAINS", "/home/zkyd/data1/mzy/PRAXIS-2/brains")
    monkeypatch.setenv("PRAXIS_SKILL_CONDA_INIT", "/home/zkyd/software/miniconda3/etc/profile.d/conda.sh")

    captured_remote_cmd: list[str] = []

    async def fake_create_subprocess_exec(*argv, **kwargs):
        # argv[-1] 是 quoted remote_cmd(经外层 shlex.quote 包过一次,line 275)
        captured_remote_cmd.append(argv[-1])
        import json as _json
        return await _fake_proc_factory(_json.dumps({"ok": True}).encode("utf-8"))

    monkeypatch.setattr(mod.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    t = mod.SkillExecTool()
    _ = _aio.run(t.run({
        "name": "perturbation_predict",
        "brain": "virtualcell",
        "inputs": {},
    }))
    cmd = captured_remote_cmd[0]
    # 关键断言:整个 rel/run.py 路径作为单一 quoted 参数,
    # 不应是 `'path'/run.py`(引号剥离形)
    assert "/run.py'" in cmd or "/run.py\"" in cmd, (
        f"`rel/run.py` 必须整体 quote(含 /run.py 在引号内),"
        f"实际 remote_cmd: {cmd!r}"
    )
    # 反向断言:不能是旧的引号剥离形 'path'/run.py
    assert "'/run.py" not in cmd, (
        f"v0.16.2 修复后,/run.py 不应跟在闭引号 ' 之后(剥离形): {cmd!r}"
    )


def test_skill_exec_ssh_exec_stdout_non_json_returns_error(monkeypatch):
    """run.py 输出非 JSON → ok=False,error 含 JSONDecodeError 提示 + 保留 stdout_raw。"""
    import asyncio as _aio

    from praxis2.tools import skill_exec as mod

    monkeypatch.setenv("PRAXIS_SKILL_SSH_HOST", "zkyd@10.102.106.53")
    monkeypatch.setenv("PRAXIS_SKILL_REMOTE_BRAINS", "/home/zkyd/data1/mzy/PRAXIS-2/brains")
    monkeypatch.setenv("PRAXIS_SKILL_CONDA_INIT", "/home/zkyd/software/miniconda3/etc/profile.d/conda.sh")

    async def fake_create_subprocess_exec(*argv, **kwargs):
        return await _fake_proc_factory(b"not a json output", b"")

    monkeypatch.setattr(mod.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    t = mod.SkillExecTool()
    r = _aio.run(t.run({
        "name": "perturbation_predict",
        "brain": "virtualcell",
        "inputs": {},
    }))
    assert not r.ok
    assert "非 JSON" in (r.error or "") or "JSON" in (r.error or "")
    assert "not a json output" in r.value.get("stdout_raw", "")


def test_skill_exec_rmcp_op_matches_execute_phase_whitelist():
    """latent bug:rmcp_op 须等于 ALLOWED_OPS[EXECUTE] 的成员(call_skill),
    否则即便相位到 EXECUTE,PhaseAwarePermission 也对不上而拒。"""
    from praxis2.core.rmcp import ALLOWED_OPS, Phase
    from praxis2.tools.skill_exec import SkillExecTool

    assert SkillExecTool.rmcp_op == "call_skill"
    assert SkillExecTool.rmcp_op in ALLOWED_OPS[Phase.EXECUTE]
