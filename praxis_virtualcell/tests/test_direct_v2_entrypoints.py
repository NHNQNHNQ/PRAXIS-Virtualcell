"""The generic direct-v2 path has one explicit Python/CLI/HTTP submission seam."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from praxis_vc_api.main import app, configure_direct_v2_factory
from praxis_vc_api.models.api_schema import ResearchTaskDescriptor
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


def _research_task_descriptor(request: object) -> dict:
    return {
        "schema_version": "vc.research-task.v1",
        "task_id": "test-only-direct-v2-research",
        "request": request.to_dict(),
        "pack_id": _PACK_ID,
        "pack_version": _PACK_VERSION,
        "model_name": _MODEL_NAME,
        "model_version": "dummy-v1",
        "execution_scope": "research_only",
        "scientifically_validated": False,
    }


def test_factory_compatibility_uses_the_registered_direct_v2_stack_without_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, request = _factory_and_request(tmp_path / "factory")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("compatibility must not prepare input or execute a model")

    monkeypatch.setattr(_ScalarAdapter, "prepare_input", forbidden)
    monkeypatch.setattr(_ScalarWrapper, "run_prediction", forbidden)

    plan = factory.compatibility(request, _PACK_ID, _PACK_VERSION)

    assert plan["schema_version"] == "vc.execution-plan.v2"
    assert plan["executable"] is True
    assert plan["steps"][0]["model_name"] == _MODEL_NAME
    assert plan["reports"][0]["research_execution_scope"] == "research_only"
    assert plan["reports"][0]["scientifically_validated"] is False
    rendered = json.dumps(plan, sort_keys=True)
    assert str(tmp_path) not in rendered
    assert "asset_paths" not in rendered
    assert "cache_root" not in rendered

    factory._wrapper_registry = WrapperRegistry()
    unavailable = factory.compatibility(request, _PACK_ID, _PACK_VERSION)
    assert unavailable["executable"] is False
    assert "model.wrapper" in unavailable["reports"][0]["reasons"]


def test_research_task_catalog_and_compatibility_are_explicit_read_only_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, request = _factory_and_request(tmp_path / "factory")
    descriptor = _research_task_descriptor(request)
    client = TestClient(app, raise_server_exceptions=False)
    executions: list[dict] = []

    def execute(request_payload, mode, enable_llm_report, pack_id, pack_version, **kwargs):
        executions.append(
            {
                "request": request_payload,
                "mode": mode,
                "enable_llm_report": enable_llm_report,
                "pack_id": pack_id,
                "pack_version": pack_version,
                **kwargs,
            }
        )
        return {"job_id": "bound-research-job", "status": "done"}

    monkeypatch.setattr("praxis_vc_api.main.svc.run_job", execute)

    configure_direct_v2_factory(None)
    assert client.get("/api/research-tasks").json() == {"tasks": []}
    configure_direct_v2_factory(factory, research_tasks=(descriptor,))
    try:
        catalog = client.get("/api/research-tasks")
        compatible = client.post("/api/research-tasks/test-only-direct-v2-research/compatibility")
        compatibility_payload = compatible.json()
        executed = client.post(
            "/api/research-tasks/test-only-direct-v2-research/execute",
            json={"compatibility_fingerprint": compatibility_payload["compatibility_fingerprint"]},
        )
        stale = client.post(
            "/api/research-tasks/test-only-direct-v2-research/execute",
            json={"compatibility_fingerprint": "0" * 64},
        )
        missing = client.post("/api/research-tasks/unknown/compatibility")
    finally:
        configure_direct_v2_factory(None)

    assert catalog.status_code == 200
    assert catalog.json() == {"tasks": [descriptor]}
    assert compatible.status_code == 200
    payload = compatible.json()
    assert payload["schema_version"] == "vc.research-task-compatibility.v1"
    assert payload["task_id"] == descriptor["task_id"]
    assert len(payload["descriptor_fingerprint"]) == 64
    assert len(payload["compatibility_fingerprint"]) == 64
    assert payload["execution_plan"]["executable"] is True
    assert payload["execution_plan"]["reports"][0]["research_execution_scope"] == "research_only"
    assert executed.status_code == 200
    assert executed.json() == {"job_id": "bound-research-job", "status": "done"}
    assert stale.status_code == 409
    assert stale.json() == {"detail": "research_task_compatibility_stale"}
    assert len(executions) == 1
    assert executions[0]["request"] == descriptor["request"]
    assert executions[0]["mode"] == "offline"
    assert executions[0]["enable_llm_report"] is False
    assert executions[0]["pack_id"] == _PACK_ID
    assert executions[0]["pack_version"] == _PACK_VERSION
    assert executions[0]["submission_contract"] == "vc.direct-v2-execution.v1"
    assert executions[0]["direct_v2_factory"] is factory
    assert missing.status_code == 404
    assert missing.json() == {"detail": "research_task_not_found"}
    rendered = json.dumps({"catalog": catalog.json(), "compatibility": payload}, sort_keys=True)
    assert str(tmp_path) not in rendered
    assert "asset_paths" not in rendered


def test_research_task_compatibility_fails_closed_without_a_factory(tmp_path: Path) -> None:
    _factory, request = _factory_and_request(tmp_path / "factory")
    configure_direct_v2_factory(
        None,
        research_tasks=(_research_task_descriptor(request),),
    )
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/research-tasks/test-only-direct-v2-research/compatibility"
        )
    finally:
        configure_direct_v2_factory(None)

    assert response.status_code == 503
    assert response.json() == {"detail": "direct_v2_factory_unconfigured"}


def test_research_task_compatibility_rejects_descriptor_model_drift(tmp_path: Path) -> None:
    factory, request = _factory_and_request(tmp_path / "factory")
    descriptor = _research_task_descriptor(request)
    descriptor["model_name"] = "wrong_model"
    configure_direct_v2_factory(factory, research_tasks=(descriptor,))
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/research-tasks/test-only-direct-v2-research/compatibility"
        )
    finally:
        configure_direct_v2_factory(None)

    assert response.status_code == 409
    assert response.json() == {"detail": "research_task_unavailable"}


def test_research_task_schema_rejects_unknown_fields_and_private_paths(tmp_path: Path) -> None:
    _factory, request = _factory_and_request(tmp_path / "factory")
    descriptor = _research_task_descriptor(request)

    with pytest.raises(ValueError):
        ResearchTaskDescriptor.model_validate({**descriptor, "cache_root": str(tmp_path)})

    descriptor["request"]["metadata"]["server_root"] = str(tmp_path)
    with pytest.raises(ValueError, match="rooted local paths"):
        ResearchTaskDescriptor.model_validate(descriptor)

    descriptor = _research_task_descriptor(request)
    descriptor["request"]["metadata"]["server_root"] = "../../private/cache"
    with pytest.raises(ValueError, match="rooted local paths"):
        ResearchTaskDescriptor.model_validate(descriptor)


def test_research_task_configuration_detaches_and_deep_freezes_requests(tmp_path: Path) -> None:
    factory, request = _factory_and_request(tmp_path / "factory")
    descriptor = _research_task_descriptor(request)
    configured_payload = _research_task_descriptor(request)
    configured_payload["task_id"] = "test-only-direct-v2-research-model"
    configured = ResearchTaskDescriptor.model_validate(configured_payload)

    with pytest.raises(TypeError):
        configured.request.metadata["mutated"] = True

    configure_direct_v2_factory(factory, research_tasks=(descriptor, configured))
    descriptor["request"]["metadata"]["leak"] = "/private/server/root"
    try:
        tasks = TestClient(app).get("/api/research-tasks").json()["tasks"]
    finally:
        configure_direct_v2_factory(None)

    assert "leak" not in tasks[0]["request"]["metadata"]
    assert "leak" not in tasks[1]["request"]["metadata"]


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
    assert summary["execution_scope"] == "research_only"
    assert summary["scientifically_validated"] is False
    assert summary["models_used"] == [_MODEL_NAME]


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
        configured_tasks = []
        for task in app.state.research_tasks:
            payload = task.model_dump(mode="json")
            payload["request"] = task.request.to_dict()
            configured_tasks.append(payload)
        assert configured_tasks == [
            {
                "schema_version": "vc.research-task.v1",
                "task_id": "norman-2019-ahr-klf1-research",
                "request": golden.golden_ahr_klf1_request().to_dict(),
                "pack_id": golden.PACK_ID,
                "pack_version": golden.PACK_VERSION,
                "model_name": golden.MODEL_NAME,
                "model_version": golden.MODEL_VERSION,
                "execution_scope": "research_only",
                "scientifically_validated": False,
            }
        ]
        assert kwargs == {"host": "127.0.0.1", "port": 8765, "reload": False}

    configure_direct_v2_factory(None)
    monkeypatch.setattr(uvicorn, "run", run)
    assert cli_main(["serve", "--port", "8765", *root_args]) == 0
    assert app.state.direct_v2_factory is None
    assert app.state.research_tasks == ()
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
            "execution_scope": None,
            "scientifically_validated": None,
            "models_used": [],
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
            "execution_scope": None,
            "scientifically_validated": None,
            "models_used": [],
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
