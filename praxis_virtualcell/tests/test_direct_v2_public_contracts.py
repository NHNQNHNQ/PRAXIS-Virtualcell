"""Public contracts required by the generic direct-v2 execution slice."""

from __future__ import annotations

from pathlib import Path

import pytest

from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2, require_v2_request
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterInputReceipt,
    PreparedAdapterInput,
)
from praxis_virtualcell.model_zoo.wrapper_registry import (
    WrapperNotFoundError,
    WrapperRegistry,
)
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper

_U1_DOCUMENT_MARKER = "## U1 本地 direct-v2 发布可验证性补充（未发布）"


def _request() -> dict:
    return {
        "schema_version": "vc.request.v2",
        "request_id": "direct-v2-public-contract",
        "species": {
            "schema_version": "vc.species-ref.v1",
            "taxonomy_id": "NCBITaxon:999999999",
            "scientific_name": "test-only organism",
            "common_name": None,
        },
        "cell_context": {
            "schema_version": "vc.cell-context.v1",
            "cell_type_name": None,
            "cell_type_id": None,
            "tissue_name": None,
            "tissue_id": None,
            "attributes": {},
        },
        "input_modality": {
            "schema_version": "vc.modality.v1",
            "name": "test_input",
            "ontology_id": None,
            "unit": "dimensionless",
            "feature_namespace": "TestFeature",
        },
        "output_modality": {
            "schema_version": "vc.modality.v1",
            "name": "test_output",
            "ontology_id": None,
            "unit": "dimensionless",
            "feature_namespace": "TestFeature",
        },
        "perturbation": {
            "schema_version": "vc.perturbation.v1",
            "kind": "gene",
            "targets": ["TEST:1"],
            "dose_value": None,
            "dose_unit": None,
            "timepoint": None,
        },
        "task": {
            "schema_version": "vc.task.v1",
            "task_type": "test_scalar_task",
            "requested_outputs": ["test_output"],
        },
        "baseline_context": None,
        "metadata": {},
        "constraints": {},
    }


class _SyntheticWrapper(ModelWrapper):
    def declare_scope(self) -> dict:
        return {}

    def run_prediction(self, model_input: dict) -> dict:
        raise AssertionError("public-contract test must not execute a wrapper")


def test_require_v2_request_accepts_only_explicit_v2_contract() -> None:
    request = require_v2_request(_request())

    assert isinstance(request, VirtualCellRequestV2)
    assert request.request_id == "direct-v2-public-contract"

    legacy_shaped = _request()
    legacy_shaped.pop("schema_version")
    with pytest.raises(InputValidationError, match="schema_version"):
        require_v2_request(legacy_shaped)


def test_wrapper_registry_resolves_only_explicit_exact_class_registration() -> None:
    entrypoint = f"{_SyntheticWrapper.__module__}.{_SyntheticWrapper.__qualname__}"
    registry = WrapperRegistry()

    registry.register(entrypoint, _SyntheticWrapper)

    assert registry.resolve(entrypoint) is _SyntheticWrapper
    with pytest.raises(WrapperNotFoundError, match="not registered"):
        registry.resolve("praxis_virtualcell.tests.not_registered.Wrapper")


def test_prepared_input_receipt_is_hash_bound_and_never_contains_model_payload() -> None:
    prepared = PreparedAdapterInput(
        schema_version="vc.prepared-adapter-input.v1",
        adapter_fingerprint="1" * 64,
        input_contract_fingerprint="2" * 64,
        task="test_scalar_task",
        output="test_output",
        request_fingerprint="3" * 64,
        pack_fingerprint="4" * 64,
        compatibility_fingerprint="5" * 64,
        model_input={"test_only_private_value": [0.25]},
        values=(0.25,),
        shape=(1,),
        unit="dimensionless",
        feature_contract=None,
        feature_contract_fingerprint=None,
        alignment_report=None,
    )

    receipt = AdapterInputReceipt.from_prepared(prepared)
    rendered = receipt.to_dict()

    assert receipt.prepared_input_fingerprint == prepared.fingerprint()
    assert rendered["request_fingerprint"] == "3" * 64
    assert rendered["pack_fingerprint"] == "4" * 64
    assert "model_input" not in rendered
    assert "values" not in rendered
    assert "test_only_private_value" not in str(rendered)


def test_u1_docs_describe_the_current_explicit_generic_boundary() -> None:
    root = Path(__file__).resolve().parents[2]
    documents = (
        root / "docs" / "ADR-0009-virtualcell-model-zoo-v2.md",
        root / "docs" / "ADR-0010-virtualcell-model-adapter-sdk.md",
        root / "docs" / "runbooks" / "VIRTUALCELL-MODEL-ADAPTER-SDK.md",
        root / "docs" / "PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md",
        root / "docs" / "TESTING.md",
        root / "docs" / "VERSIONING.md",
        root / "README.md",
    )
    required_terms = (
        "DirectV2RuntimeFactory",
        "vc.direct-v2-execution.v1",
        "submit_direct_v2_job_from_factory()",
        "output_reducer_required",
        "artifact_snapshot_supported",
        "vc.artifact-snapshot-budget-policy.v1",
        "vc.environment.v3",
        "EnvironmentIdentityV2",
        "未发布",
    )

    for path in documents:
        content = path.read_text(encoding="utf-8")
        if path.name not in {"VERSIONING.md", "README.md", "TESTING.md"}:
            assert _U1_DOCUMENT_MARKER in content
        for term in required_terms:
            if path.name not in {"VERSIONING.md", "README.md", "TESTING.md"}:
                assert term in content
        if path.name not in {"VERSIONING.md", "README.md"}:
            assert "RuntimeBuilder" not in content

    adr = documents[0].read_text(encoding="utf-8")
    versioning = documents[-2].read_text(encoding="utf-8")
    readme = documents[-1].read_text(encoding="utf-8")
    testing = documents[-3].read_text(encoding="utf-8")
    assert "缺 Pack 可写入 v4 hard-abstain" in adr
    assert "reserved → failed" in adr
    assert "per-runtime execution context" in adr
    assert "ArtifactSnapshot" in adr
    assert "memory/retention budget" in adr
    assert "synthetic-only" in adr
    assert "pack.integrity_drift" in adr
    assert "vc.execution-plan.v3" in adr
    assert "vc.job-execution-identity.v5" in adr
    assert "output_reducer_required" in adr
    assert "运行边界从当前 registry 再解析同一 binding" in adr
    assert "path-safe public identifiers" in adr
    assert "closed allowlist" in adr
    assert "本地未发布候选" in adr
    assert "本地、未发布候选" in versioning
    assert "local/unreleased `vc.execution-plan.v3`" in versioning
    assert "local/unreleased `.v5`" in versioning
    assert "P17 compilation" in readme
    assert "U1 direct-v2 execution" in readme
    assert "U2 V3" in testing
