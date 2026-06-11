---
name: catalytic-site-annotator
description: 自动定位催化残基 / 辅因子配位 / 金属位 / 二硫键 / 寡聚界面, 输出强制 excluded_positions 列表。整合 CSA (Catalytic Site Atlas) / M-CSA / EzCatDB / UniProt feature table / CAZy active-site annotation 多源. 是 Hard Rule 4 (结构与催化要素强制确认) + Hard Rule 9 (强制分析门控) 的核心 skill.
---

# Catalytic Site Annotator Skill

## 一句话原则
**没有催化残基 / 辅因子位的明确清单, 不允许进入 design 阶段**. 这是 Hard Rule 4 与 Hard Rule 9 共同的入口闸门——把"agent 凭印象推 catalytic Asp/Glu"的失败模式从源头堵住.

## 适用阶段
Scoping / Design 阶段强制调用. 输出直接进入 design_artifact 的 `excluded_positions` 字段, review agent 检查每个 mutation 候选都不在此列表中.

## 先检查环境
```bash
which curl                                # 拉 CSA / M-CSA REST API
python -c "import requests" 2>&1
# CSA: https://www.ebi.ac.uk/thornton-srv/databases/CSA-2023/  
# M-CSA: https://www.ebi.ac.uk/thornton-srv/m-csa/api/
# UniProt feature: https://rest.uniprot.org/uniprotkb/{accession}
```

## 输入契约
```json
{
  "uniprot_accession": "P62694",
  "pdb_id": "1CEL",                          // 可选, 用于 CSA / M-CSA 主查询
  "ec_number": "3.2.1.176",
  "cazy_family": "GH7",                      // 可选, 触发 CAZy 家族特定催化模式
  "include_sources": [
    "uniprot_features",                       // ACT_SITE / BINDING / METAL / DISULFID / SITE
    "csa",                                    // Catalytic Site Atlas
    "m_csa",                                  // Mechanism and Catalytic Site Atlas
    "cazy_landscape_rule",                    // 从 memory/rules/cazy-class-overviews/ 拉 mask
    "interpro_active_site",                   // InterPro 域注释
    "interface_residues_from_pdb"            // 从 PDB 复合物自动算界面
  ]
}
```

## 输出契约
```json
{
  "skill_id": "catalytic-site-annotator",
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
1. **多源 consensus**: 一个位点至少 2 个来源都标为催化或辅因子, confidence = high
2. **Second-shell 警告**: 催化残基 5 Å 内的所有非 backbone 残基进 second_shell, design agent 默认避开
3. **Disulfide 配对**: 任一 Cys 进 excluded_positions 时, 其配对 Cys 也必须进 (拆 disulfide = 失活)
4. **Oligomeric interface**: 若蛋白以二聚体 / 四聚体活性形式工作 (CSA / M-CSA / 文献标注), 界面残基必须排除
5. **CAZy family-specific motif**: GH7 的 EE motif, GH18 的 DXE motif, GT-A 的 DXD motif, AA10 的 His brace 等家族标志必须进 excluded_positions

## 与上下游的衔接
- **上游必跑**:
  - `uniprot-fetcher` → 必备 UniProt feature
  - `pdb-fetcher` → PDB metadata + structure
  - `cazy-crawler` → 家族归属
- **本 skill 输出强制供下游**:
  - `conservation-msa-analyzer` → 验证保守性是否一致 (催化残基应高度保守)
  - `esm-mutation-scan` → mutation 候选必须先剔除 excluded_positions
  - `pyrosetta-stability-scan` → ddG 扫描时严格不扫 excluded_positions
  - `pocket-tunnel-analyzer` → 标 active-site 入口

## 失败模式与排查
| 现象 | 根因 | 解法 |
|---|---|---|
| CSA / M-CSA 无该 PDB 条目 | 罕见酶 / 新发现 | 退到 UniProt feature + 同源 PDB | 
| 多源给出不同催化残基 | 突变体 PDB / 错位编号 | 报 ambiguous, 强制人审 |
| 寡聚化状态不清楚 | 单 chain PDB | 走 PDB AssemblyID (BU) 重查 |
| 编号偏移 | signal peptide 切除 | 必须用 mature protein 编号一致地映射 |
| CAZy 家族无 landscape rule | 数据库未覆盖 | 走通用 EC 类策略, 标 "low coverage" |

## 与 Anti-rule / Hard Rule 的关联
- **Hard Rule 4**: 本 skill 是 Rule 4 的执行 skill — 结构与催化要素的"强制确认"由本 skill 完成
- **Anti-rule 1-12**: design 阶段任何候选若触发 catalytic_residue_in_candidate_list, 直接 reject; 这是 Anti-rule 系统的最高优先级守门
- **Hard Rule 9**: 是强制分析门控的入口 — 没跑过本 skill, 后续 skill 链断

## 引用与出处
- Furnham N et al. "The Catalytic Site Atlas 2.0: cataloging catalytic sites and residues identified in enzymes." Nucleic Acids Res 2014;42:D485-D489.
- Ribeiro AJM et al. "Mechanism and Catalytic Site Atlas (M-CSA): a database of enzyme reaction mechanisms and active sites." Nucleic Acids Res 2018;46:D618-D623.
- UniProt Consortium. "UniProt: the Universal Protein Knowledgebase in 2025." Nucleic Acids Res 2025;53:D609-D617.
- Lombard V et al. "The carbohydrate-active enzymes database (CAZy) in 2013." Nucleic Acids Res 2014;42:D490-D495.

## Skill 版本
v1.0, 2026-04-29.
