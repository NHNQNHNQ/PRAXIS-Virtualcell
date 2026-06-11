---
name: predict_structure_monomer
description: Single-chain structure prediction via ESMFold/AF3 with multi-model consensus
host_env: praxis-protein
---

## 一句话原则
≥ 2 predictor consensus + ≥ 5 seed; pLDDT_mean > 70 才 promote。Single seed/model 输出视为 anti-pattern (rule 01)。

## 适用场景
- design_task ∈ {structure_prediction, high_throughput_structure_prediction}
- 单链 monomer 蛋白
- 序列已知，结构未知

## 不适用
- ❌ multimer / 复合物 — 用 `predict_complex`
- ❌ 抗体 — 用 `antibody_pipeline`
- ❌ 突变扫描 — 用 `mutation_effect_scan`

## 环境检查
```bash
which esmfold || python -c "import esm" 2>/dev/null
echo $ESMFOLD_WEIGHTS  # /opt/esm/checkpoints
nvidia-smi             # GPU > 11 GB recommended for ≤ 1024 aa
```

## 输入契约
```json
{
  "sequence": "MAKL...PVE",         // required
  "tools": ["ESMFold", "AlphaFold3"],  // ≥ 2 predictors required (rule 01)
  "n_seeds": 5,                     // ≥ 5 (rule 01)
  "out_dir": "runs/<task_id>/predict_structure_monomer/<design_id>"
}
```

## 输出契约
```json
{
  "skill_id": "predict_structure_monomer",
  "sequence": "",
  "model_path": "",
  "plddt_mean": 0.0,
  "ptm": 0.0,
  "n_residues": 0,
  "runtime_sec": 0.0,
  "diagnostics": {
    "brain": "protein",
    "archetype": "structure_predict"
  }
}
```

## QC gate
- pLDDT_mean > 70 → pass
- 50 < pLDDT_mean ≤ 70 → review (partial fold)
- pLDDT_mean ≤ 50 → discard or flag IDP (require disorder-predictor cross-check)
- cross_model_agreement_RMSD > 3 Å → low confidence
- sequence length > context window of model → require chunking + warn

## 速率上限
- ESMFold: ~10 sec/seq (A100 40GB, ≤ 1024 aa)
- AlphaFold3: ~3 min/seq (A100 40GB, MSA included)

## 跑法
```bash
python skills/workflows/predict_structure_monomer/runner.py \
    --sequence MAKL... --tools ESMFold,AlphaFold3 --n-seeds 5 \
    --out-dir runs/example/predict_structure_monomer/D001
# Auto-falls back to --simulate when binaries/weights missing.
```

## 实现状态
- ✅ SKILL.md (this file) — full contract
- ✅ runner.py — `--simulate` deterministic mock
- 🔧 TODO (Linux/GPU): wire real ESMFold + AF3 calls in `# === REAL RUNNER ===` block
