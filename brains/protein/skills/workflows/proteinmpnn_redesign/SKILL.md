---
name: proteinmpnn_redesign
description: ProteinMPNN sequence redesign on existing backbone with active-site freeze
status: green
host_env: proteinmpnn
deps: [python]
---

## 一句话原则
**`freeze_residues[]` 必填非空** (rule 03); MPNN T=0.1 conservative; sequence_recovery > 30% 才 promote。

## 适用场景
- design_task ∈ {redesign, stabilization}
- 已有 backbone PDB
- 已知 active site / disulfide / TM / glyco 位点

## 不适用
- ❌ De novo backbone — 用 `de_novo_binder_pipeline` 或 `symmetric_design_pipeline`
- ❌ 抗体 — 用 `antibody_pipeline`

## 环境检查
```bash
echo $PROTEINMPNN_PATH
which python  # need pytorch
```

## 输入契约
```json
{
  "backbone_pdb": "path/to/backbone.pdb",
  "freeze_residues": [42, 95, 96, 119],   // ★ MANDATORY non-empty (rule 03)
  "freeze_categories": {"42": "active_site", "95": "disulfide", "96": "disulfide", "119": "active_site"},
  "temperature": 0.1,
  "num_seq_per_target": 64,
  "out_dir": "..."
}
```

## 输出契约
```json
{
  "n_sequences_generated": 64,
  "sequences": [
    {"id": "S001", "sequence": "M...", "score": -2.34, "sequence_recovery": 0.42, "passed_recovery": true}
  ],
  "freeze_check": {"all_frozen_preserved": true, "violations": []},
  "provenance": {...}
}
```

## QC gate
- sequence_recovery > 30% 才 promote
- frozen positions 必须 100% 保留 (runner 会校验 — 任何 violation = fail)

## 跑法
```bash
python skills/workflows/proteinmpnn_redesign/runner.py \
    --backbone-pdb scaffold.pdb --freeze-residues 42,95,96,119 \
    --temperature 0.1 --num-seq 64 --out-dir runs/...
```

## 实现状态
- ✅ SKILL.md
- ✅ runner.py with --simulate + freeze-residues precondition + violation check
- 🔧 TODO (Linux/GPU): wire ProteinMPNN call
