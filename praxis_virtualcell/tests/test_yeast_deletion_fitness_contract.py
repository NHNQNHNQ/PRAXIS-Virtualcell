"""P15E: contract-only S. cerevisiae deletion-fitness adapter tests.

Every identity and value here is synthetic. The tests never read a deletion
screen, H5AD, model artifact, GEM, or scientific result.
"""

from __future__ import annotations

import inspect
from copy import deepcopy

import pytest
from pydantic import Field, ValidationError

from praxis_virtualcell.core.request_v2 import SpeciesRef, VirtualCellRequestV2
from praxis_virtualcell.data_packs.feature_alignment import MappingAssetRef
from praxis_virtualcell.model_zoo import yeast_deletion_fitness_contract
from praxis_virtualcell.model_zoo.adapter_sdk import (
    DEFAULT_ADAPTER_REGISTRY,
    AdapterContractError,
    AdapterRegistry,
    AdapterUncertainty,
    run_adapter_conformance,
)
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.model_zoo.registry_v2 import (
    ArtifactIdentity,
    EnvironmentIdentity,
    ModelReleaseRecord,
)
from praxis_virtualcell.model_zoo.yeast_deletion_fitness_contract import (
    YeastDeletionFitnessAdapter,
    YeastDeletionFitnessAdapterInputContract,
    YeastDeletionFitnessAdapterOutputContract,
    YeastDeletionFitnessPreparedModelInput,
    YeastDeletionFitnessScope,
    YeastFitnessCompatibilityBinding,
    YeastFitnessDataBinding,
    YeastFitnessExecutionBinding,
    YeastFitnessGeneMappingBinding,
    YeastFitnessValidationProtocol,
)


def _bindings():
    adapter = YeastDeletionFitnessAdapter()
    artifact = ArtifactIdentity.from_dict(
        {
            "schema_version": "vc.model-artifact.v1",
            "artifact_id": "test-only-yeast-fitness-model",
            "model_fingerprint": "1" * 64,
            "uri": None,
            "cache_key": "test-only/no-model.json",
            "size_bytes": 1,
            "sha256": "2" * 64,
            "media_type": "application/json",
            "license": "test-only",
            "source": "synthetic identity; no file exists",
            "safe_load_policy": "data_only",
            "legacy_incomplete": False,
        }
    )
    environment = EnvironmentIdentity.from_dict(
        {
            "schema_version": "vc.model-environment.v1",
            "environment_id": "test-only-yeast-fitness",
            "python_version": "3.test",
            "cpu_architecture": "test-only",
            "packages": [{"name": "numpy", "version": "test-only"}],
            "lock_digest": "3" * 64,
            "image_digest": None,
            "resources": ["cpu"],
            "accelerators": [],
            "adapter_fingerprints": [adapter.fingerprint()],
            "legacy_incomplete": False,
        }
    )
    mapping = YeastFitnessGeneMappingBinding(
        schema_version="vc.yeast-deletion-fitness-gene-mapping-binding.v1",
        asset=MappingAssetRef(
            asset_id="test-only-sgd-to-model",
            path="test-only/no-mapping.tsv",
            version="test-only",
            sha256="4" * 64,
        ),
        source_namespace="SGD",
        source_namespace_version="R64",
        source_namespace_version_fingerprint="5" * 64,
        source_id_format="sgd_systematic",
        target_namespace="test-only-model-feature",
        target_universe_id="test-only-nuclear-orf-universe",
        target_universe_fingerprint="6" * 64,
        exact_mapping_required=True,
    )
    pack = YeastFitnessDataBinding(
        schema_version="vc.yeast-deletion-fitness-data-binding.v1",
        pack_id="test-only-deletion-fitness-screen",
        pack_version="test-only",
        pack_fingerprint="7" * 64,
        data_kind="deletion_fitness_screen",
        taxonomy_id="NCBITaxon:4932",
        strain_id="NCBITaxon:559292",
        assembly_name="R64",
        assembly_accession="GCF_000146045.2",
        condition_id="test-only-rich-medium-30c",
        condition_fingerprint="8" * 64,
        control_id="test-only-matched-non-deletion-control",
        control_fingerprint="9" * 64,
        assay_id="test-only-arrayed-deletion-fitness",
        assay_fingerprint="a" * 64,
        platform_id="test-only-colony-growth-platform",
        platform_fingerprint="b" * 64,
        fitness_semantics_id="test-only-assay-defined-fitness",
        fitness_semantics_fingerprint="c" * 64,
        target_universe_id=mapping.target_universe_id,
        target_universe_fingerprint=mapping.target_universe_fingerprint,
    )
    execution = YeastFitnessExecutionBinding(
        schema_version="vc.yeast-deletion-fitness-execution-binding.v1",
        condition_id=pack.condition_id,
        condition_fingerprint=pack.condition_fingerprint,
        control_id=pack.control_id,
        control_fingerprint=pack.control_fingerprint,
        assay_id=pack.assay_id,
        assay_fingerprint=pack.assay_fingerprint,
        platform_id=pack.platform_id,
        platform_fingerprint=pack.platform_fingerprint,
        fitness_semantics_id=pack.fitness_semantics_id,
        fitness_semantics_fingerprint=pack.fitness_semantics_fingerprint,
        target_universe_id=pack.target_universe_id,
        target_universe_fingerprint=pack.target_universe_fingerprint,
        runner_id="test-only-fitness-runner",
        runner_version="test-only",
        inference_configuration_fingerprint="d" * 64,
    )
    release = ModelReleaseRecord.from_dict(
        {
            "schema_version": "vc.model-release.v1",
            "release_id": "test-only-yeast-fitness",
            "model_name": "yeast_deletion_fitness_contract",
            "model_version": "test-only",
            "model_fingerprint": artifact.model_fingerprint,
            "pack_fingerprints": [pack.pack_fingerprint],
            "artifact_fingerprints": [artifact.fingerprint()],
            "environment_fingerprint": environment.fingerprint(),
            "adapter_fingerprints": [adapter.fingerprint()],
            "evidence_fingerprints": [],
            "policy_fingerprint": None,
            "migration_status": "native",
            "legacy_status": None,
            "incomplete_reasons": [],
        }
    )
    compatibility = YeastFitnessCompatibilityBinding(
        schema_version="vc.yeast-deletion-fitness-compatibility-binding.v1",
        model_release_fingerprint=release.fingerprint(),
        model_fingerprint=artifact.model_fingerprint,
        artifact_fingerprint=artifact.fingerprint(),
        environment_fingerprint=environment.fingerprint(),
        adapter_fingerprint=adapter.fingerprint(),
        pack_fingerprint=pack.pack_fingerprint,
        data_binding_fingerprint=pack.fingerprint(),
        mapping_asset_fingerprint=mapping.fingerprint(),
        execution_binding_fingerprint=execution.fingerprint(),
        assets_verified=False,
        executable=False,
        reason="p15r_not_authorized",
    )
    scope = YeastDeletionFitnessScope(
        schema_version="vc.yeast-deletion-fitness-scope.v1",
        taxonomy_id="NCBITaxon:4932",
        scientific_name="Saccharomyces cerevisiae",
        strain_id="NCBITaxon:559292",
        strain_name="Saccharomyces cerevisiae S288C",
        assembly_name="R64",
        assembly_accession="GCF_000146045.2",
        model_fingerprint=artifact.model_fingerprint,
        model_release_fingerprint=release.fingerprint(),
        model_artifact_fingerprint=artifact.fingerprint(),
        environment_fingerprint=environment.fingerprint(),
        adapter_fingerprint=adapter.fingerprint(),
        pack_fingerprint=pack.pack_fingerprint,
        data_binding_fingerprint=pack.fingerprint(),
        compatibility_fingerprint=compatibility.fingerprint(),
        mapping_asset_fingerprint=mapping.fingerprint(),
        execution_binding_fingerprint=execution.fingerprint(),
        condition_id=pack.condition_id,
        condition_fingerprint=pack.condition_fingerprint,
        control_id=pack.control_id,
        control_fingerprint=pack.control_fingerprint,
        assay_id=pack.assay_id,
        assay_fingerprint=pack.assay_fingerprint,
        platform_id=pack.platform_id,
        platform_fingerprint=pack.platform_fingerprint,
        fitness_semantics_id=pack.fitness_semantics_id,
        fitness_semantics_fingerprint=pack.fitness_semantics_fingerprint,
        target_universe_id=pack.target_universe_id,
        target_universe_fingerprint=pack.target_universe_fingerprint,
        inference_configuration_fingerprint=execution.inference_configuration_fingerprint,
        request_gene_namespace="SGD",
        request_gene_namespace_version=mapping.source_namespace_version,
        request_gene_namespace_version_fingerprint=(mapping.source_namespace_version_fingerprint),
        request_gene_id_format="sgd_systematic",
        model_gene_namespace=mapping.target_namespace,
        output="fitness",
        output_unit="dimensionless",
        reference="matched_non_deletion_control_same_condition_platform",
    )
    protocol = YeastFitnessValidationProtocol(
        schema_version="vc.yeast-deletion-fitness-validation-protocol.v1",
        scope_fingerprint=scope.fingerprint(),
        deletion_data_fingerprint=pack.pack_fingerprint,
        baseline_fingerprint="e" * 64,
        split_unit="held_out_biological_group",
        biological_group_keys=(
            "target_gene_id",
            "condition_id",
            "replicate_group_id",
        ),
        baseline="training_mean_fitness_same_condition",
        primary_metric="mean_squared_error_fitness",
        metric_direction="lower_is_better",
        paired_ci_required=True,
        independent_condition_required=True,
        independent_platform_required=True,
        external_adaptation_steps=0,
        validation_only_tuning=True,
        stochastic_seeds=(11, 23, 37),
        record_role="preregistration_not_evidence",
        ood_axes=(
            "strain",
            "assembly",
            "assay",
            "condition",
            "control",
            "platform",
            "gene_namespace",
            "target_universe",
            "target",
        ),
    )
    return (
        adapter,
        artifact,
        environment,
        release,
        mapping,
        execution,
        pack,
        compatibility,
        scope,
        protocol,
    )


def _request(scope: YeastDeletionFitnessScope, protocol: YeastFitnessValidationProtocol, **changes):
    raw = {
        "schema_version": "vc.request.v2",
        "request_id": "p15e-test-only",
        "species": {
            "schema_version": "vc.species-ref.v1",
            "taxonomy_id": scope.taxonomy_id,
            "scientific_name": scope.scientific_name,
            "common_name": "yeast",
        },
        "cell_context": {
            "schema_version": "vc.cell-context.v1",
            "cell_type_name": scope.strain_name,
            "cell_type_id": None,
            "tissue_name": None,
            "tissue_id": None,
            "attributes": {
                "strain_id": scope.strain_id,
                "assembly_name": scope.assembly_name,
                "assembly_accession": scope.assembly_accession,
                "gene_namespace_version": scope.request_gene_namespace_version,
                "gene_namespace_version_fingerprint": (scope.request_gene_namespace_version_fingerprint),
                "condition_id": scope.condition_id,
                "condition_fingerprint": scope.condition_fingerprint,
                "control_id": scope.control_id,
                "control_fingerprint": scope.control_fingerprint,
                "assay_id": scope.assay_id,
                "assay_fingerprint": scope.assay_fingerprint,
                "platform_id": scope.platform_id,
                "platform_fingerprint": scope.platform_fingerprint,
                "fitness_semantics_id": scope.fitness_semantics_id,
                "fitness_semantics_fingerprint": scope.fitness_semantics_fingerprint,
                "target_universe_id": scope.target_universe_id,
                "target_universe_fingerprint": scope.target_universe_fingerprint,
            },
        },
        "input_modality": {
            "schema_version": "vc.modality.v1",
            "name": "deletion_screen",
            "ontology_id": "PRAXISASSAY:deletion_screen",
            "unit": None,
            "feature_namespace": "SGD",
        },
        "output_modality": {
            "schema_version": "vc.modality.v1",
            "name": "fitness",
            "ontology_id": "PRAXISOUTPUT:fitness",
            "unit": "dimensionless",
            "feature_namespace": None,
        },
        "perturbation": {
            "schema_version": "vc.perturbation.v1",
            "kind": "gene",
            "targets": ["YAL001C"],
            "dose_value": None,
            "dose_unit": None,
            "timepoint": None,
        },
        "task": {
            "schema_version": "vc.task.v1",
            "task_type": "predict_deletion_fitness",
            "requested_outputs": ["fitness"],
        },
        "baseline_context": {
            "reference": scope.reference,
            "control_id": scope.control_id,
            "control_fingerprint": scope.control_fingerprint,
            "scope_fingerprint": scope.fingerprint(),
        },
        "metadata": {},
        "constraints": {
            "perturbation_semantics": "complete_gene_deletion",
            "scope_fingerprint": scope.fingerprint(),
            "validation_protocol_fingerprint": protocol.fingerprint(),
        },
    }
    for path, value in changes.items():
        target = raw
        parts = path.split("__")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return VirtualCellRequestV2.from_dict(raw)


def _prepare_kwargs(bindings):
    _, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = bindings
    return {
        "scope": scope,
        "model_artifact": artifact,
        "environment": environment,
        "model_release": release,
        "mapping_asset": mapping,
        "execution_binding": execution,
        "validation_protocol": protocol,
        "pack": pack,
        "compatibility_report": compatibility,
    }


def _prepared():
    bindings = _bindings()
    adapter, *_, scope, protocol = bindings
    prepared = adapter.prepare_input(
        _request(scope, protocol),
        **_prepare_kwargs(bindings),
    )
    return adapter, prepared, scope


def _raw(*, fitness=-0.25, status="success", ood=False, abstain=False):
    scope = _prepared()[2]
    return {
        "prediction": (
            None
            if abstain
            else {
                "fitness": fitness,
                "fitness_semantics_id": scope.fitness_semantics_id,
                "reference": scope.reference,
                "unit": scope.output_unit,
            }
        ),
        "prediction_status": status,
        "scope_fingerprint": scope.fingerprint(),
        "uncertainty": {
            "available": False,
            "method": "not_available",
            "calibrated": False,
            "reason": "no_calibrated_uncertainty_declared",
        },
        "ood": {
            "detected": ood,
            "dimensions": ["target"] if ood else [],
            "reason": "target outside exact scope" if ood else None,
        },
        "abstain": abstain,
        "abstain_reasons": ["exact scope rejected"] if abstain else [],
    }


def test_contracts_are_strict_frozen_versioned_and_fingerprint_bound():
    adapter, *_, scope, protocol = _bindings()
    assert isinstance(adapter.input_contract, YeastDeletionFitnessAdapterInputContract)
    assert isinstance(adapter.output_contract, YeastDeletionFitnessAdapterOutputContract)
    assert adapter.input_contract.schema_version.endswith(".v1")
    assert adapter.output_contract.schema_version.endswith(".v1")
    assert adapter.identity().task == "predict_deletion_fitness"
    assert adapter.identity().outputs == ("fitness",)
    assert adapter.output_contract.shape == (1,)
    assert adapter.output_contract.unit == "dimensionless"
    assert adapter.input_contract.fingerprint() == adapter.identity().input_contract_fingerprint
    assert adapter.output_contract.fingerprint() == adapter.identity().output_contract_fingerprint
    assert all(len(value) == 64 for value in (adapter.fingerprint(), scope.fingerprint(), protocol.fingerprint()))
    assert scope.fingerprint() == deepcopy(scope).fingerprint()
    assert scope.model_copy(update={"condition_id": "changed"}).fingerprint() != scope.fingerprint()
    with pytest.raises(ValidationError, match="extra"):
        YeastDeletionFitnessScope.model_validate({**scope.to_dict(), "scientifically_validated": True})
    with pytest.raises(ValidationError, match="frozen"):
        scope.condition_id = "changed"


def test_scope_freezes_exact_s288c_r64_sgd_and_fitness_semantics():
    *_, scope, _ = _bindings()
    assert (
        scope.taxonomy_id,
        scope.strain_id,
        scope.assembly_name,
        scope.assembly_accession,
    ) == (
        "NCBITaxon:4932",
        "NCBITaxon:559292",
        "R64",
        "GCF_000146045.2",
    )
    assert (scope.request_gene_namespace, scope.request_gene_id_format) == (
        "SGD",
        "sgd_systematic",
    )
    assert scope.output == "fitness" and scope.output_unit == "dimensionless"
    assert scope.fitness_semantics_id == "test-only-assay-defined-fitness"
    assert scope.reference == "matched_non_deletion_control_same_condition_platform"
    for field, value in (
        ("taxonomy_id", "NCBITaxon:559292"),
        ("strain_id", "PRAXISCELL:yeast_s288c"),
        ("assembly_name", "R63"),
        ("assembly_accession", "GCF_000000000.1"),
        ("request_gene_namespace", "NCBIGene"),
        ("request_gene_id_format", "symbol"),
        ("output_unit", "log2"),
    ):
        with pytest.raises(ValidationError, match=field):
            YeastDeletionFitnessScope.model_validate({**scope.to_dict(), field: value})


def test_validation_protocol_is_exact_preregistration_not_evidence_or_policy():
    *_, scope, protocol = _bindings()
    assert protocol.baseline == "training_mean_fitness_same_condition"
    assert protocol.baseline != scope.reference
    assert protocol.primary_metric == "mean_squared_error_fitness"
    assert protocol.metric_direction == "lower_is_better"
    assert protocol.stochastic_seeds == (11, 23, 37)
    assert protocol.external_adaptation_steps == 0
    assert protocol.paired_ci_required
    assert protocol.independent_condition_required
    assert protocol.independent_platform_required
    assert protocol.record_role == "preregistration_not_evidence"
    assert not {
        "result_sha256",
        "benchmark_passed",
        "scientifically_validated",
        "promotion_eligible",
        "production_promoted",
    }.intersection(protocol.to_dict())
    with pytest.raises(ValidationError, match="extra"):
        YeastFitnessValidationProtocol.model_validate({**protocol.to_dict(), "promotion_eligible": True})


@pytest.mark.parametrize(
    "seeds",
    [
        (11, 23),
        (11, 23, 23),
        (True, 23, 37),
        (-1, 23, 37),
        (2**53, 23, 37),
        ("11", 23, 37),
    ],
)
def test_protocol_requires_three_unique_nonnegative_json_safe_integer_seeds(seeds):
    *_, protocol = _bindings()
    with pytest.raises(ValidationError, match="stochastic_seeds"):
        YeastFitnessValidationProtocol.model_validate({**protocol.to_dict(), "stochastic_seeds": seeds})
    assert YeastFitnessValidationProtocol.model_validate(
        {**protocol.to_dict(), "stochastic_seeds": (11, 23, 37, 41)}
    ).stochastic_seeds == (11, 23, 37, 41)


def test_protocol_freezes_group_keys_baseline_metric_and_canonical_ood_order():
    *_, protocol = _bindings()
    changes = (
        ("biological_group_keys", tuple(reversed(protocol.biological_group_keys))),
        ("baseline", "matched_non_deletion_control_same_condition_platform"),
        ("primary_metric", "mean_absolute_error_fitness"),
        ("metric_direction", "higher_is_better"),
        ("ood_axes", tuple(reversed(protocol.ood_axes))),
        ("ood_axes", (*protocol.ood_axes, "invented_axis")),
    )
    for field, value in changes:
        with pytest.raises(ValidationError, match=field):
            YeastFitnessValidationProtocol.model_validate({**protocol.to_dict(), field: value})


def test_adapter_is_local_only_and_legacy_card_remains_planned():
    adapter, *_ = _bindings()
    assert DEFAULT_ADAPTER_REGISTRY.keys() == (("predict_delta_expression", "delta_expression"),)
    with pytest.raises(AdapterContractError, match="unregistered"):
        DEFAULT_ADAPTER_REGISTRY.resolve("predict_deletion_fitness", "fitness")
    local = AdapterRegistry([adapter])
    assert local.resolve("predict_deletion_fitness", "fitness") is adapter
    legacy = ModelZooRegistry().get("yeast_deletion_fitness")
    assert legacy["status"] == "planned"
    assert "planned" in legacy["training_card"]["provenance"].lower()


def test_prepare_input_binds_every_exact_identity_without_values_or_io(monkeypatch):
    bindings = _bindings()
    adapter, *_, scope, protocol = bindings

    def forbid_open(*_args, **_kwargs):
        raise AssertionError("contract adapter attempted file I/O")

    monkeypatch.setattr("builtins.open", forbid_open)
    prepared = adapter.prepare_input(
        _request(scope, protocol),
        **_prepare_kwargs(bindings),
    )
    model_input = YeastDeletionFitnessPreparedModelInput.model_validate(prepared.model_input)
    assert model_input.scope == scope
    assert model_input.target_gene_id == "YAL001C"
    assert model_input.scope_fingerprint == scope.fingerprint()
    assert model_input.adapter_fingerprint == adapter.fingerprint()
    assert prepared.pack_fingerprint == scope.pack_fingerprint
    assert prepared.compatibility_fingerprint == scope.compatibility_fingerprint
    assert prepared.values is None and prepared.shape is None and prepared.unit is None


@pytest.mark.parametrize(
    ("change", "value", "match"),
    [
        ("species__taxonomy_id", "NCBITaxon:559292", "taxonomy"),
        ("species__scientific_name", "Schizosaccharomyces pombe", "species"),
        ("species__common_name", "fungus", "species"),
        ("cell_context__cell_type_name", "Saccharomyces cerevisiae", "strain"),
        ("cell_context__attributes__assembly_name", "R63", "scope"),
        ("cell_context__attributes__condition_id", "other", "scope"),
        ("cell_context__attributes__control_id", "other", "scope"),
        ("cell_context__attributes__assay_id", "other", "scope"),
        ("cell_context__attributes__platform_id", "other", "scope"),
        ("cell_context__attributes__fitness_semantics_id", "other", "scope"),
        ("cell_context__attributes__target_universe_id", "other", "scope"),
        ("input_modality__name", "scRNA", "deletion screen"),
        ("input_modality__feature_namespace", "symbol", "namespace"),
        ("output_modality__name", "growth", "task/output"),
        ("output_modality__unit", None, "unit"),
        ("perturbation__kind", "drug", "complete gene deletion"),
        ("perturbation__targets", ["YAL001C", "YBR166C"], "one exact"),
        ("perturbation__dose_value", 1.0, "complete gene deletion"),
        ("perturbation__timepoint", "1h", "complete gene deletion"),
        ("task__task_type", "deletion_fitness", "task/output"),
        ("task__requested_outputs", ["fitness", "growth"], "task/output"),
        ("baseline_context__reference", "wild_type", "baseline"),
        ("constraints__scope_fingerprint", "f" * 64, "scope/protocol"),
        ("constraints__perturbation_semantics", "knockdown", "scope/protocol"),
        ("metadata", {"ignored": True}, "metadata"),
    ],
)
def test_prepare_input_rejects_scope_task_condition_and_semantics_drift(change, value, match):
    bindings = _bindings()
    adapter, *_, scope, protocol = bindings
    with pytest.raises(AdapterContractError, match=match):
        adapter.prepare_input(
            _request(scope, protocol, **{change: value}),
            **_prepare_kwargs(bindings),
        )


@pytest.mark.parametrize(
    "target",
    [
        "GAL4",
        "SGD:YAL001C",
        "yal001c",
        "NCBIGene:851229",
        "Q0045",
        "YQL001C",
        "YAL001X",
    ],
)
def test_prepare_input_accepts_only_one_canonical_sgd_systematic_target(target):
    bindings = _bindings()
    adapter, *_, scope, protocol = bindings
    with pytest.raises(AdapterContractError, match="SGD systematic"):
        adapter.prepare_input(
            _request(scope, protocol, perturbation__targets=[target]),
            **_prepare_kwargs(bindings),
        )


@pytest.mark.parametrize(
    ("parameter", "match"),
    [
        ("model_artifact", "artifact"),
        ("environment", "environment"),
        ("model_release", "release"),
        ("mapping_asset", "mapping"),
        ("execution_binding", "execution"),
        ("validation_protocol", "protocol"),
        ("pack", "Pack"),
        ("compatibility_report", "compatibility"),
    ],
)
def test_prepare_input_rejects_missing_required_identity_bindings(parameter, match):
    bindings = _bindings()
    adapter, *_, scope, protocol = bindings
    kwargs = _prepare_kwargs(bindings)
    kwargs[parameter] = None
    with pytest.raises((AdapterContractError, TypeError), match=match):
        adapter.prepare_input(_request(scope, protocol), **kwargs)


@pytest.mark.parametrize(
    ("parameter", "field", "value", "match"),
    [
        ("model_artifact", "size_bytes", 2, "artifact"),
        ("environment", "python_version", "other", "environment"),
        ("model_release", "model_version", "other", "release"),
        ("mapping_asset", "target_universe_id", "other", "mapping"),
        ("execution_binding", "platform_id", "other", "execution"),
        ("pack", "condition_id", "other", "data binding"),
        ("compatibility_report", "model_fingerprint", "f" * 64, "compatibility"),
        ("validation_protocol", "baseline_fingerprint", "f" * 64, "scope/protocol"),
    ],
)
def test_prepare_input_rejects_artifact_release_environment_and_contract_drift(parameter, field, value, match):
    bindings = _bindings()
    adapter, *_, scope, protocol = bindings
    kwargs = _prepare_kwargs(bindings)
    kwargs[parameter] = kwargs[parameter].model_copy(update={field: value})
    with pytest.raises(AdapterContractError, match=match):
        adapter.prepare_input(_request(scope, protocol), **kwargs)


def test_artifact_load_policy_media_release_evidence_and_policy_fail_closed():
    bindings = _bindings()
    adapter, artifact, *_, scope, protocol = bindings
    base = _prepare_kwargs(bindings)
    for field, value, match in (
        ("safe_load_policy", "restricted_deserializer", "data_only"),
        ("media_type", "application/octet-stream", "application/json"),
        ("legacy_incomplete", True, "artifact"),
    ):
        changed = artifact.model_copy(update={field: value})
        changed_release = base["model_release"].model_copy(update={"artifact_fingerprints": (changed.fingerprint(),)})
        changed_scope = scope.model_copy(
            update={
                "model_artifact_fingerprint": changed.fingerprint(),
                "model_release_fingerprint": changed_release.fingerprint(),
            }
        )
        changed_protocol = protocol.model_copy(update={"scope_fingerprint": changed_scope.fingerprint()})
        kwargs = {
            **base,
            "scope": changed_scope,
            "model_artifact": changed,
            "model_release": changed_release,
            "validation_protocol": changed_protocol,
        }
        with pytest.raises(AdapterContractError, match=match):
            adapter.prepare_input(
                _request(changed_scope, changed_protocol),
                **kwargs,
            )

    release = base["model_release"].model_copy(update={"evidence_fingerprints": ("f" * 64,)})
    with pytest.raises(AdapterContractError, match="release"):
        adapter.prepare_input(
            _request(scope, protocol),
            **{**base, "model_release": release},
        )
    release = base["model_release"].model_copy(update={"policy_fingerprint": "f" * 64})
    with pytest.raises(AdapterContractError, match="release"):
        adapter.prepare_input(
            _request(scope, protocol),
            **{**base, "model_release": release},
        )


def test_p10_yeast_tiny_and_untyped_objects_cannot_impersonate_fitness_data():
    bindings = _bindings()
    adapter, *_, scope, protocol = bindings
    base = _prepare_kwargs(bindings)
    with pytest.raises(TypeError, match="YeastFitnessDataBinding"):
        adapter.prepare_input(
            _request(scope, protocol),
            **{
                **base,
                "pack": {
                    "pack_id": "p10-yeast-tiny",
                    "data_kind": "scRNA",
                    "pack_fingerprint": base["pack"].pack_fingerprint,
                },
            },
        )
    with pytest.raises(TypeError, match="YeastFitnessCompatibilityBinding"):
        adapter.prepare_input(
            _request(scope, protocol),
            **{**base, "compatibility_report": object()},
        )
    relabeled = base["pack"].model_copy(update={"pack_id": "p10-yeast-tiny"})
    with pytest.raises(AdapterContractError, match="deletion-data binding"):
        adapter.prepare_input(
            _request(scope, protocol),
            **{**base, "pack": relabeled},
        )


def test_model_copy_cannot_bypass_binding_literals_and_exact_semantics():
    bindings = _bindings()
    adapter, *_, scope, protocol = bindings
    base = _prepare_kwargs(bindings)
    cases = (
        (
            "pack",
            base["pack"].model_copy(update={"data_kind": "scRNA"}),
            "Pack binding",
        ),
        (
            "compatibility_report",
            base["compatibility_report"].model_copy(update={"executable": True}),
            "compatibility binding",
        ),
        (
            "mapping_asset",
            base["mapping_asset"].model_copy(update={"exact_mapping_required": False}),
            "mapping binding",
        ),
        (
            "execution_binding",
            base["execution_binding"].model_copy(update={"fitness_semantics_id": "unbound"}),
            "execution binding",
        ),
        (
            "scope",
            scope.model_copy(update={"assembly_accession": "GCF_000000000.1"}),
            "scope binding",
        ),
    )
    for parameter, value, match in cases:
        with pytest.raises(AdapterContractError, match=match):
            adapter.prepare_input(
                _request(scope, protocol),
                **{**base, parameter: value},
            )


def test_nested_pydantic_model_copy_extras_and_subtypes_fail_closed():
    class PromotedSpeciesRef(SpeciesRef):
        production_promoted: bool = Field(exclude=True)

    class ScientificMappingAsset(MappingAssetRef):
        scientifically_validated: bool = Field(exclude=True)

    bindings = _bindings()
    adapter, *_, scope, protocol = bindings
    request = _request(scope, protocol)
    base = _prepare_kwargs(bindings)
    nested_request = request.model_copy(
        update={"species": request.species.model_copy(update={"production_promoted": True})}
    )
    nested_mapping = base["mapping_asset"].model_copy(
        update={"asset": base["mapping_asset"].asset.model_copy(update={"scientifically_validated": True})}
    )
    nested_environment = base["environment"].model_copy(
        update={"packages": (base["environment"].packages[0].model_copy(update={"promotion_eligible": True}),)}
    )
    for candidate_request, kwargs, match in (
        (nested_request, base, "invalid request"),
        (request, {**base, "mapping_asset": nested_mapping}, "invalid mapping"),
        (
            request,
            {**base, "environment": nested_environment},
            "invalid environment",
        ),
    ):
        with pytest.raises(AdapterContractError, match=match):
            adapter.prepare_input(candidate_request, **kwargs)

    promoted_species = PromotedSpeciesRef(
        **request.species.model_dump(mode="python"),
        production_promoted=True,
    )
    with pytest.raises(AdapterContractError, match="invalid request"):
        adapter.prepare_input(
            request.model_copy(update={"species": promoted_species}),
            **base,
        )
    scientific_asset = ScientificMappingAsset(
        **base["mapping_asset"].asset.model_dump(mode="python"),
        scientifically_validated=True,
    )
    with pytest.raises(AdapterContractError, match="invalid mapping"):
        adapter.prepare_input(
            request,
            **{
                **base,
                "mapping_asset": base["mapping_asset"].model_copy(update={"asset": scientific_asset}),
            },
        )


@pytest.mark.parametrize("fitness", [-0.25, 0.0, 1.25, 250.0])
def test_synthetic_scalar_fitness_passes_through_without_normalization(fitness):
    adapter, prepared, scope = _prepared()
    raw = _raw(fitness=fitness)
    envelope = adapter.adapt_output(prepared, raw)
    assert envelope.values == (fitness,)
    assert envelope.shape == (1,)
    assert envelope.unit == "dimensionless"
    assert envelope.projection_metadata == {
        "fitness_semantics_id": scope.fitness_semantics_id,
        "prediction_status": "success",
        "reference": scope.reference,
        "scope_fingerprint": scope.fingerprint(),
        "unit": "dimensionless",
    }
    assert adapter.project_prepared_output(prepared, envelope) == {"fitness": [fitness]}
    second = adapter.adapt_output(prepared, deepcopy(raw))
    assert second.to_dict() == envelope.to_dict()
    assert second.fingerprint() == envelope.fingerprint()
    report = run_adapter_conformance(adapter, prepared, raw)
    assert report.adapter_fingerprint == adapter.fingerprint()
    assert report.deterministic is True


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("prediction", "fitness"), True, "finite number"),
        (("prediction", "fitness"), "-0.25", "finite number"),
        (("prediction", "fitness"), float("nan"), "finite number"),
        (("prediction", "fitness"), float("inf"), "finite number"),
        (("prediction", "fitness"), 2**53, "JSON-safe"),
        (("prediction", "unit"), "log2", "semantics"),
        (("prediction", "reference"), "other", "semantics"),
        (("prediction", "fitness_semantics_id"), "other", "semantics"),
        (("scope_fingerprint",), "f" * 64, "scope"),
        (("prediction_status",), "invented-status", "status"),
        (("uncertainty", "available"), True, "unavailable"),
        (("uncertainty", "method"), "p15r_not_authorized", "unavailable"),
        (
            ("uncertainty", "reason"),
            "p15r_not_authorized",
            "unavailable",
        ),
    ],
)
def test_output_rejects_nonfinite_shape_unit_status_scope_and_uncertainty(path, value, match):
    adapter, prepared, _ = _prepared()
    raw = _raw()
    cursor = raw
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(AdapterContractError, match=match):
        adapter.adapt_output(prepared, raw)


@pytest.mark.parametrize(
    "reserved",
    [
        "absolute_growth",
        "essentiality",
        "evidence",
        "policy",
        "benchmark_passed",
        "scientifically_validated",
        "promotion_eligible",
        "production_promoted",
    ],
)
def test_output_rejects_reserved_science_policy_and_unrequested_fields(reserved):
    adapter, prepared, _ = _prepared()
    raw = _raw()
    raw[reserved] = True
    with pytest.raises(AdapterContractError, match="unknown wrapper output"):
        adapter.adapt_output(prepared, raw)


@pytest.mark.parametrize("status", ["target_not_found", "unsupported_scope", "error"])
def test_non_success_status_requires_value_free_abstention(status):
    adapter, prepared, _ = _prepared()
    if status == "unsupported_scope":
        with pytest.raises(AdapterContractError, match="requires detected OOD"):
            adapter.adapt_output(prepared, _raw(status=status, abstain=True))
        non_abstaining = _raw(status=status, ood=True)
    else:
        non_abstaining = _raw(status=status)
    with pytest.raises(AdapterContractError, match="must abstain"):
        adapter.adapt_output(prepared, non_abstaining)
    envelope = adapter.adapt_output(
        prepared,
        _raw(
            status=status,
            ood=status == "unsupported_scope",
            abstain=True,
        ),
    )
    assert envelope.abstain
    assert envelope.values is None and envelope.shape is None
    assert envelope.projection_metadata == {}


def test_ood_and_abstain_require_exact_ordered_dimensions_reason_and_no_values():
    adapter, prepared, _ = _prepared()
    with pytest.raises(AdapterContractError, match="OOD output must abstain"):
        adapter.adapt_output(prepared, _raw(ood=True))
    envelope = adapter.adapt_output(prepared, _raw(ood=True, abstain=True))
    assert envelope.abstain and envelope.ood.detected
    raw = _raw(ood=True, abstain=True)
    raw["abstain_reasons"] = []
    with pytest.raises(AdapterContractError, match="requires reasons"):
        adapter.adapt_output(prepared, raw)
    raw = _raw()
    raw["ood"]["dimensions"] = ["invented_axis"]
    with pytest.raises(AdapterContractError, match="unknown OOD"):
        adapter.adapt_output(prepared, raw)
    raw = _raw()
    raw["ood"]["dimensions"] = ["target"]
    with pytest.raises(AdapterContractError, match="non-detected OOD"):
        adapter.adapt_output(prepared, raw)
    raw = _raw(ood=True, abstain=True)
    raw["ood"]["dimensions"] = []
    with pytest.raises(AdapterContractError, match="dimension and reason"):
        adapter.adapt_output(prepared, raw)
    raw = _raw(ood=True, abstain=True)
    raw["ood"]["dimensions"] = ["target", "strain"]
    with pytest.raises(AdapterContractError, match="canonical order"):
        adapter.adapt_output(prepared, raw)
    raw = _raw(status="success", abstain=True)
    with pytest.raises(AdapterContractError, match="detected OOD"):
        adapter.adapt_output(prepared, raw)


def test_output_requires_exact_scalar_prediction_and_every_wrapper_field():
    class RawOutput(dict):
        pass

    adapter, prepared, _ = _prepared()
    raw = _raw()
    raw["prediction"]["fitness"] = [-0.25]
    with pytest.raises(AdapterContractError, match="finite number"):
        adapter.adapt_output(prepared, raw)
    raw = _raw()
    raw["prediction"]["normalized_fitness"] = 0.0
    with pytest.raises(AdapterContractError, match="unknown prediction"):
        adapter.adapt_output(prepared, raw)
    raw = _raw()
    raw["prediction"].pop("fitness_semantics_id")
    with pytest.raises(AdapterContractError, match="missing fields"):
        adapter.adapt_output(prepared, raw)
    raw = _raw()
    raw.pop("prediction_status")
    with pytest.raises(AdapterContractError, match="missing fields"):
        adapter.adapt_output(prepared, raw)
    with pytest.raises(AdapterContractError, match="exact JSON object"):
        adapter.adapt_output(prepared, RawOutput(_raw()))


def test_direct_envelope_and_nested_model_copy_forgery_fail_closed():
    adapter, prepared, _ = _prepared()
    envelope = adapter.adapt_output(prepared, _raw())
    forged_uncertainty = envelope.model_copy(
        update={
            "uncertainty": AdapterUncertainty(
                available=True,
                method="pretend",
                calibrated=False,
                value=0.1,
            )
        }
    )
    with pytest.raises(AdapterContractError, match="unavailable"):
        adapter.validate_prepared_envelope(prepared, forged_uncertainty)
    cases = (
        (
            "uncertainty",
            envelope.uncertainty.model_copy(update={"scientifically_validated": True}),
            "uncertainty",
        ),
        (
            "ood",
            envelope.ood.model_copy(update={"promotion_eligible": True}),
            "ood",
        ),
        (
            "provenance",
            envelope.provenance.model_copy(update={"production_promoted": True}),
            "provenance",
        ),
    )
    for field, nested, match in cases:
        with pytest.raises(AdapterContractError, match=match):
            adapter.validate_prepared_envelope(
                prepared,
                envelope.model_copy(update={field: nested}),
            )


def test_prepared_input_metadata_provenance_and_projection_cannot_drift():
    adapter, prepared, _ = _prepared()
    envelope = adapter.adapt_output(prepared, _raw())
    forged = prepared.model_copy(
        update={
            "model_input": {
                **deepcopy(dict(prepared.model_input)),
                "request_fingerprint": "f" * 64,
            }
        }
    )
    with pytest.raises(AdapterContractError, match="request fingerprint"):
        adapter.adapt_output(forged, _raw())
    forged_protocol = prepared.model_copy(
        update={
            "model_input": {
                **deepcopy(dict(prepared.model_input)),
                "validation_protocol_fingerprint": "f" * 64,
            }
        }
    )
    with pytest.raises(AdapterContractError, match="prepared yeast fitness"):
        adapter.validate_prepared_input(forged_protocol)
    drifted_metadata = envelope.model_copy(
        update={
            "projection_metadata": {
                **dict(envelope.projection_metadata),
                "fitness_semantics_id": "unbound",
            }
        }
    )
    with pytest.raises(AdapterContractError, match="prepared input"):
        adapter.validate_prepared_envelope(prepared, drifted_metadata)
    forged_provenance = envelope.model_copy(
        update={
            "provenance": envelope.provenance.model_copy(
                update={
                    "input_fingerprints": ("a" * 64,),
                    "request_fingerprints": ("b" * 64,),
                    "pack_fingerprints": ("c" * 64,),
                    "compatibility_fingerprints": ("d" * 64,),
                }
            )
        }
    )
    with pytest.raises(AdapterContractError, match="provenance"):
        adapter.validate_prepared_envelope(prepared, forged_provenance)
    with pytest.raises(AdapterContractError, match="only fitness"):
        adapter.validate_projection({"fitness": [-0.25], "growth": [1.0]})


def test_standalone_output_paths_and_abstaining_projection_fail_closed():
    adapter, prepared, _ = _prepared()
    envelope = adapter.adapt_output(prepared, _raw())
    for operation, match in (
        (lambda: adapter.validate_envelope(envelope), "prepared input"),
        (lambda: adapter.aggregate((envelope,)), "no standalone aggregation"),
        (lambda: adapter.project_output(envelope), "prepared input"),
    ):
        with pytest.raises(AdapterContractError, match=match):
            operation()
    abstention = adapter.adapt_output(
        prepared,
        _raw(status="target_not_found", abstain=True),
    )
    with pytest.raises(AdapterContractError, match="cannot project an abstaining"):
        adapter.project_prepared_output(prepared, abstention)


def test_contract_module_has_no_ecoli_gem_asset_or_runtime_fallbacks():
    source = inspect.getsource(yeast_deletion_fitness_contract)
    for forbidden in (
        "E. coli",
        "Ecoli",
        "NCBIGene",
        "GEM",
        "gem_",
        "solver",
        "objective",
        "medium",
        "SBML",
        "import cobra",
        "import anndata",
        "import scanpy",
        "import torch",
        "read_h5ad",
        ".h5ad",
        "yeast_gem",
        "GemWrapper",
        "open(",
    ):
        assert forbidden not in source
