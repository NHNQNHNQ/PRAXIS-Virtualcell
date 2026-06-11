---
name: vina_gnina_dock
description: |
  Dual docking with AutoDock Vina + GNINA, then RRF-style consensus rank.
  Implements rule 02. Calls external binaries via subprocess (paths from tools.yaml).
inputs:
  receptor_pdbqt: str (path)
  ligand_pdbqt_dir_or_file: str (path)
  center_x, center_y, center_z: float
  size_x, size_y, size_z: float (default 22.0 each)
  exhaustiveness: int (default 32)
  num_modes: int (default 9)
outputs:
  poses: list[{ligand_id, vina_score, gnina_cnn_score, consensus_rank, pose_pdbqt}]
  enrichment_factor_1pct: float | null  (computed if --known-actives provided)
env:
  - praxis-drug-vina (vina-py / py-vina)
  - praxis-drug-gnina (gnina CLI, CUDA)
status: ready
stage: execution
domain: docking
host_env: praxis-drug
---

# vina_gnina_dock

Drives Vina + GNINA via subprocess (paths in `config/tools.yaml`), then computes RRF consensus on (vina_score, gnina_cnn_score) to produce final ranking. Enrichment Factor at 1% (`EF1%`) computed when known-actives are provided (spike-in).

## Why dual docking
Vina = force-field + geometry. GNINA = CNN re-scoring. Consensus rank improves DUD-E enrichment ~5-10% over either alone (rule 02).

## Modality routing
- `small_mol_inhibitor`, `allosteric`, `fragment` → use this skill
- `covalent` → use `covalent_docking` instead (rule 04)
- `protac` → use `protac_ternary` instead (rule 04 + rule 12)

## CLI
```bash
python -m skills.workflows.vina_gnina_dock.run \
    --receptor egfr.pdbqt --ligand-dir ligand_prep/ \
    --center 5.4 12.1 -3.2 --size 22 22 22 \
    --known-actives erlotinib.smi  # optional, computes EF1%
```

## 输出契约

```json
{
  "skill_id": "vina_gnina_dock",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
