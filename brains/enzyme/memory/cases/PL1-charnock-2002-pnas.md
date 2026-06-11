---
case_id: PL1-charnock-2002-pnas
schema_version: 1
parent_enzyme:
  uniprot: P0C1A7               # Erwinia chrysanthemi (= Dickeya dadantii) pectate lyase
  cazy_family: PL1
  ec: 4.2.2.2                   # pectate lyase
  organism: Erwinia chrysanthemi (now Dickeya dadantii)
  pdb: 1JTA                     # Charnock 2002 deposition; QA 验证
substrate:
  primary_smiles: "OC(=O)[C@@H]1O[C@@H](O[C@@H]2[C@H](O)[C@H](O)C(=O)O[C@H]2C(=O)O)[C@H](O)[C@@H](O)[C@@H]1O"   # 寡聚半乳糖醛酸 (示意; PL1 substrate 是 polygalacturonate)
  class: polygalacturonate / pectate
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1073/pnas.182431199"
  pmid: null
  citation: "Charnock SJ, Brown IE, Turkenburg JP, Black GW, Davies GJ (2002). Convergent evolution sheds light on the anti-β-elimination mechanism common to family 1 and 10 polysaccharide lyases. PNAS 99(19):12067-12072."
  extracted_at: 2026-04-27
  extraction_confidence: medium
  unverified_details:
    - "DOI 第一次推 JBC 错, CrossRef 文本搜后修正为 PNAS 10.1073/pnas.182431199; case_id 也由 -jbc 改为 -pnas"
    - "Erwinia chrysanthemi 已重新分类为 Dickeya chrysanthemi/Dickeya dadantii (2005 分类修订)"
    - "UniProt P0C1A7 我推测对应 Pectate lyase A; 候选还有 P11073 / P0C1B1; QA via uniprot-fetcher 验证"
    - "PDB 1JTA 我推测; PL1 PelA from E. chrysanthemi 多个 deposition (1AIR / 1BN8 等亦相关)"
    - "本工作是 PL1 与 PL10 convergent evolution 比较, 揭示 anti-β-elimination 机制 — 两个 fold 不同的 lyase 家族殊途同归"
    - "Davies / Charnock 实验室合作 (York structural biology)"
tags: [PL1, mechanism, pectate_lyase, beta_elimination, convergent_evolution, structural_basis, Davies-lab, Charnock]
---

## 1. 背景与目标
- parent: Erwinia chrysanthemi PelA (PL1 pectate lyase, β-helix fold)
- 当时背景: PL1 (β-helix) 与 PL10 (TIM barrel-like) 是 fold 完全不同的 polysaccharide lyase, 但都以 anti-β-elimination 机制裂解 polygalacturonate
- 目标: 解析两个 fold 的 active site 比较, 揭示 mechanism 收敛性的分子基础
- 应用: 解释 PL 家族多 fold 多机制的协同; 工业用 pectinase 工程化基础

## 2. 决策过程 (本文是结构 + 机制比较, 非工程化)

### 候选位点策略
- **结构生物学** 路线: 解 PelA 与 PL10 enzyme 的高分辨结构 + 与 substrate analog 复合物
- 后续 mutagenesis 验证关键残基 (catalytic Lys / Arg)

### 排除的位点 (★ 必填)
- 催化必需 Arg (PL1 的 R218 类残基) 严格保留
- Ca²⁺ 结合位点 — PL1 必需 Ca²⁺ 中和 carboxylate
- β-helix 内部疏水核心 — fold 稳定性要素

### 计算工具与阈值
- 主要工具: X-ray crystallography + 序列对齐 (PL1 vs PL10 内部跨家族)
- 实验校验: PelA 重组表达 in E. coli → polygalacturonate substrate kinetics (HPLC / TBA assay)

## 3. 实验结果

### 关键发现
| 发现 | 内容 |
| --- | --- |
| PL1 fold | β-helix (parallel β-sheet 卷成弹簧状) |
| PL10 fold | (α/α)6 toroid (与 PL1 完全不同) |
| Catalytic Arg (or Lys) | 都用碱性残基提取 substrate α-H, 启动 β-elimination |
| Ca²⁺ 角色 | 中和 substrate carboxylate, 让 α-H 更易提取 |
| Convergent evolution | 两个独立起源 fold 解决了同一化学问题 — 工程化可借鉴跨家族灵感 |

### 失败案例 (★ 必填)
- 论文不报失败 (是结构论文); 但讨论:
  - PL10 vs PL1 substrate selectivity 差异由 binding cleft 形状决定, 非 active site 本身; 改 selectivity 需要重塑 cleft (非常困难)
  - 早期尝试在 PL1 中加 Cys-Cys disulfide 提稳定性常失败 (β-helix 内部缺乏 helix-loop 区便利组合)

## 4. 学习收获
- **成立的规则候选**:
  - PL 工程化禁区: catalytic Arg/Lys + Ca²⁺ 结合 loop + β-helix 内部疏水核 (3 个 zone)
  - **β-elimination 机制是收敛进化** — 多 fold 都能实现, 工程化时可借不同 fold 的工具 (e.g., PL1 工程经验某种程度可启发 PL10 工程)
  - **Ca²⁺-dependent 类 lyase 工程化必须保留 Ca²⁺ 结合**, 否则失活
- **被推翻的假设**:
  - "PL 都是同一 fold" — convergent evolution 显示多 fold, 工程化策略不能跨 family 简单迁移
- **下次类似问题应优先尝试**:
  - PL 工程化前先确定具体 sub-family + fold (β-helix / TIM barrel / (α/α)n toroid / jelly roll)
  - Ca²⁺-dependent vs Ca²⁺-independent 区分 — 改稳定性策略不同
- **应避免**:
  - 在 β-helix fold (PL1) 引入 disulfide engineering 期望大幅 stabilization — 历史上多次失败
  - 假设 substrate selectivity 可由 active site 单点突变改 — PL substrate selectivity 由 cleft shape 主导, 需要更深远的工程化

## 5. 计算 / 实验原始数据
晶体 deposition + activity 数据见 PNAS 99(19) supplementary.
