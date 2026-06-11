---
name: predict_complex
description: Hetero/homo complex prediction via AF-Multimer/AF3/Boltz-1 with paired MSA
host_env: praxis-protein
---

## 一句话原则
**Paired MSA mandatory** (rule 02); **ESMFold rejected** for multimer (rule 04); ≥ 2 model cross-validation; iPTM ≥ 0.6 + BSA ≥ 600 Å² 才 promote。

## 适用场景
- design_task ∈ {complex_prediction, structure_prediction_complex}
- 异源/同源二聚体或多聚体
- 蛋白-蛋白相互作用

## 不适用
- ❌ 抗体-抗原 → 用 `antibody_pipeline`（IgFold + AF-Multimer 联合）
- ❌ ESMFold 不支持 multimer (rule 04)

## 环境检查
```bash
echo $ALPHAFOLD_PATH    # /opt/alphafold
echo $AF3_PATH          # /opt/alphafold3
which colabfold_search  # for paired MSA
nvidia-smi              # GPU ≥ 24 GB recommended
```

## 输入契约
```json
{
  "sequences": ["MAKL...", "MGGS..."],   // ≥ 2 chains
  "tool": "AlphaFold-Multimer",          // ∈ {AlphaFold-Multimer, AlphaFold3, Boltz-1, Chai-1}
  "paired_msa": true,                    // ★ MANDATORY (rule 02), reviewer blocks if false
  "n_seeds": 5,                          // ≥ 5 (rule 01)
  "n_models": 5,                         // 5 model AF-Multimer default
  "cofactors": [],                       // optional metadata
  "out_dir": "runs/<task_id>/predict_complex/<design_id>"
}
```

## 输出契约
```json
{
  "design_id": "...",
  "structure_path": "....cif",
  "metrics": {
    "iPTM": 0.78, "pTM": 0.85, "pLDDT_mean": 81.2,
    "pAE_interface": 4.2, "BSA_A2": 980, "RMSD_to_target": 1.4
  },
  "passed_qc": true,
  "qc_notes": "iPTM ≥ 0.6 ✓; BSA ≥ 600 Å² ✓",
  "provenance": {...}
}
```

## QC gate
- iPTM ≥ 0.6 + BSA ≥ 600 Å² → pass
- iPTM < 0.6 → fail (low binding confidence)
- BSA < 600 Å² → warn (artifact-like interface)
- cross-model RMSD > 5 Å → low_consensus

## 速率上限
- AF-Multimer: ~10-30 min/complex (A100 40GB, ~500 aa total)
- AF3: ~5-15 min/complex
- Boltz-1: ~2-5 min (5x faster)

## 跑法
```bash
python skills/workflows/predict_complex/runner.py \
    --sequences "MAKL...,MGGS..." --tool AlphaFold-Multimer \
    --paired-msa --n-seeds 5 \
    --out-dir runs/example/predict_complex/C001
```

## 实现状态
- ✅ SKILL.md
- ✅ runner.py with --simulate + paired_msa precondition check
- 🔧 TODO (Linux/GPU): wire AF-Multimer / AF3 / Boltz-1 calls
