"""P16E: contract-only K562 Golden Norman delta-expression adapter tests.

The numeric vectors are synthetic.  Only the small checked-in YAML/JSON
identity manifests are read; no H5AD, NPY, model wrapper, or science runner is
imported or opened.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import Field, ValidationError

from praxis_virtualcell.core.request_v2 import SpeciesRef, VirtualCellRequestV2
from praxis_virtualcell.model_zoo import k562_golden_delta_contract
from praxis_virtualcell.model_zoo.adapter_sdk import (
    DEFAULT_ADAPTER_REGISTRY,
    AdapterContractError,
    AdapterRegistry,
    AdapterUncertainty,
    DeltaExpressionReferenceAdapter,
    run_adapter_conformance,
)
from praxis_virtualcell.model_zoo.k562_golden_delta_contract import (
    K562GoldenAdapterInputContract,
    K562GoldenAdapterOutputContract,
    K562GoldenCompatibilityBinding,
    K562GoldenDataBinding,
    K562GoldenExecutionBinding,
    K562GoldenPerturbationAdapter,
    K562GoldenPerturbationBinding,
    K562GoldenPerturbationScope,
    K562GoldenPreparedModelInput,
    K562GoldenValidationProtocol,
)
from praxis_virtualcell.model_zoo.registry_v2 import (
    ArtifactIdentity,
    EnvironmentIdentity,
    ModelReleaseRecord,
)

_ROOT = Path(__file__).resolve().parents[2]
_GOLDEN = _ROOT / "data" / "golden" / "norman_2019"
_CONTRACT_SHA256 = "6bfc46e23e55e05a2c87dcdac9bd48da6c1f6bd2240742dc18f73ec963cf0d76"
_PACK_MANIFEST_SHA256 = "704b81da74fd96907b7e6012757b2c12104fcf3a2a3ae56af52c76d7f2c163a6"
_ARTIFACT_MANIFEST_SHA256 = "724b701beda574ad344b764de09dafb86648e49c9a327df717212aaf25cc71ac"
_PACK_FINGERPRINT = "42165e430bab3474cdc9e607770ff5e204608c4243f84e492c08e2c6442c55ee"
_CANONICAL_CONTRACT_SHA256 = "f34afa761239abc97033c78bb9d0c29a1c36a4c7d1a106a9cbbaa805a5196ff5"
_DEFAULT_ADAPTER_SHA256 = "17afc27e56dba13567001ff1982cbf1660e2948fadf2147301a1d0dcf61aeb3d"
_DEFAULT_INPUT_CONTRACT_SHA256 = "d10cf437291dc1ebb1689c3f4c5eea4d82af3842491c224172215faddca93078"
_DEFAULT_OUTPUT_CONTRACT_SHA256 = "d863783786504ebf768cfd7e2fbad66cfd03a029deb1dee3543a9872712e363d"
_H5AD_SHA256 = "43da7aeeaca2a3ceb00ec6e9ee983b9b708b01f85922cc7afee229225a66792a"
_GOLDEN_CONTRACT_SHA256 = "456242651b50a87f507c6e9787999d4fd325beec82106363c7261cbdaa744521"
_FEATURE_IDS_SHA256 = "ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7"
_FEATURE_RECORDS_SHA256 = "1cc8b612bef0a0d7daac01bb8cc509346a4a32850f93298f29865bb2328d9747"
_SPLIT_SHA256 = "c501e8a05514b914b216ddb2dbe0a94e709fa7a1e2214d727b831102503f956e"
_CONDITION_IDS_SHA256 = "6f41dd46159a926ad476152d20c2f82e5def422f16a8213b0918af48594cabb3"
_MATCHED_CONTROL_SHA256 = "2fc6ba835e3a9353345651b9369abdd189c6017a854932c038b157faa4b378ae"
_PERTURBATION_IDS_SHA256 = "e69d8b83e3f69a628c545b3c44f6ad694d8406619451f1db1b6489be33fc9e21"
_CONDITION_VALUES_SHA256 = "7f3e175c495bc9499d852965869bafc23249948e0be5c87eb89e5d01befc44c9"
_PERTURBATION_RECORDS_SHA256 = "0a43f9c57560f7192c0a848cb1ec044a9bf2bfdbc20d6405f98d73b3ca04d1e9"
_TARGET_IDS_SHA256 = "4f58ed5c3ad7355ccba64eed0dd95e02cbcbf75a977d6aec2a1cfd5357abd64c"
_CONTROL_ASSIGNMENT_SHA256 = "8f09650026e297ce0e010120814230bc7de306364ab49316b7c102e836c6e3d5"
_UNSEEN_TARGETS_SHA256 = "3bec2a15f4c5965dd32112c3508e4b70ead1724f308d597ab61e9b6210587de3"
_NO_CHANGE_RESULT_SHA256 = "38182a3fdb24666b8d76d9b118d2de4fd8cfd998ae025a54d7fecc42e09f7b5e"
_GLOBAL_MEAN_RESULT_SHA256 = "2b757d3e2d4e657f9bdc3aa890ee6d84ae5096661246ff4f881045676bb98d3a"
_ADDITIVE_RESULT_SHA256 = "b82dc7ab26c6f6fdef4414f6b05c51edb32b2a35e4c00f45824cc839ab9cf1a9"
_EVALUATION_SHA256 = "1cc1110a75183f1b271a8caf34db9998046f93bd42abda278f725879d38eb79c"
_SINGLE_RECORD_SHA256 = "e04567ee8d8fb3273d600b3dc8956c3f0dd35d4e4bab1d1a5ba1fb83f483b9c1"
_COMBINATION_RECORD_SHA256 = "7b77f2c32cde91604fe8182fa38af90a991c1c10f27fdc116d6f94aa6eff2a85"
_SINGLE_TARGETS = ("ENSG00000106546",)
_COMBINATION_TARGETS = ("ENSG00000106546", "ENSG00000163497")
_OOD_AXES = (
    "iid",
    "perturbation",
    "combination",
    "cell_type",
    "donor",
    "dataset_platform",
    "species",
    "dose_time",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _checked_in_manifests():
    contract = yaml.safe_load((_GOLDEN / "contract.yaml").read_text())
    pack = yaml.safe_load((_GOLDEN / "pack.manifest.yaml").read_text())
    artifact = json.loads((_GOLDEN / "artifact-manifest.json").read_text())
    return contract, pack, artifact


def _bindings(evaluation_scope: str = "single_gene"):
    adapter = K562GoldenPerturbationAdapter()
    artifact = ArtifactIdentity.from_dict(
        {
            "schema_version": "vc.model-artifact.v1",
            "artifact_id": "test-only-k562-delta-model",
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
            "environment_id": "test-only-k562-delta",
            "python_version": "3.test",
            "cpu_architecture": "test-only",
            "packages": [{"name": "pydantic", "version": "test-only"}],
            "lock_digest": "3" * 64,
            "image_digest": None,
            "resources": ["cpu"],
            "accelerators": [],
            "adapter_fingerprints": [adapter.fingerprint()],
            "legacy_incomplete": False,
        }
    )
    pack = K562GoldenDataBinding(
        schema_version="vc.k562-golden-data-binding.v1",
        pack_id="norman-2019-k562-golden",
        pack_version="1.0.0",
        pack_fingerprint=_PACK_FINGERPRINT,
        canonical_contract_fingerprint=_CANONICAL_CONTRACT_SHA256,
        contract_yaml_sha256=_CONTRACT_SHA256,
        contract_yaml_size_bytes=4749,
        pack_manifest_sha256=_PACK_MANIFEST_SHA256,
        pack_manifest_size_bytes=30074,
        artifact_manifest_sha256=_ARTIFACT_MANIFEST_SHA256,
        artifact_manifest_size_bytes=3864,
        h5ad_path="norman_k562_golden.h5ad",
        h5ad_media_type="application/vnd.anndata+hdf5",
        h5ad_sha256=_H5AD_SHA256,
        h5ad_size_bytes=2285816806,
        golden_contract_path="golden_contract.json",
        golden_contract_media_type="application/json",
        golden_contract_sha256=_GOLDEN_CONTRACT_SHA256,
        golden_contract_size_bytes=4663,
        matrix_shape=(91205, 5045),
        license_id="CC0-1.0",
        taxonomy_id="NCBITaxon:9606",
        scientific_name="Homo sapiens",
        cell_identity_id="CVCL_0004",
        assembly_name="GRCh38",
        assembly_accession="GCA_000001405.15",
        modality_name="scRNA",
        modality_id="EFO:0008913",
        feature_namespace="EnsemblGene",
        feature_namespace_version="Ensembl 84",
        feature_id_format="ensembl_gene",
        source_cell_type_value="A549",
        source_cell_type_interpretation="upstream_metadata_error_preserved",
        feature_ids_sha256=_FEATURE_IDS_SHA256,
        feature_records_sha256=_FEATURE_RECORDS_SHA256,
        split_sha256=_SPLIT_SHA256,
        condition_ids_sha256=_CONDITION_IDS_SHA256,
        matched_control_sha256=_MATCHED_CONTROL_SHA256,
        perturbation_ids_sha256=_PERTURBATION_IDS_SHA256,
        condition_values_sha256=_CONDITION_VALUES_SHA256,
        perturbation_records_sha256=_PERTURBATION_RECORDS_SHA256,
        target_ids_sha256=_TARGET_IDS_SHA256,
        control_assignment_sha256=_CONTROL_ASSIGNMENT_SHA256,
        unseen_train_target_ids_sha256=_UNSEEN_TARGETS_SHA256,
        source_control_condition="ctrl",
        train_control_condition_id="norman.control.train",
        validation_control_condition_id="norman.control.validation",
        test_control_condition_id="norman.control.test",
        train_control_guide="NegCtrl0_NegCtrl0__NegCtrl0_NegCtrl0",
        validation_control_guide="NegCtrl10_NegCtrl0__NegCtrl10_NegCtrl0",
        test_control_guide="NegCtrl11_NegCtrl0__NegCtrl11_NegCtrl0",
    )
    if evaluation_scope == "single_gene":
        condition_id = "AHR+ctrl"
        condition_record_fingerprint = _SINGLE_RECORD_SHA256
        perturbation_kind = "gene"
        targets = _SINGLE_TARGETS
    else:
        condition_id = "AHR+FEV"
        condition_record_fingerprint = _COMBINATION_RECORD_SHA256
        perturbation_kind = "gene_combination"
        targets = _COMBINATION_TARGETS
    perturbation = K562GoldenPerturbationBinding(
        schema_version="vc.k562-golden-perturbation-binding.v1",
        evaluation_scope=evaluation_scope,
        condition_id=condition_id,
        condition_record_fingerprint=condition_record_fingerprint,
        perturbation_kind=perturbation_kind,
        ordered_target_ids=targets,
        pack_fingerprint=pack.pack_fingerprint,
        artifact_manifest_sha256=pack.artifact_manifest_sha256,
        condition_values_sha256=pack.condition_values_sha256,
        perturbation_records_sha256=pack.perturbation_records_sha256,
        target_ids_sha256=pack.target_ids_sha256,
        record_membership_verified=False,
        reason="p16r_not_authorized",
    )
    execution = K562GoldenExecutionBinding(
        schema_version="vc.k562-golden-execution-binding.v1",
        runner_id="test-only-k562-delta-runner",
        runner_version="test-only",
        execution_mode="native_delta_expression",
        feature_count=5045,
        feature_ids_sha256=pack.feature_ids_sha256,
        feature_records_sha256=pack.feature_records_sha256,
        value_semantics="condition_mean_X_minus_matched_split_control_mean_X",
        reference="matched_split_control_mean_X",
        output_unit=None,
        inference_configuration_fingerprint="d" * 64,
        preserve_feature_order=True,
        absolute_to_delta_conversion_allowed=False,
        normalization_allowed=False,
        reordering_allowed=False,
        fill_allowed=False,
        imputation_allowed=False,
        deduplication_allowed=False,
    )
    release = ModelReleaseRecord.from_dict(
        {
            "schema_version": "vc.model-release.v1",
            "release_id": "test-only-k562-golden-delta",
            "model_name": "k562_golden_delta_contract",
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
    compatibility = K562GoldenCompatibilityBinding(
        schema_version="vc.k562-golden-compatibility-binding.v1",
        model_release_fingerprint=release.fingerprint(),
        model_fingerprint=artifact.model_fingerprint,
        artifact_fingerprint=artifact.fingerprint(),
        environment_fingerprint=environment.fingerprint(),
        adapter_fingerprint=adapter.fingerprint(),
        pack_fingerprint=pack.pack_fingerprint,
        data_binding_fingerprint=pack.fingerprint(),
        perturbation_binding_fingerprint=perturbation.fingerprint(),
        execution_binding_fingerprint=execution.fingerprint(),
        assets_verified=False,
        executable=False,
        reason="p16r_not_authorized",
    )
    scope = K562GoldenPerturbationScope(
        schema_version="vc.k562-golden-perturbation-scope.v1",
        taxonomy_id="NCBITaxon:9606",
        scientific_name="Homo sapiens",
        cell_identity_name="K562",
        cell_identity_id="CVCL_0004",
        assembly_name="GRCh38",
        assembly_accession="GCA_000001405.15",
        assay_name="scRNA",
        assay_id="EFO:0008913",
        feature_namespace="EnsemblGene",
        feature_namespace_version="Ensembl 84",
        feature_id_format="ensembl_gene",
        feature_count=5045,
        feature_ids_sha256=pack.feature_ids_sha256,
        feature_records_sha256=pack.feature_records_sha256,
        perturbation_action="CRISPR activation",
        dose_value=1.0,
        dose_unit="1",
        time_value=5.0,
        time_unit="d",
        request_timepoint="5d",
        evaluation_scope=evaluation_scope,
        model_fingerprint=artifact.model_fingerprint,
        model_release_fingerprint=release.fingerprint(),
        model_artifact_fingerprint=artifact.fingerprint(),
        environment_fingerprint=environment.fingerprint(),
        adapter_fingerprint=adapter.fingerprint(),
        pack_fingerprint=pack.pack_fingerprint,
        data_binding_fingerprint=pack.fingerprint(),
        perturbation_binding_fingerprint=perturbation.fingerprint(),
        execution_binding_fingerprint=execution.fingerprint(),
        compatibility_fingerprint=compatibility.fingerprint(),
        output="delta_expression",
        value_semantics="condition_mean_X_minus_matched_split_control_mean_X",
        reference="matched_split_control_mean_X",
        output_unit=None,
    )
    protocol = K562GoldenValidationProtocol(
        schema_version="vc.k562-golden-validation-protocol.v1",
        scope_fingerprint=scope.fingerprint(),
        data_binding_fingerprint=pack.fingerprint(),
        split_name="norman-condition-holdout-v1",
        source_train_role="train",
        source_test_role="validation",
        source_ood_role="test",
        train_noncontrol_conditions=137,
        validation_noncontrol_conditions=30,
        test_noncontrol_conditions=116,
        leakage_guard=("condition_id",),
        primary_metric="condition_macro_full_feature_delta_mse",
        metric_direction="lower_is_better",
        truth_semantics="condition_mean_X_minus_matched_split_control_mean_X",
        primary_comparator="condition_level_additive_ridge",
        historical_additive_result_sha256=_ADDITIVE_RESULT_SHA256,
        historical_additive_test_mse=0.0032570634320908554,
        historical_no_change_result_sha256=_NO_CHANGE_RESULT_SHA256,
        historical_global_mean_result_sha256=_GLOBAL_MEAN_RESULT_SHA256,
        historical_evaluation_result_sha256=_EVALUATION_SHA256,
        same_runtime_required=True,
        historical_comparator_role="checked_in_historical_reference_only",
        contamination_audit_required=True,
        paired_comparison=True,
        paired_difference="candidate_mse_minus_additive_ridge_mse",
        bootstrap_unit="held_out_perturbation_condition",
        bootstrap_method="paired_percentile",
        bootstrap_rng="numpy.PCG64",
        bootstrap_seed=0,
        bootstrap_replicates=2000,
        bootstrap_interval=(0.025, 0.975),
        candidate_superiority_requirement="paired_difference_ci_upper_below_zero",
        stochastic_seeds=(11, 23, 37),
        validation_only_tuning=True,
        independent_k562_dataset_required=True,
        independent_platform_required=True,
        external_dataset_requirement="independent_semantically_compatible_k562_dataset_platform",
        non_k562_or_donor_external_as_ood_only=True,
        external_adaptation_steps=0,
        separate_scope_evaluation_required=True,
        record_role="preregistration_not_evidence",
        ood_axes=_OOD_AXES,
    )
    return (
        adapter,
        artifact,
        environment,
        release,
        pack,
        perturbation,
        execution,
        compatibility,
        scope,
        protocol,
    )


def _synthetic_delta():
    return [((index % 19) - 9) / 8 for index in range(5045)]


def _raw(scope, *, values=None, status="success", ood=False, abstain=False):
    if values is None:
        values = _synthetic_delta()
    return {
        "prediction": (
            None
            if abstain
            else {
                "delta_expression": values,
                "feature_ids_sha256": scope.feature_ids_sha256,
                "feature_records_sha256": scope.feature_records_sha256,
                "n_features": scope.feature_count,
                "value_semantics": scope.value_semantics,
                "reference": scope.reference,
                "condition_id": "AHR+ctrl" if scope.evaluation_scope == "single_gene" else "AHR+FEV",
                "evaluation_scope": scope.evaluation_scope,
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
            "dimensions": ["perturbation"] if ood else [],
            "reason": "perturbation outside exact scope" if ood else None,
        },
        "abstain": abstain,
        "abstain_reasons": ["exact scope rejected"] if abstain else [],
    }


def _prepare_kwargs(bindings):
    _, artifact, environment, release, pack, perturbation, execution, compatibility, scope, protocol = bindings
    return {
        "scope": scope,
        "model_artifact": artifact,
        "environment": environment,
        "model_release": release,
        "perturbation_binding": perturbation,
        "execution_binding": execution,
        "validation_protocol": protocol,
        "pack": pack,
        "compatibility_report": compatibility,
    }


def _request(scope, protocol, perturbation, **changes):
    raw = {
        "schema_version": "vc.request.v2",
        "request_id": f"p16e-{scope.evaluation_scope}-test-only",
        "species": {
            "schema_version": "vc.species-ref.v1",
            "taxonomy_id": "NCBITaxon:9606",
            "scientific_name": "Homo sapiens",
            "common_name": "human",
        },
        "cell_context": {
            "schema_version": "vc.cell-context.v1",
            "cell_type_name": "K562",
            "cell_type_id": None,
            "tissue_name": None,
            "tissue_id": None,
            "attributes": {
                "cell_identity_id": "CVCL_0004",
                "assembly_name": "GRCh38",
                "assembly_accession": "GCA_000001405.15",
                "assay_id": "EFO:0008913",
                "feature_namespace_version": "Ensembl 84",
                "feature_ids_sha256": _FEATURE_IDS_SHA256,
                "evaluation_scope": scope.evaluation_scope,
            },
        },
        "input_modality": {
            "schema_version": "vc.modality.v1",
            "name": "scRNA",
            "ontology_id": "EFO:0008913",
            "unit": None,
            "feature_namespace": "EnsemblGene",
        },
        "output_modality": {
            "schema_version": "vc.modality.v1",
            "name": "delta_expression",
            "ontology_id": "PRAXISOUTPUT:delta_expression",
            "unit": None,
            "feature_namespace": "EnsemblGene",
        },
        "perturbation": {
            "schema_version": "vc.perturbation.v1",
            "kind": perturbation.perturbation_kind,
            "targets": list(perturbation.ordered_target_ids),
            "dose_value": 1.0,
            "dose_unit": "1",
            "timepoint": "5d",
        },
        "task": {
            "schema_version": "vc.task.v1",
            "task_type": "predict_delta_expression",
            "requested_outputs": ["delta_expression"],
        },
        "baseline_context": {
            "reference": "matched_split_control_mean_X",
            "source_control_condition": "ctrl",
            "matched_control_sha256": _MATCHED_CONTROL_SHA256,
            "control_assignment_sha256": _CONTROL_ASSIGNMENT_SHA256,
            "scope_fingerprint": scope.fingerprint(),
        },
        "metadata": {},
        "constraints": {
            "condition_id": perturbation.condition_id,
            "value_semantics": scope.value_semantics,
            "perturbation_binding_fingerprint": perturbation.fingerprint(),
            "validation_protocol_fingerprint": protocol.fingerprint(),
            "record_membership_verified": False,
        },
    }
    for path, value in changes.items():
        cursor = raw
        parts = path.split("__")
        for part in parts[:-1]:
            cursor = cursor[part]
        cursor[parts[-1]] = value
    return VirtualCellRequestV2.from_dict(raw)


def _prepared(evaluation_scope: str = "single_gene"):
    bindings = _bindings(evaluation_scope)
    adapter, *_, perturbation, _, _, scope, protocol = bindings
    prepared = adapter.prepare_input(
        _request(scope, protocol, perturbation),
        **_prepare_kwargs(bindings),
    )
    return adapter, prepared, scope, perturbation, bindings


def test_contracts_are_strict_frozen_versioned_and_fingerprint_bound():
    adapter, *_, scope, protocol = _bindings()
    assert isinstance(adapter.input_contract, K562GoldenAdapterInputContract)
    assert isinstance(adapter.output_contract, K562GoldenAdapterOutputContract)
    assert adapter.identity().task == "predict_delta_expression"
    assert adapter.identity().outputs == ("delta_expression",)
    assert adapter.output_contract.shape == (5045,)
    assert adapter.output_contract.unit is None
    assert adapter.input_contract.fingerprint() == adapter.identity().input_contract_fingerprint
    assert adapter.output_contract.fingerprint() == adapter.identity().output_contract_fingerprint
    assert all(len(value) == 64 for value in (adapter.fingerprint(), scope.fingerprint(), protocol.fingerprint()))
    assert deepcopy(scope).fingerprint() == scope.fingerprint()
    assert scope.model_copy(update={"evaluation_scope": "combination"}).fingerprint() != scope.fingerprint()
    with pytest.raises(ValidationError, match="extra"):
        K562GoldenPerturbationScope.model_validate({**scope.to_dict(), "scientifically_validated": True})
    with pytest.raises(ValidationError, match="frozen"):
        scope.cell_identity_name = "A549"


def test_exact_native_bindings_freeze_k562_golden_identity_without_evidence_or_policy():
    (
        adapter,
        artifact,
        environment,
        release,
        pack,
        perturbation,
        execution,
        compatibility,
        scope,
        _,
    ) = _bindings()
    assert (
        scope.taxonomy_id,
        scope.scientific_name,
        scope.cell_identity_name,
        scope.cell_identity_id,
        scope.assembly_name,
        scope.assembly_accession,
        scope.assay_name,
        scope.assay_id,
    ) == (
        "NCBITaxon:9606",
        "Homo sapiens",
        "K562",
        "CVCL_0004",
        "GRCh38",
        "GCA_000001405.15",
        "scRNA",
        "EFO:0008913",
    )
    assert (
        scope.feature_namespace,
        scope.feature_namespace_version,
        scope.feature_id_format,
        scope.feature_count,
    ) == ("EnsemblGene", "Ensembl 84", "ensembl_gene", 5045)
    assert (scope.perturbation_action, scope.dose_value, scope.dose_unit) == (
        "CRISPR activation",
        1.0,
        "1",
    )
    assert (scope.time_value, scope.time_unit, scope.request_timepoint) == (5.0, "d", "5d")
    assert scope.value_semantics == "condition_mean_X_minus_matched_split_control_mean_X"
    assert scope.reference == "matched_split_control_mean_X"
    assert scope.output == "delta_expression" and scope.output_unit is None
    assert (
        pack.contract_yaml_size_bytes,
        pack.pack_manifest_size_bytes,
        pack.artifact_manifest_size_bytes,
    ) == (4749, 30074, 3864)
    assert (pack.h5ad_path, pack.h5ad_media_type) == (
        "norman_k562_golden.h5ad",
        "application/vnd.anndata+hdf5",
    )
    assert (pack.golden_contract_path, pack.golden_contract_media_type) == (
        "golden_contract.json",
        "application/json",
    )

    assert artifact.safe_load_policy == "data_only" and artifact.media_type == "application/json"
    assert release.migration_status == "native"
    assert release.artifact_fingerprints == (artifact.fingerprint(),)
    assert release.environment_fingerprint == environment.fingerprint()
    assert release.adapter_fingerprints == (adapter.fingerprint(),)
    assert release.pack_fingerprints == (pack.pack_fingerprint,)
    assert release.evidence_fingerprints == () and release.policy_fingerprint is None
    assert execution.preserve_feature_order
    assert not any(
        (
            execution.absolute_to_delta_conversion_allowed,
            execution.normalization_allowed,
            execution.reordering_allowed,
            execution.fill_allowed,
            execution.imputation_allowed,
            execution.deduplication_allowed,
        )
    )
    assert not perturbation.record_membership_verified
    assert perturbation.reason == "p16r_not_authorized"
    assert not compatibility.assets_verified and not compatibility.executable
    assert compatibility.reason == "p16r_not_authorized"
    assert {
        "condition_id",
        "condition_record_fingerprint",
        "ordered_target_ids",
        "record_membership_verified",
    }.isdisjoint(pack.to_dict())
    with pytest.raises(ValidationError, match="record_membership_verified"):
        K562GoldenPerturbationBinding.model_validate({**perturbation.to_dict(), "record_membership_verified": True})
    with pytest.raises(ValidationError, match="executable"):
        K562GoldenCompatibilityBinding.model_validate({**compatibility.to_dict(), "executable": True})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pack_id", "other-pack"),
        ("pack_version", "1.0.1"),
        ("pack_fingerprint", "f" * 64),
        ("canonical_contract_fingerprint", "f" * 64),
        ("contract_yaml_sha256", "f" * 64),
        ("contract_yaml_size_bytes", 4748),
        ("pack_manifest_sha256", "f" * 64),
        ("pack_manifest_size_bytes", 30073),
        ("artifact_manifest_sha256", "f" * 64),
        ("artifact_manifest_size_bytes", 3863),
        ("h5ad_path", "other.h5ad"),
        ("h5ad_media_type", "application/octet-stream"),
        ("h5ad_sha256", "f" * 64),
        ("h5ad_size_bytes", 2285816805),
        ("golden_contract_path", "other.json"),
        ("golden_contract_media_type", "application/octet-stream"),
        ("golden_contract_sha256", "f" * 64),
        ("golden_contract_size_bytes", 4662),
        ("matrix_shape", (91205, 5044)),
        ("license_id", "unknown"),
        ("taxonomy_id", "NCBITaxon:10090"),
        ("scientific_name", "Mus musculus"),
        ("cell_identity_id", "CVCL_0023"),
        ("assembly_accession", "GCA_000001405.29"),
        ("modality_id", "EFO:0000001"),
        ("feature_namespace", "HGNC"),
        ("feature_namespace_version", "Ensembl 85"),
        ("feature_id_format", "symbol"),
        ("source_cell_type_value", "K562"),
        ("source_cell_type_interpretation", "canonical_cell_identity"),
        ("feature_ids_sha256", "f" * 64),
        ("feature_records_sha256", "f" * 64),
        ("split_sha256", "f" * 64),
        ("condition_ids_sha256", "f" * 64),
        ("matched_control_sha256", "f" * 64),
        ("perturbation_ids_sha256", "f" * 64),
        ("condition_values_sha256", "f" * 64),
        ("perturbation_records_sha256", "f" * 64),
        ("target_ids_sha256", "f" * 64),
        ("control_assignment_sha256", "f" * 64),
        ("unseen_train_target_ids_sha256", "f" * 64),
        ("source_control_condition", "control"),
        ("train_control_condition_id", "norman.control.validation"),
        ("validation_control_condition_id", "norman.control.test"),
        ("test_control_condition_id", "norman.control.train"),
        ("train_control_guide", "NegCtrl11_NegCtrl0__NegCtrl11_NegCtrl0"),
        ("validation_control_guide", "NegCtrl0_NegCtrl0__NegCtrl0_NegCtrl0"),
        ("test_control_guide", "NegCtrl10_NegCtrl0__NegCtrl10_NegCtrl0"),
    ],
)
def test_data_binding_rejects_every_checked_in_identity_drift(field, value):
    pack = _bindings()[4]
    with pytest.raises(ValidationError):
        K562GoldenDataBinding.model_validate({**pack.to_dict(), field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("execution_mode", "absolute_expression"),
        ("feature_count", 5044),
        ("feature_ids_sha256", "f" * 64),
        ("feature_records_sha256", "f" * 64),
        ("value_semantics", "absolute_expression"),
        ("reference", "global_control_mean_X"),
        ("output_unit", "log2_fold_change"),
        ("preserve_feature_order", False),
        ("absolute_to_delta_conversion_allowed", True),
        ("normalization_allowed", True),
        ("reordering_allowed", True),
        ("fill_allowed", True),
        ("imputation_allowed", True),
        ("deduplication_allowed", True),
    ],
)
def test_execution_binding_rejects_feature_semantics_and_transform_drift(field, value):
    execution = _bindings()[6]
    with pytest.raises(ValidationError):
        K562GoldenExecutionBinding.model_validate({**execution.to_dict(), field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("taxonomy_id", "NCBITaxon:10090"),
        ("cell_identity_name", "A549"),
        ("cell_identity_id", "CVCL_0023"),
        ("assembly_name", "GRCh37"),
        ("assembly_accession", "GCA_000001405.29"),
        ("assay_name", "bulk_RNA"),
        ("assay_id", "EFO:0000001"),
        ("feature_namespace", "HGNC"),
        ("feature_namespace_version", "Ensembl 85"),
        ("feature_id_format", "symbol"),
        ("feature_count", 5044),
        ("perturbation_action", "CRISPR interference"),
        ("dose_value", 0.0),
        ("dose_unit", "dimensionless"),
        ("time_value", 4.0),
        ("time_unit", "h"),
        ("request_timepoint", "120h"),
        ("value_semantics", "absolute_expression"),
        ("reference", "global_control_mean_X"),
        ("output_unit", "log2_fold_change"),
    ],
)
def test_scope_rejects_biology_assay_namespace_dose_time_and_semantics_drift(field, value):
    *_, scope, _ = _bindings()
    with pytest.raises(ValidationError, match=field):
        K562GoldenPerturbationScope.model_validate({**scope.to_dict(), field: value})


def test_single_and_combination_scopes_and_membership_evidence_are_not_pooled():
    single = _bindings("single_gene")
    combination = _bindings("combination")
    single_binding, single_scope, single_protocol = single[5], single[8], single[9]
    combination_binding, combination_scope, combination_protocol = (
        combination[5],
        combination[8],
        combination[9],
    )
    assert (
        single_binding.evaluation_scope,
        single_binding.condition_id,
        single_binding.perturbation_kind,
        single_binding.ordered_target_ids,
        single_binding.condition_record_fingerprint,
    ) == (
        "single_gene",
        "AHR+ctrl",
        "gene",
        _SINGLE_TARGETS,
        _SINGLE_RECORD_SHA256,
    )
    assert (
        combination_binding.evaluation_scope,
        combination_binding.condition_id,
        combination_binding.perturbation_kind,
        combination_binding.ordered_target_ids,
        combination_binding.condition_record_fingerprint,
    ) == (
        "combination",
        "AHR+FEV",
        "gene_combination",
        _COMBINATION_TARGETS,
        _COMBINATION_RECORD_SHA256,
    )
    assert single_binding.fingerprint() != combination_binding.fingerprint()
    assert single_scope.fingerprint() != combination_scope.fingerprint()
    assert single_protocol.fingerprint() != combination_protocol.fingerprint()
    for raw in (
        {
            **single_binding.to_dict(),
            "condition_id": "ARID1A+ctrl",
            "condition_record_fingerprint": "f" * 64,
        },
        {**single_binding.to_dict(), "evaluation_scope": "combination"},
        {**single_binding.to_dict(), "perturbation_kind": "gene_combination"},
        {**single_binding.to_dict(), "ordered_target_ids": list(_COMBINATION_TARGETS)},
        {**combination_binding.to_dict(), "ordered_target_ids": list(reversed(_COMBINATION_TARGETS))},
    ):
        with pytest.raises(ValidationError):
            K562GoldenPerturbationBinding.model_validate(raw)


@pytest.mark.parametrize(
    ("evaluation_scope", "condition_id", "ordered_target_ids"),
    [
        ("single_gene", "BCL2L11+ctrl", ("ENSG00000153094",)),
        (
            "combination",
            "BCL2L11+CEBPA",
            ("ENSG00000153094", "ENSG00000245848"),
        ),
    ],
)
def test_perturbation_binding_is_generic_and_does_not_hardcode_ahr_fixtures(
    evaluation_scope,
    condition_id,
    ordered_target_ids,
):
    binding = _bindings(evaluation_scope)[5]
    record = {
        "id": condition_id,
        "kind": "genetic",
        "targets": list(ordered_target_ids),
    }
    candidate = K562GoldenPerturbationBinding.model_validate(
        {
            **binding.to_dict(),
            "condition_id": condition_id,
            "condition_record_fingerprint": _canonical_sha256(record),
            "ordered_target_ids": ordered_target_ids,
        }
    )
    assert candidate.condition_id == condition_id
    assert candidate.ordered_target_ids == ordered_target_ids
    assert not candidate.record_membership_verified


def test_protocol_freezes_split_metric_baseline_ci_external_gate_and_scope_separation():
    *_, scope, protocol = _bindings()
    assert (
        protocol.split_name,
        protocol.source_train_role,
        protocol.source_test_role,
        protocol.source_ood_role,
    ) == ("norman-condition-holdout-v1", "train", "validation", "test")
    assert (
        protocol.train_noncontrol_conditions,
        protocol.validation_noncontrol_conditions,
        protocol.test_noncontrol_conditions,
        protocol.leakage_guard,
    ) == (137, 30, 116, ("condition_id",))
    assert protocol.primary_metric == "condition_macro_full_feature_delta_mse"
    assert protocol.truth_semantics == scope.value_semantics
    assert protocol.metric_direction == "lower_is_better"
    assert protocol.primary_comparator == "condition_level_additive_ridge"
    assert protocol.historical_additive_test_mse == 0.0032570634320908554
    assert protocol.historical_additive_result_sha256 == _ADDITIVE_RESULT_SHA256
    assert protocol.historical_no_change_result_sha256 == _NO_CHANGE_RESULT_SHA256
    assert protocol.historical_global_mean_result_sha256 == _GLOBAL_MEAN_RESULT_SHA256
    assert protocol.historical_evaluation_result_sha256 == _EVALUATION_SHA256
    assert protocol.historical_comparator_role == "checked_in_historical_reference_only"
    assert protocol.same_runtime_required
    assert protocol.contamination_audit_required
    assert protocol.paired_comparison
    assert protocol.paired_difference == "candidate_mse_minus_additive_ridge_mse"
    assert (
        protocol.bootstrap_unit,
        protocol.bootstrap_method,
        protocol.bootstrap_rng,
        protocol.bootstrap_seed,
        protocol.bootstrap_replicates,
        protocol.bootstrap_interval,
    ) == (
        "held_out_perturbation_condition",
        "paired_percentile",
        "numpy.PCG64",
        0,
        2000,
        (0.025, 0.975),
    )
    assert protocol.candidate_superiority_requirement == "paired_difference_ci_upper_below_zero"
    assert protocol.stochastic_seeds == (11, 23, 37)
    assert protocol.validation_only_tuning
    assert protocol.independent_k562_dataset_required
    assert protocol.independent_platform_required
    assert protocol.external_dataset_requirement == "independent_semantically_compatible_k562_dataset_platform"
    assert protocol.non_k562_or_donor_external_as_ood_only
    assert protocol.external_adaptation_steps == 0
    assert protocol.separate_scope_evaluation_required
    assert protocol.record_role == "preregistration_not_evidence"
    assert protocol.ood_axes == _OOD_AXES
    assert not {
        "benchmark_passed",
        "scientifically_validated",
        "promotion_eligible",
        "production_promoted",
    }.intersection(protocol.to_dict())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_test_role", "test"),
        ("source_ood_role", "validation"),
        ("train_noncontrol_conditions", 136),
        ("validation_noncontrol_conditions", 31),
        ("test_noncontrol_conditions", 115),
        ("leakage_guard", ("target_id",)),
        ("primary_metric", "pooled_cell_mse"),
        ("truth_semantics", "absolute_expression"),
        ("primary_comparator", "no_change"),
        ("historical_additive_test_mse", 0.003),
        ("historical_additive_result_sha256", "f" * 64),
        ("historical_comparator_role", "candidate_evidence"),
        ("same_runtime_required", False),
        ("contamination_audit_required", False),
        ("paired_comparison", False),
        ("paired_difference", "additive_ridge_mse_minus_candidate_mse"),
        ("bootstrap_rng", "numpy.MT19937"),
        ("bootstrap_seed", 1),
        ("bootstrap_replicates", 1999),
        ("bootstrap_interval", (0.05, 0.95)),
        ("candidate_superiority_requirement", "point_estimate_below_baseline"),
        ("validation_only_tuning", False),
        ("independent_k562_dataset_required", False),
        ("independent_platform_required", False),
        ("external_dataset_requirement", "any_human_dataset"),
        ("non_k562_or_donor_external_as_ood_only", False),
        ("external_adaptation_steps", 1),
        ("separate_scope_evaluation_required", False),
        ("record_role", "scientific_evidence"),
        ("ood_axes", tuple(reversed(_OOD_AXES))),
    ],
)
def test_protocol_rejects_split_metric_ci_adaptation_and_ood_drift(field, value):
    *_, protocol = _bindings()
    with pytest.raises(ValidationError, match=field):
        K562GoldenValidationProtocol.model_validate({**protocol.model_dump(mode="python"), field: value})


@pytest.mark.parametrize(
    "seeds",
    [(11, 23), (11, 23, 23), (True, 23, 37), (-1, 23, 37), (2**53, 23, 37), ("11", 23, 37)],
)
def test_protocol_requires_three_unique_nonnegative_json_safe_integer_seeds(seeds):
    *_, protocol = _bindings()
    with pytest.raises(ValidationError, match="stochastic_seeds"):
        K562GoldenValidationProtocol.model_validate({**protocol.model_dump(mode="python"), "stochastic_seeds": seeds})


@pytest.mark.parametrize("evaluation_scope", ["single_gene", "combination"])
def test_prepare_input_binds_every_native_identity_without_values_or_asset_io(
    evaluation_scope,
    monkeypatch,
):
    bindings = _bindings(evaluation_scope)
    adapter, *_, perturbation, execution, _, scope, protocol = bindings

    def forbid_open(*_args, **_kwargs):
        raise AssertionError("contract adapter attempted asset I/O")

    monkeypatch.setattr("builtins.open", forbid_open)
    prepared = adapter.prepare_input(
        _request(scope, protocol, perturbation),
        **_prepare_kwargs(bindings),
    )
    model_input = K562GoldenPreparedModelInput.model_validate(prepared.model_input)
    assert model_input.scope == scope
    assert model_input.evaluation_scope == evaluation_scope
    assert model_input.ordered_target_ids == perturbation.ordered_target_ids
    assert model_input.perturbation_binding == perturbation
    assert model_input.execution_binding_fingerprint == execution.fingerprint()
    assert model_input.scope_fingerprint == scope.fingerprint()
    assert model_input.adapter_fingerprint == adapter.fingerprint()
    assert prepared.pack_fingerprint == scope.pack_fingerprint
    assert prepared.compatibility_fingerprint == scope.compatibility_fingerprint
    assert prepared.values is None and prepared.shape is None and prepared.unit is None

    generic = DEFAULT_ADAPTER_REGISTRY.resolve(
        "predict_delta_expression",
        "delta_expression",
    )
    with pytest.raises(AdapterContractError, match="prepared input does not match"):
        generic.validate_prepared_input(prepared)


@pytest.mark.parametrize(
    ("change", "value"),
    [
        ("species__taxonomy_id", "NCBITaxon:10090"),
        ("species__scientific_name", "Mus musculus"),
        ("species__common_name", "person"),
        ("cell_context__cell_type_name", "A549"),
        ("cell_context__cell_type_id", "CL:0000123"),
        ("cell_context__attributes__cell_identity_id", None),
        ("cell_context__attributes__cell_identity_id", "CVCL_0023"),
        ("cell_context__attributes__source_cell_type_value", "A549"),
        ("cell_context__attributes__assembly_name", "GRCh37"),
        ("cell_context__attributes__assembly_accession", "GCA_000001405.29"),
        ("cell_context__attributes__assay_id", "EFO:0000001"),
        ("cell_context__attributes__feature_namespace_version", "Ensembl 85"),
        ("cell_context__attributes__feature_ids_sha256", "f" * 64),
        ("input_modality__name", "bulk_RNA"),
        ("input_modality__ontology_id", "EFO:0000001"),
        ("input_modality__feature_namespace", "HGNC"),
        ("output_modality__name", "expression"),
        ("output_modality__ontology_id", "PRAXISOUTPUT:expression"),
        ("output_modality__unit", "log2_fold_change"),
        ("output_modality__feature_namespace", "HGNC"),
        ("perturbation__dose_value", 0.0),
        ("perturbation__dose_unit", "dimensionless"),
        ("perturbation__timepoint", "4d"),
        ("task__task_type", "predict_expression"),
        ("task__requested_outputs", ["delta_expression", "expression"]),
        ("baseline_context__reference", "global_control_mean_X"),
        ("baseline_context__source_control_condition", "control"),
        ("baseline_context__matched_control_sha256", "f" * 64),
        ("baseline_context__control_assignment_sha256", "f" * 64),
        ("baseline_context__scope_fingerprint", "f" * 64),
        ("constraints__condition_id", "AHR+KLF1"),
        ("constraints__value_semantics", "absolute_expression"),
        ("constraints__perturbation_binding_fingerprint", "f" * 64),
        ("constraints__validation_protocol_fingerprint", "f" * 64),
        ("constraints__record_membership_verified", True),
        ("metadata", {"scientifically_validated": True}),
    ],
)
def test_prepare_input_rejects_request_scope_semantics_and_control_drift(change, value):
    bindings = _bindings()
    adapter, *_, perturbation, _, _, scope, protocol = bindings
    request = _request(scope, protocol, perturbation, **{change: value})
    with pytest.raises(AdapterContractError):
        adapter.prepare_input(request, **_prepare_kwargs(bindings))


@pytest.mark.parametrize(
    "target",
    [
        "AHR",
        "ensg00000106546",
        "ENSG00000106546.1",
        "ENSG:ENSG00000106546",
        "ENSG0000106546",
        "ENSG0000010654A",
    ],
)
def test_prepare_input_rejects_noncanonical_ensembl_targets(target):
    bindings = _bindings()
    adapter, *_, perturbation, _, _, scope, protocol = bindings
    with pytest.raises(AdapterContractError):
        adapter.prepare_input(
            _request(scope, protocol, perturbation, perturbation__targets=[target]),
            **_prepare_kwargs(bindings),
        )


@pytest.mark.parametrize("evaluation_scope", ["single_gene", "combination"])
def test_prepare_input_rejects_target_order_kind_count_duplicates_and_scope_pooling(evaluation_scope):
    bindings = _bindings(evaluation_scope)
    adapter, *_, perturbation, _, _, scope, protocol = bindings
    if evaluation_scope == "single_gene":
        changes = (
            {"perturbation__kind": "gene_combination"},
            {"perturbation__targets": list(_COMBINATION_TARGETS)},
            {"cell_context__attributes__evaluation_scope": "combination"},
        )
    else:
        changes = (
            {"perturbation__kind": "gene"},
            {"perturbation__targets": list(reversed(_COMBINATION_TARGETS))},
            {"perturbation__targets": [_COMBINATION_TARGETS[0]] * 2},
            {"perturbation__targets": [_COMBINATION_TARGETS[0]]},
            {"cell_context__attributes__evaluation_scope": "single_gene"},
        )
    for change in changes:
        with pytest.raises(AdapterContractError):
            adapter.prepare_input(
                _request(scope, protocol, perturbation, **change),
                **_prepare_kwargs(bindings),
            )


@pytest.mark.parametrize(
    "parameter",
    [
        "scope",
        "model_artifact",
        "environment",
        "model_release",
        "perturbation_binding",
        "execution_binding",
        "validation_protocol",
        "pack",
        "compatibility_report",
    ],
)
def test_prepare_input_rejects_missing_native_bindings(parameter):
    bindings = _bindings()
    adapter, *_, perturbation, _, _, scope, protocol = bindings
    kwargs = _prepare_kwargs(bindings)
    kwargs[parameter] = None
    with pytest.raises((AdapterContractError, TypeError)):
        adapter.prepare_input(_request(scope, protocol, perturbation), **kwargs)


@pytest.mark.parametrize(
    ("parameter", "field", "value"),
    [
        ("model_artifact", "size_bytes", 2),
        ("environment", "python_version", "other"),
        ("model_release", "model_version", "other"),
        ("perturbation_binding", "condition_record_fingerprint", "f" * 64),
        ("execution_binding", "inference_configuration_fingerprint", "f" * 64),
        ("validation_protocol", "bootstrap_seed", 1),
        ("pack", "artifact_manifest_sha256", "f" * 64),
        ("compatibility_report", "model_fingerprint", "f" * 64),
        ("scope", "model_fingerprint", "f" * 64),
    ],
)
def test_prepare_input_rejects_release_artifact_environment_and_contract_drift(
    parameter,
    field,
    value,
):
    bindings = _bindings()
    adapter, *_, perturbation, _, _, scope, protocol = bindings
    kwargs = _prepare_kwargs(bindings)
    kwargs[parameter] = kwargs[parameter].model_copy(update={field: value})
    with pytest.raises(AdapterContractError):
        adapter.prepare_input(_request(scope, protocol, perturbation), **kwargs)


def test_release_cannot_smuggle_evidence_policy_or_unsafe_artifact_loading():
    bindings = _bindings()
    adapter, artifact, *_, perturbation, _, _, scope, protocol = bindings
    kwargs = _prepare_kwargs(bindings)
    cases = (
        ("model_artifact", artifact.model_copy(update={"safe_load_policy": "restricted_deserializer"})),
        ("model_artifact", artifact.model_copy(update={"media_type": "application/octet-stream"})),
        (
            "model_release",
            kwargs["model_release"].model_copy(update={"evidence_fingerprints": ("f" * 64,)}),
        ),
        (
            "model_release",
            kwargs["model_release"].model_copy(update={"policy_fingerprint": "f" * 64}),
        ),
    )
    for parameter, value in cases:
        with pytest.raises(AdapterContractError):
            adapter.prepare_input(
                _request(scope, protocol, perturbation),
                **{**kwargs, parameter: value},
            )


def test_nested_hidden_fields_model_copy_and_subtypes_fail_closed():
    class PromotedSpeciesRef(SpeciesRef):
        production_promoted: bool = Field(exclude=True)

    bindings = _bindings()
    adapter, *_, perturbation, _, _, scope, protocol = bindings
    kwargs = _prepare_kwargs(bindings)
    request = _request(scope, protocol, perturbation)
    promoted_species = PromotedSpeciesRef(
        **request.species.model_dump(mode="python"),
        production_promoted=True,
    )
    cases = (
        (
            request.model_copy(update={"species": promoted_species}),
            kwargs,
        ),
        (
            request,
            {
                **kwargs,
                "pack": kwargs["pack"].model_copy(update={"scientifically_validated": True}),
            },
        ),
        (
            request,
            {
                **kwargs,
                "perturbation_binding": kwargs["perturbation_binding"].model_copy(
                    update={"record_membership_verified": True}
                ),
            },
        ),
        (
            request,
            {
                **kwargs,
                "compatibility_report": kwargs["compatibility_report"].model_copy(update={"production_promoted": True}),
            },
        ),
    )
    for candidate_request, candidate_kwargs in cases:
        with pytest.raises(AdapterContractError):
            adapter.prepare_input(candidate_request, **candidate_kwargs)


@pytest.mark.parametrize("evaluation_scope", ["single_gene", "combination"])
def test_synthetic_5045_vector_passes_through_without_transform_or_reordering(evaluation_scope):
    adapter, prepared, scope, _, _ = _prepared(evaluation_scope)
    values = _synthetic_delta()
    values[0] = -42.5
    values[-1] = 1000.25
    raw = _raw(scope, values=values)
    envelope = adapter.adapt_output(prepared, raw)
    assert envelope.values == tuple(values)
    assert envelope.shape == (5045,)
    assert envelope.unit is None
    assert envelope.projection_metadata == {
        "feature_ids_sha256": _FEATURE_IDS_SHA256,
        "feature_records_sha256": _FEATURE_RECORDS_SHA256,
        "n_features": 5045,
        "value_semantics": scope.value_semantics,
        "reference": scope.reference,
        "condition_id": "AHR+ctrl" if evaluation_scope == "single_gene" else "AHR+FEV",
        "evaluation_scope": evaluation_scope,
        "unit": None,
        "prediction_status": "success",
        "scope_fingerprint": scope.fingerprint(),
    }
    assert adapter.project_prepared_output(prepared, envelope) == {"delta_expression": values}
    second = adapter.adapt_output(prepared, deepcopy(raw))
    assert second.to_dict() == envelope.to_dict()
    assert second.fingerprint() == envelope.fingerprint()
    report = run_adapter_conformance(adapter, prepared, raw)
    assert report.adapter_fingerprint == adapter.fingerprint()
    assert report.deterministic is True


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("prediction", "delta_expression"), [0.0] * 5044),
        (("prediction", "delta_expression"), [0.0] * 5046),
        (("prediction", "delta_expression"), [[0.0] * 5045]),
        (("prediction", "feature_ids_sha256"), "f" * 64),
        (("prediction", "feature_records_sha256"), "f" * 64),
        (("prediction", "n_features"), 5044),
        (("prediction", "n_features"), 5045.0),
        (("prediction", "value_semantics"), "absolute_expression"),
        (("prediction", "reference"), "global_control_mean_X"),
        (("prediction", "condition_id"), "AHR+KLF1"),
        (("prediction", "evaluation_scope"), "combination"),
        (("prediction", "unit"), "log2_fold_change"),
        (("scope_fingerprint",), "f" * 64),
        (("prediction_status",), "invented-status"),
        (("uncertainty", "available"), True),
        (("uncertainty", "method"), "p16r_not_authorized"),
        (("uncertainty", "reason"), "p16r_not_authorized"),
    ],
)
def test_output_rejects_shape_feature_semantics_scope_status_and_uncertainty_drift(path, value):
    adapter, prepared, scope, _, _ = _prepared()
    raw = _raw(scope)
    cursor = raw
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, raw)


@pytest.mark.parametrize("value", [True, "0.1", float("nan"), float("inf"), 2**53])
def test_output_rejects_non_numeric_nonfinite_and_non_json_safe_vector_values(value):
    adapter, prepared, scope, _, _ = _prepared()
    values = _synthetic_delta()
    values[101] = value
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, _raw(scope, values=values))


@pytest.mark.parametrize(
    "reserved",
    [
        "absolute_expression",
        "normalized_delta",
        "evidence",
        "policy",
        "benchmark_passed",
        "scientifically_validated",
        "promotion_eligible",
        "production_promoted",
    ],
)
def test_output_rejects_reserved_science_policy_transform_and_unrequested_fields(reserved):
    adapter, prepared, scope, _, _ = _prepared()
    raw = _raw(scope)
    raw[reserved] = True
    with pytest.raises(AdapterContractError, match="wrapper output fields"):
        adapter.adapt_output(prepared, raw)


def test_output_requires_exact_prediction_and_wrapper_objects():
    class RawOutput(dict):
        pass

    adapter, prepared, scope, _, _ = _prepared()
    raw = _raw(scope)
    raw["prediction"]["extra"] = True
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, raw)
    raw = _raw(scope)
    raw["prediction"].pop("feature_records_sha256")
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, raw)
    raw = _raw(scope)
    raw.pop("prediction_status")
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, raw)
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, RawOutput(_raw(scope)))


@pytest.mark.parametrize("status", ["target_not_found", "unsupported_scope", "error"])
def test_non_success_status_requires_value_free_abstention(status):
    adapter, prepared, scope, _, _ = _prepared()
    if status == "unsupported_scope":
        with pytest.raises(AdapterContractError):
            adapter.adapt_output(prepared, _raw(scope, status=status, abstain=True))
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(
            prepared,
            _raw(scope, status=status, ood=status == "unsupported_scope"),
        )
    envelope = adapter.adapt_output(
        prepared,
        _raw(
            scope,
            status=status,
            ood=status == "unsupported_scope",
            abstain=True,
        ),
    )
    assert envelope.abstain
    assert envelope.values is None and envelope.shape is None
    assert envelope.projection_metadata == {}


def test_ood_requires_value_free_abstention_reason_and_canonical_axis_order():
    adapter, prepared, scope, _, _ = _prepared()
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, _raw(scope, ood=True))
    envelope = adapter.adapt_output(prepared, _raw(scope, ood=True, abstain=True))
    assert envelope.abstain and envelope.ood.detected
    raw = _raw(scope, ood=True, abstain=True)
    raw["abstain_reasons"] = []
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, raw)
    raw = _raw(scope)
    raw["ood"]["dimensions"] = ["invented_axis"]
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, raw)
    raw = _raw(scope, ood=True, abstain=True)
    raw["ood"]["dimensions"] = []
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, raw)
    raw = _raw(scope, ood=True, abstain=True)
    raw["ood"]["dimensions"] = ["perturbation", "iid"]
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, raw)
    raw = _raw(scope, status="success", abstain=True)
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(prepared, raw)


def test_prepared_scope_replay_metadata_provenance_and_hidden_envelope_fields_fail_closed():
    adapter, single, single_scope, _, _ = _prepared("single_gene")
    _, combination, _, _, _ = _prepared("combination")
    envelope = adapter.adapt_output(single, _raw(single_scope))
    with pytest.raises(AdapterContractError):
        adapter.validate_prepared_envelope(combination, envelope)

    forged = single.model_copy(
        update={
            "model_input": {
                **deepcopy(dict(single.model_input)),
                "request_fingerprint": "f" * 64,
            }
        }
    )
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(forged, _raw(single_scope))
    forged_protocol = json.loads(json.dumps(single.model_input))
    forged_protocol["validation_protocol"]["data_binding_fingerprint"] = "f" * 64
    forged_protocol["validation_protocol_fingerprint"] = _canonical_sha256(forged_protocol["validation_protocol"])
    with pytest.raises(AdapterContractError):
        adapter.adapt_output(
            single.model_copy(update={"model_input": forged_protocol}),
            _raw(single_scope),
        )
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
    with pytest.raises(AdapterContractError):
        adapter.validate_prepared_envelope(single, forged_uncertainty)
    for field, nested in (
        (
            "uncertainty",
            envelope.uncertainty.model_copy(update={"scientifically_validated": True}),
        ),
        ("ood", envelope.ood.model_copy(update={"promotion_eligible": True})),
        ("provenance", envelope.provenance.model_copy(update={"production_promoted": True})),
    ):
        with pytest.raises(AdapterContractError):
            adapter.validate_prepared_envelope(
                single,
                envelope.model_copy(update={field: nested}),
            )


def test_projection_is_prepared_only_exact_and_abstention_cannot_project():
    adapter, prepared, scope, _, _ = _prepared()
    envelope = adapter.adapt_output(prepared, _raw(scope))
    for operation in (
        lambda: adapter.validate_envelope(envelope),
        lambda: adapter.aggregate((envelope,)),
        lambda: adapter.project_output(envelope),
    ):
        with pytest.raises(AdapterContractError):
            operation()
    with pytest.raises(AdapterContractError):
        adapter.validate_projection(
            {
                "delta_expression": _synthetic_delta(),
                "absolute_expression": _synthetic_delta(),
            }
        )
    abstention = adapter.adapt_output(
        prepared,
        _raw(scope, status="target_not_found", abstain=True),
    )
    with pytest.raises(AdapterContractError):
        adapter.project_prepared_output(prepared, abstention)


def test_checked_in_small_manifests_freeze_exact_p8_identities_and_scope_records():
    assert (_GOLDEN / "contract.yaml").stat().st_size == 4749
    assert (_GOLDEN / "pack.manifest.yaml").stat().st_size == 30074
    assert (_GOLDEN / "artifact-manifest.json").stat().st_size == 3864
    assert _sha256(_GOLDEN / "contract.yaml") == _CONTRACT_SHA256
    assert _sha256(_GOLDEN / "pack.manifest.yaml") == _PACK_MANIFEST_SHA256
    assert _sha256(_GOLDEN / "artifact-manifest.json") == _ARTIFACT_MANIFEST_SHA256
    contract, pack, artifact = _checked_in_manifests()

    assert (contract["schema_version"], contract["benchmark_id"], contract["pack_version"]) == (
        "vc.golden-norman.v1",
        "norman-2019-k562-golden",
        "1.0.0",
    )
    assert artifact["contract"]["canonical_sha256"] == _CANONICAL_CONTRACT_SHA256
    assert artifact["pack"]["fingerprint"] == _PACK_FINGERPRINT
    assert _canonical_sha256(contract) == _CANONICAL_CONTRACT_SHA256
    assert _canonical_sha256(pack) == _PACK_FINGERPRINT
    assert pack["assets"] == [
        {
            "id": "expression",
            "path": "norman_k562_golden.h5ad",
            "media_type": "application/vnd.anndata+hdf5",
            "sha256": _H5AD_SHA256,
            "size_bytes": 2285816806,
        },
        {
            "id": "golden-contract",
            "path": "golden_contract.json",
            "media_type": "application/json",
            "sha256": _GOLDEN_CONTRACT_SHA256,
            "size_bytes": 4663,
        },
    ]
    assert contract["source"]["h5ad"]["feature_ids_sha256"] == _FEATURE_IDS_SHA256
    assert contract["source"]["h5ad"]["feature_records_sha256"] == _FEATURE_RECORDS_SHA256
    assert contract["biology"] == {
        "taxon": {
            "ontology_id": "NCBITaxon:9606",
            "scientific_name": "Homo sapiens",
        },
        "assembly": {"name": "GRCh38", "accession": "GCA_000001405.15"},
        "feature_namespace": {"name": "EnsemblGene", "version": "Ensembl 84"},
        "cell_identity_id": "CVCL_0004",
        "source_cell_type_value": "A549",
        "source_cell_type_interpretation": "upstream_metadata_error_preserved",
        "state_id": "VCSTATE:unspecified",
        "context_id": "VCCONTEXT:in_vitro",
        "dose": {"control": 0.0, "perturbation": 1.0, "unit": "1"},
        "time": {"value": 5.0, "unit": "d"},
        "perturbation_action": "CRISPR activation",
    }
    assert pack["modality"] == {"name": "scRNA", "ontology_id": "EFO:0008913"}
    assert pack["feature_namespace"] == {"name": "EnsemblGene", "version": "Ensembl 84"}
    assert pack["feature_semantics"]["id_format"] == "ensembl_gene"
    assert pack["matrix"]["shape"] == [91205, 5045]
    assert contract["expected"] == {
        **contract["expected"],
        "golden_split_by_observation_sha256": _SPLIT_SHA256,
        "condition_id_by_observation_sha256": _CONDITION_IDS_SHA256,
        "matched_control_by_observation_sha256": _MATCHED_CONTROL_SHA256,
        "perturbation_id_by_observation_sha256": _PERTURBATION_IDS_SHA256,
        "condition_values_sha256": _CONDITION_VALUES_SHA256,
        "perturbation_records_sha256": _PERTURBATION_RECORDS_SHA256,
        "target_ids_sha256": _TARGET_IDS_SHA256,
        "control_assignment_sha256": _CONTROL_ASSIGNMENT_SHA256,
        "unseen_train_target_ids_sha256": _UNSEEN_TARGETS_SHA256,
    }
    assert contract["split"]["source_mapping"] == {
        "train": "train",
        "test": "validation",
        "ood": "test",
    }
    assert contract["split"]["leakage_guard"] == ["condition_id"]
    assert contract["expected"]["noncontrol_conditions_by_split"] == {
        "train": 137,
        "validation": 30,
        "test": 116,
    }
    assert contract["metric"] == {
        "name": "condition_macro_full_feature_delta_mse",
        "direction": "lower_is_better",
        "features": "all_ordered_pack_features",
        "truth": "condition_mean_X_minus_matched_split_control_mean_X",
        "bootstrap": {
            "unit": "held_out_perturbation_condition",
            "method": "paired_percentile",
            "rng": "numpy.PCG64",
            "seed": 0,
            "replicates": 2000,
            "interval": [0.025, 0.975],
        },
    }
    assert contract["baselines"]["additive_linear"] == {
        "definition": "condition-level additive ridge",
        "model_name": "norman_additive_linear",
        "alpha": 1.0,
        "intercept": "unpenalized",
    }
    assert artifact["remote_files"]["model_cache/norman_additive_linear/baseline.json"] == {
        "sha256": _ADDITIVE_RESULT_SHA256,
        "size_bytes": 95682,
    }
    assert artifact["remote_files"]["evaluation/evaluation.json"] == {
        "sha256": _EVALUATION_SHA256,
        "size_bytes": 243236,
    }
    assert artifact["primary_test_scores"]["additive_linear"] == {
        "mse": 0.0032570634320908554,
        "ci95": [0.0027929521401756927, 0.0037390136902566485],
    }
    assert artifact["states"] == {
        "pack_valid": True,
        "model_compatible": True,
        "scientifically_validated": False,
    }

    records = {item["id"]: item for item in pack["perturbations"]["values"]}
    conditions = set(pack["conditions"]["values"])
    assert len(records) == 284
    assert len(conditions) == 286
    assert set(records).difference(conditions) == {"ctrl"}
    assert conditions.difference(records) == {
        "norman.control.train",
        "norman.control.validation",
        "norman.control.test",
    }
    assert contract["split"]["control_condition_ids"] == {
        "train": "norman.control.train",
        "validation": "norman.control.validation",
        "test": "norman.control.test",
    }
    assert contract["split"]["source_control_condition"] == "ctrl"
    assert contract["split"]["control_guides"] == {
        "train": "NegCtrl0_NegCtrl0__NegCtrl0_NegCtrl0",
        "validation": "NegCtrl10_NegCtrl0__NegCtrl10_NegCtrl0",
        "test": "NegCtrl11_NegCtrl0__NegCtrl11_NegCtrl0",
    }
    expected = {
        "AHR+ctrl": ("genetic", list(_SINGLE_TARGETS), _SINGLE_RECORD_SHA256),
        "AHR+FEV": ("genetic", list(_COMBINATION_TARGETS), _COMBINATION_RECORD_SHA256),
    }
    for condition, (kind, targets, fingerprint) in expected.items():
        record = records[condition]
        assert record == {"id": condition, "kind": kind, "targets": targets}
        assert _canonical_sha256(record) == fingerprint
    assert sum(len(item["targets"]) == 0 for item in records.values()) == 1
    assert sum(len(item["targets"]) == 1 for item in records.values()) == 152
    assert sum(len(item["targets"]) == 2 for item in records.values()) == 131


def test_contract_import_is_dependency_free_local_only_and_not_a_model_card_path():
    adapter = K562GoldenPerturbationAdapter()
    default = DEFAULT_ADAPTER_REGISTRY.resolve(
        "predict_delta_expression",
        "delta_expression",
    )
    assert DEFAULT_ADAPTER_REGISTRY.keys() == (("predict_delta_expression", "delta_expression"),)
    assert isinstance(default, DeltaExpressionReferenceAdapter)
    assert not isinstance(default, K562GoldenPerturbationAdapter)
    assert default.fingerprint() == _DEFAULT_ADAPTER_SHA256
    assert default.input_contract.fingerprint() == _DEFAULT_INPUT_CONTRACT_SHA256
    assert default.output_contract.fingerprint() == _DEFAULT_OUTPUT_CONTRACT_SHA256
    local = AdapterRegistry([adapter])
    assert local.resolve("predict_delta_expression", "delta_expression") is adapter

    source = inspect.getsource(k562_golden_delta_contract)
    for forbidden in (
        "import numpy",
        "from numpy",
        "import anndata",
        "import h5py",
        "import torch",
        "import cobra",
        "import gears",
        "import scgpt",
        "read_h5ad",
        "read_text",
        "read_bytes",
        "open(",
        "numpy.load",
        "np.load",
        "torch.load",
        "golden_baseline_wrapper",
        "GoldenBaselineWrapper",
        "ModelZooRegistry",
        "benchmarks.golden_norman",
        "benchmarks.norman_eval",
    ):
        assert forbidden not in source

    probe = (
        "import sys\n"
        "from praxis_virtualcell.model_zoo.adapter_sdk "
        "import DEFAULT_ADAPTER_REGISTRY\n"
        "from praxis_virtualcell.model_zoo.k562_golden_delta_contract "
        "import K562GoldenPerturbationAdapter\n"
        "default = DEFAULT_ADAPTER_REGISTRY.resolve("
        "'predict_delta_expression', 'delta_expression')\n"
        "assert type(default).__name__ == 'DeltaExpressionReferenceAdapter'\n"
        "assert not isinstance(default, K562GoldenPerturbationAdapter)\n"
        "forbidden = ('numpy', 'anndata', 'scanpy', 'h5py', "
        "'torch', 'cobra', 'gears', 'scgpt')\n"
        "blocked = sorted(name for name in forbidden if name in sys.modules)\n"
        "assert not blocked, blocked\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
