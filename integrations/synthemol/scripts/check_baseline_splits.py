"""Check imported direct MIC checkpoints against their relocated frozen splits."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
import torch

def main():
    parser = argparse.ArgumentParser()
    repo = Path(__file__).resolve().parents[3]
    parser.add_argument("--model-root", type=Path, default=repo / "models/abaumannii/direct_mic")
    parser.add_argument("--data-root", type=Path, default=repo / "data/antibacterial/abaumannii")
    parser.add_argument("--prediction-root", type=Path, default=repo / "reports/antibacterial/direct_mic/predictions")
    parser.add_argument("--seeds", nargs="+", type=int, default=[17, 42, 2026])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for scheme in ("compound", "scaffold", "study", "isolate"):
        for seed in args.seeds:
            path = args.model_root / f"direct_mic_{scheme}_seed{seed}.pt"
            ck = torch.load(path, map_location="cpu", weights_only=True)
            split_path = args.data_root / "splits" / Path(ck["split_manifest"]).name
            assert hashlib.sha256(split_path.read_bytes()).hexdigest() == ck["split_sha256"]
            split = pd.read_csv(split_path, dtype={"record_id": str})
            predictions = pd.read_csv(args.prediction_root / f"direct_mic_{scheme}_seed{seed}_test.csv", dtype={"record_id": str})
            assert set(predictions.record_id) == set(split.loc[split.split.eq("test"), "record_id"])
            assert not (set(split.loc[split.split.eq("train"), "group"]) & set(split.loc[split.split.eq("test"), "group"]))
            results.append(dict(scheme=scheme, seed=seed, checkpoint=path.name, split=split_path.name,
                                split_verified=True, prediction_rows=len(predictions)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
