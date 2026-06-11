---
name: esmfold_high_throughput
description: ESMFold batch prediction with length-bucket batching + pLDDT triage
status: green
host_env: esmfold
---

## 一句话原则
ESMFold 不能跑 multimer (rule 04); length-bucket 否则 GPU mem 浪费; pLDDT < 50 → IDP flag (需 IUPred/flDPnn 二验); fp16 不稳 → fallback fp32。

## 适用场景
- design_task == high_throughput_structure_prediction
- ≥ 100 sequences
- monomer only

## 不适用
- ❌ Multimer/复合物 (rule 04, synthesis §一)
- ❌ 突变效应预测 — 用 `mutation_effect_scan`
- ❌ < 100 序列 — 用 `predict_structure_monomer` 求精度

## 环境检查
```bash
echo $ESMFOLD_WEIGHTS
nvidia-smi  # ≥ 11 GB; A100 40GB ~1200 seq/h @ 150 aa
```

## 输入契约
```json
{
  "fasta_path": "input.fasta",
  "length_buckets": [[1, 100], [100, 200], [200, 400], [400, 1024]],
  "pLDDT_keep_threshold": 70,
  "pLDDT_review_threshold": 50,
  "use_fp16": false,         // turn off if NaN observed
  "out_dir": "..."
}
```

## 输出契约
```json
{
  "n_input": 10000,
  "n_kept": 4500,
  "n_review": 3000,
  "n_discard": 2500,
  "buckets_processed": [...],
  "throughput_seqs_per_hour": 1200,
  "warnings": [
    "147 sequences > 1024 aa context window — chunked with loss of global context",
    "23 sequences detected NaN — fallback to fp32"
  ],
  "results_jsonl_path": "results.jsonl",
  "provenance": {...}
}
```

## QC gate
- pLDDT ≥ 70 → keep
- 50 ≤ pLDDT < 70 → review (partial fold; require disorder predictor cross-check)
- pLDDT < 50 → discard or IDP flag
- coiled-coil/repeat detected (high pLDDT but register error) → manual review

## 跑法
```bash
python skills/workflows/esmfold_high_throughput/runner.py \
    --fasta-path bigbatch.fasta --out-dir runs/example/esmfold_ht/B001
```

## 实现状态
- ✅ SKILL.md
- ✅ runner.py with --simulate + length-bucket logic + GPU memory estimator (CPU-side)
- 🔧 TODO (Linux/GPU): wire ESMFold batch call
