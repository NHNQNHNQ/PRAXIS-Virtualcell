"""P19 controlled Pack Factory contracts and fail-closed lifecycle gates."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from praxis_virtualcell.pack_factory import (
    REQUIRED_REVIEW_TOPICS,
    FactoryRegisteredPackV1,
    MetadataConfirmationV1,
    PackCandidateV1,
    PackFactoryError,
    PackFactoryStore,
    PackMetadataReviewV1,
    PackOperatorDecisionV1,
    PackSupersessionV1,
    PackValidationReportV1,
    PreparedPackCandidate,
    UploadReceiptV1,
    bind_pack_candidate,
    declare_pack_supersession,
    factory_catalog_payload,
    load_quarantined_upload,
    prepare_pack_candidate,
    register_pack_candidate,
    validate_metadata_review,
    validate_operator_decision,
    validate_pack_candidate,
)
from praxis_virtualcell.pack_product import PackIndex, PackIndexError

_PACKAGE = Path(__file__).parents[1]
_HUMAN_PACK = _PACKAGE / "example_packs" / "human"
_FEATURE_IDS = ("ENSG00000106546", "ENSG00000141510")
_NAMESPACE = {
    "schema_version": "vc.pack-factory-mapping-namespace.v1",
    "name": "EnsemblGene",
    "version": "GRCh38",
}


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _uuid4(index: int) -> str:
    return f"00000000-0000-4000-8000-{index:012d}"


def _identity_mapping() -> dict:
    return {
        "schema_version": "vc.pack-factory-feature-mapping.v1",
        "mapping_id": "primary-identity-map",
        "mapping_version": "1.0.0",
        "modality_key": "primary",
        "source_namespace": dict(_NAMESPACE),
        "target_namespace": dict(_NAMESPACE),
        "source_feature_ids": list(_FEATURE_IDS),
        "target_feature_ids": list(_FEATURE_IDS),
        "mappings": [],
    }


def _write_candidate_root(
    root: Path,
    *,
    pack_id: str = "p8-human-tiny",
    version: str = "1.0.0",
    mapping_update=None,
) -> Path:
    shutil.copytree(_HUMAN_PACK, root)
    mapping = _identity_mapping()
    if mapping_update is not None:
        mapping_update(mapping)
    mapping_bytes = json.dumps(
        mapping,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    mapping_path = root / "identity-mapping.json"
    mapping_path.write_bytes(mapping_bytes)

    manifest_path = root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["pack_id"] = pack_id
    manifest["pack_version"] = version
    manifest["assets"].append(
        {
            "id": "primary-identity-map",
            "path": mapping_path.name,
            "media_type": "application/json",
            "sha256": _sha256(mapping_bytes),
            "size_bytes": len(mapping_bytes),
        }
    )
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    return root


def _write_exact_p7_upload(
    root: Path,
    payload: bytes,
    *,
    index: int,
    filename: str = "tiny.h5ad",
    declared_content_type: str = "application/vnd.anndata+hdf5",
) -> Path:
    upload_id = _uuid4(index)
    upload = root / "uploads" / "quarantine" / upload_id
    upload.mkdir(parents=True)
    (upload / "payload").write_bytes(payload)
    receipt = {
        "schema_version": "vc.upload-receipt.v1",
        "upload_id": upload_id,
        "status": "quarantined",
        "species": "human",
        "filename": filename,
        "size_bytes": len(payload),
        "sha256": _sha256(payload),
        "declared_content_type": declared_content_type,
        "created_at": f"2026-08-06T00:00:{index:02d}Z",
    }
    (upload / "receipt.json").write_text(
        json.dumps(
            receipt,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return upload


def _factory_init_args(data_root: Path, upload_id: str, store_root: Path) -> list[str]:
    return [
        "pack",
        "factory-init",
        "--data-root",
        str(data_root),
        "--upload-id",
        upload_id,
        "--store",
        str(store_root),
    ]


def _candidate_authoring() -> dict:
    return {
        "schema_version": "vc.pack-candidate-authoring.v1",
        "source_asset_id": "expression",
        "mapping_asset_ids": {"primary": "primary-identity-map"},
        "value_semantics": {"primary": "raw_counts"},
        "units": {"dose_units": ["1"], "time_units": ["h"]},
        "claim_origins": {topic: "operator_declared" for topic in REQUIRED_REVIEW_TOPICS},
    }


def _prepare(
    root: Path,
    *,
    index: int = 1,
    pack_id: str = "p8-human-tiny",
    version: str = "1.0.0",
    mapping_update=None,
):
    root.mkdir(parents=True, exist_ok=True)
    pack_root = _write_candidate_root(
        root / "candidate",
        pack_id=pack_id,
        version=version,
        mapping_update=mapping_update,
    )
    payload = (pack_root / "tiny.h5ad").read_bytes()
    upload_root = _write_exact_p7_upload(root, payload, index=index)
    upload = load_quarantined_upload(upload_root)
    prepared = prepare_pack_candidate(
        upload,
        pack_root,
        source_asset_id="expression",
        mapping_asset_ids={"primary": "primary-identity-map"},
        value_semantics={"primary": "raw_counts"},
        units={"dose_units": ["1"], "time_units": ["h"]},
        claim_origins={topic: "inferred_candidate" for topic in REQUIRED_REVIEW_TOPICS},
    )
    return prepared


def _review(prepared: PreparedPackCandidate) -> PackMetadataReviewV1:
    return PackMetadataReviewV1(
        schema_version="vc.pack-metadata-review.v1",
        candidate_fingerprint=prepared.candidate.fingerprint(),
        reviewer_id="test:metadata-reviewer",
        reviewer_role="metadata_reviewer",
        reviewed_at="2026-08-06T01:00:00Z",
        decision="approve_for_strict_validation",
        rationale="all candidate claims checked in a synthetic contract fixture",
        confirmations=tuple(
            MetadataConfirmationV1(
                schema_version="vc.pack-factory-metadata-confirmation.v1",
                topic=claim.topic,
                claim_fingerprint=claim.fingerprint(),
                status="confirmed",
            )
            for claim in prepared.candidate.metadata_claims
        ),
        scientific_validation_performed=False,
        product_policy_created=False,
    )


def _decision(
    prepared: PreparedPackCandidate,
    review: PackMetadataReviewV1,
    report,
    *,
    decision: str = "approve_register",
    decided_at: str = "2026-08-06T02:00:00Z",
) -> PackOperatorDecisionV1:
    assert report.validated_pack_fingerprint is not None
    return PackOperatorDecisionV1(
        schema_version="vc.pack-operator-decision.v1",
        candidate_fingerprint=prepared.candidate.fingerprint(),
        review_fingerprint=review.fingerprint(),
        validation_report_fingerprint=report.fingerprint(),
        pack_id=prepared.candidate.pack_id,
        pack_version=prepared.candidate.pack_version,
        pack_fingerprint=report.validated_pack_fingerprint,
        operator_id="test:pack-registration-operator",
        operator_role="pack_registration_operator",
        decided_at=decided_at,
        decision=decision,
        reason="contract-only registration fixture",
        decision_scope="pack_registration_only",
        scientific_evidence_decision=False,
        product_promotion_decision=False,
    )


def _chain(
    root: Path,
    *,
    index_number: int = 1,
    pack_id: str = "p8-human-tiny",
    version: str = "1.0.0",
    pack_index: PackIndex | None = None,
    factory_store: PackFactoryStore | None = None,
    register: bool = True,
):
    prepared = _prepare(
        root,
        index=index_number,
        pack_id=pack_id,
        version=version,
    )
    review = _review(prepared)
    report = validate_pack_candidate(prepared, review)
    decision = _decision(
        prepared,
        review,
        report,
        decided_at=f"2026-08-06T02:00:{index_number:02d}Z",
    )
    if pack_index is None:
        pack_index = PackIndex(
            index_path=(root / "pack-index.json").resolve(),
            include_builtins=False,
        )
    if factory_store is None:
        factory_store = PackFactoryStore.create((root / "factory-store").resolve())
    registration = (
        register_pack_candidate(
            prepared,
            review,
            report,
            decision,
            index=pack_index,
            store=factory_store,
        )
        if register
        else None
    )
    return SimpleNamespace(
        prepared=prepared,
        review=review,
        report=report,
        decision=decision,
        registration=registration,
        index=pack_index,
        store=factory_store,
    )


def _failed_codes(report) -> set[str]:
    return {check.code for check in report.checks if not check.passed}


def _write_contract(path: Path, value) -> Path:
    path.write_text(
        json.dumps(
            value.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    return path


def _nested_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(map(_nested_keys, value.values())))
    if isinstance(value, list):
        return set().union(*(map(_nested_keys, value)))
    return set()


def _assert_no_science_markers(value) -> None:
    forbidden_true = {
        "normalization_performed",
        "fill_performed",
        "imputation_performed",
        "deduplication_performed",
        "reordering_performed",
        "random_split_performed",
        "identifier_conversion_performed",
        "training_performed",
        "checkpoint_created",
        "model_card_created",
        "benchmark_performed",
        "evidence_created",
        "scientific_validation_performed",
        "scientific_evidence_decision",
        "scientifically_validated",
        "promotion_created",
        "promotion_eligible",
        "product_policy_created",
        "product_promotion_decision",
        "production_promoted",
        "executable",
    }

    def visit(item):
        if isinstance(item, dict):
            for key, nested in item.items():
                if key in forbidden_true:
                    assert nested is False
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(value.to_dict() if hasattr(value, "to_dict") else value)


def test_complete_chain_is_deterministic_separated_and_contract_only(tmp_path):
    chain = _chain(tmp_path / "chain")
    prepared = chain.prepared
    candidate = prepared.candidate
    registration = chain.registration

    assert chain.report.passed is True
    assert chain.report.registration_allowed is True
    assert all(check.passed for check in chain.report.checks)
    assert candidate.feature_mappings[0].order_preserved is True
    assert not any(
        (
            candidate.feature_mappings[0].duplicate_source_feature_ids,
            candidate.feature_mappings[0].duplicate_target_feature_ids,
            candidate.feature_mappings[0].unmapped_source_feature_ids,
            candidate.feature_mappings[0].unmapped_target_feature_ids,
        )
    )
    assert (
        prepare_pack_candidate(
            prepared.upload,
            prepared.root,
            source_asset_id="expression",
            mapping_asset_ids={"primary": "primary-identity-map"},
            value_semantics={"primary": "raw_counts"},
            units={"dose_units": ["1"], "time_units": ["h"]},
            claim_origins={topic: "inferred_candidate" for topic in REQUIRED_REVIEW_TOPICS},
        ).candidate.fingerprint()
        == candidate.fingerprint()
    )
    assert validate_pack_candidate(prepared, chain.review).fingerprint() == chain.report.fingerprint()
    assert (
        register_pack_candidate(
            prepared,
            chain.review,
            chain.report,
            chain.decision,
            index=chain.index,
            store=chain.store,
        ).fingerprint()
        == registration.fingerprint()
    )

    identities = {
        prepared.upload.receipt.fingerprint(),
        candidate.fingerprint(),
        chain.review.fingerprint(),
        chain.report.fingerprint(),
        chain.decision.fingerprint(),
        registration.fingerprint(),
    }
    assert len(identities) == 6
    assert registration.factory_registered is True
    assert registration.pack_valid is True
    assert registration.model_compatible is None
    assert registration.environment_compatible is None
    assert registration.adapter_compatible is None
    assert registration.executable is False
    assert (prepared.root / "tiny.h5ad").read_bytes() == (prepared.upload.directory / "payload").read_bytes()
    assert (
        chain.index.get_record(registration.pack_id, registration.pack_version)["pack_fingerprint"]
        == registration.pack_fingerprint
    )
    with pytest.raises(PackIndexError, match="controlled Pack Factory"):
        chain.index.register(prepared.root)

    for value in (
        candidate,
        chain.review,
        chain.report,
        chain.decision,
        registration,
    ):
        _assert_no_science_markers(value)
        assert type(value).from_dict(value.to_dict()) == value


def test_v03_multiomics_chain_preserves_modality_order_and_exact_h5mu_source(
    tmp_path,
):
    pytest.importorskip("mudata")
    from praxis_virtualcell.data_packs.mudata_adapter import load_mudata_view
    from praxis_virtualcell.tests.test_mudata_alignment import _write_pack

    root = tmp_path / "multiomics"
    root.mkdir()
    pack_root = _write_pack(root / "candidate")
    manifest_path = pack_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["pack_id"] = "p19-human-rna-protein-synthetic"
    manifest["pack_version"] = "1.0.0"
    modality_keys = tuple(item["key"] for item in manifest["multiomics"]["modalities"])
    assert modality_keys == ("rna", "protein")
    assert modality_keys != tuple(sorted(modality_keys))

    with load_mudata_view(pack_root) as view:
        actual_features = {key: list(view.modality(key).feature_ids) for key in modality_keys}

    mapping_asset_ids = {}
    for modality in manifest["multiomics"]["modalities"]:
        key = modality["key"]
        asset_id = f"{key}-p19-identity-map"
        mapping_asset_ids[key] = asset_id
        namespace = {
            "schema_version": "vc.pack-factory-mapping-namespace.v1",
            **modality["feature_namespace"],
        }
        mapping = {
            "schema_version": "vc.pack-factory-feature-mapping.v1",
            "mapping_id": asset_id,
            "mapping_version": "1.0.0",
            "modality_key": key,
            "source_namespace": namespace,
            "target_namespace": namespace,
            "source_feature_ids": actual_features[key],
            "target_feature_ids": actual_features[key],
            "mappings": [],
        }
        mapping_bytes = json.dumps(
            mapping,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        mapping_path = pack_root / f"{asset_id}.json"
        mapping_path.write_bytes(mapping_bytes)
        manifest["assets"].append(
            {
                "id": asset_id,
                "path": mapping_path.name,
                "media_type": "application/json",
                "sha256": _sha256(mapping_bytes),
                "size_bytes": len(mapping_bytes),
            }
        )
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    payload = (pack_root / "tiny.h5mu").read_bytes()
    upload = load_quarantined_upload(
        _write_exact_p7_upload(
            root,
            payload,
            index=40,
            filename="tiny.h5mu",
            declared_content_type="application/vnd.mudata+hdf5",
        )
    )
    authoring = {
        "mapping_asset_ids": mapping_asset_ids,
        "value_semantics": {
            "rna": "raw_counts",
            "protein": "raw_abundance",
        },
        "units": {"dose_units": ["1"], "time_units": ["h"]},
        "claim_origins": {topic: "inferred_candidate" for topic in REQUIRED_REVIEW_TOPICS},
    }
    with pytest.raises(
        PackFactoryError,
        match="actual matrix or multiomics data asset",
    ):
        prepare_pack_candidate(
            upload,
            pack_root,
            source_asset_id="rna-mapping",
            **authoring,
        )

    prepared = prepare_pack_candidate(
        upload,
        pack_root,
        source_asset_id="multiomics",
        **authoring,
    )
    review = _review(prepared)
    report = validate_pack_candidate(prepared, review)
    decision = _decision(prepared, review, report)
    index = PackIndex(
        index_path=(root / "pack-index.json").resolve(),
        include_builtins=False,
    )
    store = PackFactoryStore.create((root / "factory-store").resolve())

    assert store.record_upload(upload) == upload.receipt.fingerprint()
    assert store.record_candidate(prepared) == prepared.candidate.fingerprint()
    assert store.get(PackCandidateV1, prepared.candidate.fingerprint()) == prepared.candidate
    registration = register_pack_candidate(
        prepared,
        review,
        report,
        decision,
        index=index,
        store=store,
    )

    mappings = prepared.candidate.feature_mappings
    assert tuple(item.modality_key for item in mappings) == modality_keys
    assert [(item.source_feature_count, item.target_feature_count) for item in mappings] == [
        (5, 5),
        (2, 2),
    ]
    assert all(item.order_preserved for item in mappings)
    assert all(item.transformation_policy == "identity_only_no_transform" for item in mappings)
    assert all(
        not any(
            (
                item.duplicate_source_feature_ids,
                item.duplicate_target_feature_ids,
                item.duplicate_mapping_sources,
                item.duplicate_mapping_targets,
                item.out_of_domain_mapping_sources,
                item.out_of_domain_mapping_targets,
                item.unmapped_source_feature_ids,
                item.unmapped_target_feature_ids,
            )
        )
        for item in mappings
    )
    assert prepared.candidate.manifest_schema_version == "vc.pack.v0.3"
    assert prepared.candidate.source_asset_id == "multiomics"
    assert report.passed is report.pack_valid is report.registration_allowed is True
    assert next(check for check in report.checks if check.code == "no_forbidden_transformations").passed is True
    assert store.list(PackCandidateV1) == (prepared.candidate,)
    assert store.list(FactoryRegisteredPackV1) == (registration,)
    assert (
        index.factory_registration_fingerprint(
            registration.pack_id,
            registration.pack_version,
        )
        == registration.fingerprint()
    )
    _assert_no_science_markers(prepared.candidate)
    _assert_no_science_markers(report)
    _assert_no_science_markers(registration)


def test_review_requires_every_exact_confirmation_and_never_implicitly_approves(tmp_path):
    prepared = _prepare(tmp_path / "review")
    review = _review(prepared)
    raw = review.to_dict()

    for topic in REQUIRED_REVIEW_TOPICS:
        missing = dict(raw)
        missing["confirmations"] = [item for item in raw["confirmations"] if item["topic"] != topic]
        with pytest.raises(PackFactoryError, match="every topic"):
            PackMetadataReviewV1.from_dict(missing)

    wrong = review.model_copy(
        update={
            "confirmations": (
                review.confirmations[0].model_copy(update={"claim_fingerprint": "f" * 64}),
                *review.confirmations[1:],
            )
        }
    )
    with pytest.raises(PackFactoryError, match="does not bind candidate claim"):
        validate_metadata_review(prepared, wrong)

    rejected = PackMetadataReviewV1.from_dict(
        {
            **raw,
            "decision": "reject",
            "confirmations": [],
        }
    )
    report = validate_pack_candidate(prepared, rejected)
    assert report.passed is False
    assert "explicit_metadata_review" in report.errors


def test_unused_declared_upload_asset_cannot_masquerade_as_the_matrix_source(tmp_path):
    root = tmp_path / "unused-source"
    root.mkdir()
    pack_root = _write_candidate_root(root / "candidate")
    payload = (pack_root / "tiny.h5ad").read_bytes()
    unused_path = pack_root / "unused-upload.h5ad"
    unused_path.write_bytes(payload)
    manifest_path = pack_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"].append(
        {
            "id": "unused-upload",
            "path": unused_path.name,
            "media_type": "application/vnd.anndata+hdf5",
            "sha256": _sha256(payload),
            "size_bytes": len(payload),
        }
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    upload = load_quarantined_upload(_write_exact_p7_upload(root, payload, index=30))

    with pytest.raises(PackFactoryError, match="actual matrix or multiomics data asset"):
        prepare_pack_candidate(
            upload,
            pack_root,
            source_asset_id="unused-upload",
            mapping_asset_ids={"primary": "primary-identity-map"},
            value_semantics={"primary": "raw_counts"},
            units={"dose_units": ["1"], "time_units": ["h"]},
            claim_origins={topic: "inferred_candidate" for topic in REQUIRED_REVIEW_TOPICS},
        )


@pytest.mark.parametrize(
    "tampered_field",
    [
        "receipt_fingerprint",
        "receipt_bytes_sha256",
        "upload_id",
        "source_payload_sha256",
        "source_payload_size_bytes",
        "complete_tuple",
    ],
)
def test_candidate_must_bind_every_member_of_the_complete_receipt_tuple(
    tmp_path,
    tampered_field,
):
    prepared = _prepare(tmp_path / "receipt-tuple", index=31)
    replacements = {
        "receipt_fingerprint": "f" * 64,
        "receipt_bytes_sha256": "e" * 64,
        "upload_id": _uuid4(99),
        "source_payload_sha256": "d" * 64,
        "source_payload_size_bytes": prepared.candidate.source_payload_size_bytes + 1,
    }
    update = replacements if tampered_field == "complete_tuple" else {tampered_field: replacements[tampered_field]}
    candidate = prepared.candidate.model_copy(update=update)

    with pytest.raises(PackFactoryError, match="exact supplied upload identity"):
        bind_pack_candidate(prepared.upload, prepared.root, candidate)


def test_registration_requires_explicit_absolute_index_and_store(tmp_path):
    chain = _chain(tmp_path / "explicit-dependencies", register=False)
    ordinary_directory = (tmp_path / "ordinary-existing-directory").resolve()
    ordinary_directory.mkdir()
    with pytest.raises(PackFactoryError, match="write-new directory"):
        PackFactoryStore.open(ordinary_directory)
    with pytest.raises(PackFactoryError, match="write-new"):
        PackFactoryStore.create(ordinary_directory)

    with pytest.raises(PackFactoryError, match="explicitly injected exact PackIndex"):
        register_pack_candidate(
            chain.prepared,
            chain.review,
            chain.report,
            chain.decision,
            index=None,
            store=chain.store,
        )
    with pytest.raises(PackFactoryError, match="explicit absolute index"):
        register_pack_candidate(
            chain.prepared,
            chain.review,
            chain.report,
            chain.decision,
            index=PackIndex(include_builtins=False),
            store=chain.store,
        )
    with pytest.raises(PackFactoryError, match="explicitly injected exact PackFactoryStore"):
        register_pack_candidate(
            chain.prepared,
            chain.review,
            chain.report,
            chain.decision,
            index=chain.index,
            store=None,
        )
    assert chain.index.list_records() == []
    assert factory_catalog_payload(chain.store)["registration_count"] == 0


def test_stage_skip_report_and_decision_tampering_fail_before_index_write(tmp_path):
    chain = _chain(tmp_path / "stages", register=False)
    with pytest.raises(PackFactoryError, match="require runtime verification"):
        chain.store.record(chain.prepared.candidate)

    invalid_report = chain.report.model_copy(update={"passed": False})
    with pytest.raises(PackFactoryError, match="validation report"):
        register_pack_candidate(
            chain.prepared,
            chain.review,
            invalid_report,
            chain.decision,
            index=chain.index,
            store=chain.store,
        )

    wrong_decision = chain.decision.model_copy(update={"candidate_fingerprint": "f" * 64})
    with pytest.raises(PackFactoryError, match="does not bind"):
        validate_operator_decision(
            chain.prepared.candidate,
            chain.review,
            chain.report,
            wrong_decision,
        )

    rejected = _decision(
        chain.prepared,
        chain.review,
        chain.report,
        decision="reject",
    )
    with pytest.raises(PackFactoryError, match="did not approve"):
        register_pack_candidate(
            chain.prepared,
            chain.review,
            chain.report,
            rejected,
            index=chain.index,
            store=chain.store,
        )

    tampered_candidate = chain.prepared.candidate.model_copy(update={"source_payload_sha256": "f" * 64})
    tampered_prepared = replace(chain.prepared, candidate=tampered_candidate)
    with pytest.raises(PackFactoryError, match="exact supplied upload identity"):
        register_pack_candidate(
            tampered_prepared,
            chain.review,
            chain.report,
            chain.decision,
            index=chain.index,
            store=chain.store,
        )
    assert chain.index.list_records() == []


def test_source_and_candidate_tree_tamper_are_retained_as_failures(tmp_path):
    chain = _chain(tmp_path / "tamper", register=False)
    payload_path = chain.prepared.upload.directory / "payload"
    original = payload_path.read_bytes()
    payload_path.write_bytes(original + b"tampered")

    receipt_report = validate_pack_candidate(chain.prepared, chain.review)
    assert {"receipt_bytes_immutable", "source_payload_binding"} <= _failed_codes(receipt_report)
    invalid_approval = _decision(chain.prepared, chain.review, receipt_report)
    with pytest.raises(PackFactoryError, match="cannot approve"):
        validate_operator_decision(
            chain.prepared.candidate,
            chain.review,
            receipt_report,
            invalid_approval,
        )
    with pytest.raises(PackFactoryError, match="immutable receipt"):
        register_pack_candidate(
            chain.prepared,
            chain.review,
            chain.report,
            chain.decision,
            index=chain.index,
            store=chain.store,
        )
    assert chain.index.list_records() == []

    payload_path.write_bytes(original)
    (chain.prepared.root / "undeclared.txt").write_text("not declared\n", encoding="utf-8")
    tree_report = validate_pack_candidate(chain.prepared, chain.review)
    assert {"candidate_tree_immutable", "declared_files_only"} <= _failed_codes(tree_report)
    assert tree_report.pack_valid is True
    assert tree_report.registration_allowed is False


def test_mapping_duplicates_order_namespace_and_hash_drift_fail_closed(tmp_path):
    cases = (
        (
            "duplicate-source",
            lambda value: value["source_feature_ids"].__setitem__(1, _FEATURE_IDS[0]),
            "duplicate_source_feature_ids",
        ),
        (
            "reordered-target",
            lambda value: value["target_feature_ids"].reverse(),
            "order_preserved",
        ),
        (
            "namespace-drift",
            lambda value: value["target_namespace"].update(version="GRCh37"),
            "unmapped_source_feature_ids",
        ),
        (
            "out-of-domain-rule",
            lambda value: value["mappings"].append(
                {
                    "schema_version": "vc.pack-factory-feature-map-entry.v1",
                    "source": "ENSG99999999998",
                    "target": "ENSG99999999999",
                }
            ),
            "out_of_domain_mapping_sources",
        ),
    )
    for number, (name, mutate, issue) in enumerate(cases, start=10):
        prepared = _prepare(
            tmp_path / name,
            index=number,
            mapping_update=mutate,
        )
        summary = prepared.candidate.feature_mappings[0]
        observed = getattr(summary, issue)
        assert observed is False if issue == "order_preserved" else bool(observed)
        if name == "out-of-domain-rule":
            assert summary.out_of_domain_mapping_targets == ("ENSG99999999999",)
        report = validate_pack_candidate(prepared, _review(prepared))
        assert {"feature_mapping_binding", "no_forbidden_transformations"} <= (_failed_codes(report))
        assert report.pack_valid is True
        assert report.registration_allowed is False

    valid = _prepare(tmp_path / "hash-drift", index=20)
    mapping_path = valid.root / "identity-mapping.json"
    mapping_path.write_bytes(mapping_path.read_bytes() + b"\n")
    with pytest.raises(PackFactoryError, match="mapping asset"):
        prepare_pack_candidate(
            valid.upload,
            valid.root,
            source_asset_id="expression",
            mapping_asset_ids={"primary": "primary-identity-map"},
            value_semantics={"primary": "raw_counts"},
            units={"dose_units": ["1"], "time_units": ["h"]},
            claim_origins={topic: "operator_declared" for topic in REQUIRED_REVIEW_TOPICS},
        )


def test_generic_record_cannot_persist_forged_all_green_derived_truth(tmp_path):
    chain = _chain(tmp_path / "verified-chain")
    generic_store = PackFactoryStore.create((tmp_path / "generic-store").resolve())
    forged_report = chain.report.model_copy(update={"candidate_fingerprint": "f" * 64})
    forged_registration = chain.registration.model_copy(update={"operator_id": "forged:operator"})

    assert forged_report.passed is True
    assert all(check.passed for check in forged_report.checks)
    for forged in (forged_report, forged_registration):
        with pytest.raises(PackFactoryError, match="require runtime verification"):
            generic_store.record(forged)

    catalog = factory_catalog_payload(generic_store)
    assert catalog["validation_count"] == 0
    assert catalog["registration_count"] == 0


def test_store_catalog_and_supersession_are_append_only_and_root_free(tmp_path):
    index = PackIndex(
        index_path=(tmp_path / "pack-index.json").resolve(),
        include_builtins=False,
    )
    store = PackFactoryStore.create((tmp_path / "store").resolve())
    first = _chain(
        tmp_path / "first",
        index_number=1,
        version="1.0.0",
        pack_index=index,
        factory_store=store,
    )
    replacement = _chain(
        tmp_path / "replacement",
        index_number=2,
        version="1.1.0",
        pack_index=index,
        factory_store=store,
    )
    original_registration = first.registration.to_dict()

    supersession = declare_pack_supersession(
        first.registration,
        replacement.registration,
        operator_id="test:pack-registration-operator",
        decided_at="2026-08-06T03:00:00Z",
        reason="contract-only replacement fixture",
    )
    assert store.record(supersession) == supersession.fingerprint()
    assert store.record(supersession) == supersession.fingerprint()
    assert first.registration.to_dict() == original_registration

    catalog = factory_catalog_payload(store)
    rendered = json.dumps(catalog, sort_keys=True)
    assert catalog["configured"] is True
    assert catalog["write_api_enabled"] is False
    assert len(catalog["receipts"]) == 2
    assert len(catalog["candidates"]) == 2
    assert len(catalog["reviews"]) == 2
    assert len(catalog["validations"]) == 2
    assert len(catalog["decisions"]) == 2
    assert len(catalog["registrations"]) == 2
    assert len(catalog["supersessions"]) == 1
    assert all(item["reviewed"] for item in catalog["candidates"])
    assert all(item["validation_passed"] for item in catalog["candidates"])
    assert all(item["factory_registered"] for item in catalog["candidates"])
    old = next(item for item in catalog["registrations"] if item["pack_version"] == "1.0.0")
    assert old["superseded_by"] == replacement.registration.fingerprint()
    assert str(tmp_path) not in rendered
    assert "test:metadata-reviewer" not in rendered
    assert "all candidate claims checked" not in rendered
    assert "test:pack-registration-operator" not in rendered
    assert "contract-only registration fixture" not in rendered
    assert "contract-only replacement fixture" not in rendered
    assert {
        "operator_id",
        "reviewer_id",
        "rationale",
        "reason",
        "root",
        "directory",
    }.isdisjoint(_nested_keys(catalog))
    _assert_no_science_markers(catalog)

    reverse = declare_pack_supersession(
        replacement.registration,
        first.registration,
        operator_id="test:pack-registration-operator",
        decided_at="2026-08-06T03:00:01Z",
        reason="must be rejected as a cycle",
    )
    with pytest.raises(PackFactoryError, match="cycle"):
        store.record(reverse)


def test_registration_provenance_rejects_a_second_decision_for_the_same_pack_identity(
    tmp_path,
):
    chain = _chain(tmp_path / "identity", register=False)
    changed = chain.decision.model_copy(
        update={
            "operator_id": "test:second-pack-registration-operator",
            "reason": "same Pack, distinct explicit registration decision",
        }
    )
    validate_operator_decision(
        chain.prepared.candidate,
        chain.review,
        chain.report,
        changed,
    )
    first = register_pack_candidate(
        chain.prepared,
        chain.review,
        chain.report,
        chain.decision,
        index=chain.index,
        store=chain.store,
    )
    with pytest.raises(PackFactoryError, match="controlled Pack index registration failed"):
        register_pack_candidate(
            chain.prepared,
            chain.review,
            chain.report,
            changed,
            index=chain.index,
            store=chain.store,
        )

    assert chain.index.factory_registration_fingerprint(first.pack_id, first.pack_version) == first.fingerprint()
    assert {value.fingerprint() for value in chain.store.list(PackOperatorDecisionV1)} == {
        chain.decision.fingerprint(),
        changed.fingerprint(),
    }
    assert chain.store.list(FactoryRegisteredPackV1) == (first,)
    assert len(chain.index.list_records()) == 1


@pytest.mark.parametrize(
    "model",
    [
        PackCandidateV1,
        PackMetadataReviewV1,
        PackOperatorDecisionV1,
        FactoryRegisteredPackV1,
        PackSupersessionV1,
    ],
)
def test_contracts_reject_unknown_fields(model):
    with pytest.raises(PackFactoryError):
        model.from_dict({"schema_version": "wrong", "unexpected": True})


def test_cli_register_requires_explicit_paths_and_commits_exact_chain(
    tmp_path,
    capsys,
):
    from praxis_virtualcell.cli import main

    chain = _chain(
        tmp_path / "cli",
        pack_id="p19-cli-synthetic",
        register=False,
    )
    contract_files = {
        "--candidate": _write_contract(
            tmp_path / "candidate.json",
            chain.prepared.candidate,
        ),
        "--review": _write_contract(tmp_path / "review.json", chain.review),
        "--validation": _write_contract(
            tmp_path / "validation.json",
            chain.report,
        ),
        "--decision": _write_contract(
            tmp_path / "decision.json",
            chain.decision,
        ),
    }
    args = [
        "pack",
        "register",
        "--upload-directory",
        str(chain.prepared.upload.directory),
        "--pack-root",
        str(chain.prepared.root),
        *(item for flag, path in contract_files.items() for item in (flag, str(path.resolve()))),
        "--index",
        str(chain.index.path),
        "--store",
        str(chain.store.root),
    ]

    for required_path in ("--index", "--store"):
        missing = list(args)
        position = missing.index(required_path)
        del missing[position : position + 2]
        with pytest.raises(SystemExit) as exc_info:
            main(missing)
        assert exc_info.value.code == 2
        assert not chain.index.path.exists()
        assert factory_catalog_payload(chain.store)["registration_count"] == 0

    capsys.readouterr()
    assert main(args) == 0
    output = json.loads(capsys.readouterr().out)
    registration = chain.store.list(FactoryRegisteredPackV1)[0]
    assert output["registration_fingerprint"] == registration.fingerprint()

    committed = PackIndex(
        index_path=chain.index.path,
        include_builtins=False,
    )
    record = committed.get_record(
        registration.pack_id,
        registration.pack_version,
    )
    assert record["pack_fingerprint"] == registration.pack_fingerprint
    assert (
        committed.factory_registration_fingerprint(
            registration.pack_id,
            registration.pack_version,
        )
        == registration.fingerprint()
    )
    catalog = factory_catalog_payload(chain.store)
    assert catalog["registration_count"] == 1
    assert len(catalog["receipts"]) == len(catalog["candidates"]) == 1
    assert len(catalog["reviews"]) == len(catalog["validations"]) == 1
    assert len(catalog["decisions"]) == len(catalog["registrations"]) == 1


def test_cli_factory_init_records_a_real_quarantine_receipt(tmp_path, capsys):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    upload_root = _write_exact_p7_upload(data_root, b"exact-omics-bytes", index=40)
    upload = load_quarantined_upload(upload_root)
    store_root = (tmp_path / "factory-store").resolve()
    args = _factory_init_args(data_root, upload.receipt.upload_id, store_root)
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out) == {
        "schema_version": "vc.pack-factory-init.v1",
        "status": "receipt_recorded",
        "upload_id": upload.receipt.upload_id,
        "receipt_fingerprint": upload.receipt.fingerprint(),
        "store_root": str(store_root),
        "candidate_created": False,
        "factory_registered": False,
        "scientifically_validated": False,
        "executable": False,
    }
    store = PackFactoryStore.open(store_root)
    assert store.get(UploadReceiptV1, upload.receipt.fingerprint()) == upload.receipt

    with pytest.raises(PackFactoryError, match="write-new"):
        main(args)


@pytest.mark.parametrize(
    "upload_id",
    ["../00000000-0000-4000-8000-000000000040", "00000000-0000-1000-8000-000000000040"],
)
def test_cli_factory_init_rejects_traversal_and_non_v4_ids(tmp_path, upload_id):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    _write_exact_p7_upload(data_root, b"exact-omics-bytes", index=40)
    store_root = (tmp_path / f"store-{len(upload_id)}").resolve()

    with pytest.raises(PackFactoryError, match="canonical UUIDv4"):
        main(_factory_init_args(data_root, upload_id, store_root))
    assert not store_root.exists()


@pytest.mark.parametrize("symlink_level", ["data-root", "uploads", "quarantine"])
def test_cli_factory_init_rejects_symlinked_roots(tmp_path, symlink_level):
    from praxis_virtualcell.cli import main

    real_data_root = (tmp_path / "real-data").resolve()
    upload_root = _write_exact_p7_upload(real_data_root, b"exact-omics-bytes", index=41)
    data_root = real_data_root
    if symlink_level == "data-root":
        data_root = tmp_path / "linked-data"
        data_root.symlink_to(real_data_root, target_is_directory=True)
    elif symlink_level == "uploads":
        data_root = (tmp_path / "data").resolve()
        data_root.mkdir()
        (data_root / "uploads").symlink_to(real_data_root / "uploads", target_is_directory=True)
    else:
        data_root = (tmp_path / "data").resolve()
        (data_root / "uploads").mkdir(parents=True)
        (data_root / "uploads" / "quarantine").symlink_to(
            real_data_root / "uploads" / "quarantine",
            target_is_directory=True,
        )
    store_root = (tmp_path / f"store-{symlink_level}").resolve()

    with pytest.raises(PackFactoryError, match="canonical real|non-symlink"):
        main(_factory_init_args(data_root, upload_root.name, store_root))
    assert not store_root.exists()


def test_cli_factory_init_rejects_tampering_before_store_creation(tmp_path):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    upload_root = _write_exact_p7_upload(data_root, b"exact-omics-bytes", index=42)
    (upload_root / "payload").write_bytes(b"tampered")
    store_root = (tmp_path / "factory-store").resolve()

    with pytest.raises(PackFactoryError, match="immutable receipt"):
        main(_factory_init_args(data_root, upload_root.name, store_root))
    assert not store_root.exists()


def test_cli_factory_init_rejects_store_inside_uploads(tmp_path):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    upload_root = _write_exact_p7_upload(data_root, b"exact-omics-bytes", index=43)
    store_root = upload_root / "factory-store"

    with pytest.raises(PackFactoryError, match="outside the data-root uploads subtree"):
        main(_factory_init_args(data_root, upload_root.name, store_root))
    assert not store_root.exists()


def test_cli_candidate_prepare_records_exact_unvalidated_candidate(tmp_path, capsys):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    pack_root = _write_candidate_root((tmp_path / "candidate-pack").resolve())
    upload_root = _write_exact_p7_upload(
        data_root,
        (pack_root / "tiny.h5ad").read_bytes(),
        index=44,
    )
    store_root = (tmp_path / "factory-store").resolve()
    assert main(_factory_init_args(data_root, upload_root.name, store_root)) == 0
    capsys.readouterr()
    authoring_path = (tmp_path / "candidate-authoring.json").resolve()
    authoring_path.write_text(json.dumps(_candidate_authoring()), encoding="utf-8")

    assert (
        main(
            [
                "pack",
                "candidate-prepare",
                "--data-root",
                str(data_root),
                "--upload-id",
                upload_root.name,
                "--store",
                str(store_root),
                "--pack-root",
                str(pack_root),
                "--authoring",
                str(authoring_path),
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    candidate = PackFactoryStore.open(store_root).get(
        PackCandidateV1,
        output["candidate_fingerprint"],
    )
    assert output == {
        "schema_version": "vc.pack-candidate-prepare-result.v1",
        "status": "candidate_unvalidated",
        "upload_id": upload_root.name,
        "receipt_fingerprint": candidate.receipt_fingerprint,
        "candidate_fingerprint": candidate.fingerprint(),
        "candidate_path": str(store_root / "candidates" / f"{candidate.fingerprint()}.json"),
        "pack_valid": None,
        "review_created": False,
        "validation_performed": False,
        "factory_registered": False,
        "model_compatible": None,
        "scientifically_validated": False,
        "executable": False,
    }
    assert candidate.status == "candidate_unvalidated"
    assert candidate.source_payload_sha256 == _sha256((pack_root / "tiny.h5ad").read_bytes())


def test_cli_candidate_prepare_requires_recorded_receipt_and_strict_authoring(tmp_path):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    pack_root = _write_candidate_root((tmp_path / "candidate-pack").resolve())
    upload_root = _write_exact_p7_upload(
        data_root,
        (pack_root / "tiny.h5ad").read_bytes(),
        index=45,
    )
    store = PackFactoryStore.create((tmp_path / "factory-store").resolve())
    authoring_path = (tmp_path / "candidate-authoring.json").resolve()
    authoring_path.write_text(json.dumps(_candidate_authoring()), encoding="utf-8")
    args = [
        "pack",
        "candidate-prepare",
        "--data-root",
        str(data_root),
        "--upload-id",
        upload_root.name,
        "--store",
        str(store.root),
        "--pack-root",
        str(pack_root),
        "--authoring",
        str(authoring_path),
    ]

    with pytest.raises(PackFactoryError, match="does not exist"):
        main(args)
    assert store.list(PackCandidateV1) == ()

    upload = load_quarantined_upload(upload_root)
    store.record_upload(upload)
    authoring_path.write_text(
        '{"schema_version":"vc.pack-candidate-authoring.v1","schema_version":"vc.pack-candidate-authoring.v1"}',
        encoding="utf-8",
    )
    with pytest.raises(PackFactoryError, match="invalid candidate authoring JSON"):
        main(args)
    assert store.list(PackCandidateV1) == ()


def test_cli_candidate_validate_records_review_and_strict_report(tmp_path, capsys):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    prepared = _prepare(data_root, index=46, pack_id="p19-cli-flow")
    store = PackFactoryStore.create((tmp_path / "factory-store").resolve())
    store.record_upload(prepared.upload)
    candidate_fingerprint = store.record_candidate(prepared)
    candidate_path = store.root / "candidates" / f"{candidate_fingerprint}.json"
    review_path = _write_contract(
        (tmp_path / "metadata-review.json").resolve(),
        _review(prepared),
    )

    assert (
        main(
            [
                "pack",
                "candidate-validate",
                "--data-root",
                str(data_root),
                "--upload-id",
                prepared.upload.receipt.upload_id,
                "--store",
                str(store.root),
                "--pack-root",
                str(prepared.root),
                "--candidate",
                str(candidate_path),
                "--review",
                str(review_path),
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    review = store.get(PackMetadataReviewV1, output["review_fingerprint"])
    report = store.get(
        PackValidationReportV1,
        output["validation_report_fingerprint"],
    )
    assert output == {
        "schema_version": "vc.pack-candidate-validate-result.v1",
        "status": "validated",
        "candidate_fingerprint": candidate_fingerprint,
        "review_fingerprint": review.fingerprint(),
        "review_path": str(store.root / "reviews" / f"{review.fingerprint()}.json"),
        "validation_report_fingerprint": report.fingerprint(),
        "validation_path": str(store.root / "validations" / f"{report.fingerprint()}.json"),
        "pack_valid": True,
        "registration_allowed": True,
        "factory_registered": False,
        "model_compatible": None,
        "scientifically_validated": False,
        "executable": False,
    }
    decision_path = _write_contract(
        (tmp_path / "registration-decision.json").resolve(),
        _decision(prepared, review, report),
    )
    capsys.readouterr()
    assert (
        main(
            [
                "pack",
                "register",
                "--upload-directory",
                str(prepared.upload.directory),
                "--pack-root",
                str(prepared.root),
                "--candidate",
                str(candidate_path),
                "--review",
                output["review_path"],
                "--validation",
                output["validation_path"],
                "--decision",
                str(decision_path),
                "--index",
                str((tmp_path / "pack-index.json").resolve()),
                "--store",
                str(store.root),
            ]
        )
        == 0
    )
    registered = json.loads(capsys.readouterr().out)
    assert registered["factory_registered"] is True
    assert registered["scientifically_validated"] is False
    assert registered["executable"] is False


def test_cli_candidate_validate_rejects_review_for_another_candidate(tmp_path):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    prepared = _prepare(data_root, index=47)
    other = _prepare((tmp_path / "other").resolve(), index=48, version="1.0.1")
    store = PackFactoryStore.create((tmp_path / "factory-store").resolve())
    store.record_upload(prepared.upload)
    candidate_fingerprint = store.record_candidate(prepared)
    review_path = _write_contract(
        (tmp_path / "wrong-review.json").resolve(),
        _review(other),
    )

    with pytest.raises(PackFactoryError, match="does not bind the exact candidate"):
        main(
            [
                "pack",
                "candidate-validate",
                "--data-root",
                str(data_root),
                "--upload-id",
                prepared.upload.receipt.upload_id,
                "--store",
                str(store.root),
                "--pack-root",
                str(prepared.root),
                "--candidate",
                str(store.root / "candidates" / f"{candidate_fingerprint}.json"),
                "--review",
                str(review_path),
            ]
        )
    assert store.list(PackMetadataReviewV1) == ()
    assert store.list(PackValidationReportV1) == ()


def test_cli_candidate_validate_requires_complete_stored_receipt_chain(tmp_path):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    prepared = _prepare(data_root, index=49, pack_id="p19-missing-receipt")
    store = PackFactoryStore.create((tmp_path / "factory-store").resolve())
    receipt_fingerprint = store.record_upload(prepared.upload)
    candidate_fingerprint = store.record_candidate(prepared)
    (store.root / "receipts" / f"{receipt_fingerprint}.json").unlink()
    review_path = _write_contract(
        (tmp_path / "metadata-review.json").resolve(),
        _review(prepared),
    )

    with pytest.raises(PackFactoryError, match="does not exist"):
        main(
            [
                "pack",
                "candidate-validate",
                "--data-root",
                str(data_root),
                "--upload-id",
                prepared.upload.receipt.upload_id,
                "--store",
                str(store.root),
                "--pack-root",
                str(prepared.root),
                "--candidate",
                str(store.root / "candidates" / f"{candidate_fingerprint}.json"),
                "--review",
                str(review_path),
            ]
        )
    assert store.list(PackMetadataReviewV1) == ()
    assert store.list(PackValidationReportV1) == ()


def test_cli_candidate_validate_records_pack_tree_drift_as_failed_report(tmp_path, capsys):
    from praxis_virtualcell.cli import main

    data_root = (tmp_path / "data").resolve()
    prepared = _prepare(data_root, index=50, pack_id="p19-drifted-candidate")
    store = PackFactoryStore.create((tmp_path / "factory-store").resolve())
    store.record_upload(prepared.upload)
    candidate_fingerprint = store.record_candidate(prepared)
    review_path = _write_contract(
        (tmp_path / "metadata-review.json").resolve(),
        _review(prepared),
    )
    (prepared.root / "undeclared-empty-file").touch()

    assert (
        main(
            [
                "pack",
                "candidate-validate",
                "--data-root",
                str(data_root),
                "--upload-id",
                prepared.upload.receipt.upload_id,
                "--store",
                str(store.root),
                "--pack-root",
                str(prepared.root),
                "--candidate",
                str(store.root / "candidates" / f"{candidate_fingerprint}.json"),
                "--review",
                str(review_path),
            ]
        )
        == 2
    )
    output = json.loads(capsys.readouterr().out)
    report = store.get(
        PackValidationReportV1,
        output["validation_report_fingerprint"],
    )
    assert output["status"] == "validation_failed"
    assert report.pack_valid is True
    assert report.registration_allowed is False
    assert "candidate_tree_immutable" in report.errors


def test_pack_factory_http_surface_is_complete_and_read_only(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from praxis_vc_api.main import app

    chain = _chain(tmp_path / "api", pack_id="p19-api-synthetic")
    monkeypatch.setenv("PRAXIS_VC_PACK_FACTORY_STORE", str(chain.store.root))
    expected = factory_catalog_payload(chain.store)
    client = TestClient(app)

    response = client.get("/api/pack-factory")
    assert response.status_code == 200
    assert response.json() == expected
    assert expected["configured"] is True
    assert expected["write_api_enabled"] is False
    assert all(
        expected[layer]
        for layer in (
            "receipts",
            "candidates",
            "reviews",
            "validations",
            "decisions",
            "registrations",
        )
    )

    factory_routes = [route for route in app.routes if getattr(route, "path", "").startswith("/api/pack-factory")]
    assert factory_routes
    assert all("POST" not in getattr(route, "methods", set()) for route in factory_routes)
    assert client.post("/api/pack-factory", json={}).status_code in {404, 405}
    assert client.post("/api/pack-factory/register", json={}).status_code in {
        404,
        405,
    }
    assert factory_catalog_payload(chain.store) == expected
