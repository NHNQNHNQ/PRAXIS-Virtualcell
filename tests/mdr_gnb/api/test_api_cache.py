"""9.3 API↔缓存集成(fakeredis DI,常规套件)。缓存命中返回逐字相等响应,
X-MDR-Cache 头标 hit/miss;无 cache 时行为不变。"""
import copy

import fakeredis
from dataclasses import replace
from fastapi.testclient import TestClient

from praxis_virtualcell.mdr_gnb.api.app import create_app
from praxis_virtualcell.mdr_gnb.api.cache import PredictionCache
from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.api.service import canonical_task_id
from praxis_virtualcell.model_zoo.runtime_manifest import (
    RuntimeModelExecutionContext,
    RuntimeModelManifest,
)

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts

KP = {
    "species": "klebsiella_pneumoniae",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC-2": True},
}

EC_CIPRO_ACTIVITY = {
    "species": "escherichia_coli",
    "smiles": "OC(=O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O",
    "drug_panel": [{"drug": "ciprofloxacin", "drug_class": "novel_compound"}],
    "requested_outputs": ["activity"],
}


def test_predict_cache_hit_identical():
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    c = TestClient(create_app(cache=cache))
    r1 = c.post("/predict", json=KP)
    r2 = c.post("/predict", json=KP)
    assert r1.json() == r2.json()                       # 逐字相等
    assert r1.headers.get("x-mdr-cache") == "miss"
    assert r2.headers.get("x-mdr-cache") == "hit"       # 第二次命中


def test_cached_predict_rechecks_runtime_context_before_return(monkeypatch):
    """A cache hit must fail closed when its captured artifact receipt drifted."""
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    client = TestClient(create_app(cache=cache))
    assert client.post("/predict", json=KP).headers.get("x-mdr-cache") == "miss"

    def _drifted_context(_self):
        raise ValueError("request_artifact_integrity_drift")

    def _predict_must_not_run(*_args, **_kwargs):
        raise AssertionError("drifted cache hit must not reach core prediction")

    monkeypatch.setattr(
        RuntimeModelExecutionContext,
        "assert_current",
        _drifted_context,
        raising=False,
    )
    monkeypatch.setattr(service, "predict", _predict_must_not_run)

    response = client.post("/predict", json=KP)

    assert response.status_code == 503
    assert response.headers.get("x-mdr-cache") == "bypass"
    assert response.json()["detail"] == "request_artifact_integrity_drift"


def test_cached_payload_with_mismatched_identity_is_recomputed(monkeypatch):
    """A shared-cache entry cannot bypass the current execution identity contract."""
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    client = TestClient(create_app(cache=cache))
    first = client.post("/predict", json=KP)
    assert first.headers.get("x-mdr-cache") == "miss"
    expected = first.json()

    stale_payload = copy.deepcopy(expected)
    stale_payload["execution_id"] = "mdr-exec-stale-payload"
    stale_payload["requested_model_integrity"]["requested_readiness_digest"] = "f" * 64
    cache.set(expected["execution_id"], stale_payload)

    calls = 0
    original_predict = service.predict

    def _count_recompute(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_predict(*args, **kwargs)

    monkeypatch.setattr(service, "predict", _count_recompute)
    second = client.post("/predict", json=KP)

    assert second.headers.get("x-mdr-cache") == "miss"
    assert calls == 1
    assert second.json()["execution_id"] == expected["execution_id"]
    assert second.json()["requested_model_integrity"] == expected[
        "requested_model_integrity"
    ]


def test_raw_task_id_cache_entry_cannot_bypass_catalog_policy_namespace():
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    # This is the legacy key shape.  It must not be replayed after P1 because it
    # does not identify a catalog digest or a runtime policy version.
    cache.set(canonical_task_id(KP), {"stale": True})
    response = TestClient(create_app(cache=cache)).post("/predict", json=KP)
    assert response.headers.get("x-mdr-cache") == "miss"
    assert response.json()["report"]["sir"] == "R"


def test_predict_no_cache_still_works():
    c = TestClient(create_app())                        # 无 cache
    r = c.post("/predict", json=KP)
    assert r.json()["report"]["sir"] == "R"
    assert r.headers.get("x-mdr-cache") in (None, "off")


def test_governance_digest_change_invalidates_the_execution_cache(monkeypatch):
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    client = TestClient(create_app(cache=cache))
    first = client.post("/predict", json=KP)
    assert first.headers.get("x-mdr-cache") == "miss"

    original_context = service.governance_execution_context()
    changed_snapshot = {
        **original_context.snapshot,
        "governance_digest": "f" * 64,
    }
    changed_context = replace(original_context, snapshot=changed_snapshot)
    monkeypatch.setattr(service, "governance_execution_context", lambda: changed_context)

    second = client.post("/predict", json=KP)
    assert second.headers.get("x-mdr-cache") == "miss"


def test_requested_model_integrity_change_invalidates_the_execution_cache(monkeypatch):
    """A cache hit must not bypass a newly observed model/source readiness state."""
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    client = TestClient(create_app(cache=cache))
    first = client.post("/predict", json=KP)
    assert first.headers.get("x-mdr-cache") == "miss"

    observed = service.runtime_model_execution_context(KP)
    changed = {
        **observed.requested_model_integrity,
        "requested_readiness_digest": "f" * 64,
    }
    changed_context = replace(observed, requested_model_integrity=changed)
    monkeypatch.setattr(
        service,
        "runtime_model_execution_context",
        lambda raw: changed_context,
    )

    second = client.post("/predict", json=KP)
    third = client.post("/predict", json=KP)
    assert second.headers.get("x-mdr-cache") == "miss"
    assert third.headers.get("x-mdr-cache") == "hit"


def test_sidecar_contract_change_invalidates_activity_response_cache(monkeypatch):
    """A potential experimental FBA sidecar must be in the activity cache receipt.

    Ciprofloxacin itself abstains from FBA, keeping this a fast cache test; the
    captured EC sidecar contract still represents the mechanism branch that the
    same activity route is allowed to execute for a metabolic-target drug.
    """
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    client = TestClient(create_app(cache=cache))
    first = client.post("/predict", json=EC_CIPRO_ACTIVITY)
    assert first.headers.get("x-mdr-cache") == "miss"
    first_payload = first.json()
    first_contract = first_payload["requested_model_integrity"][
        "experimental_sidecars"
    ][0]

    original = RuntimeModelManifest.inspect_experimental_sidecar

    def _rotated_sidecar_receipt(self, model_id, *, loader_path=None):
        contract = original(self, model_id, loader_path=loader_path)
        return replace(contract, reason_code=f"{contract.reason_code}:rotated")

    monkeypatch.setattr(
        RuntimeModelManifest,
        "inspect_experimental_sidecar",
        _rotated_sidecar_receipt,
    )
    second = client.post("/predict", json=EC_CIPRO_ACTIVITY)
    assert second.headers.get("x-mdr-cache") == "miss"
    second_payload = second.json()
    second_contract = second_payload["requested_model_integrity"][
        "experimental_sidecars"
    ][0]
    assert second_payload["execution_id"] != first_payload["execution_id"]
    assert second_contract["reason_code"] == f"{first_contract['reason_code']}:rotated"


def test_api_captures_one_runtime_model_context_for_cache_and_core(monkeypatch):
    observed = service.runtime_model_execution_context(KP)
    calls = 0

    def _one_context_only(raw):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise AssertionError("API request must capture model context once")
        return observed

    monkeypatch.setattr(service, "runtime_model_execution_context", _one_context_only)
    response = TestClient(create_app()).post("/predict", json=KP)

    assert response.status_code == 200
    assert calls == 1
    assert response.json()["requested_model_integrity"] == observed.requested_model_integrity


def test_unavailable_model_preflight_bypasses_response_cache(monkeypatch):
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    observed = service.runtime_model_execution_context(KP)
    unavailable = replace(
        observed,
        context=None,
        lifecycle_identity={"catalog_version": None, "catalog_digest": None},
        cacheable=False,
    )

    def _cache_read_must_not_run(_key):
        raise AssertionError("unavailable model preflight must not replay response cache")

    def _cache_write_must_not_run(_key, _value):
        raise AssertionError("unavailable model preflight must not populate response cache")

    monkeypatch.setattr(service, "runtime_model_execution_context", lambda raw: unavailable)
    monkeypatch.setattr(cache, "get", _cache_read_must_not_run)
    monkeypatch.setattr(cache, "set", _cache_write_must_not_run)

    response = TestClient(create_app(cache=cache)).post("/predict", json=KP)

    assert response.status_code == 503
    assert response.headers.get("x-mdr-cache") == "bypass"


def test_api_binds_one_governance_snapshot_for_cache_and_core_execution(monkeypatch):
    context = service.governance_execution_context()
    snapshot = {**context.snapshot, "governance_digest": "d" * 64}
    captured_context = replace(context, snapshot=snapshot)
    calls = 0

    def _one_context_only():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise AssertionError("API request must capture governance inputs once")
        return captured_context

    monkeypatch.setattr(service, "governance_execution_context", _one_context_only)
    response = TestClient(create_app()).post("/predict", json=KP)

    assert response.status_code == 200
    assert calls == 1
    assert response.json()["governance_snapshot"]["governance_digest"] == "d" * 64


def test_health_reports_cache_state():
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    c = TestClient(create_app(cache=cache))
    assert c.get("/health").json()["cache"] == "on"
