"""Generic domain extensions can only veto direct-v2 execution by exact taxon."""

from __future__ import annotations

import json

import pytest

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.domain_extension import (
    DomainBrainContextV1,
    DomainExtension,
    DomainModulePolicyV1,
)
from praxis_virtualcell.core.runtime import AgentRuntime
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
from praxis_virtualcell.workflows.submit_job import submit_direct_v2_job


def _brain(_request):
    return DomainBrainContextV1.from_dict(
        {
            "schema_version": "vc.domain-brain-context.v1",
            "brain_id": "test_domain_brain",
            "brain_version": "1.0.0",
            "context": {"private_selection": "not-for-wrapper"},
        }
    )


def _deny(_request, _brain_context):
    return DomainModulePolicyV1.from_dict(
        {
            "schema_version": "vc.domain-module-policy.v1",
            "policy_id": "test_domain_policy",
            "policy_version": "1.0.0",
            "allow_execution": False,
            "reasons": ["synthetic_denied"],
            "context": {"private_rule": "not-for-wrapper"},
        }
    )


def _allow(_request, _brain_context):
    return DomainModulePolicyV1.from_dict(
        {
            "schema_version": "vc.domain-module-policy.v1",
            "policy_id": "test_domain_allow_policy",
            "policy_version": "1.0.0",
            "allow_execution": True,
            "reasons": [],
            "context": {"private_rule": "not-for-wrapper"},
        }
    )


def _runtime(tmp_path, *, extensions=()):
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
    pack = packs.record("tiny-human-scrna", "0.1.0")
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
    return DirectV2RuntimeFactory(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
        domain_extensions=extensions,
    ).build(clock=Clock(), idgen=IdGen())


def test_exact_taxon_domain_policy_denies_before_wrapper_execution(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extension = DomainExtension(
        domain_id="test_domain",
        taxon_ids=("NCBITaxon:9606",),
        brain_provider=_brain,
        module_policy_provider=_deny,
    )
    runtime = _runtime(tmp_path, extensions=(extension,))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("a denied domain policy must stop before wrapper execution")

    monkeypatch.setattr(_ScalarWrapper, "run_prediction", forbidden)
    result = runtime.run_workflow_v2(
        _pack_bound_request(),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert result["abstain"] is True
    assert result["prediction"] is None
    assert "domain.policy.synthetic_denied" in result["abstain_reasons"]
    assert result["provenance"]["execution_plan"]["steps"] == []
    identity = result["provenance"]["domain_extension_identity"]
    assert identity["taxonomy_id"] == "NCBITaxon:9606"
    assert identity["allow_execution"] is False
    assert "private_selection" not in json.dumps(identity, sort_keys=True)
    assert "private_rule" not in json.dumps(identity, sort_keys=True)


def test_domain_extension_rejects_non_exact_taxon_registration() -> None:
    with pytest.raises(ValueError, match="taxon"):
        DomainExtension(
            domain_id="test_domain",
            taxon_ids=("NCBITaxon:*",),
            brain_provider=_brain,
            module_policy_provider=_deny,
        )


def test_domain_extension_provider_failure_and_overlap_fail_closed() -> None:
    def invalid_brain(_request):
        return {"not": "a contract"}

    extension = DomainExtension(
        domain_id="test_domain",
        taxon_ids=("NCBITaxon:9606",),
        brain_provider=invalid_brain,
        module_policy_provider=_deny,
    )
    identity = extension.evaluate(_pack_bound_request())
    assert identity.allow_execution is False
    assert identity.reasons == ("provider_invalid",)
    assert identity.brain_context_fingerprint is None

    with pytest.raises(ValueError, match="overlap"):
        AgentRuntime(
            RuntimeConfig(),
            bus=MessageBus(),
            clock=Clock(),
            idgen=IdGen(),
            domain_extensions=(extension, extension),
        )


def test_domain_extension_identity_is_redacted_and_replay_bound(tmp_path) -> None:
    extension = DomainExtension(
        domain_id="test_domain",
        taxon_ids=("NCBITaxon:9606",),
        brain_provider=_brain,
        module_policy_provider=_deny,
    )
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        _pack_bound_request(),
        runtime=_runtime(tmp_path, extensions=(extension,)),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
        job_store=store,
        job_id="domain-extension-denied",
    )
    loaded = store.load(submitted["job_id"])

    assert loaded["execution_identity"]["schema_version"] == "vc.job-execution-identity.v4"
    assert loaded["provenance"]["domain_extension_identity"]["taxonomy_id"] == (
        "NCBITaxon:9606"
    )
    assert "private_selection" not in json.dumps(loaded, sort_keys=True)
    assert "private_rule" not in json.dumps(loaded, sort_keys=True)

    provenance_path = tmp_path / "runs" / submitted["job_id"] / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["domain_extension_identity"]["taxonomy_id"] = "NCBITaxon:10090"
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    assert store.load(submitted["job_id"])["execution_identity"]["available"] is False


def test_allowed_domain_extension_v3_reducer_persists_and_loads_v5_identity(tmp_path) -> None:
    """One generic allowed domain extension remains bound through V3/V5."""

    from praxis_virtualcell.tests.test_direct_v2_multi_model_reducer import (
        _runtime_with_mean_policy,
    )

    extension = DomainExtension(
        domain_id="test_domain",
        taxon_ids=("NCBITaxon:9606",),
        brain_provider=_brain,
        module_policy_provider=_allow,
    )
    request, runtime, _adapter, zoo, policy = _runtime_with_mean_policy(
        tmp_path / "runtime",
        domain_extensions=(extension,),
    )
    store = JobStore(str(tmp_path / "runs"))

    submitted = submit_direct_v2_job(
        request,
        runtime=runtime,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
        job_store=store,
        job_id="generic-domain-v3-v5",
    )
    loaded = store.load(submitted["job_id"])

    assert submitted == {"job_id": "generic-domain-v3-v5", "status": "done"}
    assert loaded["report"]["abstain"] is False
    assert loaded["report"]["prediction"]["values"] == [0.5]
    assert loaded["report"]["models_used"] == zoo.capability_names()
    assert loaded["provenance"]["execution_plan"]["schema_version"] == "vc.execution-plan.v3"
    assert loaded["provenance"]["output_reducer_receipt"]["output_reducer"] == policy.binding().to_dict()
    domain_identity = loaded["provenance"]["domain_extension_identity"]
    assert domain_identity["schema_version"] == "vc.domain-extension-identity.v1"
    assert domain_identity["domain_id"] == "test_domain"
    assert domain_identity["taxonomy_id"] == "NCBITaxon:9606"
    assert domain_identity["brain_id"] == "test_domain_brain"
    assert domain_identity["policy_id"] == "test_domain_allow_policy"
    assert domain_identity["allow_execution"] is True
    assert domain_identity["reasons"] == []
    assert len(domain_identity["brain_context_fingerprint"]) == 64
    assert len(domain_identity["module_policy_fingerprint"]) == 64
    assert loaded["execution_identity"]["schema_version"] == "vc.job-execution-identity.v5"
    assert loaded["execution_identity"]["output_reducer"] == policy.binding().to_dict()
    rendered = json.dumps(loaded, sort_keys=True)
    assert "private_selection" not in rendered
    assert "private_rule" not in rendered

    root = tmp_path / "runs" / submitted["job_id"]
    provenance_path = root / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["domain_extension_identity"]["policy_version"] = "2.0.0"
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    report_path = root / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["provenance"] = provenance
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert store.load(submitted["job_id"])["execution_identity"]["available"] is False


@pytest.mark.parametrize(
    ("field", "secret"),
    (
        ("domain_id", "/private/domain-id"),
        ("brain_id", "/private/brain-id"),
        ("brain_version", "/private/brain-version"),
        ("policy_id", "/private/policy-id"),
        ("policy_version", "/private/policy-version"),
    ),
)
def test_pathlike_domain_identity_fields_never_enter_public_provenance(
    tmp_path,
    field: str,
    secret: str,
) -> None:
    """Malformed archived domain identities are unavailable, never echoed."""

    extension = DomainExtension(
        domain_id="test_domain",
        taxon_ids=("NCBITaxon:9606",),
        brain_provider=_brain,
        module_policy_provider=_deny,
    )
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        _pack_bound_request(),
        runtime=_runtime(tmp_path, extensions=(extension,)),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
        job_store=store,
        job_id=f"domain-extension-public-{field}",
    )
    root = tmp_path / "runs" / submitted["job_id"]
    provenance_path = root / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["domain_extension_identity"][field] = secret
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    report_path = root / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["provenance"] = provenance
    report_path.write_text(json.dumps(report), encoding="utf-8")

    loaded = store.load(submitted["job_id"])

    assert secret not in json.dumps(loaded, sort_keys=True)
    assert loaded["provenance"] == {
        "execution_contract": "vc.direct-v2-execution.v1",
        "available": False,
        "reason": "unsupported_or_invalid_direct_v2_provenance",
    }
    assert loaded["execution_identity"]["available"] is False


def test_direct_identity_binds_domain_taxonomy_to_request_and_plan(tmp_path) -> None:
    """The domain taxon cannot be changed independently of the V2 request/plan."""

    extension = DomainExtension(
        domain_id="test_domain",
        taxon_ids=("NCBITaxon:9606",),
        brain_provider=_brain,
        module_policy_provider=_deny,
    )
    store = JobStore(str(tmp_path / "runs"))
    submitted = submit_direct_v2_job(
        _pack_bound_request(),
        runtime=_runtime(tmp_path, extensions=(extension,)),
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
        job_store=store,
        job_id="domain-extension-taxonomy-binding",
    )
    root = tmp_path / "runs" / submitted["job_id"]
    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    provenance = json.loads((root / "provenance.json").read_text(encoding="utf-8"))
    report = json.loads((root / "report.json").read_text(encoding="utf-8"))
    trace = json.loads((root / "trace.json").read_text(encoding="utf-8"))
    provenance["domain_extension_identity"]["taxonomy_id"] = "NCBITaxon:10090"
    report["provenance"] = provenance

    with pytest.raises(ValueError, match="domain extension identity taxon"):
        JobStore._execution_identity(
            {
                "provenance": provenance,
                "structured_report": report,
                "trace": trace,
            },
            request=request,
        )

    request["species"]["taxonomy_id"] = "NCBITaxon:10090"
    with pytest.raises(ValueError, match="submitted request does not match"):
        JobStore._execution_identity(
            {
                "provenance": provenance,
                "structured_report": report,
                "trace": trace,
            },
            request=request,
        )
