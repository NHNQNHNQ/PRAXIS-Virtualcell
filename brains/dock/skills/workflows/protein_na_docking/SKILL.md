---
name: protein_na_docking
description: Protein-RNA / Protein-DNA docking — 专用 docker (HDOCK / NPDock / AF3-NA / RoseTTAFold-2NA)。AF3 NA support 是 first-line。Sequence specificity 强制 validation（TF-DNA 必须 PWM-matched）。CRISPR-gRNA 必显式指定 PAM。
status: skeleton
source_case: dock-010-protein-rna-dna-docking
host_env: praxis-dock
---

# protein_na_docking — Protein-nucleic acid docking

## 一句话原则
**NA-specific docker (不 PP) + sequence specificity validation + Cas-gRNA 必指定 PAM + RNA 3D structure quality 上游瓶颈**.

## 输入契约

```json
{
  "protein_pdb": "/path/to/protein.pdb",
  "na_3d_pdb": "/path/to/rna.pdb",
  "na_sequence": "ACGUACGU",
  "na_strandedness": "ds | ss | hairpin",
  "sequence_specificity": "PWM | PAM | random",
  "expected_motif_or_PAM": "NGG",
  "tool": "af3 | hdock | npdock | rosettafold_2na",
  "remote_gpu": true
}
```

## ★ Sanity checks
1. **NA-specific docker** else BLOCK (PP docker scoring function 偏 protein-protein)
2. **Sequence specificity 必校验**: interface residue ↔ base specific contact
3. **Cas-gRNA → PAM 必显式 specify**
4. **DNA bending 警告**: TBP/IHF 等弯 DNA 蛋白；rigid B-form 假设破坏
5. **RNA secondary structure**: 上游 (RNAComposer 出 3D) 必先校验
6. **Modified base** (5mC, 6mA, m1A) → 专用 force field
7. **R-loop / triplex / G-quadruplex** caveat (多数 docker 不支持)

## 实现状态: skeleton
AF3 NA mode 远程；HDOCK web server。`run.py` 待实现。

## 引用案例
- **dock-010-protein-rna-dna-docking**: 1FJG (ribosome-mRNA), 1MEY (Zif268-DNA TF benchmark)

## 输出契约

```json
{
  "skill_id": "protein_na_docking",
  "receptor": "",
  "ligand": "",
  "best_affinity": 0.0,
  "poses": [
    {
      "rank": 1,
      "affinity_kcal_per_mol": 0.0,
      "pose_path": ""
    }
  ],
  "runtime_sec": 0.0,
  "diagnostics": {
    "brain": "dock",
    "archetype": "docking"
  }
}
```
