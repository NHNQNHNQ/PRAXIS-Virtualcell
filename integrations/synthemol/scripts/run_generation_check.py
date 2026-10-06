"""Exercise the unmodified, installed generator twice with a fixed seed."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import pandas as pd
from rdkit import Chem


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--generator-root", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    base = (args.generator_root or args.project / "integrations/synthemol/external/SyntheMol-MCTS").resolve()
    if not (base / "assets/Models/antibiotic_chemprop").exists():
        raise FileNotFoundError("SyntheMol assets are not bundled. Pass --generator-root to a verified existing installation.")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONHASHSEED="17", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    common = [str(Path(sys.executable).parent / "synthemol"),
        "--model_path", str(base / "assets/Models/antibiotic_chemprop"),
        "--model_type", "chemprop", "--building_blocks_path",
        str(base / "assets/Models/antibiotic_chemprop/building_blocks.csv"),
        "--building_blocks_score_column", "chemprop_ensemble_preds",
        "--building_blocks_id_column", "Reagent_ID", "--reaction_to_building_blocks_path",
        str(base / "assets/Data/4_real_space/reaction_to_building_blocks_filtered.pkl"),
        "--max_reactions", "1", "--n_rollout", "20", "--rng_seed", "17", "--replicate"]
    protocol = dict(command=common, env={k: env[k] for k in
        ("PYTHONHASHSEED", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
        purpose="generation and repeatability smoke check, not efficacy validation or model training",
        versions={n: importlib.metadata.version(n) for n in
        ("synthemol", "chemprop", "chemfunc", "torch", "rdkit", "numpy", "pandas", "scikit-learn")})
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    (output / "requirements.freeze.txt").write_text(subprocess.check_output(
        [sys.executable, "-m", "pip", "freeze"], text=True))
    frames = []
    timing = []
    for i in (1, 2):
        start = time.monotonic()
        print(f"Starting generator repeat {i}", flush=True)
        with (output / f"repeat_{i}.log").open("w") as stream:
            subprocess.run(common + ["--save_dir", str(output / f"repeat_{i}")],
                           env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
        df = pd.read_csv(output / f"repeat_{i}/molecules.csv")
        assert len(df) > 0
        assert df.smiles.map(lambda s: Chem.MolFromSmiles(s) is not None).all()
        assert np.isfinite(df.score).all() and df.score.between(0, 1).all()
        frames.append(df)
        timing.append(time.monotonic() - start)
        print(f"Finished repeat {i}: {len(df)} valid rows", flush=True)
    pd.testing.assert_frame_equal(frames[0], frames[1], check_exact=True)
    result = dict(completed=True, seed=17, rollouts_per_repeat=20,
                  generated_rows=len(frames[0]), unique_smiles=frames[0].smiles.nunique(),
                  valid_fraction=1.0, repeat_predictions_identical=True, seconds=timing,
                  model="10-member antibiotic_chemprop ensemble",
                  biological_validation=False, integrated_with_v1=False)
    (output / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
