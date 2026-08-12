"""The generic direct-v2 path has one explicit Python/CLI/HTTP submission seam."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from praxis_vc_api.main import app, configure_direct_v2_factory
from praxis_virtualcell.cli import main as cli_main
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.io.job_store import JobStore
from praxis_virtualcell.model_zoo.adapter_sdk import AdapterRegistry
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.wrapper_registry import WrapperRegistry
from praxis_virtualcell.tests.test_capability_runtime import (
    _MODEL_BYTES,
    _TEST_ARTIFACT_SNAPSHOT_BUDGET,
    _card,
    _pack_registry,
    _v2_registry_and_environment,
    _write_registry,
)
from praxis_virtualcell.tests.test_direct_v2_single_model import (
    _MODEL_NAME,
    _pack_bound_request,
    _ScalarAdapter,
    _ScalarWrapper,
)
from praxis_virtualcell.workflows.runtime_builder import DirectV2RuntimeFactory
from praxis_virtualcell.workflows.submit_job import submit_direct_v2_job_from_factory

_PACK_ID = "tiny-human-scrna"
_PACK_VERSION = "0.1.0"


def _factory_and_request(tmp_path: Path) -> tuple[DirectV2RuntimeFactory, object]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    request = _pack_bound_request()
    card = _card()
    card.update(
        {
            "name": _MODEL_NAME,
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    packs = _pack_registry()
    pack = packs.record(_PACK_ID, _PACK_VERSION)
    adapter = _ScalarAdapter()
    registry_v2, environment = _v2_registry_and_environment(
        card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET,
    )
    zoo = _write_registry(tmp_path, card, registry_v2=registry_v2)
    cache = ModelCache(root=str(tmp_path / "cache"))
    asset_path = cache.asset_path(_MODEL_NAME, "model.bin")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(card["wrapper"], _ScalarWrapper)
    return (
        DirectV2RuntimeFactory(
            registry=zoo,
            cache=cache,
            pack_registry=packs,
            environment=environment,
            adapter_registry=AdapterRegistry([adapter]),
            wrapper_registry=wrappers,
        ),
        request,
    )


def _direct_v2_body(request: object) -> dict:
    return {
        "request": request.to_dict(),
        "mode": "offline",
        "pack_id": _PACK_ID,
        "pack_version": _PACK_VERSION,
        "submission_contract": "vc.direct-v2-execution.v1",
    }


def test_http_direct_v2_requires_explicit_factory_and_never_uses_p17(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import praxis_vc_api.services.runtime_service as runtime_service

    monkeypatch.setenv("PRAXIS_VC_RUNS", str(tmp_path / "runs"))
    runtime_service = importlib.reload(runtime_service)
    configure_direct_v2_factory(None)
    client = TestClient(app, raise_server_exceptions=False)
    factory, request = _factory_and_request(tmp_path / "factory")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("direct-v2 must not enter the P17 compiler")

    monkeypatch.setattr(runtime_service, "virtual_experiment_payload", forbidden)
    unavailable = client.post("/api/jobs", json=_direct_v2_body(request))
    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "direct_v2_factory_unconfigured"}
    assert not (tmp_path / "runs").exists()

    llm_body = _direct_v2_body(request)
    llm_body["mode"] = "llm_assisted"
    llm_rejected = client.post("/api/jobs", json=llm_body)
    assert llm_rejected.status_code == 400
    assert llm_rejected.json() == {"detail": "invalid_request"}
    assert not (tmp_path / "runs").exists()

    configure_direct_v2_factory(factory)
    try:
        submitted = client.post("/api/jobs", json=_direct_v2_body(request))
    finally:
        configure_direct_v2_factory(None)

    assert submitted.status_code == 200
    loaded = JobStore(str(tmp_path / "runs")).load(submitted.json()["job_id"])
    assert loaded["report"]["abstain"] is False
    assert loaded["provenance"]["execution_contract"] == "vc.direct-v2-execution.v1"
    summary = runtime_service.list_jobs()[0]
    assert summary["species"] == "human"
    assert summary["perturbation_targets"] == ["AHR"]
    assert summary["pack_id"] == _PACK_ID
    assert summary["pack_version"] == _PACK_VERSION


def test_python_cli_and_http_use_the_same_explicit_direct_v2_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    factory, request = _factory_and_request(tmp_path / "factory")
    python_store = JobStore(str(tmp_path / "python-runs"))
    python_job = submit_direct_v2_job_from_factory(
        request,
        factory=factory,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        job_store=python_store,
        job_id="python-direct-v2",
    )
    python_identity = python_store.load(python_job["job_id"])["execution_identity"]

    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request.to_dict()), encoding="utf-8")
    cli_root = tmp_path / "cli-runs"
    assert (
        cli_main(
            [
                "direct-v2",
                "run",
                "--request",
                str(request_path),
                "--pack-id",
                _PACK_ID,
                "--pack-version",
                _PACK_VERSION,
                "--out",
                str(cli_root / "cli-direct-v2"),
            ],
            direct_v2_factory=factory,
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {
        "job_id": "cli-direct-v2",
        "status": "done",
    }
    cli_identity = JobStore(str(cli_root)).load("cli-direct-v2")["execution_identity"]

    import praxis_vc_api.services.runtime_service as runtime_service

    monkeypatch.setenv("PRAXIS_VC_RUNS", str(tmp_path / "http-runs"))
    runtime_service = importlib.reload(runtime_service)
    configure_direct_v2_factory(factory)
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/jobs",
            json=_direct_v2_body(request),
        )
    finally:
        configure_direct_v2_factory(None)

    assert response.status_code == 200
    http_identity = JobStore(str(tmp_path / "http-runs")).load(response.json()["job_id"])["execution_identity"]
    assert python_identity == cli_identity == http_identity


def test_direct_v2_runtime_return_never_exposes_private_asset_paths(tmp_path: Path) -> None:
    """The Python runtime return has the same public redaction as persisted jobs."""

    factory, request = _factory_and_request(tmp_path / "factory")

    result = factory.build().run_workflow_v2(
        request,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
    )

    rendered = json.dumps(result, sort_keys=True)
    assert str(tmp_path / "factory" / "cache") not in rendered
    assert "asset_paths" not in rendered
    assert "cache_root" not in rendered

    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job_from_factory(
        request,
        factory=factory,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
        job_store=store,
        job_id="public-python-result",
    )
    loaded = store.load(submitted["job_id"])
    assert result == loaded["report"]
    assert result["provenance"] == loaded["provenance"]


def test_direct_v2_export_outputs_projects_only_the_matching_three_message_chain(tmp_path: Path) -> None:
    factory, request = _factory_and_request(tmp_path / "factory")
    runtime = factory.build()
    runtime.bus.send(
        AgentMessage(
            "unrelated-before",
            "noise",
            "sink",
            "unrelated",
            {"value": "before"},
            "2026-08-12T00:00:00Z",
        )
    )
    report = runtime.run_workflow_v2(
        request,
        pack_id=_PACK_ID,
        pack_version=_PACK_VERSION,
    )
    runtime.bus.send(
        AgentMessage(
            "unrelated-after",
            "noise",
            "sink",
            "unrelated",
            {"value": "after"},
            "2026-08-12T00:00:01Z",
        )
    )
    cache_root = str(tmp_path / "factory" / "cache")
    raw_plan = runtime.bus.latest("execution_plan_ready").payload["execution_plan"]
    assert cache_root in json.dumps(raw_plan, sort_keys=True)

    runtime.export_outputs(str(tmp_path / "export"), report)

    trace = json.loads((tmp_path / "export" / "trace.json").read_text(encoding="utf-8"))
    assert cache_root not in json.dumps(trace, sort_keys=True)
    assert len(trace) == 3
    assert [message["message_type"] for message in trace] == [
        "execution_plan_v2_request",
        "execution_plan_ready",
        "execution_result_ready",
    ]
    assert trace[1]["parent_message_id"] == trace[0]["message_id"]
    assert trace[2]["parent_message_id"] == trace[1]["message_id"]
    assert all("payload" not in message and "payload_fingerprint" in message for message in trace)


def test_direct_v2_cli_without_an_injected_factory_fails_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _factory, request = _factory_and_request(tmp_path / "factory")
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request.to_dict()), encoding="utf-8")

    assert (
        cli_main(
            [
                "direct-v2",
                "run",
                "--request",
                str(request_path),
                "--pack-id",
                _PACK_ID,
                "--pack-version",
                _PACK_VERSION,
                "--out",
                str(tmp_path / "unavailable-runs" / "job"),
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out) == {
        "status": "rejected",
        "reason": "direct_v2_factory_unconfigured",
    }
    assert not (tmp_path / "unavailable-runs").exists()


def test_cli_loads_one_explicit_golden_factory_for_run_and_serve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import uvicorn

    import praxis_virtualcell.model_zoo.golden_additive_research as golden

    factory, request = _factory_and_request(tmp_path / "factory")
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request.to_dict()), encoding="utf-8")
    roots = {
        "registration_root": str(tmp_path / "registration"),
        "pack_root": str(tmp_path / "pack"),
        "model_cache_root": str(tmp_path / "cache"),
    }
    observed: list[dict] = []

    class Loaded:
        def factory(self):
            return factory

    def load(**kwargs):
        observed.append(kwargs)
        return Loaded()

    monkeypatch.setattr(golden, "load_golden_additive_research", load)
    root_args = [
        "--golden-registration-root",
        roots["registration_root"],
        "--golden-pack-root",
        roots["pack_root"],
        "--golden-model-cache-root",
        roots["model_cache_root"],
    ]
    assert (
        cli_main(
            [
                "direct-v2",
                "run",
                "--request",
                str(request_path),
                "--pack-id",
                _PACK_ID,
                "--pack-version",
                _PACK_VERSION,
                "--out",
                str(tmp_path / "runs" / "golden-cli"),
                *root_args,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {
        "job_id": "golden-cli",
        "status": "done",
    }

    def run(asgi_app, **kwargs):
        assert asgi_app is app
        assert app.state.direct_v2_factory is factory
        assert kwargs == {"host": "127.0.0.1", "port": 8765, "reload": False}

    configure_direct_v2_factory(None)
    monkeypatch.setattr(uvicorn, "run", run)
    assert cli_main(["serve", "--port", "8765", *root_args]) == 0
    assert app.state.direct_v2_factory is None
    assert observed == [roots, roots]


def test_cli_rejects_partial_golden_roots_before_job_creation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _factory, request = _factory_and_request(tmp_path / "factory")
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request.to_dict()), encoding="utf-8")
    assert (
        cli_main(
            [
                "direct-v2",
                "run",
                "--request",
                str(request_path),
                "--pack-id",
                _PACK_ID,
                "--pack-version",
                _PACK_VERSION,
                "--out",
                str(tmp_path / "runs" / "partial"),
                "--golden-registration-root",
                str(tmp_path / "registration"),
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out) == {
        "status": "rejected",
        "reason": "golden_research_configuration_invalid",
    }
    assert not (tmp_path / "runs").exists()


def test_direct_v2_cli_reports_duplicate_job_without_second_execution(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    factory, request = _factory_and_request(tmp_path / "factory")
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request.to_dict()), encoding="utf-8")
    output = tmp_path / "runs" / "duplicate-job"
    args = [
        "direct-v2",
        "run",
        "--request",
        str(request_path),
        "--pack-id",
        _PACK_ID,
        "--pack-version",
        _PACK_VERSION,
        "--out",
        str(output),
    ]

    assert cli_main(args, direct_v2_factory=factory) == 0
    assert json.loads(capsys.readouterr().out) == {
        "job_id": "duplicate-job",
        "status": "done",
    }

    assert cli_main(args, direct_v2_factory=factory) == 2
    assert json.loads(capsys.readouterr().out) == {
        "status": "rejected",
        "reason": "job_already_exists",
    }


def test_direct_v2_http_maps_job_id_collision_without_second_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import praxis_vc_api.services.runtime_service as runtime_service

    monkeypatch.setenv("PRAXIS_VC_RUNS", str(tmp_path / "runs"))
    importlib.reload(runtime_service)
    monkeypatch.setattr(
        runtime_service,
        "_job_id",
        lambda *_args, **_kwargs: "http-direct-v2-collision",
    )
    factory, request = _factory_and_request(tmp_path / "factory")
    configure_direct_v2_factory(factory)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        first = client.post("/api/jobs", json=_direct_v2_body(request))
        second = client.post("/api/jobs", json=_direct_v2_body(request))
    finally:
        configure_direct_v2_factory(None)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json() == {"detail": "job_already_exists"}
    assert first.json() == {"job_id": "http-direct-v2-collision", "status": "done"}
    assert JobStore(str(tmp_path / "runs")).list_jobs() == ["http-direct-v2-collision"]


def test_list_jobs_marks_wrong_typed_done_companion_corrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed completed job must not make the Jobs listing fail."""

    import praxis_vc_api.services.runtime_service as runtime_service

    monkeypatch.setenv("PRAXIS_VC_RUNS", str(tmp_path / "runs"))
    runtime_service = importlib.reload(runtime_service)
    job_root = tmp_path / "runs" / "wrong-typed-companion"
    job_root.mkdir(parents=True)
    (job_root / "status").write_text("done", encoding="utf-8")
    (job_root / "request.json").write_text("[1]", encoding="utf-8")

    assert runtime_service.list_jobs() == [
        {
            "job_id": "wrong-typed-companion",
            "status": "corrupt",
            "species": None,
            "perturbation_targets": [],
            "abstain": None,
            "reliability": None,
            "pack_id": None,
            "pack_version": None,
            "pack_fingerprint": None,
        }
    ]


def test_list_jobs_projects_deep_json_companion_as_corrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An archive decoder RecursionError must not turn the Jobs list into a 500."""

    import praxis_vc_api.services.runtime_service as runtime_service

    monkeypatch.setenv("PRAXIS_VC_RUNS", str(tmp_path / "runs"))
    runtime_service = importlib.reload(runtime_service)
    job_root = tmp_path / "runs" / "deep-json-companion"
    job_root.mkdir(parents=True)
    (job_root / "status").write_text("done", encoding="utf-8")
    (job_root / "request.json").write_text("[" * 20_000 + "]" * 20_000, encoding="utf-8")

    assert runtime_service.list_jobs() == [
        {
            "job_id": "deep-json-companion",
            "status": "corrupt",
            "species": None,
            "perturbation_targets": [],
            "abstain": None,
            "reliability": None,
            "pack_id": None,
            "pack_version": None,
            "pack_fingerprint": None,
        }
    ]


def test_job_identity_keeps_p17_and_direct_v2_submissions_distinct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import praxis_vc_api.services.runtime_service as runtime_service

    monkeypatch.setenv("PRAXIS_VC_RUNS", str(tmp_path / "runs"))
    runtime_service = importlib.reload(runtime_service)

    p17_job_id = runtime_service._job_id(
        _pack_bound_request().to_dict(),
        _PACK_ID,
        _PACK_VERSION,
        submission_contract="vc.virtual-experiment-compilation.v1",
    )
    direct_v2_job_id = runtime_service._job_id(
        _pack_bound_request().to_dict(),
        _PACK_ID,
        _PACK_VERSION,
        submission_contract="vc.direct-v2-execution.v1",
    )

    assert p17_job_id != direct_v2_job_id
