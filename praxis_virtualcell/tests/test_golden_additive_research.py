"""First real Golden research release: identity and strict adapter boundaries."""

from __future__ import annotations

import importlib.resources
import json

import pytest

from praxis_virtualcell.data_packs.registry import (
    PackViewAssetV1,
    PackViewReceiptV1,
    PreparedPackViewV1,
)
from praxis_virtualcell.model_zoo.adapter_sdk import AdapterContractError
from praxis_virtualcell.model_zoo.capability_registry import CompatibilityReportV2
from praxis_virtualcell.model_zoo.golden_additive_research import (
    AHR,
    CONDITION_ID,
    FEATURE_IDS_SHA256,
    KLF1,
    MODEL_NAME,
    MODEL_VERSION,
    PACK_FINGERPRINT,
    GoldenAdditiveResearchAdapter,
    GoldenAdditiveResearchWrapper,
    _fingerprint,
    _release_pin,
    _research_card,
    golden_ahr_klf1_request,
    load_golden_additive_research,
)


def test_checked_in_research_release_pin_closes_real_identifiers() -> None:
    pin = _release_pin()
    card = _research_card()

    assert pin["registry_fingerprint"] == ("734379d961534771a1be2002cdf55a00aabf5d5b773f806629919c4f9da86a2f")
    assert pin["model_name"] == card.name == MODEL_NAME
    assert pin["model_version"] == card.version == MODEL_VERSION
    assert pin["model_fingerprint"] == card.fingerprint()
    assert pin["pack_fingerprint"] == PACK_FINGERPRINT
    assert card.perturbation == ("gene_combination",)
    assert card.resources.python_dependencies == ("numpy", "yaml")
    assert len(pin["artifacts"]) == 3
    assert all(item["safe_load_policy"] == "data_only" for item in pin["artifacts"])
    assert pin["research_execution_authorized"] is True
    assert pin["research_execution_scope"] == "research_only"
    assert pin["benchmark_passed"] is False
    assert pin["scientifically_validated"] is False
    assert pin["promotion_eligible"] is False
    assert pin["production_promoted"] is False
    rendered = json.dumps(pin, sort_keys=True)
    for forbidden in ("/Volumes/", "/private/", "model_cache", "operator_id"):
        assert forbidden not in rendered


def test_research_release_binds_the_exact_three_artifact_snapshot_budget() -> None:
    from praxis_virtualcell.model_zoo.golden_additive_research import (
        _ARTIFACT_SNAPSHOT_BUDGET,
        _ARTIFACTS,
    )

    assert _ARTIFACT_SNAPSHOT_BUDGET == {
        "schema_version": "vc.artifact-snapshot-budget-policy.v1",
        "max_live_snapshot_payload_bytes": sum(item[1] for item in _ARTIFACTS.values()),
        "max_snapshot_entries_per_execution": 3,
        "retention_scope": "execution_only",
    }


def test_exact_ahr_klf1_request_uses_strict_crispra_combination_semantics() -> None:
    request = golden_ahr_klf1_request()

    assert request.perturbation.kind == "gene_combination"
    assert request.perturbation.targets == (AHR, KLF1)
    assert request.perturbation.dose_value == 1.0
    assert request.perturbation.dose_unit == "1"
    assert request.perturbation.timepoint == "5d"
    assert request.constraints == {
        "condition_id": CONDITION_ID,
        "partition": "test",
        "source_real_run_sha256": ("fe82a306ff2ecdb42d2da9abc5fb9007c9c46ecf1051734789da5afb0598f52d"),
        "execution_scope": "research_only",
    }
    assert request.cell_context.attributes["feature_ids_sha256"] == FEATURE_IDS_SHA256


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["perturbation"].update({"kind": "gene"}),
        lambda value: value["perturbation"].update({"targets": [KLF1, AHR]}),
        lambda value: value["perturbation"].update({"timepoint": "4d"}),
        lambda value: value["baseline_context"].update({"reference": "global_mean"}),
        lambda value: value["constraints"].update({"partition": "train"}),
        lambda value: value.update({"metadata": {"scientifically_validated": True}}),
    ],
)
def test_adapter_rejects_request_scope_drift_before_any_model_execution(mutation) -> None:
    request = golden_ahr_klf1_request()
    pin = _release_pin()
    assets = (
        PackViewAssetV1(
            asset_id="expression",
            media_type="application/vnd.anndata+hdf5",
            sha256="43da7aeeaca2a3ceb00ec6e9ee983b9b708b01f85922cc7afee229225a66792a",
            size_bytes=2285816806,
        ),
        PackViewAssetV1(
            asset_id="golden-contract",
            media_type="application/json",
            sha256="456242651b50a87f507c6e9787999d4fd325beec82106363c7261cbdaa744521",
            size_bytes=4663,
        ),
    )
    receipt = PackViewReceiptV1(
        schema_version="vc.prepared-pack-view-receipt.v1",
        pack_id="norman-2019-k562-golden",
        pack_version="1.0.0",
        pack_fingerprint=PACK_FINGERPRINT,
        taxonomy_id="NCBITaxon:9606",
        assembly_accession="GCA_000001405.15",
        assets=assets,
    )
    pack = PreparedPackViewV1(
        schema_version="vc.prepared-pack-view.v1",
        pack_id=receipt.pack_id,
        pack_version=receipt.pack_version,
        fingerprint=receipt.pack_fingerprint,
        taxonomy_id=receipt.taxonomy_id,
        assembly_accession=receipt.assembly_accession,
        assets=assets,
        receipt=receipt,
    )
    report = CompatibilityReportV2.from_dict(
        {
            "schema_version": "vc.compatibility-report.v2",
            "request_id": request.request_id,
            "request_fingerprint": _fingerprint(request.to_dict()),
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "model_fingerprint": pin["model_fingerprint"],
            "release_fingerprint": pin["release_fingerprint"],
            "capability_fingerprint": pin["capability_fingerprint"],
            "pack_id": receipt.pack_id,
            "pack_version": receipt.pack_version,
            "pack_fingerprint": PACK_FINGERPRINT,
            "environment_fingerprint": pin["environment_fingerprint"],
            "environment_snapshot_fingerprint": "1" * 64,
            "artifact_fingerprints": [item["fingerprint"] for item in pin["artifacts"]],
            "adapter_fingerprints": [pin["adapter_fingerprint"]],
            "evidence_fingerprints": [pin["evidence_fingerprint"]],
            "policy_fingerprint": pin["policy_fingerprint"],
            "cataloged": True,
            "artifact_ready": True,
            "revoked": False,
            "superseded_by": None,
            "pack_valid": True,
            "model_compatible": True,
            "environment_compatible": True,
            "adapter_compatible": True,
            "assets_ready": True,
            "wrapper_ready": True,
            "benchmark_passed": False,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "policy_present": True,
            "production_promoted": False,
            "research_execution_authorized": True,
            "research_execution_scope": "research_only",
            "executable": True,
            "checks": {},
            "reasons": [],
            "asset_paths": {},
        }
    )
    GoldenAdditiveResearchAdapter().prepare_input(
        request,
        pack=pack,
        compatibility_report=report,
    )
    value = request.to_dict()
    mutation(value)
    drifted = type(request).from_dict(value)
    with pytest.raises((AdapterContractError, TypeError, ValueError)):
        GoldenAdditiveResearchAdapter().prepare_input(
            drifted,
            pack=pack,
            compatibility_report=report,
        )


def test_research_definition_is_package_data() -> None:
    root = importlib.resources.files("praxis_virtualcell.model_zoo").joinpath("registrations")

    assert root.joinpath("golden_additive_source_card.yaml").is_file()
    assert root.joinpath("golden_additive_research_release.json").is_file()
    assert GoldenAdditiveResearchWrapper.artifact_snapshot_supported is True


def test_loader_rejects_an_incomplete_registration_file_set(tmp_path) -> None:
    registration = tmp_path / "registration"
    registration.mkdir()
    (registration / "unexpected.json").write_text("{}", encoding="utf-8")
    pack = tmp_path / "pack"
    cache = tmp_path / "cache"
    pack.mkdir()
    cache.mkdir()

    with pytest.raises(ValueError, match="environment-lock.json"):
        load_golden_additive_research(
            registration_root=registration,
            pack_root=pack,
            model_cache_root=cache,
        )
