"""P14E: contract-only E. coli K-12 knockout-growth adapter tests.

All identities and values in this file are synthetic.  The tests must never
load Cobra, SBML, a GEM, or growth/essentiality data.
"""

from __future__ import annotations

import inspect
from copy import deepcopy

import pytest
from pydantic import Field, ValidationError

from praxis_virtualcell.core.request_v2 import SpeciesRef, VirtualCellRequestV2
from praxis_virtualcell.data_packs.feature_alignment import MappingAssetRef
from praxis_virtualcell.model_zoo import ecoli_growth_contract
from praxis_virtualcell.model_zoo.adapter_sdk import (
    DEFAULT_ADAPTER_REGISTRY,
    AdapterContractError,
    AdapterRegistry,
    AdapterUncertainty,
    run_adapter_conformance,
)
from praxis_virtualcell.model_zoo.ecoli_growth_contract import (
    EcoliGrowthCompatibilityBinding,
    EcoliGrowthDataBinding,
    EcoliGrowthExecutionBinding,
    EcoliGrowthGeneMappingBinding,
    EcoliGrowthScope,
    EcoliGrowthValidationProtocol,
    EcoliK12KnockoutGrowthAdapter,
    EcoliK12KnockoutGrowthInput,
)
from praxis_virtualcell.model_zoo.registry_v2 import (
    ArtifactIdentity,
    EnvironmentIdentity,
    ModelReleaseRecord,
)


def _bindings():
    adapter = EcoliK12KnockoutGrowthAdapter()
    artifact = ArtifactIdentity.from_dict(
        {
            "schema_version": "vc.model-artifact.v1",
            "artifact_id": "test-only-ecoli-gem",
            "model_fingerprint": "1" * 64,
            "uri": None,
            "cache_key": "test-only/ecoli-gem.xml",
            "size_bytes": 1,
            "sha256": "2" * 64,
            "media_type": "application/sbml+xml",
            "license": "test-only",
            "source": "synthetic identity; no file exists",
            "safe_load_policy": "data_only",
            "legacy_incomplete": False,
        }
    )
    environment = EnvironmentIdentity.from_dict(
        {
            "schema_version": "vc.model-environment.v1",
            "environment_id": "test-only-ecoli-growth",
            "python_version": "3.test",
            "cpu_architecture": "test-only",
            "packages": [
                {"name": "cobra", "version": "test-only"},
                {"name": "swiglpk", "version": "test-only"},
            ],
            "lock_digest": "3" * 64,
            "image_digest": None,
            "resources": ["cpu"],
            "accelerators": [],
            "adapter_fingerprints": [adapter.fingerprint()],
            "legacy_incomplete": False,
        }
    )
    mapping = EcoliGrowthGeneMappingBinding(
        schema_version="vc.ecoli-growth-gene-mapping-binding.v1",
        asset=MappingAssetRef(
            asset_id="test-only-ncbigene-to-gem",
            path="test-only/no-file.tsv",
            version="test-only",
            sha256="4" * 64,
        ),
        source_namespace="NCBIGene",
        source_namespace_version="GCF_000005845.2",
        source_id_format="ncbi_gene_curie",
        target_namespace="test-only-gem-locus-tag",
        exact_mapping_required=True,
    )
    pack = EcoliGrowthDataBinding(
        schema_version="vc.ecoli-growth-data-binding.v1",
        pack_id="test-only-growth-data",
        pack_version="test-only",
        pack_fingerprint="5" * 64,
        data_kind="growth_condition",
        taxonomy_id="NCBITaxon:562",
        strain_id="NCBITaxon:511145",
        assembly_accession="GCF_000005845.2",
    )
    release = ModelReleaseRecord.from_dict(
        {
            "schema_version": "vc.model-release.v1",
            "release_id": "test-only-ecoli-growth",
            "model_name": "ecoli_growth_contract",
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
    execution = EcoliGrowthExecutionBinding(
        schema_version="vc.ecoli-growth-execution-binding.v1",
        medium_id="test-only-glucose-minimal",
        medium_fingerprint="8" * 64,
        condition_id="test-only-aerobic-37c",
        condition_fingerprint="9" * 64,
        objective_id="test-only-biomass-objective",
        objective_fingerprint="a" * 64,
        objective_unit="1/h",
        solver_id="test-only-linear-solver",
        solver_version="test-only",
        solver_configuration_fingerprint="b" * 64,
        deterministic=True,
    )
    mapping_fingerprint = mapping.fingerprint()
    compatibility = EcoliGrowthCompatibilityBinding(
        schema_version="vc.ecoli-growth-compatibility-binding.v1",
        model_release_fingerprint=release.fingerprint(),
        model_fingerprint=artifact.model_fingerprint,
        artifact_fingerprint=artifact.fingerprint(),
        environment_fingerprint=environment.fingerprint(),
        adapter_fingerprint=adapter.fingerprint(),
        pack_fingerprint=pack.pack_fingerprint,
        data_binding_fingerprint=pack.fingerprint(),
        mapping_asset_fingerprint=mapping_fingerprint,
        execution_binding_fingerprint=execution.fingerprint(),
        assets_verified=False,
        executable=False,
        reason="p14r_not_authorized",
    )
    scope = EcoliGrowthScope(
        schema_version="vc.ecoli-growth-scope.v1",
        taxonomy_id="NCBITaxon:562",
        scientific_name="Escherichia coli",
        strain_id="NCBITaxon:511145",
        strain_name="Escherichia coli K-12 MG1655",
        assembly_accession="GCF_000005845.2",
        gem_model_fingerprint=artifact.model_fingerprint,
        model_release_fingerprint=release.fingerprint(),
        gem_artifact_fingerprint=artifact.fingerprint(),
        environment_fingerprint=environment.fingerprint(),
        adapter_fingerprint=adapter.fingerprint(),
        pack_fingerprint=pack.pack_fingerprint,
        data_binding_fingerprint=pack.fingerprint(),
        compatibility_fingerprint=compatibility.fingerprint(),
        mapping_asset_fingerprint=mapping_fingerprint,
        execution_binding_fingerprint=execution.fingerprint(),
        medium_id=execution.medium_id,
        medium_fingerprint=execution.medium_fingerprint,
        condition_id=execution.condition_id,
        condition_fingerprint=execution.condition_fingerprint,
        objective_id=execution.objective_id,
        objective_fingerprint=execution.objective_fingerprint,
        objective_unit=execution.objective_unit,
        solver_configuration_fingerprint=execution.solver_configuration_fingerprint,
        request_gene_namespace="NCBIGene",
        request_gene_namespace_version="GCF_000005845.2",
        request_gene_id_format="ncbi_gene_curie",
        gem_gene_namespace="test-only-gem-locus-tag",
        output="growth_ratio",
        output_unit="dimensionless",
        reference="wild_type_same_gem_medium_condition",
    )
    protocol = EcoliGrowthValidationProtocol(
        schema_version="vc.ecoli-growth-validation-protocol.v1",
        scope_fingerprint=scope.fingerprint(),
        condition_data_fingerprint=pack.pack_fingerprint,
        baseline_fingerprint="d" * 64,
        split_unit="held_out_gene",
        biological_group_keys=("target_gene_id", "condition_id"),
        baseline="wild_type_same_gem_medium_condition",
        primary_metric="mean_absolute_error_growth_ratio",
        metric_direction="lower_is_better",
        paired_ci_required=True,
        independent_cohort_required=True,
        external_adaptation_steps=0,
        ood_axes=(
            "strain",
            "assembly",
            "gem",
            "medium",
            "condition",
            "gene_namespace",
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


def _request(scope: EcoliGrowthScope, protocol: EcoliGrowthValidationProtocol, **changes):
    raw = {
        "schema_version": "vc.request.v2",
        "request_id": "p14e-test-only",
        "species": {
            "schema_version": "vc.species-ref.v1",
            "taxonomy_id": scope.taxonomy_id,
            "scientific_name": scope.scientific_name,
            "common_name": "E. coli",
        },
        "cell_context": {
            "schema_version": "vc.cell-context.v1",
            "cell_type_name": scope.strain_name,
            "cell_type_id": None,
            "tissue_name": None,
            "tissue_id": None,
            "attributes": {
                "strain_id": scope.strain_id,
                "assembly_accession": scope.assembly_accession,
                "medium_id": scope.medium_id,
                "medium_fingerprint": scope.medium_fingerprint,
                "condition_id": scope.condition_id,
                "condition_fingerprint": scope.condition_fingerprint,
            },
        },
        "input_modality": {
            "schema_version": "vc.modality.v1",
            "name": "GEM",
            "ontology_id": "PRAXISMODALITY:FBA",
            "unit": None,
            "feature_namespace": scope.request_gene_namespace,
        },
        "output_modality": {
            "schema_version": "vc.modality.v1",
            "name": "growth_ratio",
            "ontology_id": "PRAXISOUTPUT:growth_ratio",
            "unit": "dimensionless",
            "feature_namespace": None,
        },
        "perturbation": {
            "schema_version": "vc.perturbation.v1",
            "kind": "gene",
            "targets": ["NCBIGene:945006"],
            "dose_value": None,
            "dose_unit": None,
            "timepoint": None,
        },
        "task": {
            "schema_version": "vc.task.v1",
            "task_type": "predict_knockout_growth",
            "requested_outputs": ["growth_ratio"],
        },
        "baseline_context": {
            "reference": scope.reference,
            "scope_fingerprint": scope.fingerprint(),
        },
        "metadata": {},
        "constraints": {
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


def _prepared():
    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    prepared = adapter.prepare_input(
        _request(scope, protocol),
        scope=scope,
        gem_artifact=artifact,
        environment=environment,
        model_release=release,
        mapping_asset=mapping,
        execution_binding=execution,
        validation_protocol=protocol,
        pack=pack,
        compatibility_report=compatibility,
    )
    return adapter, prepared, scope


def _raw(*, ratio=0.25, status="optimal", ood=False, abstain=False):
    return {
        "prediction": (
            None
            if abstain
            else {
                "knockout_objective": ratio,
                "wild_type_objective": 1.0,
                "objective_unit": "1/h",
            }
        ),
        "solver_status": status,
        "scope_fingerprint": _prepared()[2].fingerprint(),
        "uncertainty": {
            "available": False,
            "method": "deterministic_fba",
            "calibrated": False,
            "reason": "determinism is not calibrated uncertainty",
        },
        "ood": {
            "detected": ood,
            "dimensions": ["target"] if ood else [],
            "reason": "target outside exact scope" if ood else None,
        },
        "abstain": abstain,
        "abstain_reasons": ["exact scope rejected"] if abstain else [],
    }


def test_contracts_are_versioned_strict_frozen_and_identity_bound():
    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    assert adapter.input_contract.schema_version == "vc.ecoli-growth-adapter-input-contract.v1"
    assert adapter.output_contract.schema_version == "vc.ecoli-growth-adapter-output-contract.v1"
    assert adapter.identity().task == "predict_knockout_growth"
    assert adapter.identity().outputs == ("growth_ratio",)
    assert adapter.output_contract.shape == (1,)
    assert adapter.output_contract.unit == "dimensionless"
    assert adapter.input_contract.fingerprint() == adapter.identity().input_contract_fingerprint
    assert adapter.output_contract.fingerprint() == adapter.identity().output_contract_fingerprint
    assert len(scope.fingerprint()) == len(protocol.fingerprint()) == 64
    with pytest.raises(ValidationError, match="extra"):
        EcoliGrowthScope.model_validate({**scope.to_dict(), "scientifically_validated": True})
    with pytest.raises(ValidationError, match="frozen"):
        scope.medium_id = "changed"


def test_validation_protocol_is_preregistration_not_evidence_or_policy():
    *_, protocol = _bindings()
    assert protocol.external_adaptation_steps == 0
    assert protocol.paired_ci_required is True
    assert protocol.independent_cohort_required is True
    assert not {
        "result_sha256",
        "benchmark_passed",
        "scientifically_validated",
        "promotion_eligible",
        "production_promoted",
    }.intersection(protocol.to_dict())
    raw = protocol.to_dict()
    raw["promotion_eligible"] = True
    with pytest.raises(ValidationError, match="extra"):
        EcoliGrowthValidationProtocol.model_validate(raw)


def test_growth_adapter_is_local_only_and_default_registry_stays_delta_only():
    adapter, *_ = _bindings()
    assert DEFAULT_ADAPTER_REGISTRY.keys() == (("predict_delta_expression", "delta_expression"),)
    with pytest.raises(AdapterContractError, match="unregistered"):
        DEFAULT_ADAPTER_REGISTRY.resolve("predict_knockout_growth", "growth_ratio")
    local = AdapterRegistry([adapter])
    assert local.resolve("predict_knockout_growth", "growth_ratio") is adapter
    with pytest.raises(AdapterContractError, match="ambiguous"):
        local.resolve_requested("predict_knockout_growth", ["growth_ratio", "growth"])


def test_prepare_input_binds_every_exact_identity_without_reading_assets():
    adapter, prepared, scope = _prepared()
    model_input = EcoliK12KnockoutGrowthInput.model_validate(prepared.model_input)
    assert prepared.pack_fingerprint == scope.pack_fingerprint
    assert prepared.compatibility_fingerprint == scope.compatibility_fingerprint
    assert model_input.scope == scope
    assert model_input.target_gene_id == "NCBIGene:945006"
    assert model_input.scope_fingerprint == scope.fingerprint()
    assert model_input.adapter_fingerprint == adapter.fingerprint()
    assert prepared.values is None and prepared.shape is None


@pytest.mark.parametrize(
    ("change", "value", "match"),
    [
        ("species__taxonomy_id", "NCBITaxon:2", "taxonomy"),
        ("species__scientific_name", "Bacteria", "species"),
        ("cell_context__cell_type_name", "Escherichia coli K-12", "strain"),
        ("cell_context__attributes__assembly_accession", "GCF_000000000.1", "scope"),
        ("input_modality__name", "scRNA", "input modality"),
        ("input_modality__feature_namespace", "b-number", "namespace"),
        ("output_modality__name", "growth", "task/output"),
        ("output_modality__unit", "1", "unit"),
        ("perturbation__kind", "drug", "single gene knockout"),
        ("perturbation__targets", ["b0720"], "NCBIGene"),
        ("perturbation__targets", ["NCBIGene:945006", "NCBIGene:947479"], "single gene"),
        ("perturbation__dose_value", 1.0, "single gene knockout"),
        ("perturbation__timepoint", "1h", "single gene knockout"),
        ("task__task_type", "growth", "task/output"),
        ("task__requested_outputs", ["growth_ratio", "growth"], "task/output"),
        ("baseline_context__reference", "unspecified", "baseline"),
        ("constraints__scope_fingerprint", "f" * 64, "scope"),
        ("metadata", {"ignored": True}, "metadata"),
    ],
)
def test_prepare_input_rejects_scope_task_namespace_and_target_drift(change, value, match):
    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    request = _request(scope, protocol, **{change: value})
    with pytest.raises(AdapterContractError, match=match):
        adapter.prepare_input(
            request,
            scope=scope,
            gem_artifact=artifact,
            environment=environment,
            model_release=release,
            mapping_asset=mapping,
            execution_binding=execution,
            validation_protocol=protocol,
            pack=pack,
            compatibility_report=compatibility,
        )


@pytest.mark.parametrize(
    ("binding", "match"),
    [
        ("artifact", "artifact"),
        ("environment", "environment"),
        ("release", "release"),
        ("mapping", "mapping"),
        ("execution", "execution"),
        ("pack", "Pack"),
        ("compatibility", "compatibility"),
        ("protocol", "protocol"),
    ],
)
def test_prepare_input_rejects_missing_and_drifted_bindings(binding, match):
    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    kwargs = {
        "scope": scope,
        "gem_artifact": artifact,
        "environment": environment,
        "model_release": release,
        "mapping_asset": mapping,
        "execution_binding": execution,
        "validation_protocol": protocol,
        "pack": pack,
        "compatibility_report": compatibility,
    }
    parameter = {
        "artifact": "gem_artifact",
        "release": "model_release",
        "mapping": "mapping_asset",
        "execution": "execution_binding",
        "compatibility": "compatibility_report",
        "protocol": "validation_protocol",
    }.get(binding, binding)
    kwargs[parameter] = None
    with pytest.raises((AdapterContractError, TypeError), match=match):
        adapter.prepare_input(_request(scope, protocol), **kwargs)


def test_prepare_input_rejects_cross_bound_identity_fingerprints():
    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    changed = scope.model_copy(update={"gem_artifact_fingerprint": "e" * 64})
    with pytest.raises(AdapterContractError, match="artifact"):
        adapter.prepare_input(
            _request(changed, protocol.model_copy(update={"scope_fingerprint": changed.fingerprint()})),
            scope=changed,
            gem_artifact=artifact,
            environment=environment,
            model_release=release,
            mapping_asset=mapping,
            execution_binding=execution,
            validation_protocol=protocol.model_copy(update={"scope_fingerprint": changed.fingerprint()}),
            pack=pack,
            compatibility_report=compatibility,
        )
    wrong_environment = environment.model_copy(update={"adapter_fingerprints": ("f" * 64,)})
    changed = scope.model_copy(update={"environment_fingerprint": wrong_environment.fingerprint()})
    changed_protocol = protocol.model_copy(update={"scope_fingerprint": changed.fingerprint()})
    with pytest.raises(AdapterContractError, match="adapter"):
        adapter.prepare_input(
            _request(changed, changed_protocol),
            scope=changed,
            gem_artifact=artifact,
            environment=wrong_environment,
            model_release=release,
            mapping_asset=mapping,
            execution_binding=execution,
            validation_protocol=changed_protocol,
            pack=pack,
            compatibility_report=compatibility,
        )


def test_prepare_input_rejects_unbound_release_condition_data_and_load_policy():
    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    bad_protocol = protocol.model_copy(update={"condition_data_fingerprint": "e" * 64})
    with pytest.raises(AdapterContractError, match="condition-data Pack"):
        adapter.prepare_input(
            _request(scope, bad_protocol),
            scope=scope,
            gem_artifact=artifact,
            environment=environment,
            model_release=release,
            mapping_asset=mapping,
            execution_binding=execution,
            validation_protocol=bad_protocol,
            pack=pack,
            compatibility_report=compatibility,
        )

    unsafe_artifact = artifact.model_copy(update={"safe_load_policy": "restricted_deserializer"})
    unsafe_release = release.model_copy(update={"artifact_fingerprints": (unsafe_artifact.fingerprint(),)})
    unsafe_scope = scope.model_copy(
        update={
            "gem_artifact_fingerprint": unsafe_artifact.fingerprint(),
            "model_release_fingerprint": unsafe_release.fingerprint(),
        }
    )
    unsafe_protocol = protocol.model_copy(update={"scope_fingerprint": unsafe_scope.fingerprint()})
    with pytest.raises(AdapterContractError, match="data_only"):
        adapter.prepare_input(
            _request(unsafe_scope, unsafe_protocol),
            scope=unsafe_scope,
            gem_artifact=unsafe_artifact,
            environment=environment,
            model_release=unsafe_release,
            mapping_asset=mapping,
            execution_binding=execution,
            validation_protocol=unsafe_protocol,
            pack=pack,
            compatibility_report=compatibility,
        )

    wrong_media = artifact.model_copy(update={"media_type": "text/plain"})
    wrong_media_release = release.model_copy(
        update={"artifact_fingerprints": (wrong_media.fingerprint(),)}
    )
    wrong_media_scope = scope.model_copy(
        update={
            "gem_artifact_fingerprint": wrong_media.fingerprint(),
            "model_release_fingerprint": wrong_media_release.fingerprint(),
        }
    )
    wrong_media_protocol = protocol.model_copy(
        update={"scope_fingerprint": wrong_media_scope.fingerprint()}
    )
    with pytest.raises(AdapterContractError, match="media_type"):
        adapter.prepare_input(
            _request(wrong_media_scope, wrong_media_protocol),
            scope=wrong_media_scope,
            gem_artifact=wrong_media,
            environment=environment,
            model_release=wrong_media_release,
            mapping_asset=mapping,
            execution_binding=execution,
            validation_protocol=wrong_media_protocol,
            pack=pack,
            compatibility_report=compatibility,
        )


def test_p8_scrna_pack_and_untyped_compatibility_cannot_impersonate_growth_data():
    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    kwargs = {
        "scope": scope,
        "gem_artifact": artifact,
        "environment": environment,
        "model_release": release,
        "mapping_asset": mapping,
        "execution_binding": execution,
        "validation_protocol": protocol,
        "pack": pack,
        "compatibility_report": compatibility,
    }
    with pytest.raises(TypeError, match="EcoliGrowthDataBinding"):
        adapter.prepare_input(
            _request(scope, protocol),
            **{
                **kwargs,
                "pack": {"pack_id": "p8-bacteria-tiny", "fingerprint": pack.pack_fingerprint},
            },
        )
    with pytest.raises(TypeError, match="EcoliGrowthCompatibilityBinding"):
        adapter.prepare_input(
            _request(scope, protocol),
            **{**kwargs, "compatibility_report": object()},
        )

    relabeled_pack = pack.model_copy(update={"pack_id": "p8-bacteria-tiny"})
    with pytest.raises(AdapterContractError, match="growth-data binding fingerprint"):
        adapter.prepare_input(
            _request(scope, protocol),
            **{**kwargs, "pack": relabeled_pack},
        )


def test_model_copy_cannot_bypass_typed_binding_literals():
    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    base = {
        "scope": scope,
        "gem_artifact": artifact,
        "environment": environment,
        "model_release": release,
        "mapping_asset": mapping,
        "execution_binding": execution,
        "validation_protocol": protocol,
        "pack": pack,
        "compatibility_report": compatibility,
    }
    invalid = (
        ("pack", pack.model_copy(update={"data_kind": "scRNA"}), "Pack binding"),
        (
            "compatibility_report",
            compatibility.model_copy(update={"executable": True}),
            "compatibility binding",
        ),
        (
            "execution_binding",
            execution.model_copy(update={"deterministic": False}),
            "execution binding",
        ),
        (
            "mapping_asset",
            mapping.model_copy(update={"exact_mapping_required": False}),
            "mapping binding",
        ),
        (
            "scope",
            scope.model_copy(update={"assembly_accession": "GCF_000000000.1"}),
            "scope binding",
        ),
    )
    for parameter, value, match in invalid:
        with pytest.raises(AdapterContractError, match=match):
            adapter.prepare_input(
                _request(scope, protocol),
                **{**base, parameter: value},
            )


def test_nested_model_copy_extras_cannot_be_silently_normalized():
    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    request = _request(scope, protocol)
    kwargs = {
        "scope": scope,
        "gem_artifact": artifact,
        "environment": environment,
        "model_release": release,
        "mapping_asset": mapping,
        "execution_binding": execution,
        "validation_protocol": protocol,
        "pack": pack,
        "compatibility_report": compatibility,
    }
    nested_request = request.model_copy(
        update={
            "species": request.species.model_copy(
                update={"production_promoted": True}
            )
        }
    )
    nested_mapping = mapping.model_copy(
        update={
            "asset": mapping.asset.model_copy(
                update={"scientifically_validated": True}
            )
        }
    )
    nested_environment = environment.model_copy(
        update={
            "packages": (
                environment.packages[0].model_copy(
                    update={"promotion_eligible": True}
                ),
                *environment.packages[1:],
            )
        }
    )
    cases = (
        (nested_request, kwargs, "invalid request"),
        (
            request,
            {**kwargs, "mapping_asset": nested_mapping},
            "invalid mapping binding",
        ),
        (
            request,
            {**kwargs, "environment": nested_environment},
            "invalid environment binding",
        ),
    )
    for candidate_request, candidate_kwargs, match in cases:
        with pytest.raises(AdapterContractError, match=match):
            adapter.prepare_input(candidate_request, **candidate_kwargs)


def test_nested_declared_subclass_fields_cannot_cross_the_input_boundary():
    class PromotedSpeciesRef(SpeciesRef):
        production_promoted: bool = Field(exclude=True)

    class ScientificMappingAsset(MappingAssetRef):
        scientifically_validated: bool = Field(exclude=True)

    adapter, artifact, environment, release, mapping, execution, pack, compatibility, scope, protocol = _bindings()
    request = _request(scope, protocol)
    promoted_species = PromotedSpeciesRef(
        **request.species.model_dump(mode="python"),
        production_promoted=True,
    )
    forged = request.model_copy(update={"species": promoted_species})
    with pytest.raises(AdapterContractError, match="invalid request"):
        adapter.prepare_input(
            forged,
            scope=scope,
            gem_artifact=artifact,
            environment=environment,
            model_release=release,
            mapping_asset=mapping,
            execution_binding=execution,
            validation_protocol=protocol,
            pack=pack,
            compatibility_report=compatibility,
        )

    scientific_asset = ScientificMappingAsset(
        **mapping.asset.model_dump(mode="python"),
        scientifically_validated=True,
    )
    forged_mapping = mapping.model_copy(update={"asset": scientific_asset})
    with pytest.raises(AdapterContractError, match="invalid mapping binding"):
        adapter.prepare_input(
            request,
            scope=scope,
            gem_artifact=artifact,
            environment=environment,
            model_release=release,
            mapping_asset=forged_mapping,
            execution_binding=execution,
            validation_protocol=protocol,
            pack=pack,
            compatibility_report=compatibility,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("strain_id", "NCBITaxon:562"),
        ("strain_name", "Escherichia coli K-12"),
        ("assembly_accession", "GCF_000000000.1"),
    ],
)
def test_scope_freezes_exact_k12_mg1655_identity(field, value):
    *_, scope, _ = _bindings()
    with pytest.raises(ValidationError, match=field):
        EcoliGrowthScope.model_validate({**scope.to_dict(), field: value})


def test_protocol_freezes_group_keys_and_exact_ood_axes():
    *_, protocol = _bindings()
    with pytest.raises(ValidationError, match="biological_group_keys"):
        EcoliGrowthValidationProtocol.model_validate(
            {**protocol.to_dict(), "biological_group_keys": ["not_a_real_field"]}
        )
    with pytest.raises(ValidationError, match="ood_axes"):
        EcoliGrowthValidationProtocol.model_validate(
            {**protocol.to_dict(), "ood_axes": [*protocol.ood_axes, "invented_axis"]}
        )
    with pytest.raises(ValidationError, match="biological_group_keys"):
        EcoliGrowthValidationProtocol.model_validate(
            {
                **protocol.to_dict(),
                "biological_group_keys": list(reversed(protocol.biological_group_keys)),
            }
        )
    with pytest.raises(ValidationError, match="ood_axes"):
        EcoliGrowthValidationProtocol.model_validate(
            {**protocol.to_dict(), "ood_axes": list(reversed(protocol.ood_axes))}
        )
    with pytest.raises(ValidationError, match="metric_direction"):
        EcoliGrowthValidationProtocol.model_validate(
            {**protocol.to_dict(), "metric_direction": "higher_is_better"}
        )
    with pytest.raises(ValidationError, match="primary_metric"):
        EcoliGrowthValidationProtocol.model_validate(
            {**protocol.to_dict(), "primary_metric": "accuracy"}
        )


def test_synthetic_output_computes_only_growth_ratio_and_conforms_deterministically():
    adapter, prepared, scope = _prepared()
    raw = _raw(ratio=0.25)
    envelope = adapter.adapt_output(prepared, raw)
    assert envelope.values == (0.25,)
    assert envelope.shape == (1,)
    assert envelope.unit == "dimensionless"
    assert envelope.projection_metadata == {
        "objective_unit": "1/h",
        "reference": "wild_type_same_gem_medium_condition",
        "scope_fingerprint": scope.fingerprint(),
        "solver_status": "optimal",
    }
    projection = adapter.project_prepared_output(prepared, envelope)
    assert projection == {"growth_ratio": [0.25]}
    assert "growth" not in projection
    assert "flux" not in projection
    second = adapter.adapt_output(prepared, deepcopy(raw))
    assert second.to_dict() == envelope.to_dict()
    assert second.fingerprint() == envelope.fingerprint()
    assert adapter.project_prepared_output(prepared, second) == projection
    report = run_adapter_conformance(adapter, prepared, raw)
    assert report.adapter_fingerprint == adapter.fingerprint()
    assert report.deterministic is True


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("prediction", "knockout_objective"), True, "finite number"),
        (("prediction", "knockout_objective"), "0.25", "finite number"),
        (("prediction", "knockout_objective"), float("nan"), "finite number"),
        (("prediction", "knockout_objective"), float("inf"), "finite number"),
        (("prediction", "knockout_objective"), 2**53, "JSON-safe"),
        (("prediction", "knockout_objective"), -0.1, "non-negative"),
        (("prediction", "wild_type_objective"), 0.0, "positive"),
        (("prediction", "objective_unit"), "mmol/gDW/h", "objective unit"),
        (("scope_fingerprint",), "e" * 64, "scope"),
        (("solver_status",), "unknown-new-status", "solver status"),
        (("uncertainty", "available"), True, "uncertainty unavailable"),
    ],
)
def test_output_rejects_wrong_type_value_unit_scope_and_uncertainty(path, value, match):
    adapter, prepared, _ = _prepared()
    raw = _raw()
    cursor = raw
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(AdapterContractError, match=match):
        adapter.adapt_output(prepared, raw)


@pytest.mark.parametrize("reserved", ["flux", "essential", "evidence", "policy", "production_promoted"])
def test_output_rejects_unknown_trace_science_and_policy_fields(reserved):
    adapter, prepared, _ = _prepared()
    raw = _raw()
    raw[reserved] = {} if reserved != "production_promoted" else True
    with pytest.raises(AdapterContractError, match="unknown wrapper output"):
        adapter.adapt_output(prepared, raw)


@pytest.mark.parametrize("status", ["infeasible", "unbounded", "target_not_found", "error"])
def test_nonoptimal_solver_status_requires_value_free_abstention(status):
    adapter, prepared, _ = _prepared()
    raw = _raw(status=status)
    with pytest.raises(AdapterContractError, match="must abstain"):
        adapter.adapt_output(prepared, raw)
    raw = _raw(status=status, abstain=True)
    envelope = adapter.adapt_output(prepared, raw)
    assert envelope.abstain is True
    assert envelope.values is None and envelope.shape is None


def test_ood_requires_value_free_abstention_and_abstain_requires_reason():
    adapter, prepared, _ = _prepared()
    with pytest.raises(AdapterContractError, match="OOD output must abstain"):
        adapter.adapt_output(prepared, _raw(ood=True))
    raw = _raw(ood=True, abstain=True)
    envelope = adapter.adapt_output(prepared, raw)
    assert envelope.abstain and envelope.ood.detected
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
    with pytest.raises(AdapterContractError, match="identify an exact-scope dimension"):
        adapter.adapt_output(prepared, raw)


def test_output_rejects_prediction_shape_and_unknown_nested_fields():
    adapter, prepared, _ = _prepared()
    raw = _raw()
    raw["prediction"]["growth_ratio"] = 0.25
    with pytest.raises(AdapterContractError, match="unknown prediction"):
        adapter.adapt_output(prepared, raw)


def test_output_requires_every_field_and_direct_envelope_cannot_forge_uncertainty():
    adapter, prepared, _ = _prepared()
    raw = _raw()
    raw.pop("solver_status")
    with pytest.raises(AdapterContractError, match="missing fields"):
        adapter.adapt_output(prepared, raw)

    envelope = adapter.adapt_output(prepared, _raw())
    forged = envelope.model_copy(
        update={
            "uncertainty": AdapterUncertainty(
                available=True,
                method="pretend",
                calibrated=False,
                value=0.1,
            )
        }
    )
    with pytest.raises(AdapterContractError, match="uncertainty unavailable"):
        adapter.validate_prepared_envelope(prepared, forged)
    invalid_nested = envelope.model_copy(
        update={
            "uncertainty": envelope.uncertainty.model_copy(
                update={"available": 0, "calibrated": 0, "reason": 123}
            )
        }
    )
    with pytest.raises(AdapterContractError, match="invalid adapter output envelope"):
        adapter.validate_prepared_envelope(prepared, invalid_nested)
    raw = _raw()
    raw["prediction"]["knockout_objective"] = [0.25]
    with pytest.raises(AdapterContractError, match="finite number"):
        adapter.adapt_output(prepared, raw)


@pytest.mark.parametrize(
    ("field", "extra", "match"),
    [
        ("uncertainty", "scientifically_validated", "uncertainty"),
        ("ood", "promotion_eligible", "ood"),
        ("provenance", "production_promoted", "provenance"),
    ],
)
def test_nested_envelope_extras_fail_closed(field, extra, match):
    adapter, prepared, _ = _prepared()
    envelope = adapter.adapt_output(prepared, _raw())
    nested = getattr(envelope, field).model_copy(update={extra: True})
    forged = envelope.model_copy(update={field: nested})
    with pytest.raises(AdapterContractError, match=match):
        adapter.validate_prepared_envelope(prepared, forged)


def test_prepared_model_input_is_revalidated_and_cross_request_drift_fails():
    adapter, prepared, _ = _prepared()
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
                "validation_protocol_fingerprint": "e" * 64,
            }
        }
    )
    with pytest.raises(AdapterContractError, match="prepared E. coli growth input"):
        adapter.validate_prepared_input(forged_protocol)


def test_envelope_metadata_and_projection_cannot_escape_the_exact_scope():
    adapter, prepared, _ = _prepared()
    envelope = adapter.adapt_output(prepared, _raw())
    drifted = envelope.model_copy(
        update={
            "projection_metadata": {
                **dict(envelope.projection_metadata),
                "objective_unit": "wrong-unit",
            }
        }
    )
    with pytest.raises(AdapterContractError, match="prepared input"):
        adapter.validate_prepared_envelope(prepared, drifted)
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
    wrong_prepared = prepared.model_copy(
        update={
            "request_fingerprint": "e" * 64,
            "model_input": {
                **deepcopy(dict(prepared.model_input)),
                "request_fingerprint": "e" * 64,
            },
        }
    )
    with pytest.raises(AdapterContractError, match="provenance"):
        adapter.project_prepared_output(wrong_prepared, envelope)
    abstention = adapter.adapt_output(
        prepared,
        _raw(status="infeasible", abstain=True),
    )
    with pytest.raises(AdapterContractError, match="cannot project an abstaining"):
        adapter.project_prepared_output(prepared, abstention)
    with pytest.raises(AdapterContractError, match="only growth_ratio"):
        adapter.validate_projection({"growth_ratio": [0.25], "flux": [1.0]})


def test_standalone_output_paths_fail_closed_without_prepared_binding():
    adapter, prepared, _ = _prepared()
    envelope = adapter.adapt_output(prepared, _raw())
    for operation, match in (
        (lambda: adapter.validate_envelope(envelope), "prepared input"),
        (lambda: adapter.aggregate((envelope,)), "no standalone aggregation"),
        (lambda: adapter.project_output(envelope), "prepared input"),
    ):
        with pytest.raises(AdapterContractError, match=match):
            operation()


def test_contract_module_has_no_real_gem_runtime_or_asset_fallback_imports():
    source = inspect.getsource(ecoli_growth_contract)
    for forbidden in (
        "import cobra",
        "EcoliGEM",
        "GemModel",
        "GemWrapper",
        "read_sbml_model",
        "cobra_bundled_textbook",
        "e_coli_core",
    ):
        assert forbidden not in source
