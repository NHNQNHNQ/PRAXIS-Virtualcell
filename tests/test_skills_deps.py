from praxis2.skills.deps import DepReport, probe_dependencies


def test_all_deps_present_report_ok_no_missing():
    r = probe_dependencies(["numpy", "scipy"], env="cryo-env", available={"numpy", "scipy", "pandas"})
    assert isinstance(r, DepReport)
    assert r.ok is True
    assert r.missing == []
    assert r.install_command is None


def test_missing_deps_produce_structured_report_not_raise():
    r = probe_dependencies(["numpy", "torch", "rdkit"], env="cryo-env", available={"numpy"})
    assert r.ok is False
    assert r.missing == ["torch", "rdkit"]
    assert r.env == "cryo-env"

    assert "torch" in r.install_command and "rdkit" in r.install_command
    assert "cryo-env" in r.install_command
    assert r.alternative_envs == []


def test_env_ambiguity_reports_candidates_not_silently_pick():

    r = probe_dependencies(
        ["torch"],
        env=None,
        available=set(),
        env_catalog={"gpu-a": {"torch"}, "gpu-b": {"torch"}, "cpu": set()},
    )
    assert r.ok is False
    assert set(r.alternative_envs) == {"gpu-a", "gpu-b"}
    assert "Ambiguous" in r.message or "\u5019\u9009" in r.message


def test_to_tool_result_payload_is_error_with_actionable_text():
    r = probe_dependencies(["torch"], env="e1", available=set())
    payload = r.to_tool_result_payload()
    assert payload["is_error"] is True
    assert "torch" in payload["content"]
    assert "conda" in payload["content"] or "pip" in payload["content"]


def test_env_none_single_candidate_reports_not_fabricate_placeholder():

    r = probe_dependencies(
        ["torch"],
        env=None,
        available=set(),
        env_catalog={"gpu-only": {"torch"}, "cpu": set()},
    )
    assert r.ok is False
    assert r.alternative_envs == ["gpu-only"]
    assert r.install_command is None
    assert "select" in r.message
