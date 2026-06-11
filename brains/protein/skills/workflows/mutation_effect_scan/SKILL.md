---
name: mutation_effect_scan
description: Three-way ΔΔG voting (ThermoMPNN ∩ Rosetta ∩ PyRosetta); single-method rejected
host_env: praxis-protein
---

## 一句话原则
**≥ 2/3 predictor 同意才推** (rule 01); rank > absolute ΔΔG (per protein-004); position context (buried/surface/active) 必须分开报告。

## 适用场景
- design_task ∈ {mutation_effect_prediction, stabilization}
- 已知 backbone PDB
- 给定位点 (saturation 或 listed mutations)

## 不适用
- ❌ 单 predictor 跑给 lab 推荐 (rule 04 hard reject)
- ❌ |ΔΔG| < 0.5 kcal/mol 范围 (噪声主导)
- ❌ 大 outlier |ΔΔG| > 5 kcal/mol (蛋白完全 unfold，无意义)

## 环境检查
```bash
echo # pyrosetta python (antibody env)          # # antibody env 中的 pyrosetta (CPU)
echo $ROSETTA_BIN_DIR    # /opt/rosetta/main/source/bin
echo $THERMOMPNN_WEIGHTS # weights/
which mkdssp || which dssp
```

## 输入契约
```json
{
  "structure_pdb": "...",
  "mutations": [{"resnum": 42, "wt_aa": "L", "mut_aa": "V"}, ...],
  "predictors": ["ThermoMPNN", "Rosetta", "PyRosetta_cart"],   // ≥ 2 required
  "n_replicates": {"PyRosetta_cart": 5, "Rosetta": 3},
  "freeze_active_site": true,
  "out_dir": "..."
}
```

## 输出契约
```json
{
  "skill_id": "mutation_effect_scan",
  "wt_score": 0.0,
  "scan_csv": "",
  "top_mutations": [
    {
      "position": 1,
      "from_aa": "A",
      "to_aa": "V",
      "ddg": 0.0
    }
  ],
  "diagnostics": {
    "brain": "protein",
    "archetype": "mutation_scan"
  }
}
```

## QC gate
- ≥ 2/3 predictor agreement → recommend
- 1/3 predictor → discard
- |ΔΔG| < 0.5 → noise zone, mark as low_confidence
- |ΔΔG| > 5 → outlier, mark as protein_unfolds_regime

## 实现状态
- ✅ SKILL.md
- ✅ runner.py — **partial real (PyRosetta wrapper if binary present)** + ThermoMPNN/Rosetta `--simulate` stubs
- 🔧 TODO (Linux/GPU+server): wire ThermoMPNN + Rosetta cartesian_ddg backends
