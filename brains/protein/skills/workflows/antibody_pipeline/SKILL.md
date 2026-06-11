---
name: antibody_pipeline
description: Antibody Fv prediction via IgFold + ImmuneBuilder + AbLang2; AF-Multimer rejected
status: green
host_env: praxis-protein
deps: [anarci]
---

## 一句话原则
**抗体走专用 stack** (rule 04) — IgFold + ImmuneBuilder + AbLang2，不许跑通用 AF-Multimer 单跑；CDR H3 > 15 aa 自动 low-confidence (synthesis §一)。

## 适用场景
- design_task ∈ {antibody_cdr_modeling, antibody_design}
- Fv (VH + VL) 序列已知

## 不适用
- ❌ 通用蛋白预测 → `predict_structure_monomer` / `predict_complex`
- ❌ Bispecific antibody — 现 stack 不支持，warn

## 环境检查
```bash
echo $IGFOLD_WEIGHTS
echo $IMMUNEBUILDER_WEIGHTS
echo $ABLANG2_WEIGHTS
which ANARCI    # numbering standardization
```

## 输入契约
```json
{
  "vh_sequence": "EVQL...",
  "vl_sequence": "DIQM...",
  "antigen_pdb": "...",         // optional, for complex
  "antigen_uniprot": "P12345",  // optional, for context
  "ablang_screen": true,        // run AbLang2 humanness check
  "out_dir": "..."
}
```

## 输出契约
```json
{
  "fv_structure_path": ".../fv.pdb",
  "numbering_scheme": "Chothia",
  "cdr_lengths": {"H1": 5, "H2": 17, "H3": 22, "L1": 11, "L2": 7, "L3": 9},
  "metrics": {
    "igfold_confidence": {"H1": 0.95, "H2": 0.88, "H3": 0.42},
    "immunebuilder_consistency_RMSD": 1.6,
    "ablang2_log_likelihood": -2.3
  },
  "complex_structure_path": ".../complex.pdb",
  "complex_metrics": {"iPTM": 0.71, "BSA_A2": 980},
  "low_confidence_flags": ["CDR_H3_length_22_exceeds_15aa_threshold"],
  "passed_qc": false,
  "provenance": {...}
}
```

## QC gate
- CDR H3 ≤ 15 aa: trust IgFold (RMSE 1-2 Å typical)
- CDR H3 > 15 aa: auto low_confidence flag, recommend X-ray (synthesis §一)
- IgFold + ImmuneBuilder cross-RMSD > 2 Å: low_consensus
- AbLang2 log-likelihood很负 (humanness 差): warn
- Complex iPTM < 0.6: fail (per rule 02)

## 跑法
```bash
python skills/workflows/antibody_pipeline/runner.py \
    --vh-sequence EVQL... --vl-sequence DIQM... \
    --out-dir runs/example/antibody/A001
```

## 实现状态
- ✅ SKILL.md
- ✅ runner.py with --simulate + ANARCI numbering check + H3>15 auto-flag (CPU-side rule)
- 🔧 TODO (Linux/GPU): wire IgFold + ImmuneBuilder + AbLang2 calls
