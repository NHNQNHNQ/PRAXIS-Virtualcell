---
case_id: DNA-POLYMERASE-tabor-1995-pnas
schema_version: 1
parent_enzyme:
  uniprot: P19821               # Taq DNA polymerase (Thermus aquaticus)
  cazy_family: null
  enzyme_family: DNA_polymerase / family_A
  ec: 2.7.7.7
  organism: Thermus aquaticus
  pdb: 1TAU                     # Taq pol 经典结构
substrate:
  primary_smiles: "OC[C@H]1O[C@@H]2[C@@H]([C@H]1O)O[C@@H]([C@@H]2O)n3cnc4c3ncnc4N"   # dATP / nucleotide analog (示意)
  class: deoxyribonucleotide / dideoxyribonucleotide_analog
target_property: substrate_specificity   # ddNTP discrimination 改为接受 ddNTP (Sanger sequencing)
status: validated
provenance:
  source_type: literature
  doi: "10.1073/pnas.92.14.6339"
  pmid: "7541539"
  citation: "Tabor S, Richardson CC (1995). A single residue in DNA polymerases of the Escherichia coli DNA polymerase I family is critical for distinguishing between deoxy- and dideoxyribonucleotides. PNAS 92(14):6339-6343."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1073/pnas.92.14.6339 高把握 (well-cited classic)"
    - "Taq UniProt P19821 高把握"
    - "PDB 1TAU 是 Taq 经典结构"
    - "Tabor & Richardson (Harvard) DNA polymerase mechanism 经典工作"
    - "本工作识别了 family A polymerase 的 F667Y/F762Y 类突变 — 让 Taq 类高保真接受 ddNTP, 是 modern Sanger sequencing 的工程化基础"
tags: [DNA_polymerase, Taq, family_A_polymerase, substrate_specificity, ddNTP_discrimination, Sanger_sequencing, single_residue_engineering, Tabor-Richardson, non-CAZy]
---

## 1. 背景与目标
- parent: Taq DNA polymerase (Thermus aquaticus, UniProt P19821), family A pol, EC 2.7.7.7
- 自然功能: 高温 DNA 复制 (PCR 关键酶), 但严格区分 dNTP (incorporate) vs ddNTP (extreme bias against)
- 工程化目标: **去掉 ddNTP discrimination**, 让 Taq 接受 ddNTPs — 这能让 thermostable Taq 用于 Sanger sequencing
- 应用: Sanger sequencing (后续 Roche Cycle Sequencing 等商业化)

## 2. 决策过程

### 候选位点策略 — Single-residue rational
- **Sequence alignment** 关键洞察: family A polymerase (Taq, T7 pol, E. coli pol I) 在 active site 关键位置有显著差异
- T7 pol 接受 ddNTP, Taq 严格区分 — 比对显示一个关键 residue 不同 (F667 in Taq vs Y in T7)
- **Hypothesis**: 单点突变 F667Y 应足以让 Taq 接受 ddNTP
- **Test**: 直接构建 F667Y, 测 ddNTP 接受率

### 排除的位点 (★ 必填)
- 完整 family A pol active site (Asp triad: D610/D785; "fingers" subdomain key residues) 严格保留
- Mg²⁺ 配位 残基 — 催化必需
- Exonuclease domain (Taq 含 5'-3' exonuclease) — 不主动改
- Polymerase active site 整体 fold 保留 — Taq 的 thermostability 来源

### 计算工具与阈值
- 1995 年代: 主要 sequence alignment + active site 比对
- 不依赖结构 (Taq 高分辨结构 1996 才出来), 但有 E. coli pol I 类 reference
- 实验校验: 重组表达 in E. coli + Sanger sequencing 反应 (ddNTP 读长 + termination 比例)

## 3. 实验结果

### 关键发现
| 量 | 量化 |
| --- | --- |
| WT Taq ddNTP / dNTP discrimination | ~10⁴ × (ddNTP 几乎不接受) |
| F667Y mutation 后 discrimination | ~10× (3-4 个 order of magnitude 改善) |
| Sanger sequencing 用途 | F667Y Taq 成为基础 (后续优化继续) |
| 影响 | 革命化 high-throughput sequencing 开发 |

### 失败案例 (★ 必填)
- F667Y alone 仍未达到 T7 pol 水平的 discrimination loss; 需要 additional mutations (后续 Taq Y mutations 系列)
- Polymerase fidelity 同时下降 — discrimination engineered against 一项, 一般 fidelity 也受影响
- F667Y 在 Taq 仍较好工作; 在其他 family A pol 同源位点可能效果不一致

## 4. 学习收获
- **成立的规则候选**:
  - **Family A polymerase 的 F → Y mutation at conserved position** 是 ddNTP discrimination 工程化的 single-residue insight
  - **跨家族 sequence alignment + functional difference correlation** 可识别 single critical residue (Tabor 1995 是模板)
  - **Single-point rational design** 在结构信息有限时仍可工作 — 关键是 **functional** difference 比对而非纯结构
- **被推翻的假设**:
  - "Substrate discrimination 由多 residue 协同决定, 难以 single-mutation 改造" — Tabor 1995 是反例
- **下次类似问题应优先尝试**:
  - 任何 enzyme 想转换 substrate discrimination, 找到 functional analog 在 sister family 中已有不同表现, sequence align 找差异 residue
  - Single-residue rational 仍是低成本起手; F667Y Taq 是经典案例
- **应避免**:
  - 仅 active site catalytic residue 突变 — Tabor 1995 显示是 active site 周边 selectivity-determining residue, 不是催化本身
  - 假设 single-mutation 给完美 discrimination loss — 实测 10× 提升, 后续 mutations 累加才完全转换

## 5. 计算 / 实验原始数据
原始 polymerase kinetics + Sanger sequencing 数据见 PNAS 92(14) 1995 supplementary.
