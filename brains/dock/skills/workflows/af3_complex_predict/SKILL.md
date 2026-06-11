---
name: af3_complex_predict
description: Foundation-model 复合物预测（AlphaFold3 / Boltz-1 / Chai-1）。first-line 实现用 Boltz-1（开源 pip 装 + GPU 通过 SSH bridge），AF3 fallback 当 weights 已配置。强制多 seed (≥ 5) + PoseBusters check 必跑 + iPTM ≠ KD 显式声明。
status: usable
source_case: dock-009-af3-boltz-as-docking
host_env: praxis-dock
---

# af3_complex_predict — Foundation model complex prediction

## 一句话原则
**多 seed (≥ 5) + PoseBusters check 必跑 + iPTM/pLDDT ≠ KD**。foundation model 高 confidence 不等于 binding affinity；物理 sanity（PoseBusters）通过率 < 100% → confidence 自动降级。

## 适用阶段
Stage 3 (Execution) — `docking_type ∈ {foundation_model_complex_prediction, antibody_antigen, peptide_protein with length>20, protein_nucleic_acid, protein_ligand with novel scaffold}`.

## 输入契约

```json
{
  "receptor_sequences": ["MHQRMVK..."],
  "ligand_input": {
    "format": "smiles | protein_sequence | rna | dna",
    "value": "..."
  },
  "cofactors_metals": ["MG", "ZN"],
  "n_seeds": 5,
  "model": "boltz-1",
  "model_path": null,
  "use_gpu": true,
  "remote_gpu": true,
  "out_dir": "/runs/{tid}/af3_complex_predict/"
}
```

`model="boltz-1"` 优先（开源 + 远程 GPU 已装）；`model="af3"` 需 `AF3_PARAMS_DIR` 环境变量；`model="chai-1"` 需 `chai_lab` Python 包.

## 输出契约

```json
{
  "skill_id": "af3_complex_predict",
  "model_used": "boltz-1",
  "model_version": "0.4.1",
  "n_seeds_run": 5,
  "predictions": [
    {
      "seed": 0,
      "pose_cif_path": "/runs/{tid}/af3_complex_predict/seed0_model.cif",
      "ligand_pose_sdf_path": "...",
      "plddt_ligand": 78.4,
      "iptm_ligand": 0.83,
      "pae_interface_max": 4.2,
      "chain_pair_iptm_ligand": 0.71
    }
  ],
  "consensus_seed_index": 2,
  "posebusters_check": {
    "overall_pass_rate": 0.85,
    "per_pose": [{"pose_path": "...", "all_pass": true, "checks": {...}}]
  },
  "confidence_assessment": {
    "iptm_high_means_pose_quality": true,
    "iptm_does_NOT_mean_KD": "★ explicit declaration",
    "n_seeds_agree_top1_rmsd_lt_2A": 4
  },
  "passed_sanity": true,
  "provenance": {"command": "...", "runtime_sec": 1842.3, "remote_executed": true}
}
```

## ★ 强制 sanity checks (case dock-009 lessons)

1. **多 seed (n=5)**：单 seed 不可信；不同 seed 给不同 pose 是正常
2. **PoseBusters 必跑**：每个输出 pose 跑 `pose_buster_validate` skill；overall_pass_rate < 80% → warn；< 50% → SanityFail
3. **iPTM ≠ KD**：所有输出必带 explicit declaration "Confidence ≠ binding affinity"
4. **Cofactor / metal / glycan**：缺失则在 metadata 显式列出（"模型不含 NAD; active site 几何可能塌"）
5. **Train data leakage check (if benchmark)**：用户提供 `target_pdb_release_year`；< 2021 → AF3 训练含此 PDB → fair benchmark warning
6. **Stereochemistry**：手性 ligand → 检查输出 chirality 是否与输入一致（AF3 偶尔翻转）

## 实现状态: usable
- `run.py` 完整可跑：Boltz-1 通过 SSH bridge 在 zkyd@10.102.106.53 5x A100 GPU 跑；本地仅做 input prep + PoseBusters validation
- AF3 fallback：当 `AF3_PARAMS_DIR` 设置时切换到 AF3 inference
- Chai-1 fallback：当 `chai_lab` Python 包安装时
- PoseBusters: 本地 `posebusters` Python lib（CPU OK）

## 引用案例
- **dock-009-af3-boltz-as-docking**: AF3 PoseBusters benchmark top-1 ≤ 2Å rate ~76%，但 ~50% 输出 PoseBusters check fail；Boltz-1 / Chai-1 类似量级
- 失败模式: OOD ligand 退化到 Vina 水平; 手性翻转; 多 binding site 不区分; cofactor-dependent fold 缺失; 训练集泄漏
