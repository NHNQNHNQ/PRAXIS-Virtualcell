"""T4-08: MDR core, HTTP API, and dedicated CLI must share one contract."""
from __future__ import annotations

import hashlib
import json
import sys
import tomllib
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.api.app import create_app
from praxis_virtualcell.mdr_gnb.api.schemas import PredictRequest
from praxis_virtualcell.mdr_gnb.cli import main
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


# Deliberately omit drug_class: the test proves the CLI uses the same Pydantic
# normalization as FastAPI before it reaches the MDR core.
_REQUESTS = [
    {
        "species": "escherichia_coli",
        "drug_panel": [{"drug": "ceftriaxone"}],
        "requested_outputs": ["SIR"],
        "amr_profile": {"blaCTX-M-15": True},
    },
    {
        "species": "morganella_morganii",
        "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
        "requested_outputs": ["SIR"],
        "amr_profile": {"blaKPC": True},
    },
    {
        "species": "escherichia_coli",
        "drug_panel": [{"drug": "C", "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
        "smiles": "C",
    },
]


class _DriftedRuntimeModelContext:
    """A pre-cache receipt that becomes unsafe before either adapter executes."""

    def assert_current(self) -> None:
        raise RuntimeError("simulated catalog/artifact drift")


def _report_sha256(report: dict) -> str:
    blob = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_dedicated_mdr_console_script_is_registered():
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[3] / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"]["scripts"]["praxis-mdr"] == (
        "praxis_virtualcell.mdr_gnb.cli:main"
    )


@pytest.mark.parametrize("payload", _REQUESTS)
def test_mdr_cli_matches_normalized_core_and_http(payload, tmp_path, capsys):
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["run", "--request", str(request_path)]) == 0
    cli_response = json.loads(capsys.readouterr().out)

    normalized = PredictRequest.model_validate(payload).to_raw()
    core = run_mdr_query(
        normalized,
        seed_task_id=service.canonical_task_id(normalized),
    )
    http_response = TestClient(create_app()).post("/predict", json=payload).json()

    # The CLI emits the exact /predict response; it does not invent a parallel
    # request schema, runtime-evidence policy, or active-learning projection.
    assert cli_response == http_response
    assert cli_response["task_id"] == core["report"]["task_id"]
    assert cli_response["report"] == core["report"]
    assert _report_sha256(cli_response["report"]) == core["trace_metadata"][
        "report_sha256"
    ]


def test_mdr_cli_reads_stdin_and_rejects_invalid_json(monkeypatch, capsys):
    request = _REQUESTS[0]
    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(read=lambda: json.dumps(request)))
    assert main(["run", "--stdin"]) == 0
    assert json.loads(capsys.readouterr().out)["task_id"] == service.canonical_task_id(
        PredictRequest.model_validate(request).to_raw()
    )

    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(read=lambda: "not-json"))
    assert main(["run", "--stdin"]) == 2
    assert "invalid JSON" in capsys.readouterr().err

    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(read=lambda: '{"species": 42}'))
    assert main(["run", "--stdin"]) == 2
    assert "invalid request schema" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("detail", "context"),
    [
        ("runtime_model_preflight_unavailable", None),
        ("request_artifact_integrity_drift", _DriftedRuntimeModelContext()),
    ],
)
def test_mdr_cli_fails_closed_like_http_for_runtime_model_integrity(
    detail,
    context,
    monkeypatch,
    tmp_path,
    capsys,
):
    """CLI must expose the same safe availability code as the HTTP adapter.

    A CLI has no HTTP status/header channel, so it uses exit 1 and a single
    machine-readable stderr line.  It must never print a report or call the
    service core under an unobservable or drifted model receipt.
    """
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(_REQUESTS[0]), encoding="utf-8")

    def failed_preflight(_raw):
        return service.RuntimeModelPreflight(
            context=context,
            lifecycle_identity={"catalog_version": "test", "catalog_digest": "test"},
            requested_model_integrity={
                "schema_version": "test",
                "catalog_version": "test",
                "catalog_digest": "test",
                "requested_readiness_digest": "test",
                "requested_capability_count": 0,
                "preflight_state": "test",
            },
            cacheable=False,
        )

    def never_predict(*_args, **_kwargs):
        raise AssertionError("core prediction must not run after a failed runtime preflight")

    monkeypatch.setattr(service, "runtime_model_execution_context", failed_preflight)
    monkeypatch.setattr(service, "predict", never_predict)

    http = TestClient(create_app()).post("/predict", json=_REQUESTS[0])
    assert http.status_code == 503
    assert http.headers["X-MDR-Cache"] == "bypass"
    assert http.json() == {"detail": detail}

    assert main(["run", "--request", str(request_path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{detail}\n"


def test_mdr_cli_serve_targets_the_mdr_asgi_entrypoint(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def fake_run(target: str, **kwargs) -> None:
        calls.append((target, kwargs))

    monkeypatch.setitem(sys.modules, "uvicorn", types.SimpleNamespace(run=fake_run))

    assert main(["serve", "--host", "127.0.0.1", "--port", "8111"]) == 0
    assert calls == [
        (
            "praxis_virtualcell.mdr_gnb.api.asgi:app",
            {"host": "127.0.0.1", "port": 8111, "reload": False},
        )
    ]
