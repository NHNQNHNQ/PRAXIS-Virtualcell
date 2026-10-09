from praxis2.skills.executor import (
    CallableSkillExecutor,
    EnvChoice,
    SubprocessSkillExecutor,
    choose_env,
)
from praxis2.skills.loader import SkillManifest


def _mf(env=None):
    m = SkillManifest(name="s", description="d", when_to_use="w")
    m.skill_env = env
    return m


def test_manifest_env_wins_over_agent_default():
    c = choose_env(_mf(env="cryo-gpu"), agent_env="agent-default", available_envs={"cryo-gpu", "agent-default"})
    assert isinstance(c, EnvChoice)
    assert c.env == "cryo-gpu"
    assert c.source == "skill"
    assert c.ambiguous is False


def test_inherit_agent_env_when_manifest_silent():
    c = choose_env(_mf(env=None), agent_env="agent-default", available_envs={"agent-default"})
    assert c.env == "agent-default"
    assert c.source == "agent"


def test_env_ambiguity_reported_not_silently_picked():
    c = choose_env(_mf(env=None), agent_env=None, available_envs={"e1", "e2"})
    assert c.ambiguous is True
    assert c.env is None
    assert c.source == "none"
    assert set(c.candidates) == {"e1", "e2"}


def test_choice_written_to_transcript_observable():
    rec: list[dict] = []
    c = choose_env(_mf(env="e1"), agent_env=None, available_envs={"e1"}, transcript_sink=rec.append)
    assert c.env == "e1"
    assert rec and rec[0]["type"] == "env_choice"
    assert rec[0]["env"] == "e1" and rec[0]["source"] == "skill"


async def test_callable_executor_runs_in_process():
    async def fn(payload):
        return {"out": payload["x"] * 2}

    ex = CallableSkillExecutor(fn)
    out = await ex.call({"x": 21})
    assert out == {"out": 42}


async def test_subprocess_executor_m7_real_impl_signature():

    ex = SubprocessSkillExecutor(
        cmd=["python", "-c", "import json; print(json.dumps({'ok': True}))"],
        timeout_s=5.0,
    )
    out = await ex.call({"x": 1})
    assert out == {"ok": True}


def test_sole_available_env_source_is_sole_not_agent():

    c = choose_env(_mf(env=None), agent_env=None, available_envs={"only-env"})
    assert c.env == "only-env"
    assert c.source == "sole"
    assert c.ambiguous is False


def test_no_env_available_yields_none_source():

    c = choose_env(_mf(env=None), agent_env=None, available_envs=set())
    assert c.env is None
    assert c.source == "none"
    assert c.ambiguous is False


def test_empty_string_skill_env_falls_back_not_skill_source():

    c = choose_env(_mf(env=""), agent_env="a", available_envs={"a"})
    assert c.env == "a"
    assert c.source == "agent"
