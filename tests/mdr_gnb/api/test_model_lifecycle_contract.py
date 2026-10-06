"""P1 API contract: model declaration, runtime readiness, and validation differ."""
from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from praxis_virtualcell.mdr_gnb.api import service


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


_EC_MEROPENEM = {
    "species": "escherichia_coli",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC": True},
}

_EC_TRIMETHOPRIM = {
    "species": "escherichia_coli",
    "smiles": "COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC",
    "drug_panel": [{"drug": "trimethoprim", "drug_class": "novel_compound"}],
    "requested_outputs": ["activity"],
}


def test_models_lifecycle_is_probed_and_does_not_promote_limited_models(client):
    payload = client.get("/models").json()
    lifecycle = payload["model_lifecycle"]

    assert lifecycle["readiness_check"] == (
        "artifact_sha256_dependency_deserialization_schema_probe"
    )
    assert len(lifecycle["catalog_digest"]) == 64
    assert lifecycle["declared"] == sum(model["declared"] for model in lifecycle["models"])
    assert lifecycle["ready"] == sum(model["ready"] for model in lifecycle["models"])
    assert lifecycle["validated"] == sum(model["validated"] for model in lifecycle["models"])
    # Current catalog has only limited/unverified scientific evidence.  A successful
    # load probe must not upgrade that fact to `validated`.
    assert lifecycle["validated"] == 0
    assert all(model["validated"] is False for model in lifecycle["models"])

    mero = next(
        model for model in lifecycle["models"]
        if model["id"] == "sir/escherichia_coli/meropenem"
    )
    assert mero["declared"] is True
    assert mero["ready"] is True
    assert mero["validated"] is False
    assert mero["validation_status"] == "limited"
    assert mero["reason_code"] == "ready"
    assert mero["expected_sha256"]


def test_prediction_and_trace_carry_the_catalog_identity_without_changing_task_id():
    result = service.predict(_EC_MEROPENEM)
    response = result["response"]
    identity = response["model_lifecycle"]

    assert identity == result["trace_record"]["model_lifecycle"]
    assert set(identity) == {"catalog_version", "catalog_digest"}
    assert identity == service.model_lifecycle_identity()
    # The response keeps content-addressed request identity semantics; the model
    # digest is provenance, not an unannounced input mutation.
    assert response["task_id"] == service.canonical_task_id(_EC_MEROPENEM)
    assert response["execution_id"] == result["trace_record"]["execution_id"]
    assert response["runtime_policy_version"] == service.RUNTIME_POLICY_VERSION
    capability = result["trace_record"]["capability"]
    assert capability["catalog_digest"] == identity["catalog_digest"]
    assert capability["selected"] == [
        {
            "model_id": "sir/escherichia_coli/meropenem",
            "catalog_digest": identity["catalog_digest"],
            "artifact_sha256": capability["requested"][0]["expected_sha256"],
            "ready": True,
        }
    ]


def test_cached_response_identity_contract_requires_every_execution_fact():
    """A cache hit must carry the exact public facts used to namespace it."""
    preflight = service.runtime_model_execution_context(_EC_MEROPENEM)
    governance_context = service.governance_execution_context()
    result = service.predict(
        _EC_MEROPENEM,
        runtime_model_preflight=preflight,
        governance_context=governance_context,
    )
    response = result["response"]
    expected_key = service.execution_cache_key(
        _EC_MEROPENEM,
        lifecycle_identity=preflight.lifecycle_identity,
        governance_snapshot=governance_context.snapshot,
        requested_model_integrity=preflight.requested_model_integrity,
    )

    def matches(candidate):
        return service.cache_response_matches_execution(
            candidate,
            execution_id=expected_key,
            lifecycle_identity=preflight.lifecycle_identity,
            governance_snapshot=governance_context.snapshot,
            requested_model_integrity=preflight.requested_model_integrity,
        )

    assert matches(response)
    for key, value in (
        ("execution_id", "mdr-exec-stale"),
        ("model_lifecycle", {"catalog_version": "stale", "catalog_digest": "f" * 64}),
        ("requested_model_integrity", {"requested_readiness_digest": "f" * 64}),
        ("governance_snapshot", {"schema_version": "stale", "governance_digest": "f" * 64}),
        ("runtime_policy_version", "stale-policy"),
    ):
        stale = copy.deepcopy(response)
        stale[key] = value
        assert not matches(stale), key


def test_service_passes_the_captured_runtime_model_context_to_core(monkeypatch):
    """Route/readiness/load provenance must share the pre-cache observation."""
    preflight = service.runtime_model_execution_context(_EC_MEROPENEM)
    observed_contexts = []
    original = service.run_mdr_query

    def _capture_core_context(*args, **kwargs):
        observed_contexts.append(kwargs.get("runtime_manifest"))
        return original(*args, **kwargs)

    monkeypatch.setattr(service, "run_mdr_query", _capture_core_context)
    result = service.predict(
        _EC_MEROPENEM,
        runtime_model_preflight=preflight,
    )

    assert observed_contexts == [preflight.context]
    assert result["response"]["requested_model_integrity"] == (
        preflight.requested_model_integrity
    )
    assert result["trace_record"]["requested_model_integrity"] == (
        preflight.requested_model_integrity
    )
    preflight_event = next(
        event
        for event in result["trace_record"]["trace"]
        if event["message_type"] == "runtime_model_preflight_bound"
    )
    assert preflight_event["payload"] == {
        "schema_version": "mdr-trace-v1",
        "model_context": preflight.requested_model_integrity,
    }


def test_default_mechanism_sidecar_uses_the_captured_request_manifest(monkeypatch):
    """The production mechanism path must not replace an API preflight manifest.

    The small-molecule predictor remains real here.  Only the bounded FBA sidecar
    is substituted so the test can assert request-scoped plumbing without running
    a solver or creating a second, implicit catalog observation.
    """
    from praxis_virtualcell.mdr_gnb.predictors.mechanistic import gem_fba
    from praxis_virtualcell.mdr_gnb.coordinator import mechanism_fusion

    raw = {
        "species": "escherichia_coli",
        "smiles": "OC(=O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O",
        "drug_panel": [{"drug": "ciprofloxacin", "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
    }
    preflight = service.runtime_model_execution_context(raw)
    assert preflight.context is not None
    observed_manifests = []

    class _CapturingGemFbaPredictor:
        def predict(self, *, species, drug, sidecar_manifest=None):
            observed_manifests.append(sidecar_manifest)
            manifest = sidecar_manifest
            contract = {
                "contract_version": "mdr-gem-sidecar-v1",
                "model_id": "mechanism/escherichia_coli/iml1515",
                "declared": True,
                "operational": True,
                "reason_code": "ready",
                "execution": "experimental",
                "artifact_path": "data/mdr_gnb/gems/iML1515.xml.gz",
                "expected_sha256": "test-sidecar-sha256",
                "dependency_versions": {"cobra": "test"},
                "catalog_digest": getattr(manifest, "catalog_digest", "unbound"),
            }
            return SimpleNamespace(
                abstained=False,
                abstain_reason=None,
                growth_inhibition=1.0,
                baseline_growth=0.9,
                constrained_growth=0.0,
                mechanism="synthetic request-context plumbing probe",
                evidence=[
                    {"kind": "gem_sidecar_contract", **contract},
                    {"kind": "fba", "reactions_blocked": ["DHFR"]},
                ],
            )

    monkeypatch.setattr(gem_fba, "GemFbaPredictor", _CapturingGemFbaPredictor)
    mechanism_fusion._default_predictor.cache_clear()
    try:
        result = service.predict(raw, runtime_model_preflight=preflight)
        response = result["response"]
        contract = response["report"]["mechanism"]["sidecar_contract"]

        assert observed_manifests == [preflight.context.manifest]
        assert contract["catalog_digest"] == preflight.context.catalog_digest
        mechanism_event = next(
            event
            for event in result["trace_record"]["trace"]
            if event["message_type"] == "mechanism_evaluated"
        )
        assert mechanism_event["payload"]["sidecar_contract"] == contract
    finally:
        mechanism_fusion._default_predictor.cache_clear()


def test_actual_fba_sidecar_contract_is_bound_to_the_api_request_context():
    """A real production FBA run exposes the same sidecar contract in trace/report."""
    pytest.importorskip("cobra")
    artifact = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "mdr_gnb"
        / "gems"
        / "iML1515.xml.gz"
    )
    if not artifact.is_file():
        pytest.skip("iML1515 artifact unavailable")

    preflight = service.runtime_model_execution_context(_EC_TRIMETHOPRIM)
    assert preflight.context is not None
    assert len(preflight.context.experimental_sidecars) == 1
    result = service.predict(
        _EC_TRIMETHOPRIM,
        runtime_model_preflight=preflight,
    )
    report = result["response"]["report"]
    mechanism = report["mechanism"]
    assert report["abstained"] is False
    assert mechanism["available"] is True
    assert mechanism["engine"] == "gem_fba"
    assert mechanism["fba_simulation"]["reactions_blocked"] == ["DHFR"]
    assert mechanism["g3_gate"]["status"] == "not_evaluated"
    assert mechanism["mechanism_claim"] is None

    contract = mechanism["sidecar_contract"]
    assert contract == preflight.context.experimental_sidecars[0].as_dict()
    assert contract["model_id"] == "mechanism/escherichia_coli/iml1515"
    assert contract["operational"] is True
    assert len(contract["expected_sha256"]) == 64
    assert contract["dependency_versions"] == {
        "cobra": "0.31.1",
        "optlang": "1.9.1",
        "swiglpk": "5.0.13",
    }

    events = {
        event["message_type"]: event for event in result["trace_record"]["trace"]
    }
    mechanism_event = events["mechanism_evaluated"]
    assert mechanism_event["payload"]["sidecar_contract"] == contract
    assert mechanism_event["parent_message_id"] == events["abstain_decided"]["message_id"]
    assert events["rule_fusion_done"]["parent_message_id"] == mechanism_event["message_id"]


def test_default_mechanism_fusion_does_not_depend_on_offline_g3_runner_anchors(
    monkeypatch,
):
    """The request path may read G3 anchor data, but must not invoke its offline gate.

    ``run_g3_gate`` builds ``BacterialCellState`` and runs a full offline
    falsifiability workflow.  Production fusion only needs the small, immutable
    shared anchor membership lookup to preserve the conservative ``not_evaluated``
    boundary.  If that offline module becomes unavailable or changes behavior,
    the activity-sidecar result must remain a bounded candidate rather than being
    silently degraded or promoted.
    """
    from praxis_virtualcell.mdr_gnb.coordinator import mechanism_fusion
    from praxis_virtualcell.mdr_gnb.g3_anchors import G3_ANCHORS
    from praxis_virtualcell.mdr_gnb.predictors.mechanistic import run_g3_gate

    class _OfflineRunnerAnchors:
        def __contains__(self, _key):
            raise AssertionError("production fusion touched offline G3 runner state")

    class _ReadyFba:
        def predict(self, *, species, drug):
            return SimpleNamespace(
                abstained=False,
                abstain_reason=None,
                growth_inhibition=1.0,
                baseline_growth=0.9,
                constrained_growth=0.0,
                mechanism="candidate only",
                evidence=[{"kind": "fba", "reactions_blocked": ["DHFR"]}],
            )

    assert run_g3_gate.ANCHORS is G3_ANCHORS
    monkeypatch.setattr(run_g3_gate, "ANCHORS", _OfflineRunnerAnchors())
    mechanism = mechanism_fusion.fuse_mechanism(
        "escherichia_coli",
        "trimethoprim",
        predictor=_ReadyFba(),
    )

    assert mechanism["available"] is True
    assert mechanism["g3_gate"] == {
        "status": "not_evaluated",
        "claim_allowed": False,
    }
    assert mechanism["mechanism_claim"] is None
    assert "predictors.mechanistic.run_g3_gate" not in (
        mechanism_fusion._default_g3_status.__code__.co_names
    )


def test_cache_namespace_changes_when_catalog_or_policy_changes(monkeypatch):
    monkeypatch.setattr(
        service,
        "model_lifecycle_identity",
        lambda: {"catalog_version": "test", "catalog_digest": "a" * 64},
    )
    original = service.execution_cache_key(_EC_MEROPENEM)
    raw_task_id = service.canonical_task_id(_EC_MEROPENEM)

    monkeypatch.setattr(
        service,
        "model_lifecycle_identity",
        lambda: {"catalog_version": "test", "catalog_digest": "b" * 64},
    )
    changed_catalog = service.execution_cache_key(_EC_MEROPENEM)
    monkeypatch.setattr(service, "RUNTIME_POLICY_VERSION", "mdr-readiness-v2")
    changed_policy = service.execution_cache_key(_EC_MEROPENEM)

    assert original != changed_catalog != changed_policy
    assert raw_task_id == service.canonical_task_id(_EC_MEROPENEM)
