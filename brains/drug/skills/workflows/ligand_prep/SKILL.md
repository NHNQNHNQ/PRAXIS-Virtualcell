---
name: ligand_prep
description: |
  Ligand preparation: stereo enumeration + protonation states (pH 7.4) + tautomer enumeration
  + 3D embedding (ETKDGv3) + PDBQT export. Implements rule 03.
inputs:
  smiles_list: list[str]
  ph: float (default 7.4)
  out_dir: str (default runs/<task>/ligand_prep/)
  max_variants_per_compound: int (default 16)
outputs:
  pdbqt_paths: list[str]
  variants_per_compound: dict[smiles → int]
env: praxis-drug-base
status: ready
stage: design|execution
domain: prep
---

# ligand_prep

For every input SMILES:
1. Parse with RDKit
2. Enumerate stereoisomers (`Chem.EnumerateStereoisomers.EnumerateStereoisomers`)
3. Enumerate tautomers (`rdkit.Chem.MolStandardize.rdMolStandardize.TautomerEnumerator`)
4. Enumerate protonation states at pH (Dimorphite-DL if installed; else single state)
5. Generate 3D coordinates (ETKDGv3, single conformer per variant + UFF/MMFF94 minimization)
6. Convert to PDBQT (Meeko `MoleculePreparation`)

Cap per-compound output at `max_variants_per_compound` (default 16) sorted by MMFF energy.

## Why
Single-state docking misses the actual binding state ~30-50% of the time. Imidazole/carboxylate/amine/guanidinium are common pH-sensitive groups in drug-like compounds.

## Hard requirements
- ALL of (stereo, tautomer, protonation, 3D) must run; if dimorphite-dl is missing, log warning and proceed with single protonation state.

## 输出契约

```json
{
  "skill_id": "ligand_prep",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
