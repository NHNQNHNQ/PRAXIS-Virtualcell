"""P16R authorization-preflight identity tests; all inputs are synthetic."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from copy import deepcopy

import pytest
from pydantic import ConfigDict, ValidationError

from praxis_virtualcell.benchmarks import k562_p16r_preflight
from praxis_virtualcell.benchmarks.k562_p16r_preflight import (
    K562P16RAuthorizationPreflightV1,
    K562P16RExternalScopeDeclarationV1,
    P16RPreflightError,
    compile_k562_p16r_preflight,
)
from praxis_virtualcell.benchmarks.system import (
    BenchmarkProtocolV1,
    DatasetBindingV1,
    GroupIdentityV1,
)
from praxis_virtualcell.data_packs.manifest import PackManifest
from praxis_virtualcell.model_zoo.capability_registry import ModelCard
from praxis_virtualcell.model_zoo.registry_v2 import (
    ArtifactIdentity,
    ModelRegistryV2,
    ModelReleaseRecord,
    RegistryLifecycleEvent,
)
from praxis_virtualcell.tests.test_benchmark_system import _group_rows_raw, _protocol_raw
from praxis_virtualcell.tests.test_k562_golden_delta_contract import _bindings


def _fp(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _canonical(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _external_pack() -> PackManifest:
    return PackManifest.from_dict(
        {
            "schema_version": "vc.pack.v0.2",
            "pack_id": "synthetic-independent-k562-external",
            "pack_version": "1.0.0",
            "taxon": {"ontology_id": "NCBITaxon:9606", "scientific_name": "Homo sapiens"},
            "assembly": {"name": "GRCh38", "accession": "GCA_000001405.15"},
            "identity": {"observation_key": "observation_id", "feature_key": "var_names"},
            "modality": {"name": "scRNA", "ontology_id": "EFO:0008913"},
            "feature_namespace": {"name": "EnsemblGene", "version": "Ensembl 84"},
            "feature_semantics": {"id_source": "var_names", "id_format": "ensembl_gene"},
            "cell_semantics": {
                "identity": "cell_identity_id",
                "state": ["state_id"],
                "context": ["context_id"],
                "local_terms": [],
            },
            "conditions": {
                "field": "condition_id",
                "values": ["control", "perturbed"],
                "matched_control_field": "matched_control_id",
                "dose": {"value_field": "dose_value", "unit_field": "dose_unit"},
                "time": {"value_field": "time_value", "unit_field": "time_unit"},
            },
            "perturbations": {
                "field": "perturbation_id",
                "values": [
                    {"id": "control", "kind": "control", "targets": []},
                    {"id": "AHR", "kind": "genetic", "targets": ["ENSG00000106546"]},
                ],
            },
            "split": {
                "name": "predeclared-condition-holdout",
                "field": "partition",
                "strategy": "predefined",
                "values": ["train", "validation", "test", "external"],
                "leakage_guard": ["donor", "condition", "replicate", "batch"],
            },
            "provenance": {
                "source": "synthetic conformance-only declaration",
                "created_by": "pytest",
                "citation": "none",
            },
            "license": {"id": "CC0-1.0", "name": "CC0", "url": None},
            "assets": [
                {
                    "id": "external_expression",
                    "path": "external.h5ad",
                    "media_type": "application/vnd.anndata+hdf5",
                    "sha256": _fp("external-pack-asset"),
                    "size_bytes": 1,
                }
            ],
            "matrix": {"asset": "external_expression", "location": "X", "shape": [2, 2]},
        }
    )


def _external_scope(pack: PackManifest, dataset: DatasetBindingV1) -> K562P16RExternalScopeDeclarationV1:
    values = {
        "schema_version": "vc.k562-p16r-external-scope-declaration.v1",
        "pack_fingerprint": pack.fingerprint(),
        "dataset_fingerprint": dataset.dataset_fingerprint,
        "platform_fingerprint": dataset.platform_fingerprint,
        "scope_manifest_fingerprint": _fp("synthetic-external-scope-manifest"),
        "taxonomy_id": "NCBITaxon:9606",
        "scientific_name": "Homo sapiens",
        "cell_identity_name": "K562",
        "cell_identity_id": "CVCL_0004",
        "assembly_name": "GRCh38",
        "assembly_accession": "GCA_000001405.15",
        "modality_name": "scRNA",
        "modality_id": "EFO:0008913",
        "feature_namespace": "EnsemblGene",
        "feature_namespace_version": "Ensembl 84",
        "feature_id_format": "ensembl_gene",
        "feature_ids_sha256": _fp("synthetic-external-feature-ids"),
        "feature_records_sha256": _fp("synthetic-external-feature-records"),
        "feature_mapping_fingerprint": _fp("synthetic-external-feature-mapping"),
        "value_semantics": "condition_mean_X_minus_matched_split_control_mean_X",
        "reference": "matched_split_control_mean_X",
        "output_unit": None,
        "independent_from_golden": True,
        "adaptation_steps": 0,
        "record_role": "unverified_external_scope_declaration",
        "asset_bytes_verified": False,
        "record_membership_verified": False,
    }
    values["declaration_id"] = f"p16r_external_scope_{_canonical(values)[:24]}"
    return K562P16RExternalScopeDeclarationV1.model_validate(values)


def _card(*, scope: str, artifact: ArtifactIdentity) -> ModelCard:
    kind = "gene" if scope == "single_gene" else "gene_combination"
    return ModelCard.from_dict(
        {
            "schema_version": "vc.model-card.v1",
            "name": "k562_golden_delta_contract",
            "type": "public_model",
            "species": ["human"],
            "taxon": ["NCBITaxon:9606"],
            "module": "genetic_hub",
            "modality": [{"name": "scRNA", "ontology_id": "EFO:0008913"}],
            "assay": ["EFO:0008913"],
            "cell_domain": {
                "cell_type_ids": ["CVCL_0004"],
                "cell_type_names": ["K562"],
                "tissue_ids": [],
                "tissue_names": [],
                "allow_unspecified": False,
            },
            "perturbation": [kind],
            "task": "predict_delta_expression",
            "output": ["delta_expression"],
            "feature_namespace": [{"name": "EnsemblGene", "version": "Ensembl 84", "id_format": "ensembl_gene"}],
            "representation": ["asset:application/json"],
            "source": "synthetic conformance fixture",
            "license": "CC0-1.0",
            "status": "available",
            "wrapper": "tests.SyntheticK562Adapter",
            "version": "test-only",
            "requires": [],
            "assets": [
                {
                    "filename": "model.json",
                    "sha256": artifact.sha256,
                    "media_type": artifact.media_type,
                    "source_note": "synthetic identity only",
                }
            ],
            "resources": {"python_dependencies": [], "required": ["cpu"]},
            "uncertainty": {
                "required": True,
                "methods": ["synthetic_conformance_only"],
                "calibrated": False,
            },
            "ood": {
                "action": "abstain",
                "dimensions": [
                    "taxon",
                    "modality",
                    "assay",
                    "cell_domain",
                    "perturbation",
                    "task",
                    "output",
                    "feature_namespace",
                    "representation",
                ],
            },
            "reliability_policy": "synthetic fixture; no scientific claim",
            "provenance": {"synthetic_conformance_only": True},
        }
    )


def _bundle(scope_name: str = "single_gene"):
    (
        adapter,
        source_artifact,
        environment,
        source_release,
        golden,
        perturbation,
        execution,
        _source_compatibility,
        _source_scope,
        _source_preregistration,
    ) = _bindings(scope_name)
    provisional_card = _card(scope=scope_name, artifact=source_artifact)
    artifact = ArtifactIdentity.from_dict(
        {
            **source_artifact.to_dict(),
            "model_fingerprint": provisional_card.fingerprint(),
        }
    )
    card = _card(scope=scope_name, artifact=artifact)
    artifact = ArtifactIdentity.from_dict({**artifact.to_dict(), "model_fingerprint": card.fingerprint()})
    release = ModelReleaseRecord.from_dict(
        {
            **source_release.to_dict(),
            "model_fingerprint": card.fingerprint(),
            "artifact_fingerprints": [artifact.fingerprint()],
        }
    )
    from praxis_virtualcell.model_zoo.k562_golden_delta_contract import (
        K562GoldenCompatibilityBinding,
        K562GoldenPerturbationScope,
        K562GoldenValidationProtocol,
    )

    compatibility = K562GoldenCompatibilityBinding.model_validate(
        {
            **_source_compatibility.to_dict(),
            "model_release_fingerprint": release.fingerprint(),
            "model_fingerprint": card.fingerprint(),
            "artifact_fingerprint": artifact.fingerprint(),
            "environment_fingerprint": environment.fingerprint(),
            "adapter_fingerprint": adapter.fingerprint(),
            "pack_fingerprint": golden.pack_fingerprint,
            "data_binding_fingerprint": golden.fingerprint(),
            "perturbation_binding_fingerprint": perturbation.fingerprint(),
            "execution_binding_fingerprint": execution.fingerprint(),
        }
    )
    scope = K562GoldenPerturbationScope.model_validate(
        {
            **_source_scope.to_dict(),
            "model_fingerprint": card.fingerprint(),
            "model_release_fingerprint": release.fingerprint(),
            "model_artifact_fingerprint": artifact.fingerprint(),
            "environment_fingerprint": environment.fingerprint(),
            "adapter_fingerprint": adapter.fingerprint(),
            "pack_fingerprint": golden.pack_fingerprint,
            "data_binding_fingerprint": golden.fingerprint(),
            "perturbation_binding_fingerprint": perturbation.fingerprint(),
            "execution_binding_fingerprint": execution.fingerprint(),
            "compatibility_fingerprint": compatibility.fingerprint(),
        }
    )
    preregistration = K562GoldenValidationProtocol.model_validate(
        {
            **_source_preregistration.to_dict(),
            "scope_fingerprint": scope.fingerprint(),
            "data_binding_fingerprint": golden.fingerprint(),
        }
    )
    registry = ModelRegistryV2.from_dict(
        {
            "schema_version": "vc.model-registry.v2",
            "artifacts": [artifact.to_dict()],
            "environments": [environment.to_dict()],
            "adapters": [adapter.identity().to_dict()],
            "evidence_records": [],
            "policy_records": [],
            "releases": [release.to_dict()],
            "lifecycle_events": [],
        }
    )
    external_pack = _external_pack()
    external_dataset = DatasetBindingV1(
        schema_version="vc.benchmark-dataset-binding.v1",
        dataset_fingerprint=_fp(f"{scope_name}:external-dataset"),
        platform_fingerprint=_fp(f"{scope_name}:external-platform"),
    )
    external_scope = _external_scope(external_pack, external_dataset)
    groups = tuple(GroupIdentityV1.model_validate(row) for row in _group_rows_raw())
    raw_protocol = deepcopy(_protocol_raw())
    benchmark_scope = {
        "schema_version": "vc.benchmark-scope.v1",
        "organism": "Homo sapiens",
        "cell_type": "K562",
        "intervention": f"CRISPR activation:{scope_name}",
        "endpoint": preregistration.primary_metric,
    }
    raw_protocol.update(
        {
            "protocol_id": f"p16r-{scope_name}-synthetic-preflight",
            "task": "predict_delta_expression",
            "scope": benchmark_scope,
            "pack_fingerprint": golden.pack_fingerprint,
            "dataset": {
                "schema_version": "vc.benchmark-dataset-binding.v1",
                "dataset_fingerprint": golden.h5ad_sha256,
                "platform_fingerprint": golden.artifact_manifest_sha256,
            },
            "feature_contract_fingerprint": adapter.input_contract.fingerprint(),
            "output_contract_fingerprint": adapter.output_contract.fingerprint(),
            "baseline": {
                "schema_version": "vc.benchmark-baseline.v1",
                "baseline_id": preregistration.primary_comparator,
                "baseline_fingerprint": _fp(f"{scope_name}:additive-ridge"),
                "kind": "declared_simple",
                "fit_partition": "train",
                "simple": True,
            },
            "primary_metric": {
                "schema_version": "vc.benchmark-metric.v1",
                "name": preregistration.primary_metric,
                "direction": preregistration.metric_direction,
                "aggregation": "biological_group_macro",
                "difference": "candidate_minus_baseline",
            },
            "confidence_interval": {
                "schema_version": "vc.benchmark-ci-policy.v1",
                "method": "paired_group_percentile",
                "rng": preregistration.bootstrap_rng,
                "quantile_method": "linear",
                "group_unit": preregistration.bootstrap_unit,
                "confidence_level": 0.95,
                "replicates": preregistration.bootstrap_replicates,
                "seed": preregistration.bootstrap_seed,
            },
            "seeds": list(preregistration.stochastic_seeds),
            "ood_policy": [
                {
                    "schema_version": "vc.benchmark-ood-gate.v1",
                    "axis": axis,
                    "metric_name": "synthetic_preflight_metric",
                    "direction": "lower_is_better",
                    "threshold": 1.0,
                }
                for axis in preregistration.ood_axes
            ],
            "external_policy": {
                "schema_version": "vc.benchmark-external-policy.v1",
                "required": True,
                "dataset_fingerprint": external_dataset.dataset_fingerprint,
                "platform_fingerprint": external_dataset.platform_fingerprint,
                "scope_fingerprint": _canonical(benchmark_scope),
                "independent_dataset": True,
                "independent_platform": True,
                "adaptation_steps": 0,
            },
        }
    )
    raw_protocol["split"]["group_unit"] = preregistration.bootstrap_unit
    raw_protocol["split"]["leakage_records_fingerprint"] = _canonical([item.to_dict() for item in groups])
    protocol = BenchmarkProtocolV1.from_dict(raw_protocol)
    return {
        "evaluation_scope": scope_name,
        "golden_data": golden,
        "p16_scope": scope,
        "p16_perturbation": perturbation,
        "p16_compatibility": compatibility,
        "execution": execution,
        "p16_preregistration": preregistration,
        "candidate_card": card,
        "candidate_registry": registry,
        "candidate_release_fingerprint": release.fingerprint(),
        "candidate_provenance_manifest_fingerprint": _fp(f"{scope_name}:provenance"),
        "external_pack": external_pack,
        "external_dataset": external_dataset,
        "external_scope": external_scope,
        "group_records": groups,
        "protocol": protocol,
    }


def _compile(bundle):
    return compile_k562_p16r_preflight(**bundle)


def _rebind_artifact_policy(bundle, policy: str) -> None:
    artifact = ArtifactIdentity.from_dict(
        {**bundle["candidate_registry"].artifacts[0].to_dict(), "safe_load_policy": policy}
    )
    release = ModelReleaseRecord.from_dict(
        {
            **bundle["candidate_registry"].releases[0].to_dict(),
            "artifact_fingerprints": [artifact.fingerprint()],
        }
    )
    compatibility = bundle["p16_compatibility"].model_validate(
        {
            **bundle["p16_compatibility"].to_dict(),
            "model_release_fingerprint": release.fingerprint(),
            "artifact_fingerprint": artifact.fingerprint(),
        }
    )
    scope = bundle["p16_scope"].model_validate(
        {
            **bundle["p16_scope"].to_dict(),
            "model_release_fingerprint": release.fingerprint(),
            "model_artifact_fingerprint": artifact.fingerprint(),
            "compatibility_fingerprint": compatibility.fingerprint(),
        }
    )
    preregistration = bundle["p16_preregistration"].model_validate(
        {**bundle["p16_preregistration"].to_dict(), "scope_fingerprint": scope.fingerprint()}
    )
    bundle.update(
        {
            "candidate_registry": ModelRegistryV2.from_dict(
                {
                    **bundle["candidate_registry"].to_dict(),
                    "artifacts": [artifact.to_dict()],
                    "releases": [release.to_dict()],
                }
            ),
            "candidate_release_fingerprint": release.fingerprint(),
            "p16_compatibility": compatibility,
            "p16_scope": scope,
            "p16_preregistration": preregistration,
        }
    )


def test_preflight_is_deterministic_value_free_and_identity_bound():
    bundle = _bundle()
    first, second = _compile(bundle), _compile(bundle)

    assert first.to_dict() == second.to_dict()
    assert first.fingerprint() == second.fingerprint()
    assert first.evaluation_scope == "single_gene"
    assert first.record_role == "authorization_preflight_not_evidence"
    assert first.assets_verified is False and first.record_membership_verified is False
    assert first.benchmark_passed is None and first.scientifically_validated is False
    assert first.promotion_eligible is None and first.production_promoted is False
    assert first.executable is False and first.abstain is True and first.prediction is None
    assert first.authorization_fingerprint is None and first.evidence_fingerprints == ()
    assert first.abstain_reasons == (
        "p16r_authorization_missing",
        "p16r_asset_bytes_unverified",
        "p16r_record_membership_unverified",
        "p16r_science_not_run",
    )
    assert "synthetic conformance fixture" not in json.dumps(first.to_dict())


@pytest.mark.parametrize(
    "field, value",
    [
        ("candidate_release_fingerprint", "f" * 64),
        ("p16_scope", "scope_drift"),
        ("p16_compatibility", "compatibility_drift"),
        ("execution", "execution_drift"),
    ],
)
def test_candidate_graph_and_p16_binding_drift_fail_closed(field, value):
    bundle = _bundle()
    if field == "p16_scope":
        bundle[field] = bundle[field].model_copy(update={"model_fingerprint": "f" * 64})
    elif field == "p16_compatibility":
        bundle[field] = bundle[field].model_copy(update={"environment_fingerprint": "f" * 64})
    elif field == "execution":
        bundle[field] = bundle[field].model_copy(update={"normalization_allowed": True})
    else:
        bundle[field] = value

    with pytest.raises(P16RPreflightError):
        _compile(bundle)


@pytest.mark.parametrize(
    "field",
    ["candidate_release_fingerprint", "candidate_provenance_manifest_fingerprint"],
)
def test_malformed_candidate_identity_fingerprints_fail_closed(field):
    bundle = _bundle()
    bundle[field] = "not-a-sha256"

    with pytest.raises(P16RPreflightError):
        _compile(bundle)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda bundle: bundle.update(
            {"external_dataset": bundle["external_dataset"].model_copy(update={"dataset_fingerprint": "f" * 64})}
        ),
        lambda bundle: bundle.update({"protocol": bundle["protocol"].model_copy(update={"seeds": (1, 2, 3)})}),
        lambda bundle: bundle.update(
            {
                "protocol": bundle["protocol"].model_copy(
                    update={"ood_policy": tuple(reversed(bundle["protocol"].ood_policy))}
                )
            }
        ),
        lambda bundle: bundle.update(
            {"protocol": bundle["protocol"].model_copy(update={"feature_contract_fingerprint": "f" * 64})}
        ),
        lambda bundle: bundle.update(
            {"protocol": bundle["protocol"].model_copy(update={"output_contract_fingerprint": "f" * 64})}
        ),
        lambda bundle: bundle.update(
            {
                "protocol": bundle["protocol"].model_copy(
                    update={"dataset": bundle["protocol"].dataset.model_copy(update={"dataset_fingerprint": "f" * 64})}
                )
            }
        ),
    ],
)
def test_external_and_protocol_drift_fail_closed(mutation):
    bundle = _bundle()
    mutation(bundle)

    with pytest.raises(P16RPreflightError):
        _compile(bundle)


def test_scope_separation_and_combination_card_guard_fail_closed():
    single, combination = _bundle("single_gene"), _bundle("combination")
    single["p16_scope"] = combination["p16_scope"]

    with pytest.raises(P16RPreflightError):
        _compile(single)

    combination = _bundle("combination")
    combination["candidate_card"] = combination["candidate_card"].model_copy(update={"perturbation": ("gene",)})
    with pytest.raises(P16RPreflightError):
        _compile(combination)


def test_external_scope_and_lifecycle_are_not_trusted_without_the_future_receipts():
    bundle = _bundle()
    bundle["external_scope"] = bundle["external_scope"].model_copy(update={"cell_identity_name": "T cell"})
    with pytest.raises(P16RPreflightError):
        _compile(bundle)

    bundle = _bundle()
    release_fingerprint = bundle["candidate_release_fingerprint"]
    cataloged = RegistryLifecycleEvent.from_dict(
        {
            "schema_version": "vc.model-registry-event.v1",
            "event_id": "p16r-test-cataloged",
            "sequence": 1,
            "previous_event_fingerprint": None,
            "release_fingerprint": release_fingerprint,
            "action": "cataloged",
            "target_release_fingerprint": None,
            "recorded_at": "2026-08-10T00:00:00Z",
            "operator_id": "test-only",
            "reason": "synthetic conformance only",
        }
    )
    revoked = RegistryLifecycleEvent.from_dict(
        {
            "schema_version": "vc.model-registry-event.v1",
            "event_id": "p16r-test-revoked",
            "sequence": 2,
            "previous_event_fingerprint": cataloged.fingerprint(),
            "release_fingerprint": release_fingerprint,
            "action": "revoke",
            "target_release_fingerprint": None,
            "recorded_at": "2026-08-10T00:00:01Z",
            "operator_id": "test-only",
            "reason": "synthetic conformance only",
        }
    )
    bundle["candidate_registry"] = ModelRegistryV2.from_dict(
        {
            **bundle["candidate_registry"].to_dict(),
            "lifecycle_events": [cataloged.to_dict(), revoked.to_dict()],
        }
    )
    with pytest.raises(P16RPreflightError):
        _compile(bundle)


def test_native_p16_artifact_must_remain_data_only_json():
    bundle = _bundle()
    _rebind_artifact_policy(bundle, "restricted_deserializer")

    with pytest.raises(P16RPreflightError):
        _compile(bundle)


def test_group_binding_and_negative_status_ceiling_are_closed():
    bundle = _bundle()
    groups = list(bundle["group_records"])
    groups[0] = groups[0].model_copy(update={"group_id": "changed"})
    bundle["group_records"] = tuple(groups)

    with pytest.raises(P16RPreflightError):
        _compile(bundle)

    bundle = _bundle()
    incomplete = tuple(item for item in bundle["group_records"] if item.partition != "train")
    split = bundle["protocol"].split.model_copy(
        update={
            "leakage_record_count": len(incomplete),
            "leakage_records_fingerprint": _canonical([item.to_dict() for item in incomplete]),
        }
    )
    bundle["group_records"] = incomplete
    bundle["protocol"] = bundle["protocol"].model_copy(update={"split": split})
    with pytest.raises(P16RPreflightError):
        _compile(bundle)

    preflight = _compile(_bundle())
    with pytest.raises(P16RPreflightError):
        preflight.model_copy(update={"production_promoted": True}).to_dict()
    with pytest.raises(P16RPreflightError):
        preflight.model_copy(update={"candidate_artifact_fingerprints": ()}).to_dict()
    with pytest.raises(ValidationError):
        K562P16RAuthorizationPreflightV1.model_validate({**preflight.to_dict(), "prediction": [1.0]})


def test_exact_type_and_no_io_or_execution_surface():
    bundle = _bundle()

    class EvilData(type(bundle["golden_data"])):
        model_config = ConfigDict(extra="allow", frozen=True, strict=True)

    evil = EvilData.model_construct(**bundle["golden_data"].__dict__, ignored="x")
    bundle["golden_data"] = evil
    with pytest.raises(P16RPreflightError):
        _compile(bundle)

    missing = type(bundle["golden_data"]).model_construct(schema_version="vc.k562-golden-data-binding.v1")
    bundle["golden_data"] = missing
    with pytest.raises(P16RPreflightError):
        _compile(bundle)

    tree = ast.parse(inspect.getsource(k562_p16r_preflight))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} | {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(name.startswith(("pathlib", "os", "subprocess", "requests", "urllib")) for name in imported)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert {"open", "BenchmarkRunV1", "BenchmarkRunAuthorizationV1", "audit_group_leakage"}.isdisjoint(names)
    with pytest.raises(TypeError):
        compile_k562_p16r_preflight(**_bundle(), candidate=True)
