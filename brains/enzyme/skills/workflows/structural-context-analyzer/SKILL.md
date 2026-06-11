---
name: structural-context-analyzer
description: DSSP 二级结构 + GETAREA / Naccess RSA + DEPTH residue burial depth + 周围残基 packing 分析, 给每个残基一份完整结构上下文卡片. 输出供 design agent 区分 surface / buried / interface / loop / helix / sheet, 防止 mutation 误落 functional flexibility loop. Hard Rule 9 强制分析门控的核心 skill 之一.
---

# Structural Context Analyzer Skill

## 一句话原则
**每个候选 mutation 的 surface / buried / loop / SS 上下文必须显式拿到**, 不允许 design agent 凭"看起来在表面"做判断. 这是 anti-rule 3 (B-factor saturation 不滤 functional flexibility loop) 的执行 skill.

## 适用阶段
Design Agent 在生成 mutation 候选**之前**必须调用. 输出每个候选位的结构上下文卡片, 写入 design_artifact.

## 先检查环境
```bash
which mkdssp || which dssp     # DSSP 必装 (BioPython 也可作回退)
which freesasa                  # 或用 Naccess / GETAREA
python -c "import Bio.PDB" 2>&1
python -c "import numpy" 2>&1
# 残基埋深 (DEPTH or msms via Biopython): biopython >=1.83 支持
```

## 输入契约
```json
{
  "pdb_path": "/Volumes/T7/EnzymeAgent/data/pdb/1cel.cif",
  "chain": "A",
  "candidate_positions": [87, 149, 175, 212, 234, ...],  // 待评估的位点
  "active_site_residues": [212, 217],                     // 来自 catalytic-site-annotator
  "rsa_thresholds": {
    "buried": 0.10,            // RSA < 10% = buried
    "intermediate": 0.30,
    "exposed": 0.30             // RSA ≥ 30% = surface
  },
  "depth_thresholds": {
    "deep_core": 8.0,           // Å, > 8 Å = 深度埋藏
    "shell": 3.5
  }
}
```

## 输出契约
```json
{
  "skill_id": "structural-context-analyzer",
  "msa_path": "",
  "n_sequences": 0,
  "conservation_csv": "",
  "diagnostics": {
    "brain": "enzyme",
    "archetype": "msa_conservation"
  }
}
```

## 关键准则 (★ 强制)
1. **Loop 分类必须做**: 不能笼统说"在 loop 里"——必须区分 structural / substrate-access / regulatory / active-site lid 四类. 后三类 mutation 触发 anti-rule 3
2. **Functional flexibility loop 识别多 metric**:
   - B-factor 高 (但 anti-rule 3 警告: B-factor 单 metric 不可靠)
   - 距 active site < 5 Å
   - 距底物入口 < 5 Å
   - 高 MD RMSF (若有 MD trajectory 输入)
   - 文献已记录的 active-site lid (CAZy GH7 的 "lid", lipase 的 "α/α' lid" 等)
3. **RSA 多方法交叉**: FreeSASA / Naccess / GETAREA 三选一; 不依赖单方法
4. **DSSP 必跑**: 8 状态 secondary structure, 不只 3 状态
5. **Depth 分析**: residue burial depth 区分 surface vs deep core, 比单 RSA 更准

## 与上下游的衔接
- **上游必跑**:
  - `pdb-fetcher` → PDB 结构
  - `alphafold-plddt-analyzer` (若 X-ray 不可用) → AF 模型 + pLDDT 上下文
  - `catalytic-site-annotator` → active_site_residues 输入
- **本 skill 输出供下游**:
  - `conservation-msa-analyzer` → 联合判定 (high RSA + low conservation = top engineering target)
  - `esm-mutation-scan` → mutation 候选必须先剔除 functional flexibility loop
  - `pyrosetta-stability-scan` → 仅在 engineering_recommendation 列出的位点跑
  - `pocket-tunnel-analyzer` → 联合验证 substrate access loop

## 失败模式与排查
| 现象 | 根因 | 解法 |
|---|---|---|
| DSSP 报错 alt-loc | PDB 含多 alt conformation | 用 Biopython remove_disorder() 预处理 |
| RSA 全为 0 | PDB 缺溶剂可及面积 | 重跑 FreeSASA, 不用 PDB 内嵌字段 |
| Depth 不可计算 | msms 未装 | 退到 simpler 'distance to mean center' 方法 |
| Loop 误判 | 短 turn 被分到 loop | 至少 4 残基连续才视作 loop |
| AF model 上 RSA 偏 | side-chain 不准 | RSA 仅用 backbone 取近似值, 标 warning |

## 与 Anti-rule 的关联
- **Anti-rule 3 (B-factor saturation 不滤 functional flexibility loop)**: 本 skill 输出 functional flexibility loop 列表, design agent 必须 explicit 排除
- **Anti-rule 4 (AF + PyRosetta)**: 在 AF model 上跑本 skill 时, RSA / depth 不如 X-ray 准, 输出加 warning

## 引用与出处
- Kabsch W, Sander C. "Dictionary of protein secondary structure: pattern recognition of hydrogen-bonded and geometrical features." Biopolymers 1983;22:2577-2637. (DSSP)
- Mitternacht S. "FreeSASA: An open source C library for solvent accessible surface area calculations." F1000Research 2016;5:189.
- Hubbard SJ, Thornton JM. "NACCESS." Department of Biochemistry and Molecular Biology, University College London, 1993.
- Sun Z, Liu Q, Qu G, Feng Y, Reetz MT. "Utility of B-Factors in Protein Science: Interpreting Rigidity, Flexibility, and Internal Motion and Engineering Thermostability." Chem Rev 2019;119:1626-1665. (与 NEG-BFACTOR-sun-2019-chemrev 一致)

## Skill 版本
v1.0, 2026-04-29.
