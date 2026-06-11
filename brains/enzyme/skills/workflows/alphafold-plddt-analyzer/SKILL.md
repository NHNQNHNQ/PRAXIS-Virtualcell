---
name: alphafold-plddt-analyzer
description: 拉取 AlphaFold2/AFDB 模型, 做 pLDDT 区域诊断 + PAE matrix 分析 + 跨域置信检查, 输出 reliable / unreliable 区域与可工程化范围。**关键**: 强制把 pLDDT < 70 的活性位点 / loop 标为禁动区, 与 anti-rule 4 (AF model + 单一方法 ddG (例如 PyRosetta cartesian_ddg) 单跑) 联动. Hard Rule 9 强制分析门控的核心 skill 之一.
---

# AlphaFold pLDDT Analyzer Skill

## 一句话原则
**AF model 不是 X-ray 的替代品**. 用 AF 之前必须先按 pLDDT 区域诊断, 把 pLDDT < 70 的关键 loop / 活性位点写入 do-not-engineer 列表; 任何 "AF + PyRosetta ddG 单跑" 的工程化路线被 anti-rule 4 直接 vetoed.

## 适用阶段
Design Agent 在 X-ray 结构不可用 / 不全 / 缺 loop 时调用. 必须在 mutation 候选生成**之前**调用并把诊断写入 design_artifact.

## 先检查环境
```bash
which curl                    # 拉 AFDB JSON / PDB
python -c "import biotite.structure.io.pdbx as p" 2>&1 || echo "缺 biotite"
python -c "import numpy" 2>&1
# AFDB 拉取走 https://alphafold.ebi.ac.uk/files/AF-{accession}-F1-model_v4.pdb
```

## 输入契约
```json
{
  "uniprot_accession": "P62694",        // AFDB 主键
  "or_local_pdb": "/path/to/af_model.pdb",
  "active_site_residues": [212, 217],   // 必填: 用 catalytic-site-annotator 输出
  "interface_residues": [],              // 可选: 寡聚界面
  "key_loops": [[180, 195]],             // 可选: 已知关键 loop
  "plddt_thresholds": {
    "high": 90,                          // pLDDT ≥ 90: 可信结构, 可作 X-ray 替代
    "confident": 70,                     // 70-90: 可信主链, side chain 略糊
    "low": 50,                            // 50-70: 不可作 ddG 输入
    "very_low": 0                        // < 50: backbone 不可信, 通常是 IDR
  }
}
```

## 输出契约
```json
{
  "skill_id": "alphafold-plddt-analyzer",
  "sequence": "",
  "model_path": "",
  "plddt_mean": 0.0,
  "ptm": 0.0,
  "n_residues": 0,
  "runtime_sec": 0.0,
  "diagnostics": {
    "brain": "enzyme",
    "archetype": "structure_predict"
  }
}
```

## 区域诊断阈值（基于 Tunyasuvunakool 2021 + 社区评估 Akdel 2022）
- **pLDDT ≥ 90**: 可信 backbone + side-chain (DALI 类比 X-ray ~1.5 Å); 可作 X-ray 替代用于 mutation 排序
- **70 ≤ pLDDT < 90**: 可信 backbone, side-chain 偶有偏 (~0.5-1 Å RMSD); 可作 visualization, 不建议作 ddG 唯一输入
- **50 ≤ pLDDT < 70**: backbone 也开始不可信; 不能用于 mutation engineering
- **pLDDT < 50**: 通常对应 IDR (intrinsically disordered region) 或 signal peptide 切除区; 完全不可用作结构信息

## 关键检查 (★ 强制)
1. **active_site_check**: 输入的 active_site_residues (从 catalytic-site-annotator 拿) 必须全部 pLDDT ≥ 70, 否则 WARN; ≥ 80 才 PASS
2. **AF Multimer 时 PAE 检查**: 域间 PAE 必须 < 10 Å, 否则域间相对位置不可信
3. **pLDDT < 70 区域强制写入 use_xray_first_required**: design agent 不得在这些位点提候选

## 与上下游的衔接
- **上游必跑**:
  - `uniprot-fetcher` → 拿到 UniProt accession
  - `catalytic-site-annotator` → 拿到 active_site_residues
  - 可选 `pdb-fetcher` → 检查是否有 X-ray 结构覆盖
- **本 skill 的输出是其它结构敏感 skill 的前置**:
  - `pyrosetta-stability-scan` 在 AF model 上必须仅扫 engineering_zone.safe_for_mutation_with_AF_only
  - `pocket-tunnel-analyzer` 在 AF model 上需先确认隧道入口处 pLDDT
  - `proteinmpnn-design-skill` 类似

## 失败模式与排查
| 现象 | 根因 | 解法 |
|---|---|---|
| AFDB 404 | accession 不在 AFDB | 退用 ESMFold / Boltz-1 / ColabFold 本地 |
| 全局 pLDDT < 70 | 难折叠蛋白 / 多 IDR | 不建议工程化, 标 "AF unsuitable for this protein" |
| active site pLDDT 低 | AF 在罕见 fold 上不准 | 必须先解 X-ray (或借同源 PDB structural alignment) |
| 域间 PAE 高 | 多域蛋白域间相对位置不准 | 单域分别工程化, 不跨域 |
| AlphaFold-Multimer 报错 | 寡聚化 stoichiometry 错 | 与 catalytic-site-annotator 的 oligomerization 字段交叉验证 |

## 与 Anti-rule 的关联 (★)
- **Anti-rule 4**: 任何 "AF model + 单一方法 ddG (例如 PyRosetta cartesian_ddg) 单跑" 触发. 本 skill 必须把 anti_rule_4 warning 写到输出, design agent 必须 acknowledge.
- **Anti-rule 8**: 在 cofactor / heme / metal site 上用 AF model 做 docking 触发.
- **Anti-rule 10**: AF + PyRosetta top-1 直接 ship 不验证触发.

## 引用与出处
- Jumper J et al. "Highly accurate protein structure prediction with AlphaFold." Nature 2021;596:583-589.
- Akdel M et al. "A structural biology community assessment of AlphaFold2 applications." Nat Struct Mol Biol 2022;29:1056-1067.
- Buel GR, Walters KJ. "Can AlphaFold2 predict the impact of missense mutations on structure?" Nat Struct Mol Biol 2022;29:1-2. (与 NEG-AFMUTATION-buel-2022 一致)

## Skill 版本
v1.0, 2026-04-29.
