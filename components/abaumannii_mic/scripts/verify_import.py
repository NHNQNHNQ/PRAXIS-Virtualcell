"""Read-only verification of historical data, frozen splits, weights and inference."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import numpy as np
import pandas as pd
from abwm.inference import Predictor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.project.resolve()
    root = repo / "reports/antibacterial/direct_mic"
    data_root = repo / "data/antibacterial/abaumannii"
    model_root = repo / "models/abaumannii/direct_mic"
    manifest = json.loads((root / "migration_manifest.json").read_text())
    for item in manifest["files"]:
        path = repo / item["target"]
        assert path.stat().st_size == item["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    records = pd.read_csv(data_root / "curated/mic_measurements.csv", dtype={"record_id": str})
    summary = json.loads((data_root / "curated/mic_summary.json").read_text())
    assert records.record_id.is_unique and len(records) == summary["eligible"] == 12349
    assert records.compound_group.nunique() == 5807
    assert records.study.nunique() == 488
    split_checks = []
    for scheme in ("compound", "scaffold", "study", "isolate"):
        path = data_root / "splits" / f"mic_{scheme}_v3.csv"
        split = pd.read_csv(path, dtype={"record_id": str})
        assert records.record_id.tolist() == split.record_id.tolist()
        assert split.groupby("group").split.nunique().max() == 1
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == summary["splits"][scheme]["split_hash"]
        split_checks.append(dict(scheme=scheme, sha256=digest, rows=len(split)))
    original = {Path(row["checkpoint"]).name: row for row in json.loads((root / "artifact_manifest.json").read_text())}
    checkpoints = []
    for scheme in ("compound", "scaffold", "study", "isolate"):
        for seed in (17, 42, 2026):
            predictor = Predictor(model_root, seed=seed, scheme=scheme)
            ck = predictor.checkpoint
            digest = hashlib.sha256(predictor.path.read_bytes()).hexdigest()
            assert digest == original[predictor.path.name]["sha256"]
            split_path = data_root / "splits" / Path(ck["split_manifest"]).name
            assert hashlib.sha256(split_path.read_bytes()).hexdigest() == ck["split_sha256"]
            saved = pd.read_csv(root / "predictions" / f"direct_mic_{scheme}_seed{seed}_test.csv", dtype={"record_id": str})
            split = pd.read_csv(split_path, dtype={"record_id": str})
            assert set(saved.record_id) == set(split.loc[split.split.eq("test"), "record_id"])
            row = saved.iloc[0]
            smiles = records.set_index("record_id").loc[row.record_id, "smiles"]
            output = predictor.predict(dict(task="mic", model="direct", smiles=smiles))
            assert np.allclose([output["log2_mean"], output["log2_sigma"]], [row.pred_log2, row.sigma_log2], atol=1e-5, rtol=1e-5)
            checkpoints.append(dict(filename=predictor.path.name, sha256=digest, frozen_split_verified=True,
                                    record_id=row.record_id, original_log2_mean=float(row.pred_log2),
                                    replay_log2_mean=output["log2_mean"], original_log2_sigma=float(row.sigma_log2),
                                    replay_log2_sigma=output["log2_sigma"], replay_passed=True))
    payload = json.loads((root / "examples/direct_mic_input.json").read_text())
    expected = json.loads((root / "examples/direct_mic_output.json").read_text())
    output = Predictor(model_root).predict(payload)
    keys = ["log2_mean", "log2_sigma", "median", "interval90"]
    for key in keys:
        assert np.allclose(output[key], expected[key], atol=1e-6, rtol=1e-6)
    result = dict(passed=True, source_delivery_date="2026-09-13", latest_20260923_model_replayed=False,
                  training_performed=False, imported_files_verified=len(manifest["files"]),
                  mic_records=len(records), structural_parents=records.compound_group.nunique(),
                  frozen_splits=split_checks, checkpoints=checkpoints,
                  original_single_example=expected, replay_single_example=output,
                  tolerance=dict(atol=1e-5, rtol=1e-5, single_example_atol=1e-6, single_example_rtol=1e-6),
                  runtime=dict(python=sys.version.split()[0], platform=platform.platform(),
                               packages={name: importlib.metadata.version(name) for name in ["torch", "rdkit", "numpy", "pandas"]}))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(dict(passed=True, weights=len(checkpoints), mic_records=len(records), imported_files=len(manifest["files"]))))


if __name__ == "__main__":
    main()
