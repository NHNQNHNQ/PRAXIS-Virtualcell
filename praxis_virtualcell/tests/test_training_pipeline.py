"""P20 controlled, contract-only training pipeline tests.

The fixtures are deliberately tiny and local.  They exercise identity and
failure boundaries only; no scientific, benchmark, external, or GPU work runs.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import praxis_virtualcell.model_zoo.training.pipeline as training_pipeline
from praxis_virtualcell.data_packs.feature_alignment import (
    AlignmentReport,
    ModelFeatureContract,
)
from praxis_virtualcell.model_zoo.training.pipeline import (
    TRAINER_REVISION,
    CandidateCheckpointV1,
    CandidateModelArtifactV1,
    CandidateModelCardV1,
    TrainingCandidateModelV1,
    TrainingEnvironmentV1,
    TrainingJobV1,
    TrainingLeakageAuditV1,
    TrainingPipelineError,
    TrainingResourceLimitsV1,
    TrainingResultV1,
    TrainingSplitV1,
    bind_training_job,
    capture_training_environment,
    load_training_job,
    run_training_job,
    trainer_source_sha256,
    training_code_sha256,
)
from praxis_virtualcell.pack_factory import (
    REQUIRED_REVIEW_TOPICS,
    PackFactoryStore,
    load_quarantined_upload,
    prepare_pack_candidate,
    register_pack_candidate,
    validate_pack_candidate,
)
from praxis_virtualcell.pack_product import PackIndex
from praxis_virtualcell.tests.test_pack_factory import (
    _decision,
    _review,
    _write_candidate_root,
    _write_exact_p7_upload,
)

_FEATURE_IDS = ("ENSG00000106546", "ENSG00000141510")
_INVALID_LABEL_SECRET = "P20_DO_NOT_REFLECT_SECRET_74f8"
_ASSETS = {
    "split": "training-split",
    "features": "training-features",
    "labels": "training-labels",
    "test": "test-labels-poison",
    "external": "external-labels-poison",
    "uploaded_code": "uploaded-trainer-code",
}


def _canonical_bytes(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _add_json_asset(manifest: dict, root: Path, asset_id: str, filename: str, value) -> Path:
    payload = _canonical_bytes(value)
    path = root / filename
    path.write_bytes(payload)
    manifest["assets"].append(
        {
            "id": asset_id,
            "path": filename,
            "media_type": "application/json",
            "sha256": _sha256(payload),
            "size_bytes": len(payload),
        }
    )
    return path


def _add_training_assets(
    root: Path,
    *,
    overlap: bool = False,
    invalid_train_labels: bool = False,
    duplicate_train_features: bool = False,
    scalar_target_ids: bool = False,
    split_name: str = "target-holdout-v1",
) -> dict[str, Path]:
    manifest_path = root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["split"]["name"] = split_name
    paths = {
        "features": _add_json_asset(
            manifest,
            root,
            _ASSETS["features"],
            "training-features.json",
            {
                "schema_version": "vc.tiny-training-features.v1",
                "feature_ids": list(_FEATURE_IDS),
                "samples": [
                    {"sample_id": "train-1", "values": [0.0, 1.0]},
                    {"sample_id": "train-2", "values": [1.0, 0.0]},
                    {"sample_id": "train-3", "values": [2.0, 1.0]},
                ],
            },
        ),
        "labels": _add_json_asset(
            manifest,
            root,
            _ASSETS["labels"],
            "training-labels.json",
            (
                {
                    "schema_version": "invalid-label-schema",
                    "samples": "not-an-array",
                    "secret": _INVALID_LABEL_SECRET,
                }
                if invalid_train_labels
                else {
                    "schema_version": "vc.tiny-training-labels.v1",
                    "samples": [
                        {"sample_id": "train-1", "value": 1.0},
                        {"sample_id": "train-2", "value": 2.0},
                        {"sample_id": "train-3", "value": 4.0},
                    ],
                }
            ),
        ),
    }
    test_donor = "donor-train-1" if overlap else "donor-test"
    paths["split"] = _add_json_asset(
        manifest,
        root,
        _ASSETS["split"],
        "training-split.json",
        {
            "schema_version": "vc.training-split-asset.v1",
            "split_name": split_name,
            "split_field": "split",
            "leakage_guard": [
                "donor_id",
                "condition_id",
                "perturbation_id",
                "target_ids",
            ],
            "rows": [
                {
                    "sample_id": "train-1",
                    "partition": "train",
                    "leakage_groups": {
                        "donor_id": "donor-train-1",
                        "condition_id": "condition:train-control",
                        "perturbation_id": "perturbation:train-control",
                        "target_ids": "target:none-train" if scalar_target_ids else [],
                    },
                },
                {
                    "sample_id": "train-2",
                    "partition": "train",
                    "leakage_groups": {
                        "donor_id": "donor-train-2",
                        "condition_id": "condition:train-perturbed",
                        "perturbation_id": "perturbation:AHR-KO",
                        "target_ids": [_FEATURE_IDS[0]],
                    },
                },
                {
                    "sample_id": "train-3",
                    "partition": "train",
                    "leakage_groups": {
                        "donor_id": "donor-train-3",
                        "condition_id": "condition:train-replicate",
                        "perturbation_id": "perturbation:AHR-KO-replicate",
                        "target_ids": ["target:AHR-replicate"],
                    },
                },
                {
                    "sample_id": "test-poison",
                    "partition": "test",
                    "leakage_groups": {
                        "donor_id": test_donor,
                        "condition_id": "condition:test-only",
                        "perturbation_id": "perturbation:TP53-KO",
                        "target_ids": [_FEATURE_IDS[1]],
                    },
                },
            ],
            "label_assets": {
                "train": [_ASSETS["labels"]],
                "validation": [],
                "test": [_ASSETS["test"]],
                "external": [_ASSETS["external"]],
            },
        },
    )
    paths["test"] = _add_json_asset(
        manifest,
        root,
        _ASSETS["test"],
        "test-labels-poison.json",
        {"must_not_read": "test results are outside P20 authorization"},
    )
    paths["external"] = _add_json_asset(
        manifest,
        root,
        _ASSETS["external"],
        "external-labels-poison.json",
        {"must_not_read": "external results are outside P20 authorization"},
    )
    uploaded_code = b"raise RuntimeError('uploaded Pack code must never execute')\n"
    paths["uploaded_code"] = root / "uploaded-trainer.py"
    paths["uploaded_code"].write_bytes(uploaded_code)
    manifest["assets"].append(
        {
            "id": _ASSETS["uploaded_code"],
            "path": paths["uploaded_code"].name,
            "media_type": "text/x-python",
            "sha256": _sha256(uploaded_code),
            "size_bytes": len(uploaded_code),
        }
    )
    if duplicate_train_features:
        duplicate = (
            b'{"schema_version":"vc.tiny-training-features.v1",'
            b'"feature_ids":["ENSG00000106546","ENSG00000141510"],'
            b'"samples":[{"sample_id":"train-1","values":[0,1]}],'
            b'"samples":[{"sample_id":"train-1","values":[0,1]}]}'
        )
        paths["features"].write_bytes(duplicate)
        feature_asset = next(item for item in manifest["assets"] if item["id"] == _ASSETS["features"])
        feature_asset["sha256"] = _sha256(duplicate)
        feature_asset["size_bytes"] = len(duplicate)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return paths


def _registered_training_pack(
    tmp_path: Path,
    *,
    overlap: bool = False,
    invalid_train_labels: bool = False,
    duplicate_train_features: bool = False,
    scalar_target_ids: bool = False,
    split_name: str = "target-holdout-v1",
    pack_id: str = "p20-human-tiny",
    version: str = "1.0.0",
):
    root = tmp_path / "chain"
    root.mkdir(parents=True)
    pack_root = _write_candidate_root(
        root / "candidate",
        pack_id=pack_id,
        version=version,
    )
    asset_paths = _add_training_assets(
        pack_root,
        overlap=overlap,
        invalid_train_labels=invalid_train_labels,
        duplicate_train_features=duplicate_train_features,
        scalar_target_ids=scalar_target_ids,
        split_name=split_name,
    )
    payload = (pack_root / "tiny.h5ad").read_bytes()
    upload = load_quarantined_upload(_write_exact_p7_upload(root, payload, index=20))
    prepared = prepare_pack_candidate(
        upload,
        pack_root,
        source_asset_id="expression",
        mapping_asset_ids={"primary": "primary-identity-map"},
        value_semantics={"primary": "raw_counts"},
        units={"dose_units": ["1"], "time_units": ["h"]},
        claim_origins={topic: "operator_declared" for topic in REQUIRED_REVIEW_TOPICS},
    )
    review = _review(prepared)
    report = validate_pack_candidate(prepared, review)
    decision = _decision(prepared, review, report)
    index = PackIndex(
        index_path=(root / "pack-index.json").resolve(),
        include_builtins=False,
    )
    store = PackFactoryStore.create((root / "factory-store").resolve())
    registration = register_pack_candidate(
        prepared,
        review,
        report,
        decision,
        index=index,
        store=store,
    )
    return SimpleNamespace(
        root=root,
        pack_root=pack_root,
        asset_paths=asset_paths,
        prepared=prepared,
        index=index,
        store=store,
        registration=registration,
    )


def _feature_contract() -> ModelFeatureContract:
    return ModelFeatureContract.from_dict(
        {
            "schema_version": "vc.model-feature-contract.v1",
            "model_id": "p20-tiny-linear",
            "model_version": "0.0.1-candidate",
            "taxonomy_id": "NCBITaxon:9606",
            "assembly_accession": "GCF_000001405.40",
            "modality": "scRNA",
            "feature_namespace": {
                "name": "EnsemblGene",
                "version": "GRCh38",
            },
            "feature_id_format": "ensembl_gene",
            "feature_ids": list(_FEATURE_IDS),
            "reorder": False,
            "drop": [],
            "fill": [],
            "mapping_asset": None,
        }
    )


def _alignment_report(contract: ModelFeatureContract | None = None) -> AlignmentReport:
    contract = contract or _feature_contract()
    feature_ids = tuple(contract.feature_ids)
    return AlignmentReport(
        schema_version="vc.alignment-report.v1",
        contract_fingerprint=contract.fingerprint(),
        source_feature_ids=feature_ids,
        target_feature_ids=feature_ids,
        source_shape=(3, 2),
        target_shape=(3, 2),
        steps=(),
        mapping_asset=None,
    )


def _resource_limits(**updates) -> TrainingResourceLimitsV1:
    value = {
        "schema_version": "vc.training-resource-limits.v1",
        "max_input_bytes": 64 * 1024,
        "max_samples": 16,
        "max_features": 8,
        "max_labels": 4,
        "max_checkpoint_bytes": 64 * 1024,
        "timeout_seconds": 10.0,
        "cpu_threads": 1,
        "network_allowed": False,
        "gpu_allowed": False,
        **updates,
    }
    return TrainingResourceLimitsV1.from_dict(value)


def _bound_job(chain, **updates) -> TrainingJobV1:
    feature_contract = updates.pop("feature_contract", _feature_contract())
    alignment_report = updates.pop(
        "alignment_report",
        _alignment_report(feature_contract),
    )
    values = {
        "index": chain.index,
        "pack_id": chain.registration.pack_id,
        "pack_version": chain.registration.pack_version,
        "registration_fingerprint": chain.registration.fingerprint(),
        "feature_contract": feature_contract,
        "alignment_report": alignment_report,
        "split_asset_id": _ASSETS["split"],
        "train_feature_asset_ids": (_ASSETS["features"],),
        "train_label_asset_ids": (_ASSETS["labels"],),
        "trainer_revision": TRAINER_REVISION,
        "trainer_source_sha256": trainer_source_sha256(),
        "code_sha256": training_code_sha256(),
        "environment": capture_training_environment(dependency_lock_sha256="0" * 64),
        "seed": 7,
        "hyperparameters": {
            "fit_intercept": True,
            "l2_penalty": 0.0,
            "max_steps": 4,
        },
        "resource_limits": _resource_limits(),
        "model_id": "p20-tiny-linear",
        "model_version": "0.0.1-candidate",
        **updates,
    }
    return bind_training_job(**values)


def _copied_index(chain, path: Path, *, legacy: bool = False, registration=None) -> PackIndex:
    payload = json.loads(chain.index.path.read_bytes())
    if legacy:
        payload["schema_version"] = "vc.pack-index.v1"
        payload["packs"][0].pop("factory_registration_fingerprint")
        payload["packs"][0].pop("factory_store_root")
    elif registration is not None:
        payload["packs"][0]["factory_registration_fingerprint"] = registration
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload) + b"\n")
    return PackIndex(index_path=path.resolve(), include_builtins=False)


def _write_job(path: Path, job: TrainingJobV1) -> Path:
    path.write_bytes(_canonical_bytes(job.to_dict()) + b"\n")
    return path


def _forged_semantic_job(
    job: TrainingJobV1,
    *,
    model_id: str | None = None,
    model_version: str | None = None,
    taxonomy_id: str | None = None,
    assembly_accession: str | None = None,
) -> TrainingJobV1:
    payload = job.to_dict()
    if model_id is not None:
        payload["model_id"] = model_id
    if model_version is not None:
        payload["model_version"] = model_version
    if taxonomy_id is not None or assembly_accession is not None:
        feature = json.loads(payload["feature_contract_json"])
        if taxonomy_id is not None:
            feature["taxonomy_id"] = taxonomy_id
        if assembly_accession is not None:
            feature["assembly_accession"] = assembly_accession
        feature_json = _canonical_bytes(feature).decode("utf-8")
        feature_fingerprint = _sha256(feature_json.encode("utf-8"))
        alignment = json.loads(payload["alignment_report_json"])
        alignment["contract_fingerprint"] = feature_fingerprint
        alignment_json = _canonical_bytes(alignment).decode("utf-8")
        payload["feature_contract_json"] = feature_json
        payload["feature_contract_fingerprint"] = feature_fingerprint
        payload["alignment_report_json"] = alignment_json
        payload["alignment_report_fingerprint"] = _sha256(alignment_json.encode("utf-8"))
    return TrainingJobV1.from_dict(payload)


def _rebound_bundle(template, *, checkpoint=None, result=None):
    job = template.job
    checkpoint = checkpoint or template.checkpoint
    if result is None:
        result = template.result.model_copy(
            update={
                "training_job_fingerprint": job.fingerprint(),
                "checkpoint_fingerprint": checkpoint.fingerprint(),
                "checkpoint_state_sha256": checkpoint.state_sha256,
                "checkpoint_state_size_bytes": checkpoint.state_size_bytes,
            }
        )
    identity = training_pipeline._model_identity(job, checkpoint, result)
    artifact = template.artifact.model_copy(
        update={
            "model_identity_fingerprint": identity,
            "training_job_fingerprint": job.fingerprint(),
            "training_result_fingerprint": result.fingerprint(),
            "checkpoint_fingerprint": checkpoint.fingerprint(),
            "artifact_sha256": checkpoint.state_sha256,
            "artifact_size_bytes": checkpoint.state_size_bytes,
        }
    )
    model_card = template.model_card.model_copy(
        update={
            "model_identity_fingerprint": identity,
            "artifact_fingerprint": artifact.fingerprint(),
            "training_job_fingerprint": job.fingerprint(),
            "training_result_fingerprint": result.fingerprint(),
            "checkpoint_fingerprint": checkpoint.fingerprint(),
        }
    )
    candidate_model = template.candidate_model.model_copy(
        update={
            "model_identity_fingerprint": identity,
            "training_job_fingerprint": job.fingerprint(),
            "training_result_fingerprint": result.fingerprint(),
            "checkpoint_fingerprint": checkpoint.fingerprint(),
            "artifact_fingerprint": artifact.fingerprint(),
            "model_card_fingerprint": model_card.fingerprint(),
        }
    )
    return training_pipeline.TrainingRunBundle(
        job=job,
        checkpoint=checkpoint,
        result=result,
        artifact=artifact,
        model_card=model_card,
        candidate_model=candidate_model,
    )


def _nested_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(map(_nested_keys, value.values())))
    if isinstance(value, list):
        return set().union(*(map(_nested_keys, value)))
    return set()


def _assert_contract_only(value) -> None:
    payload = value.to_dict() if hasattr(value, "to_dict") else value
    forbidden_true = {
        "benchmark_performed",
        "evidence_created",
        "scientific_validation_performed",
        "scientifically_validated",
        "promotion_created",
        "promotion_eligible",
        "production_promoted",
        "product_policy_created",
        "network_access",
        "network_access_requested",
        "network_allowed",
        "network_used",
        "gpu_access",
        "gpu_access_requested",
        "gpu_allowed",
        "gpu_available",
        "gpu_used",
        "test_data_read",
        "external_data_read",
        "test_external_read",
        "production_registry_written",
    }

    def visit(item) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                if key in forbidden_true:
                    assert nested is False
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(payload)


def test_registered_training_fixture_is_an_exact_modern_p19_chain(tmp_path):
    chain = _registered_training_pack(tmp_path)
    registration = chain.store.verify_registration(chain.registration.fingerprint())

    assert registration == chain.registration
    assert chain.prepared.candidate.manifest_schema_version == "vc.pack.v0.2"
    assert (
        chain.index.factory_registration_fingerprint(
            registration.pack_id,
            registration.pack_version,
        )
        == registration.fingerprint()
    )
    declared = {item.path for item in chain.prepared.candidate.candidate_files}
    assert {
        "training-features.json",
        "training-labels.json",
        "training-split.json",
        "test-labels-poison.json",
        "external-labels-poison.json",
        "uploaded-trainer.py",
    } <= declared
    assert _alignment_report().contract_fingerprint == _feature_contract().fingerprint()


def test_frozen_job_binds_exact_factory_pack_and_contract_only_inputs(tmp_path):
    chain = _registered_training_pack(tmp_path)
    job = _bound_job(chain)
    payload = job.to_dict()
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["schema_version"] == "vc.training-job.v1"
    assert TrainingJobV1.from_dict(payload) == job
    assert _bound_job(chain).fingerprint() == job.fingerprint()
    assert chain.registration.fingerprint() in rendered
    assert chain.prepared.candidate.fingerprint() in rendered
    assert chain.prepared.candidate.candidate_tree_fingerprint in rendered
    assert _feature_contract().fingerprint() in rendered
    assert _ASSETS["split"] in rendered
    assert _ASSETS["features"] in rendered
    assert _ASSETS["labels"] in rendered
    assert trainer_source_sha256() in rendered
    assert training_code_sha256() in rendered
    assert str(chain.root) not in rendered
    assert _ASSETS["test"] not in payload["split"]["train_label_asset_ids"]
    assert _ASSETS["external"] not in payload["split"]["train_label_asset_ids"]
    _assert_contract_only(job)


def test_bind_rejects_invalid_alignment_schema_and_p19_mapping_mismatches(tmp_path):
    chain = _registered_training_pack(tmp_path)
    base_contract = _feature_contract()
    invalid_schema = replace(
        _alignment_report(base_contract),
        schema_version="vc.alignment-report.invalid",
    )
    namespace_value = base_contract.model_dump(mode="json")
    namespace_value["feature_namespace"]["version"] = "GRCh37"
    wrong_namespace = ModelFeatureContract.from_dict(namespace_value)
    order_value = base_contract.model_dump(mode="json")
    order_value["feature_ids"].reverse()
    wrong_order = ModelFeatureContract.from_dict(order_value)
    wrong_width = replace(
        _alignment_report(base_contract),
        source_shape=(3, 3),
        target_shape=(3, 3),
    )
    wrong_rows = replace(
        _alignment_report(base_contract),
        source_shape=(4, 2),
        target_shape=(4, 2),
    )

    for feature_contract, alignment_report in (
        (base_contract, invalid_schema),
        (wrong_namespace, _alignment_report(wrong_namespace)),
        (wrong_order, _alignment_report(wrong_order)),
        (base_contract, wrong_width),
        (base_contract, wrong_rows),
    ):
        with pytest.raises(TrainingPipelineError, match="alignment|mapping|namespace|order|shape"):
            _bound_job(
                chain,
                feature_contract=feature_contract,
                alignment_report=alignment_report,
            )


def test_success_is_deterministic_safe_atomic_and_evidence_neutral(tmp_path):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    first_root = (tmp_path / "first-output").resolve()
    second_root = (tmp_path / "second-output").resolve()

    first = run_training_job(job, index=chain.index, output_root=first_root)
    second = run_training_job(job, index=chain.index, output_root=second_root)

    assert first.job == second.job == job
    assert first.checkpoint.fingerprint() == second.checkpoint.fingerprint()
    assert first.result.fingerprint() == second.result.fingerprint()
    assert first.candidate_model.fingerprint() == second.candidate_model.fingerprint()
    expected_files = {
        "checkpoint.json",
        "checkpoint-manifest.json",
        "training-result.json",
        "candidate-model.json",
    }
    assert {item.name for item in first_root.iterdir()} == expected_files
    assert {item.name for item in second_root.iterdir()} == expected_files
    assert {path.name: path.read_bytes() for path in first_root.iterdir()} == {
        path.name: path.read_bytes() for path in second_root.iterdir()
    }

    checkpoint_payload = json.loads((first_root / "checkpoint.json").read_bytes())
    manifest_payload = json.loads((first_root / "checkpoint-manifest.json").read_bytes())
    published_model = json.loads((first_root / "candidate-model.json").read_bytes())
    assert checkpoint_payload["schema_version"] == "vc.tiny-json-checkpoint.v1"
    assert manifest_payload == first.checkpoint.to_dict()
    assert json.loads((first_root / "training-result.json").read_bytes()) == first.result.to_dict()
    assert published_model == {
        "schema_version": "vc.training-candidate-bundle.v1",
        "artifact": first.artifact.to_dict(),
        "model_card": first.model_card.to_dict(),
        "candidate_model": first.candidate_model.to_dict(),
    }
    assert first.result.to_dict()["status"] == "succeeded_contract_only"
    assert first.candidate_model.to_dict()["status"] == "candidate_cataloged_contract_only"
    assert first.candidate_model.to_dict()["candidate_cataloged"] is True
    assert first.artifact.safe_load_policy == "data_only"
    assert first.artifact.executable is False
    assert first.model_card.status == "candidate"
    assert first.candidate_model.model_identity_fingerprint == first.artifact.model_identity_fingerprint
    assert first.candidate_model.model_identity_fingerprint == first.model_card.model_identity_fingerprint
    assert first.candidate_model.artifact_fingerprint == first.artifact.fingerprint()
    assert first.candidate_model.model_card_fingerprint == first.model_card.fingerprint()
    for value in (
        job,
        first.checkpoint,
        first.result,
        first.artifact,
        first.model_card,
        first.candidate_model,
    ):
        _assert_contract_only(value)
    rendered = b"\n".join(path.read_bytes() for path in first_root.iterdir()).decode("utf-8")
    assert str(tmp_path) not in rendered
    assert "uploaded Pack code must never execute" not in rendered
    assert {"benchmark", "evidence", "promotion", "registry"}.isdisjoint(
        _nested_keys({path.name: json.loads(path.read_bytes()) for path in first_root.iterdir()})
    )
    changed_checkpoint = first.checkpoint.to_dict()
    changed_checkpoint["state_sha256"] = "f" * 64
    assert CandidateCheckpointV1.from_dict(changed_checkpoint).fingerprint() != first.checkpoint.fingerprint()


def test_leakage_fails_before_invalid_train_labels_are_opened(tmp_path, monkeypatch):
    chain = _registered_training_pack(
        tmp_path,
        overlap=True,
        invalid_train_labels=True,
    )
    opened = []
    original = training_pipeline._read_root_relative_file

    def reject_label_open(root, relative, **kwargs):
        name = Path(relative).as_posix()
        opened.append(name)
        if name == "training-labels.json":
            raise AssertionError("training labels opened before leakage rejection")
        return original(root, relative, **kwargs)

    monkeypatch.setattr(training_pipeline, "_read_root_relative_file", reject_label_open)

    with pytest.raises(TrainingPipelineError, match="leakage") as exc_info:
        _bound_job(chain)

    assert "training-labels.json" not in opened
    assert "invalid-label-schema" not in str(exc_info.value)
    assert "not-an-array" not in str(exc_info.value)


def test_reserved_target_ids_leakage_group_rejects_scalar_opaque_values(tmp_path):
    chain = _registered_training_pack(tmp_path, scalar_target_ids=True)

    with pytest.raises(TrainingPipelineError, match="target_ids|array"):
        _bound_job(chain)


def test_only_exact_committed_p19_factory_registration_is_accepted(tmp_path):
    chain = _registered_training_pack(tmp_path / "exact")
    legacy = _copied_index(chain, tmp_path / "legacy" / "index.json", legacy=True)
    forged = _copied_index(
        chain,
        tmp_path / "forged" / "index.json",
        registration="f" * 64,
    )
    (tmp_path / "absent").mkdir()
    absent = PackIndex(
        index_path=(tmp_path / "absent" / "index.json").resolve(),
        include_builtins=True,
    )
    forged_registration = chain.registration.model_copy(update={"operator_id": "forged:operator"})

    for updates in (
        {"index": legacy},
        {"index": forged, "registration_fingerprint": "f" * 64},
        {
            "index": chain.index,
            "registration_fingerprint": forged_registration.fingerprint(),
        },
        {
            "index": absent,
            "pack_id": "p8-human-tiny",
            "pack_version": "1.0.0",
            "registration_fingerprint": "e" * 64,
        },
    ):
        with pytest.raises(TrainingPipelineError):
            _bound_job(chain, **updates)


def test_mixed_index_store_registration_chain_is_rejected(tmp_path):
    first = _registered_training_pack(
        tmp_path / "first",
        pack_id="p20-mixed-pack",
        version="1.0.0",
    )
    second = _registered_training_pack(
        tmp_path / "second",
        pack_id="p20-mixed-pack",
        version="2.0.0",
    )
    payload = json.loads(first.index.path.read_bytes())
    payload["packs"][0]["factory_registration_fingerprint"] = second.registration.fingerprint()
    payload["packs"][0]["factory_store_root"] = str(second.store.root)
    mixed_path = tmp_path / "mixed-index.json"
    mixed_path.write_bytes(_canonical_bytes(payload) + b"\n")
    mixed = PackIndex(index_path=mixed_path.resolve(), include_builtins=False)

    with pytest.raises(TrainingPipelineError):
        _bound_job(
            first,
            index=mixed,
            registration_fingerprint=second.registration.fingerprint(),
        )


def test_allowlisted_training_asset_drift_is_rechecked_before_work(tmp_path):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    output_root = (tmp_path / "never-published").resolve()
    drifted = chain.asset_paths["features"]
    drifted.write_bytes(drifted.read_bytes() + b"# drift\n")

    with pytest.raises(TrainingPipelineError) as exc_info:
        run_training_job(job, index=chain.index, output_root=output_root)

    assert str(chain.pack_root) not in str(exc_info.value)
    assert not output_root.exists()
    assert not list(tmp_path.glob(".*never-published*.tmp"))


def test_bind_and_run_open_only_manifest_split_and_train_allowlist(tmp_path, monkeypatch):
    chain = _registered_training_pack(tmp_path / "fixture")
    opened = []
    original = training_pipeline._read_root_relative_file

    def observe(root, relative, **kwargs):
        opened.append(Path(relative).as_posix())
        return original(root, relative, **kwargs)

    monkeypatch.setattr(training_pipeline, "_read_root_relative_file", observe)
    job = _bound_job(chain)
    run_training_job(
        job,
        index=chain.index,
        output_root=(tmp_path / "read-boundary-output").resolve(),
    )

    assert set(opened) == {
        "manifest.yaml",
        "training-split.json",
        "training-features.json",
        "training-labels.json",
    }


def test_invalid_training_bytes_fail_without_secret_or_partial_candidate(tmp_path):
    chain = _registered_training_pack(
        tmp_path / "fixture",
        invalid_train_labels=True,
    )
    job = _bound_job(chain)
    output_root = (tmp_path / "failed-output").resolve()
    with pytest.raises(TrainingPipelineError) as exc_info:
        run_training_job(job, index=chain.index, output_root=output_root)
    assert _INVALID_LABEL_SECRET not in str(exc_info.value)
    assert str(chain.pack_root) not in str(exc_info.value)
    assert not output_root.exists()


def test_output_root_must_be_absolute_canonical_write_new_and_non_symlink(tmp_path):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "keep.txt"
    marker.write_text("preserve\n", encoding="utf-8")
    target = tmp_path / "symlink-target"
    target.mkdir()
    symlink = tmp_path / "symlink-output"
    symlink.symlink_to(target, target_is_directory=True)
    noncanonical = tmp_path / "fixture" / ".." / "escaped-output"

    for output_root in (
        Path("relative-p20-output"),
        existing,
        symlink,
        noncanonical,
    ):
        with pytest.raises(TrainingPipelineError):
            run_training_job(job, index=chain.index, output_root=output_root)

    assert marker.read_text(encoding="utf-8") == "preserve\n"
    assert list(target.iterdir()) == []
    assert not (tmp_path / "escaped-output").exists()


def test_cancelled_job_never_starts_or_publishes_a_candidate(tmp_path):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    output_root = (tmp_path / "cancelled-output").resolve()

    with pytest.raises(TrainingPipelineError, match="cancel"):
        run_training_job(
            job,
            index=chain.index,
            output_root=output_root,
            cancelled=True,
        )

    assert not output_root.exists()
    assert not list(tmp_path.glob(".*cancelled-output*.tmp"))


def test_worker_timeout_is_terminated_without_publishing(tmp_path, monkeypatch):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    output_root = (tmp_path / "timeout-output").resolve()
    observed_command = []

    class TimedOutProcess:
        returncode = None

        def communicate(self, payload=None, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired("fixed-worker", timeout)
            return b"", b""

        def kill(self):
            self.returncode = -9

    def popen(command, **_kwargs):
        observed_command.extend(command)
        return TimedOutProcess()

    monkeypatch.setattr(training_pipeline.subprocess, "Popen", popen)

    with pytest.raises(TrainingPipelineError, match="timed out"):
        run_training_job(
            job,
            index=chain.index,
            output_root=output_root,
            timeout_seconds=0.001,
        )
    assert observed_command[1:3] == ["-I", "-S"]
    assert not output_root.exists()


def test_worker_checkpoint_semantics_are_bound_to_exact_job_and_input(tmp_path, monkeypatch):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    current = {"payload": b""}

    class WorkerProcess:
        returncode = 0

        def __init__(self, *, stdout):
            self.stdout = stdout

        def communicate(self, payload=None, timeout=None):
            self.stdout.write(current["payload"])
            self.stdout.flush()
            return None

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr(
        training_pipeline.subprocess,
        "Popen",
        lambda *args, **kwargs: WorkerProcess(stdout=kwargs["stdout"]),
    )
    base = {
        "schema_version": "vc.tiny-json-checkpoint.v1",
        "job_fingerprint": job.fingerprint(),
        "seed": job.seed,
        "sample_ids_sha256": _sha256(_canonical_bytes(["train-1", "train-2", "train-3"])),
        "sample_count": 3,
        "feature_count": 2,
        "label_count": 1,
        "feature_means": [1.0, 2.0 / 3.0],
        "label_means": [7.0 / 3.0],
        "contract_only": True,
    }
    variants = []
    for field, value in (
        ("job_fingerprint", "f" * 64),
        ("seed", job.seed + 1),
        ("sample_ids_sha256", "e" * 64),
        ("sample_count", 4),
        ("feature_count", 3),
        ("label_count", 2),
        ("feature_means", [1.0]),
        ("label_means", [1.0, 2.0]),
    ):
        variant = dict(base)
        variant[field] = value
        variants.append(variant)

    for number, variant in enumerate(variants, start=1):
        current["payload"] = _canonical_bytes(variant) + b"\n"
        output_root = (tmp_path / f"bad-worker-output-{number}").resolve()
        with pytest.raises(TrainingPipelineError):
            run_training_job(job, index=chain.index, output_root=output_root)
        assert not output_root.exists()

    current["payload"] = b'{"schema_version":' + b"[" * 2_000 + b"0" + b"]" * 2_000 + b"}\n"
    output_root = (tmp_path / "deep-worker-output").resolve()
    with pytest.raises(TrainingPipelineError):
        run_training_job(job, index=chain.index, output_root=output_root)
    assert not output_root.exists()


def test_partial_staging_is_removed_on_publish_failure(tmp_path, monkeypatch):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    output_root = (tmp_path / "partial-output").resolve()
    original = training_pipeline._write_new_file
    writes = 0

    def fail_after_one_file(root, relative, payload):
        nonlocal writes
        writes += 1
        if writes == 2:
            raise TrainingPipelineError("injected contract-only write failure")
        return original(root, relative, payload)

    monkeypatch.setattr(training_pipeline, "_write_new_file", fail_after_one_file)

    with pytest.raises(TrainingPipelineError, match="injected"):
        run_training_job(job, index=chain.index, output_root=output_root)
    assert not output_root.exists()
    assert not list(tmp_path.glob(".partial-output.training-*"))


def test_atomic_publish_race_preserves_competing_target_and_cleans_staging(tmp_path, monkeypatch):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    output_root = (tmp_path / "raced-output").resolve()
    marker = output_root / "competitor.txt"
    original = training_pipeline._atomic_rename_no_replace

    def create_competitor_then_commit(source, target, **kwargs):
        target.mkdir()
        marker.write_text("belongs to competitor\n", encoding="utf-8")
        return original(source, target, **kwargs)

    monkeypatch.setattr(
        training_pipeline,
        "_atomic_rename_no_replace",
        create_competitor_then_commit,
    )

    with pytest.raises(TrainingPipelineError, match="exists|publish"):
        run_training_job(job, index=chain.index, output_root=output_root)
    assert marker.read_text(encoding="utf-8") == "belongs to competitor\n"
    assert {item.name for item in output_root.iterdir()} == {marker.name}
    assert not list(tmp_path.glob(".raced-output.training-*"))


def test_atomic_publish_rejects_swapped_staging_inode(tmp_path, monkeypatch):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    output_root = (tmp_path / "source-swap-output").resolve()
    original = training_pipeline._atomic_rename_no_replace
    replacement = None
    moved = None

    def swap_source_then_commit(source, target, **kwargs):
        nonlocal moved, replacement
        moved = source.with_name(f"{source.name}.verified-moved")
        source.rename(moved)
        source.mkdir()
        replacement = source / "attacker.txt"
        replacement.write_text("must not publish\n", encoding="utf-8")
        return original(source, target, **kwargs)

    monkeypatch.setattr(
        training_pipeline,
        "_atomic_rename_no_replace",
        swap_source_then_commit,
    )

    with pytest.raises(TrainingPipelineError, match="staging|identity|publishable"):
        run_training_job(job, index=chain.index, output_root=output_root)
    assert not output_root.exists()
    assert moved is not None and moved.is_dir()
    assert list(moved.iterdir()) == []
    assert replacement is not None and replacement.read_text(encoding="utf-8") == "must not publish\n"


def test_allowlisted_asset_is_rechecked_after_worker_before_atomic_publish(tmp_path, monkeypatch):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    output_root = (tmp_path / "prepublish-output").resolve()
    original = training_pipeline._run_fixed_worker

    def drift_after_worker(*args, **kwargs):
        checkpoint = original(*args, **kwargs)
        path = chain.asset_paths["features"]
        path.write_bytes(path.read_bytes() + b"# post-worker drift\n")
        return checkpoint

    monkeypatch.setattr(training_pipeline, "_run_fixed_worker", drift_after_worker)

    with pytest.raises(TrainingPipelineError):
        run_training_job(job, index=chain.index, output_root=output_root)
    assert not output_root.exists()
    assert not list(tmp_path.glob(".prepublish-output.training-*"))


def test_job_identity_covers_pack_feature_alignment_environment_seed_hparams_and_limits(
    tmp_path,
):
    chain = _registered_training_pack(tmp_path / "base")
    base = _bound_job(chain)
    changed_environment_value = base.environment.to_dict()
    changed_environment_value["declared_dependency_lock_sha256"] = "1" * 64
    changed_environment = TrainingEnvironmentV1.from_dict(changed_environment_value)
    changed_feature_value = _feature_contract().model_dump(mode="json")
    changed_feature_value["model_version"] = "0.0.2-candidate"
    changed_feature = ModelFeatureContract.from_dict(changed_feature_value)
    split_chain = _registered_training_pack(
        tmp_path / "split",
        split_name="target-holdout-v2",
        version="1.1.0",
    )

    variants = (
        _bound_job(chain, seed=8),
        _bound_job(chain, hyperparameters={"fit_intercept": False, "max_steps": 4}),
        _bound_job(chain, resource_limits=_resource_limits(max_checkpoint_bytes=96 * 1024)),
        _bound_job(chain, environment=changed_environment),
        _bound_job(
            chain,
            feature_contract=changed_feature,
            alignment_report=_alignment_report(changed_feature),
            model_version="0.0.2-candidate",
        ),
        _bound_job(split_chain),
    )

    assert all(item.fingerprint() != base.fingerprint() for item in variants)
    assert len({base.fingerprint(), *(item.fingerprint() for item in variants)}) == 7


def test_fixed_trainer_and_pipeline_source_are_not_caller_selectable(tmp_path):
    chain = _registered_training_pack(tmp_path)

    for updates in (
        {"trainer_revision": "2"},
        {"trainer_source_sha256": "1" * 64},
        {"code_sha256": "2" * 64},
        {"trainer_path": _ASSETS["uploaded_code"]},
        {"command": ["python", "uploaded-trainer.py"]},
        {"train_feature_asset_ids": (_ASSETS["uploaded_code"],)},
        {"train_label_asset_ids": (_ASSETS["test"],)},
        {"train_label_asset_ids": (_ASSETS["external"],)},
    ):
        with pytest.raises((TrainingPipelineError, TypeError)):
            _bound_job(chain, **updates)

    mismatched_feature_value = _feature_contract().model_dump(mode="json")
    mismatched_feature_value["model_id"] = "different-model"
    mismatched_feature = ModelFeatureContract.from_dict(mismatched_feature_value)
    with pytest.raises(TrainingPipelineError, match="model|feature"):
        _bound_job(
            chain,
            feature_contract=mismatched_feature,
            alignment_report=_alignment_report(mismatched_feature),
        )


def test_environment_must_match_captured_runtime_at_bind_and_run(tmp_path):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    forged_value = job.environment.to_dict()
    forged_value["python_version"] = "0.0.0"
    forged_value["platform_system"] = "forged-platform"
    forged_environment = TrainingEnvironmentV1.from_dict(forged_value)

    with pytest.raises(TrainingPipelineError, match="environment|runtime"):
        _bound_job(chain, environment=forged_environment)

    payload = job.to_dict()
    payload["environment"] = forged_environment.to_dict()
    forged_job = TrainingJobV1.from_dict(payload)
    output_root = (tmp_path / "forged-environment-output").resolve()
    with pytest.raises(TrainingPipelineError, match="environment|runtime"):
        run_training_job(forged_job, index=chain.index, output_root=output_root)
    assert not output_root.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("timeout_seconds", 0),
        ("max_samples", -1),
        ("max_features", True),
        ("max_input_bytes", 0),
        ("max_checkpoint_bytes", 0),
        ("max_input_bytes", 10**12),
        ("max_samples", 10**12),
        ("max_features", 10**12),
        ("max_labels", 10**12),
        ("max_checkpoint_bytes", 10**12),
        ("timeout_seconds", 61.0),
    ],
)
def test_resource_limits_are_strict_positive_and_hard_bounded(field, value):
    payload = _resource_limits().to_dict()
    payload[field] = value
    with pytest.raises(TrainingPipelineError):
        TrainingResourceLimitsV1.from_dict(payload)


def test_runtime_resource_hard_ceilings_fail_before_candidate_publish(tmp_path):
    chain = _registered_training_pack(tmp_path / "fixture")
    limits = (
        {"max_input_bytes": 1},
        {"max_samples": 2},
        {"max_features": 1},
        {"max_checkpoint_bytes": 1},
    )

    for number, update in enumerate(limits, start=1):
        output_root = (tmp_path / f"limited-output-{number}").resolve()
        try:
            job = _bound_job(chain, resource_limits=_resource_limits(**update))
        except TrainingPipelineError:
            pass
        else:
            with pytest.raises(TrainingPipelineError):
                run_training_job(job, index=chain.index, output_root=output_root)
        assert not output_root.exists()


@pytest.mark.parametrize(
    "hyperparameters",
    [
        {"NotCanonical": 1},
        {"nested": {"arbitrary": "code-like structure"}},
        {"array": [1, 2]},
        {"not_finite": float("nan")},
        {"empty": ""},
    ],
)
def test_hyperparameters_are_typed_canonical_scalars_only(tmp_path, hyperparameters):
    chain = _registered_training_pack(tmp_path)
    with pytest.raises(TrainingPipelineError):
        _bound_job(chain, hyperparameters=hyperparameters)


@pytest.mark.parametrize(
    "model",
    [
        TrainingEnvironmentV1,
        TrainingResourceLimitsV1,
        TrainingSplitV1,
        TrainingLeakageAuditV1,
        TrainingJobV1,
        CandidateCheckpointV1,
        TrainingResultV1,
        CandidateModelArtifactV1,
        CandidateModelCardV1,
        TrainingCandidateModelV1,
    ],
)
def test_training_contracts_reject_unknown_fields(model):
    with pytest.raises(TrainingPipelineError):
        model.from_dict({"schema_version": "wrong", "unexpected": True})


def test_job_loader_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "duplicate-job.json"
    path.write_bytes(b'{"schema_version":"vc.training-job.v1","schema_version":"vc.training-job.v1"}\n')

    with pytest.raises(TrainingPipelineError, match="duplicate|invalid"):
        load_training_job(path)


def test_job_loader_translates_json_parser_resource_failures(tmp_path):
    payloads = (
        b'{"schema_version":' + b"[" * 2_000 + b"0" + b"]" * 2_000 + b"}\n",
        b'{"seed":' + b"1" * 5_000 + b"}\n",
    )
    for number, payload in enumerate(payloads, start=1):
        path = tmp_path / f"hostile-job-{number}.json"
        path.write_bytes(payload)
        with pytest.raises(TrainingPipelineError):
            load_training_job(path)


def test_duplicate_keys_in_allowlisted_training_assets_fail_closed(tmp_path):
    chain = _registered_training_pack(
        tmp_path / "fixture",
        duplicate_train_features=True,
    )
    output_root = (tmp_path / "duplicate-output").resolve()
    try:
        job = _bound_job(chain)
    except TrainingPipelineError as exc:
        assert "duplicate" in str(exc).lower() or "invalid" in str(exc).lower()
    else:
        with pytest.raises(TrainingPipelineError, match="duplicate|invalid"):
            run_training_job(job, index=chain.index, output_root=output_root)
    assert not output_root.exists()


def test_runner_revalidates_exact_job_type_and_rejects_construct_bypasses(tmp_path):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)

    class JobSubclass(TrainingJobV1):
        pass

    subclass = JobSubclass.model_validate(job.to_dict())
    constructed = TrainingJobV1.model_construct(
        **{**job.__dict__, "seed": True},
    )
    copied = job.model_copy(update={"code_sha256": "f" * 64})

    for number, invalid in enumerate((subclass, constructed, copied), start=1):
        output_root = (tmp_path / f"invalid-{number}").resolve()
        with pytest.raises(TrainingPipelineError):
            run_training_job(invalid, index=chain.index, output_root=output_root)
        assert not output_root.exists()


def test_runner_rejects_canonical_jobs_with_forged_semantic_bindings(tmp_path):
    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    cases = (
        {"model_id": "forged-model"},
        {"model_version": "9.9.9-forged"},
        {"taxonomy_id": "NCBITaxon:10090"},
        {"assembly_accession": "GCF_000001635.27"},
    )

    for number, changes in enumerate(cases, start=1):
        forged = _forged_semantic_job(job, **changes)
        path = _write_job((tmp_path / f"forged-{number}.json").resolve(), forged)
        loaded = load_training_job(path)
        assert loaded == forged
        output_root = (tmp_path / f"forged-output-{number}").resolve()
        with pytest.raises(TrainingPipelineError):
            run_training_job(loaded, index=chain.index, output_root=output_root)
        assert not output_root.exists()


def test_duplicate_results_and_mixed_public_bundles_fail_closed(tmp_path):
    chain = _registered_training_pack(tmp_path / "fixture")
    first = run_training_job(
        _bound_job(chain),
        index=chain.index,
        output_root=(tmp_path / "first-bundle").resolve(),
    )
    second = run_training_job(
        _bound_job(chain, seed=8),
        index=chain.index,
        output_root=(tmp_path / "second-bundle").resolve(),
    )
    duplicate_result = first.result.to_dict()
    duplicate_result["metrics"][1] = duplicate_result["metrics"][0]
    inconsistent_result = first.result.to_dict()
    inconsistent_result["metrics"][0]["value"] += 1
    for invalid in (duplicate_result, inconsistent_result):
        with pytest.raises(TrainingPipelineError):
            TrainingResultV1.from_dict(invalid)

    assert first.to_dict()["schema_version"] == "vc.training-run-bundle.v1"
    mixed_bundles = (
        replace(first, artifact=second.artifact),
        replace(
            first,
            artifact=first.artifact.model_copy(update={"model_id": "forged-model"}),
        ),
        replace(
            first,
            artifact=first.artifact.model_copy(update={"artifact_size_bytes": first.artifact.artifact_size_bytes + 1}),
        ),
        replace(
            first,
            artifact=first.artifact.model_copy(update={"artifact_sha256": "f" * 64}),
        ),
        replace(
            first,
            model_card=first.model_card.model_copy(update={"model_version": "9.9.9"}),
        ),
        replace(
            first,
            model_card=first.model_card.model_copy(update={"feature_contract_fingerprint": "e" * 64}),
        ),
        replace(
            first,
            model_card=first.model_card.model_copy(update={"split_fingerprint": "d" * 64}),
        ),
        replace(
            first,
            model_card=first.model_card.model_copy(update={"leakage_audit_fingerprint": "c" * 64}),
        ),
        replace(
            first,
            candidate_model=first.candidate_model.model_copy(update={"model_id": "forged-model"}),
        ),
        replace(
            first,
            result=first.result.model_copy(update={"checkpoint_fingerprint": "f" * 64}),
        ),
        replace(
            first,
            result=first.result.model_copy(update={"checkpoint_state_sha256": "e" * 64}),
        ),
        replace(
            first,
            result=first.result.model_copy(
                update={"checkpoint_state_size_bytes": first.result.checkpoint_state_size_bytes + 1}
            ),
        ),
        _rebound_bundle(
            first,
            checkpoint=first.checkpoint.model_copy(update={"training_job_fingerprint": "d" * 64}),
        ),
        _rebound_bundle(
            first,
            result=first.result.model_copy(update={"training_job_fingerprint": "c" * 64}),
        ),
        _rebound_bundle(
            first,
            result=first.result.model_copy(update={"checkpoint_fingerprint": "b" * 64}),
        ),
        _rebound_bundle(
            first,
            result=first.result.model_copy(update={"checkpoint_state_sha256": "a" * 64}),
        ),
        _rebound_bundle(
            first,
            result=first.result.model_copy(
                update={"checkpoint_state_size_bytes": first.result.checkpoint_state_size_bytes + 1}
            ),
        ),
    )
    for mixed in mixed_bundles:
        with pytest.raises(TrainingPipelineError):
            mixed.to_dict()


def test_cli_dry_run_has_explicit_paths_and_identity_only_output(tmp_path, capsys):
    from praxis_virtualcell.cli import main

    chain = _registered_training_pack(tmp_path / "fixture")
    job = _bound_job(chain)
    job_path = _write_job((tmp_path / "training-job.json").resolve(), job)
    output_root = (tmp_path / "cli-output").resolve()
    args = [
        "training",
        "dry-run",
        "--job",
        str(job_path),
        "--index",
        str(chain.index.path.resolve()),
        "--output-root",
        str(output_root),
    ]

    assert main(args) == 0
    response = json.loads(capsys.readouterr().out)
    assert set(response) == {
        "status",
        "training_job_fingerprint",
        "checkpoint_fingerprint",
        "training_result_fingerprint",
        "candidate_model_fingerprint",
    }
    assert response["status"] == "candidate_cataloged_contract_only"
    assert response["training_job_fingerprint"] == job.fingerprint()
    assert all(
        type(response[key]) is str and len(response[key]) == 64 and set(response[key]) <= set("0123456789abcdef")
        for key in response
        if key.endswith("_fingerprint")
    )
    assert str(tmp_path) not in json.dumps(response)

    assert main(args) == 2
    assert json.loads(capsys.readouterr().out) == {"status": "rejected"}
