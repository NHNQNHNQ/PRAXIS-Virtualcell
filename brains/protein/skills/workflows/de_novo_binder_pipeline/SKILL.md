---
name: de_novo_binder_pipeline
description: End-to-end binder design — RFdiffusion → ProteinMPNN → AF2 with initial guess
status: green
host_env: rfdiffusion
---

## 一句话原则
**Hotspot mandatory** (rule 02); MPNN T=0.1 conservative (rule 03); 5-metric composite filter (pLDDT + pAE_int + iPTM + Rosetta_ddG + SAP) — single metric not allowed.

## 适用场景
- design_task == de_novo_binder
- target structure 已知 (PDB or AF)
- target hotspot residues 已知或可推断

## 不适用
- ❌ 抗体 binder → `antibody_pipeline`
- ❌ Hotspot 未知 → 阻塞，先做 epitope mapping
- ❌ binder length > 200 aa → warn (severe), require user override

## 环境检查
```bash
echo $RFDIFFUSION_PATH    # /opt/RFdiffusion
echo $PROTEINMPNN_PATH    # /opt/ProteinMPNN
echo $ALPHAFOLD_PATH      # /opt/alphafold (for AF2 with initial guess)
nvidia-smi                # ≥ 24 GB; RFdiffusion 1000 backbone ≈ 6 h on A100
```

## 输入契约
```json
{
  "target_structure": "path/to/target.pdb",
  "target_chain": "A",
  "hotspot": [56, 115, 125],          // ★ MANDATORY (rule 02)
  "binder_length": 100,                // 60-150 recommended
  "n_designs": 1000,                   // total backbones
  "mpnn_temperature": 0.1,             // ≤ 0.2 recommended (rule 03)
  "n_mpnn_per_backbone": 8,
  "specificity_panel": [],             // optional negative-design controls
  "out_dir": "runs/<task_id>/de_novo_binder/<batch_id>"
}
```

## 输出契约
```json
{
  "batch_id": "...",
  "n_designs_input": 1000,
  "n_designs_passed_5metric": 47,
  "designs": [
    {
      "design_id": "B0042",
      "structure_path": "....pdb",
      "sequence": "MKLA...",
      "metrics": {
        "pLDDT_binder": 82.5, "pAE_interaction": 7.8, "iPTM": 0.71,
        "Rosetta_ddG": -32.4, "SAP_score": 8.5,
        "MPNN_sequence_recovery": 0.34
      },
      "passed_5metric": true,
      "rank": 1
    }
  ],
  "in_silico_to_in_vitro_estimate": "5-15% (per protein-002, protein-010)",
  "specificity_panel_results": [],
  "provenance": {...}
}
```

## QC gate
- 5-metric joint: pLDDT_binder ≥ 80 + pAE_interaction < 10 + iPTM ≥ 0.6 + Rosetta_ddG < -30 REU + SAP < 30
- 任何一项 fail → discard
- top-N 排序by composite RRF over 5 metric ranks

## 跑法
```bash
python skills/workflows/de_novo_binder_pipeline/runner.py \
    --target-structure target.pdb --hotspot 56,115,125 \
    --binder-length 100 --n-designs 100 \
    --out-dir runs/example/de_novo_binder/B001
# Auto-simulate when binaries missing.
```

## 实现状态
- ✅ SKILL.md
- ✅ runner.py with --simulate + hotspot/length precondition checks
- 🔧 TODO (Linux/GPU): wire RFdiffusion + ProteinMPNN + AF2-initial-guess chain
