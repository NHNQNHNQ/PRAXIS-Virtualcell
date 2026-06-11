---
name: symmetric_design_pipeline
description: RFdiffusion symmetric (C3/C4/D2/...) + tied-position MPNN + AF-Multimer validation
status: green
host_env: rfdiffusion
---

## 一句话原则
**Tied-position MPNN 强制** (rule 04, synthesis §一); hotspot 必填 (rule 02); SEC 验证 oligomeric state 不可省 (synthesis §一); start C3/C4 don't try icosahedral first (< 1% success)。

## 适用场景
- design_task == symmetric_oligomer_de_novo
- 已知 symmetry (C3/C4/C5/D2/D3...)

## 不适用
- ❌ 高阶对称 first try (icosahedron < 1% success rate)
- ❌ 普通 MPNN (会破对称)
- ❌ 不带 hotspot 设计 (rule 02)

## 环境检查
```bash
echo $RFDIFFUSION_PATH
echo $PROTEINMPNN_PATH
nvidia-smi
```

## 输入契约
```json
{
  "symmetry": "c3",      // ∈ {c3, c4, c5, c6, d2, d3, d4}
  "monomer_length": 120,
  "interface_hotspot": [42, 67, 89],   // ★ MANDATORY (rule 02)
  "n_designs": 500,
  "tied_mpnn": true,                    // ★ MANDATORY (rule 04)
  "out_dir": "..."
}
```

## 输出契约
```json
{
  "n_designs_generated": 500,
  "designs": [
    {
      "design_id": "S0042",
      "structure_path": ".../complex.pdb",
      "monomer_sequence": "MKL...",   // single seq, applies to all copies
      "metrics": {
        "iPTM": 0.78, "pAE_inter_chain": 4.5, "symmetry_RMSD": 0.7,
        "monomer_pLDDT": 84.5, "SAP_score": 9.2
      },
      "passed_qc": true
    }
  ],
  "in_silico_to_in_vitro_estimate": "5-15% expression + correct oligomeric state (per protein-009)",
  "wet_lab_required": ["SEC for oligomeric state", "100 ns MD for symmetry stability"],
  "provenance": {...}
}
```

## QC gate
- iPTM ≥ 0.6 + symmetry_RMSD < 1 Å + monomer_pLDDT > 80 → promote
- High-order symmetries (D3+) — emit warn, recommend trying C3/C4 first
- SAP_score > 30 → aggregation risk warning

## 实现状态
- ✅ SKILL.md
- ✅ runner.py with --simulate + tied-MPNN precondition + symmetry sanity (CPU-side)
- 🔧 TODO (Linux/GPU): wire RFdiffusion symmetric mode + tied-MPNN
