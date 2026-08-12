"""Phase 8 contracts for the Norman/K562 Golden VirtualCellPack."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import anndata
import numpy as np
import pandas as pd
import pytest
from scipy import sparse

import praxis_virtualcell.benchmarks.golden_norman_run as golden_run
from praxis_virtualcell.benchmarks.golden_norman import (
    GoldenNormanError,
    build_baseline_assets,
    condition_macro_mse,
    derive_pack,
    evaluate_baselines,
    load_contract,
    paired_bootstrap_ci,
    predict_from_artifact,
    run_baseline_runtime,
)
from praxis_virtualcell.benchmarks.golden_norman_run import run_golden_condition
from praxis_virtualcell.data_packs.anndata_adapter import load_anndata_view
from praxis_virtualcell.data_packs.errors import PackAssetHashMismatch
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry

_CONTRACT = (
    Path(__file__).parents[2] / "data" / "golden" / "norman_2019" / "contract.yaml"
)
_CONTROL_GUIDES = {
    "train": "NegCtrl0_NegCtrl0__NegCtrl0_NegCtrl0",
    "validation": "NegCtrl10_NegCtrl0__NegCtrl10_NegCtrl0",
    "test": "NegCtrl11_NegCtrl0__NegCtrl11_NegCtrl0",
}
_FEATURES = (
    ("ENSG00000000001", "A"),
    ("ENSG00000000002", "B"),
    ("ENSG00000000003", "C"),
)


def _canonical_hash(value) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_source(root: Path) -> tuple[Path, dict]:
    root.mkdir()
    obs = pd.DataFrame(
        [
            ("cell-1", "ctrl", "train", _CONTROL_GUIDES["train"]),
            ("cell-2", "A+ctrl", "train", "A_guide"),
            ("cell-3", "B+ctrl", "train", "B_guide"),
            ("cell-4", "ctrl", "train", _CONTROL_GUIDES["validation"]),
            ("cell-5", "C+ctrl", "test", "C_guide"),
            ("cell-6", "ctrl", "train", _CONTROL_GUIDES["test"]),
            ("cell-7", "A+C", "ood", "A_C_guide"),
        ],
        columns=["observation", "condition", "split1", "guide_identity"],
    ).set_index("observation")
    obs["cell_type"] = "A549"
    var = pd.DataFrame(_FEATURES, columns=["id", "gene_name"]).set_index("id")
    matrix = np.asarray(
        [
            [1.0, 1.0, 1.0],
            [3.0, 1.0, 1.0],
            [1.0, 5.0, 1.0],
            [2.0, 2.0, 2.0],
            [2.0, 2.0, 5.0],
            [4.0, 4.0, 4.0],
            [7.0, 4.0, 6.0],
        ],
        dtype=np.float32,
    )
    source = root / "source.h5ad"
    adata = anndata.AnnData(
        X=sparse.csr_matrix(matrix),
        obs=obs,
        var=var,
        layers={"counts": matrix.astype(np.int32)},
    )
    adata.write_h5ad(source)

    source_conditions = obs["condition"].tolist()
    source_splits = obs["split1"].tolist()
    source_guides = obs["guide_identity"].tolist()
    feature_ids = [item[0] for item in _FEATURES]
    feature_symbols = [item[1] for item in _FEATURES]
    golden_splits = [
        "train",
        "train",
        "train",
        "validation",
        "validation",
        "test",
        "test",
    ]
    golden_conditions = [
        "norman.control.train",
        "A+ctrl",
        "B+ctrl",
        "norman.control.validation",
        "C+ctrl",
        "norman.control.test",
        "A+C",
    ]
    matched_controls = [
        "norman.control.train",
        "norman.control.train",
        "norman.control.train",
        "norman.control.validation",
        "norman.control.validation",
        "norman.control.test",
        "norman.control.test",
    ]
    contract = {
        "schema_version": "vc.golden-norman.v1",
        "benchmark_id": "norman-2019-k562-golden",
        "pack_version": "1.0.0",
        "source": {
            "dataset_doi": "fixture:test-only",
            "datafile_id": 1,
            "archive": {
                "filename": "fixture.zip",
                "size_bytes": 1,
                "sha256": "0" * 64,
            },
            "h5ad": {
                "filename": source.name,
                "size_bytes": source.stat().st_size,
                "sha256": _file_hash(source),
                "shape": [7, 3],
                "observation_ids_sha256": _canonical_hash(obs.index.tolist()),
                "feature_ids_sha256": _canonical_hash(feature_ids),
                "feature_symbols_sha256": _canonical_hash(feature_symbols),
                "condition_by_observation_sha256": _canonical_hash(
                    source_conditions
                ),
                "split_by_observation_sha256": _canonical_hash(source_splits),
                "guide_by_observation_sha256": _canonical_hash(source_guides),
            },
            "fields": {
                "condition": "condition",
                "split": "split1",
                "guide": "guide_identity",
                "source_cell_type": "cell_type",
                "feature_symbol": "gene_name",
                "counts_layer": "counts",
            },
        },
        "biology": {
            "taxon": {
                "ontology_id": "NCBITaxon:9606",
                "scientific_name": "Homo sapiens",
            },
            "assembly": {
                "name": "GRCh38",
                "accession": "GCA_000001405.15",
            },
            "feature_namespace": {
                "name": "EnsemblGene",
                "version": "Ensembl 84",
            },
            "cell_identity_id": "CVCL_0004",
            "source_cell_type_value": "A549",
            "source_cell_type_interpretation": "upstream_metadata_error_preserved",
            "state_id": "VCSTATE:unspecified",
            "context_id": "VCCONTEXT:in_vitro",
            "dose": {"control": 0.0, "perturbation": 1.0, "unit": "1"},
            "time": {"value": 5.0, "unit": "d"},
            "perturbation_action": "CRISPR activation",
        },
        "split": {
            "name": "norman-condition-holdout-v1",
            "source_mapping": {
                "train": "train",
                "test": "validation",
                "ood": "test",
            },
            "source_control_condition": "ctrl",
            "control_guides": _CONTROL_GUIDES,
            "control_condition_ids": {
                key: f"norman.control.{key}" for key in _CONTROL_GUIDES
            },
            "condition_delimiter": "+",
            "ignored_control_target": "ctrl",
            "leakage_guard": ["condition_id"],
        },
        "expected": {
            "golden_split_by_observation_sha256": _canonical_hash(golden_splits),
            "condition_id_by_observation_sha256": _canonical_hash(
                golden_conditions
            ),
            "matched_control_by_observation_sha256": _canonical_hash(
                matched_controls
            ),
            "rows_by_split": {"train": 3, "validation": 2, "test": 2},
            "controls_by_split": {"train": 1, "validation": 1, "test": 1},
            "noncontrol_conditions_by_split": {
                "train": 2,
                "validation": 1,
                "test": 1,
            },
            "target_ids_sha256": _canonical_hash(feature_ids),
            "unseen_train_target_ids_sha256": _canonical_hash(
                ["ENSG00000000003"]
            ),
        },
        "metric": {
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
        },
        "baselines": {
            "no_change": {
                "definition": "delta equals zero",
                "model_name": "norman_no_change",
            },
            "global_mean": {
                "definition": "equal mean of train condition deltas",
                "model_name": "norman_global_mean",
            },
            "additive_linear": {
                "definition": "condition-level additive ridge",
                "model_name": "norman_additive_linear",
                "alpha": 1.0,
                "intercept": "unpenalized",
            },
        },
    }
    return source, contract


def test_checked_in_contract_freezes_source_split_metric_and_baselines():
    contract = load_contract(_CONTRACT)

    assert contract["source"]["h5ad"]["sha256"] == (
        "de50bb456ea344ae934878def8339e8b7050baf934a69bda2c7196bcb3a0e6cd"
    )
    assert contract["source"]["h5ad"]["shape"] == [91205, 5045]
    assert contract["source"]["h5ad"]["feature_ids_sha256"] == (
        "ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7"
    )
    assert contract["biology"]["cell_identity_id"] == "CVCL_0004"
    assert contract["biology"]["source_cell_type_value"] == "A549"
    assert contract["split"]["source_mapping"] == {
        "train": "train",
        "test": "validation",
        "ood": "test",
    }
    assert contract["split"]["control_guides"] == _CONTROL_GUIDES
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
    assert contract["baselines"]["additive_linear"]["alpha"] == 1.0


def test_checked_in_golden_files_are_small_hash_manifests_not_data_or_weights():
    root = _CONTRACT.parent
    artifact = json.loads(
        (root / "artifact-manifest.json").read_text(encoding="utf-8")
    )

    assert artifact["remote_root"] == (
        "/home/zkyd/data1/mzy/praxis-virtualcell-data/golden/norman-2019"
    )
    assert artifact["pack"]["fingerprint"] == (
        "42165e430bab3474cdc9e607770ff5e204608c4243f84e492c08e2c6442c55ee"
    )
    assert artifact["states"] == {
        "pack_valid": True,
        "model_compatible": True,
        "scientifically_validated": False,
    }
    assert artifact["gears"] == {"run": False, "assets_accessed": False}
    assert _file_hash(root / "pack.manifest.yaml") == (
        artifact["pack"]["checked_in_manifest"]["sha256"]
    )
    for baseline in ("no_change", "global_mean", "additive_linear"):
        registry = ModelZooRegistry(
            registry_path=str(root / "model_cards" / f"{baseline}.yaml")
        )
        assert len(registry.capability_names()) == 1
    checked_in = [
        path
        for path in root.rglob("*")
        if path.is_file() and not path.name.startswith("._")
    ]
    assert not any(
        path.suffix in {".h5ad", ".npy", ".zip"} for path in checked_in
    )
    assert max(path.stat().st_size for path in checked_in) < 1_000_000


def test_derivation_preserves_source_arrays_and_adds_explicit_pack_semantics(tmp_path):
    source, contract = _write_source(tmp_path / "source")
    pack = derive_pack(source, tmp_path / "pack", contract=contract)
    manifest = PackRegistry().register(pack)

    assert manifest.pack_id == "norman-2019-k562-golden"
    assert manifest.pack_version == "1.0.0"
    original = anndata.read_h5ad(source, backed="r")
    derived = anndata.read_h5ad(
        pack / "norman_k562_golden.h5ad",
        backed="r",
    )
    try:
        assert (original.X[:] != derived.X[:]).nnz == 0
        np.testing.assert_array_equal(
            original.layers["counts"][:],
            derived.layers["counts"][:],
        )
        assert original.var.equals(derived.var)
        assert derived.obs["cell_type"].tolist() == ["A549"] * 7
        assert derived.obs["observation_id"].tolist() == list(original.obs_names)
        assert derived.obs["split"].tolist() == [
            "train",
            "train",
            "train",
            "validation",
            "validation",
            "test",
            "test",
        ]
        assert derived.obs["condition_id"].tolist() == [
            "norman.control.train",
            "A+ctrl",
            "B+ctrl",
            "norman.control.validation",
            "C+ctrl",
            "norman.control.test",
            "A+C",
        ]
        assert derived.obs["cell_identity_id"].tolist() == ["CVCL_0004"] * 7
    finally:
        original.file.close()
        derived.file.close()

    with load_anndata_view(pack) as view:
        assert view.feature_ids == tuple(item[0] for item in _FEATURES)
        assert view.feature_symbols == tuple(item[1] for item in _FEATURES)
        assert view.split_name == "norman-condition-holdout-v1"


@pytest.mark.parametrize(
    "mutation,match",
    [
        (
            lambda adata: adata.obs.__setitem__(
                "split1",
                ["train", "train", "train", "train", "mystery", "train", "ood"],
            ),
            "unknown source split",
        ),
        (
            lambda adata: adata.obs.__setitem__(
                "guide_identity",
                [
                    _CONTROL_GUIDES["train"],
                    "A_guide",
                    "B_guide",
                    "unexpected_control",
                    "C_guide",
                    _CONTROL_GUIDES["test"],
                    "A_C_guide",
                ],
            ),
            "control guide",
        ),
    ],
)
def test_derivation_fails_closed_without_random_split_or_control_fallback(
    tmp_path,
    mutation,
    match,
):
    source, contract = _write_source(tmp_path / "source")
    adata = anndata.read_h5ad(source)
    mutation(adata)
    adata.write_h5ad(source)
    contract["source"]["h5ad"]["sha256"] = _file_hash(source)
    contract["source"]["h5ad"]["size_bytes"] = source.stat().st_size
    contract["source"]["h5ad"]["split_by_observation_sha256"] = _canonical_hash(
        adata.obs["split1"].tolist()
    )
    contract["source"]["h5ad"]["guide_by_observation_sha256"] = _canonical_hash(
        adata.obs["guide_identity"].tolist()
    )

    with pytest.raises(GoldenNormanError, match=match):
        derive_pack(source, tmp_path / "pack", contract=contract)
    assert not (tmp_path / "pack").exists()


def test_derivation_never_stringifies_numeric_source_feature_symbols(tmp_path):
    source, contract = _write_source(tmp_path / "source")
    adata = anndata.read_h5ad(source)
    adata.var["gene_name"] = [1, 2, 3]
    adata.write_h5ad(source)
    contract["source"]["h5ad"]["sha256"] = _file_hash(source)
    contract["source"]["h5ad"]["size_bytes"] = source.stat().st_size
    contract["source"]["h5ad"]["feature_symbols_sha256"] = _canonical_hash(
        ["1", "2", "3"]
    )

    with pytest.raises(GoldenNormanError, match="feature symbols must be strings"):
        derive_pack(source, tmp_path / "pack", contract=contract)
    assert not (tmp_path / "pack").exists()


def test_contract_rejects_boolean_ridge_alpha_instead_of_coercing_it(tmp_path):
    source, contract = _write_source(tmp_path / "source")
    contract["baselines"]["additive_linear"]["alpha"] = True

    with pytest.raises(GoldenNormanError, match="alpha"):
        derive_pack(source, tmp_path / "pack", contract=contract)
    assert not (tmp_path / "pack").exists()


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("metric", "direction", "higher_is_better"),
        ("metric", "truth", "condition_mean_counts"),
        ("no_change", "definition", "missing values become zero"),
        ("global_mean", "definition", "cell-weighted train mean"),
        ("additive_linear", "definition", "ordinary least squares"),
    ],
)
def test_contract_rejects_labels_that_disagree_with_frozen_math(
    tmp_path,
    section,
    field,
    value,
):
    source, contract = _write_source(tmp_path / "source")
    target = (
        contract["metric"]
        if section == "metric"
        else contract["baselines"][section]
    )
    target[field] = value

    with pytest.raises(GoldenNormanError, match="contract has changed"):
        derive_pack(source, tmp_path / "pack", contract=contract)

    assert not (tmp_path / "pack").exists()


def test_derivation_enforces_frozen_control_assignment_hash(tmp_path):
    source, contract = _write_source(tmp_path / "source")
    contract["expected"]["control_assignment_sha256"] = "0" * 64

    with pytest.raises(GoldenNormanError, match="control assignment hash mismatch"):
        derive_pack(source, tmp_path / "pack", contract=contract)

    assert not (tmp_path / "pack").exists()


def test_baseline_assets_use_fixed_condition_level_math_and_flag_unseen_targets(
    tmp_path,
):
    source, contract = _write_source(tmp_path / "source")
    pack = derive_pack(source, tmp_path / "pack", contract=contract)
    bundle = build_baseline_assets(
        pack,
        tmp_path / "model_cache",
        tmp_path / "registries",
        contract=contract,
    )

    no_change = predict_from_artifact(
        bundle["no_change"]["asset_dir"],
        ["ENSG00000000001", "ENSG00000000003"],
    )
    global_mean = predict_from_artifact(
        bundle["global_mean"]["asset_dir"],
        ["ENSG00000000001", "ENSG00000000003"],
    )
    linear = predict_from_artifact(
        bundle["additive_linear"]["asset_dir"],
        ["ENSG00000000001", "ENSG00000000003"],
    )

    np.testing.assert_array_equal(no_change["delta"], np.zeros(3))
    np.testing.assert_allclose(global_mean["delta"], [1.0, 2.0, 0.0])

    x = np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    y = np.asarray([[2.0, 0.0, 0.0], [0.0, 4.0, 0.0]])
    xc = x - x.mean(axis=0)
    yc = y - y.mean(axis=0)
    coefficients = np.linalg.solve(xc.T @ xc + np.eye(3), xc.T @ yc)
    intercept = y.mean(axis=0) - x.mean(axis=0) @ coefficients
    expected = intercept + np.asarray([1.0, 0.0, 1.0]) @ coefficients
    np.testing.assert_allclose(linear["delta"], expected)
    assert linear["unseen_train_targets"] == ["ENSG00000000003"]

    with pytest.raises(GoldenNormanError, match="duplicate target"):
        predict_from_artifact(
            bundle["additive_linear"]["asset_dir"],
            ["ENSG00000000001", "ENSG00000000001"],
        )
    with pytest.raises(GoldenNormanError, match="unknown target"):
        predict_from_artifact(bundle["additive_linear"]["asset_dir"], ["UNKNOWN"])


def test_baseline_builder_rejects_tampered_pack_before_creating_artifacts(tmp_path):
    source, contract = _write_source(tmp_path / "source")
    pack = derive_pack(source, tmp_path / "pack", contract=contract)
    with (pack / "norman_k562_golden.h5ad").open("r+b") as stream:
        stream.seek(-1, 2)
        final_byte = stream.read(1)
        stream.seek(-1, 2)
        stream.write(bytes([final_byte[0] ^ 0xFF]))

    with pytest.raises(PackAssetHashMismatch, match="hash mismatch"):
        build_baseline_assets(
            pack,
            tmp_path / "model_cache",
            tmp_path / "registries",
            contract=contract,
        )

    assert not (tmp_path / "model_cache").exists()
    assert not (tmp_path / "registries").exists()


def test_primary_metric_and_condition_bootstrap_are_exact_and_deterministic():
    truth = {
        "condition-a": np.asarray([1.0, 3.0]),
        "condition-b": np.asarray([2.0, 4.0]),
    }
    prediction = {
        "condition-a": np.asarray([0.0, 1.0]),
        "condition-b": np.asarray([1.0, 3.0]),
    }
    score, losses = condition_macro_mse(truth, prediction)

    assert losses == {"condition-a": 2.5, "condition-b": 1.0}
    assert score == 1.75
    first = paired_bootstrap_ci(list(losses.values()))
    second = paired_bootstrap_ci(list(losses.values()))
    assert first == second
    assert first["seed"] == 0
    assert first["replicates"] == 2000
    assert first["unit"] == "held_out_perturbation_condition"


@pytest.mark.parametrize(
    "baseline,model_name",
    [
        ("no_change", "norman_no_change"),
        ("global_mean", "norman_global_mean"),
        ("additive_linear", "norman_additive_linear"),
    ],
)
def test_each_baseline_runs_through_pack_broker_predictor_governance_report(
    tmp_path,
    baseline,
    model_name,
):
    source, contract = _write_source(tmp_path / "source")
    pack = derive_pack(source, tmp_path / "pack", contract=contract)
    bundle = build_baseline_assets(
        pack,
        tmp_path / "model_cache",
        tmp_path / "registries",
        contract=contract,
    )

    report = run_baseline_runtime(
        pack,
        bundle[baseline]["registry"],
        tmp_path / "model_cache",
        ["ENSG00000000001", "ENSG00000000003"],
    )

    assert report["abstain"] is False
    assert report["models_used"] == [model_name]
    assert report["prediction"]["baseline"] == baseline
    assert report["prediction"]["n_features"] == 3
    assert report["prediction"]["value_type"] == "delta_expression"
    compatibility = report["provenance"]["compatibility_reports"][0]
    assert compatibility["pack_valid"] is True
    assert compatibility["model_compatible"] is True
    assert compatibility["scientifically_validated"] is False


def test_tampered_baseline_asset_abstains_without_mock_fallback(tmp_path):
    source, contract = _write_source(tmp_path / "source")
    pack = derive_pack(source, tmp_path / "pack", contract=contract)
    bundle = build_baseline_assets(
        pack,
        tmp_path / "model_cache",
        tmp_path / "registries",
        contract=contract,
    )
    metadata = bundle["global_mean"]["asset_dir"] / "baseline.json"
    raw = json.loads(metadata.read_text(encoding="utf-8"))
    raw["algorithm"] = "tampered"
    metadata.write_text(json.dumps(raw), encoding="utf-8")

    report = run_baseline_runtime(
        pack,
        bundle["global_mean"]["registry"],
        tmp_path / "model_cache",
        ["ENSG00000000001"],
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert not any(name.startswith("Mock") for name in report["models_rejected"])
    assert any(
        reason.startswith("asset.sha256:")
        for reason in report["provenance"]["compatibility_reports"][0]["reasons"]
    )


def test_evaluation_scores_every_held_out_condition_through_formal_runtime(tmp_path):
    source, contract = _write_source(tmp_path / "source")
    pack = derive_pack(source, tmp_path / "pack", contract=contract)
    build_baseline_assets(
        pack,
        tmp_path / "model_cache",
        tmp_path / "registries",
        contract=contract,
    )

    artifact = evaluate_baselines(
        pack,
        tmp_path / "model_cache",
        tmp_path / "registries",
        tmp_path / "evaluation.json",
        contract=contract,
    )

    assert artifact["primary_metric"] == contract["metric"]
    assert artifact["partitions"]["test"]["condition_ids"] == ["A+C"]
    assert artifact["partitions"]["validation"]["condition_ids"] == ["C+ctrl"]
    assert artifact["results"]["no_change"]["test"]["score"] == pytest.approx(
        13.0 / 3.0
    )
    assert artifact["results"]["global_mean"]["test"]["score"] == 4.0
    for baseline in ("no_change", "global_mean", "additive_linear"):
        formal = artifact["results"][baseline]["test"]["formal_runtime"]
        assert formal[0]["condition_id"] == "A+C"
        assert formal[0]["abstain"] is False
        assert formal[0]["scientifically_validated"] is False
    assert artifact == json.loads(
        (tmp_path / "evaluation.json").read_text(encoding="utf-8")
    )

    second_pack = derive_pack(
        source,
        tmp_path / "second-pack",
        contract=contract,
    )
    build_baseline_assets(
        second_pack,
        tmp_path / "second-model-cache",
        tmp_path / "second-registries",
        contract=contract,
    )
    second = evaluate_baselines(
        second_pack,
        tmp_path / "second-model-cache",
        tmp_path / "second-registries",
        tmp_path / "second-evaluation.json",
        contract=contract,
    )
    assert second == artifact


def test_real_condition_runner_uses_formal_nonlegacy_runtime_and_writes_once(
    tmp_path,
    monkeypatch,
):
    source, contract = _write_source(tmp_path / "source")
    monkeypatch.setattr(
        "praxis_virtualcell.benchmarks.golden_norman.load_contract",
        lambda: contract,
    )
    output = tmp_path / "real-run"

    record = run_golden_condition(source, output, condition_id="A+C")

    assert record == json.loads((output / "prediction.json").read_text(encoding="utf-8"))
    assert record["schema_version"] == "vc.golden-condition-run.v1"
    assert record["condition"] == {
        "id": "A+C",
        "partition": "test",
        "evaluation_scope": "combination",
        "targets": ["ENSG00000000001", "ENSG00000000003"],
        "legacy_perturbation_encoding": "gene_with_multiple_ordered_targets",
    }
    assert record["prediction"]["n_features"] == 3
    assert record["metric"]["score"] == record["metric"]["condition_loss"]
    assert record["runtime"]["plan_legacy_adapter"] is False
    assert record["runtime"]["legacy_predictors_registered"] is False
    assert record["runtime"]["llm_used_for_prediction"] is False
    assert record["states"] == {
        "real_data_used": True,
        "execution_performed": True,
        "pack_valid": True,
        "model_compatible": True,
        "scientifically_validated": False,
        "production_promoted": False,
        "p16r_run": False,
        "benchmark_evidence_created": False,
        "policy_changed": False,
    }
    with pytest.raises(GoldenNormanError, match="already exists"):
        run_golden_condition(source, output, condition_id="A+C")

    dangling_target = tmp_path / "must-not-be-created"
    dangling_output = tmp_path / "dangling-output"
    dangling_output.symlink_to(dangling_target, target_is_directory=True)
    with pytest.raises(GoldenNormanError, match="already exists"):
        run_golden_condition(source, dangling_output, condition_id="A+C")
    assert dangling_output.is_symlink()
    assert not dangling_target.exists()


@pytest.mark.parametrize("condition_id", ["A+ctrl", "C+ctrl"])
def test_real_condition_runner_rejects_non_test_conditions_without_publishing(
    tmp_path,
    monkeypatch,
    condition_id,
):
    source, contract = _write_source(tmp_path / "source")
    monkeypatch.setattr(
        "praxis_virtualcell.benchmarks.golden_norman.load_contract",
        lambda: contract,
    )
    output = tmp_path / "rejected-run"

    with pytest.raises(GoldenNormanError, match="frozen test partition"):
        run_golden_condition(source, output, condition_id=condition_id)

    assert not output.exists()


def test_real_condition_runner_has_no_downloader_or_remote_model_surface():
    module = (Path(__file__).parents[1] / "benchmarks" / "golden_norman_run.py").read_text(encoding="utf-8")

    assert "import requests" not in module
    assert "import urllib" not in module
    assert "GEARS" not in module
    assert "torch" not in module


@pytest.mark.parametrize(
    "tamper",
    [
        "abstain",
        "llm_used",
        "trace_receiver",
        "report_request",
        "plan_pack",
        "delta_type",
    ],
)
def test_real_condition_runner_rejects_tampered_formal_results_without_publishing(
    tmp_path,
    monkeypatch,
    tamper,
):
    source, contract = _write_source(tmp_path / "source")
    monkeypatch.setattr(
        "praxis_virtualcell.benchmarks.golden_norman.load_contract",
        lambda: contract,
    )
    original = golden_run.run_formal_query

    def forged(*args, **kwargs):
        result = original(*args, **kwargs)
        if tamper == "abstain":
            result["structured_report"]["abstain"] = None
        elif tamper == "llm_used":
            result["llm_used_for_prediction"] = True
        elif tamper == "trace_receiver":
            result["trace"] = [{"sender": "clean", "receiver": "MockCPA"}]
        elif tamper == "report_request":
            result["structured_report"]["request"]["perturbation_targets"] = ["FAKE"]
        elif tamper == "plan_pack":
            result["structured_report"]["provenance"]["execution_plan"]["pack_id"] = "wrong-pack"
        else:
            result["structured_report"]["prediction"]["delta"][0] = "1.5"
        return result

    monkeypatch.setattr(golden_run, "run_formal_query", forged)
    output = tmp_path / "tampered-run"

    with pytest.raises(GoldenNormanError):
        run_golden_condition(source, output, condition_id="A+C")

    assert not output.exists()
