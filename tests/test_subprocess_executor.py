import pytest

from praxis2.skills.executor import SubprocessSkillExecutor


async def test_subprocess_runs_python_and_returns_stdout_json():

    ex = SubprocessSkillExecutor(
        cmd=["python", "-c", "import json; print(json.dumps({'result': 'ok'}))"],
        timeout_s=5.0,
    )
    out = await ex.call(payload={})
    assert out["result"] == "ok"


async def test_subprocess_env_vars_injected():

    ex = SubprocessSkillExecutor(
        cmd=[
            "python",
            "-c",
            "import os, json; "
            "print(json.dumps({'env': os.environ.get('CONDA_DEFAULT_ENV'),"
            " 'cuda': os.environ.get('CUDA_VISIBLE_DEVICES')}))",
        ],
        timeout_s=5.0,
        env={"CONDA_DEFAULT_ENV": "af3", "CUDA_VISIBLE_DEVICES": "0,1"},
    )
    out = await ex.call(payload={})
    assert out["env"] == "af3"
    assert out["cuda"] == "0,1"


async def test_subprocess_timeout_kills_and_raises():

    ex = SubprocessSkillExecutor(
        cmd=["python", "-c", "import time; time.sleep(10)"],
        timeout_s=0.05,
    )
    with pytest.raises(TimeoutError):
        await ex.call(payload={})


async def test_subprocess_nonzero_exit_returns_error_payload():

    ex = SubprocessSkillExecutor(
        cmd=["python", "-c", "import sys; print('boom', file=sys.stderr); sys.exit(2)"],
        timeout_s=5.0,
    )
    out = await ex.call(payload={})
    assert out["ok"] is False
    assert "boom" in out["error"]
    assert out["returncode"] == 2


async def test_subprocess_invalid_json_stdout_returns_error():

    ex = SubprocessSkillExecutor(
        cmd=["python", "-c", "print('not json')"],
        timeout_s=5.0,
    )
    out = await ex.call(payload={})
    assert out["ok"] is False
    assert "JSON" in out["error"] or "json" in out["error"]


async def test_subprocess_payload_passed_via_stdin_json():

    script = "import sys, json; p = json.loads(sys.stdin.read()); print(json.dumps({'echo': p.get('msg')}))"
    ex = SubprocessSkillExecutor(cmd=["python", "-c", script], timeout_s=5.0)
    out = await ex.call(payload={"msg": "\u4f60\u597d"})
    assert out["echo"] == "\u4f60\u597d"
