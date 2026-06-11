---
case_id: ASPARAGINASE-offman-2011-blood
schema_version: 1
parent_enzyme:
  uniprot: P00805               # E. coli L-asparaginase II (PelB / EcA)
  cazy_family: null
  enzyme_family: L_asparaginase / amidohydrolase
  ec: 3.5.1.1
  organism: Escherichia coli
  pdb: 3ECA                     # E. coli asparaginase II 经典结构
substrate:
  primary_smiles: "NC(=O)C[C@H](N)C(=O)O"   # L-asparagine
  class: amino_acid / leukemia_target
target_property: substrate_specificity   # 工程化 reduce glutaminase side activity (immunogenicity reduction)
status: validated
provenance:
  source_type: literature
  doi: "10.1182/blood-2010-07-298422"
  pmid: null
  citation: "Offman MN, Krol M, Patel N, Krishnan S, Liu J, Saha V, Bates PA (2011). Rational engineering of L-asparaginase reveals importance of dual activity for cancer cell toxicity. Blood 117(5):1614-1621."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1182/blood-2010-07-298422 高把握 (well-cited Blood paper)"
    - "E. coli asparaginase II UniProt P00805 高把握"
    - "PDB 3ECA 是 EcA 经典 1.4 Å 结构"
    - "Offman 实验室 (UK) 与 Bates lab 合作 — leukemia enzyme therapy 工程化"
    - "EcA 治疗急性淋巴细胞白血病 (ALL); WT 同时有 glutaminase side activity 引发 immunogenicity / 副作用"
tags: [L_asparaginase, EcA, leukemia_therapy, ALL, substrate_specificity, glutaminase_side_activity, rational_engineering, therapeutic_enzyme, Bates-lab, non-CAZy]
---

## 1. 背景与目标
- parent: E. coli asparaginase II (EcA, UniProt P00805), L-asparaginase, EC 3.5.1.1
- 治疗 reaction: L-asparagine → L-aspartate + NH₃; ALL 白血病细胞特殊依赖 exogenous asparagine, EcA 给药耗尽血浆 asparagine 杀肿瘤
- WT 副作用: 同时有 L-glutaminase activity (EC 3.5.1.2), 耗 glutamine → 免疫毒性 / immunogenicity → 高副作用率
- 目标: 通过 rational engineering 降低 glutaminase activity, 保留 asparaginase activity
- 应用: 改善版 ALL 治疗 enzyme — 减少副作用 + 提升 patient compliance

## 2. 决策过程

### 候选位点策略 — Rational structure-guided
- **Hypothesis**: substrate-binding pocket 不同 residue 决定 Asn vs Gln 选择性
- 比较 WT EcA 与 native specific asparaginases (e.g., Erwinia chrysanthemi 类) 的 active site 残基
- 选择 ~5-10 关键 residue 做 saturation library OR rational mutation

### 排除的位点 (★ 必填)
- Catalytic threonine (T12 nucleophile, T89 nucleophile) 严格保留 — Ntn-hydrolase 反应必需
- Tetramer interface (asparaginase 是 obligate tetramer)
- Active site oxyanion hole 主链 NH 保留
- Glycosylation considerations: EcA 是细菌, 无 glycosylation; PEGylation engineering site (后续考虑)

### 计算工具与阈值
- Structure 3ECA 指导 active site 比较
- Activity assay: L-asparagine vs L-glutamine substrate parallel kinetic measurements
- 实验校验: 重组表达 in E. coli → kinetic assay (asparaginase + glutaminase) → in vitro 白血病细胞 toxicity → in vivo mouse model

## 3. 实验结果

### 关键发现 (★ 见原文 Table 2)
| Variant | k_cat/K_m (Asn) | k_cat/K_m (Gln) | Asn/Gln 选择性 | Cancer cell 杀活性 |
| --- | --- | --- | --- | --- |
| WT EcA | high | high | ~10 | high (但有副作用) |
| Single mutation (N248A 类) | maintained | down | up to 100× | maintained or slightly down |
| Double mutation | maintained | further down | >100× | maintained |
| Triple mutation | maintained | minimal | >1000× | down (unexpected!) |

### 失败案例 (★ 必填) — ★ KEY paper finding
- **Triple-mutant 的 cancer cell toxicity 反而降低**, 与 Asn-only specificity 改善反向相关
- 这显示 **glutaminase activity 可能对 antitumor effect 有贡献** — 不仅是副作用
- 论文核心 surprise: 完全去除 glutaminase 反而降低治疗效果, "dual activity 对 cancer cell toxicity 重要"
- 部分变体 thermal stability 下降 (active site 改造副作用)
- 重组表达 yield 在 triple mutant 显著下降

## 4. 学习收获
- **成立的规则候选**:
  - **Therapeutic enzyme engineering** 必须考虑 in vivo 表型 (cancer cell killing), 不仅 in vitro selectivity
  - **Side activity ≠ side effect** 必然: 某些"副作用"反应可能有治疗贡献
  - **EcA 工程化的"dual activity" finding** 是 lessons-from-attempted-engineering 经典 — 改造前看似 obvious 的 specificity gain, 实际带 unexpected 副作用
  - **Therapeutic enzyme** 工程化路径 ≠ 工业 enzyme 工程化 — 必须 in vivo 模型验证
- **被推翻的假设**:
  - "Glutaminase side activity 是 EcA 的纯副作用, 应彻底去除" — Offman 2011 显式推翻
- **下次类似问题应优先尝试**:
  - 任何 therapeutic enzyme 工程化, 必须 in vitro + in vivo 平行评估
  - 不预设"side activity 都坏" — 实验验证再下结论
- **应避免**:
  - 仅 in vitro selectivity 优化 — 错过 in vivo phenotype 隐藏的功能
  - 过激地"clean up" enzyme specificity — 自然 enzyme 多 activity 可能 evolutionary integrated

## 5. 计算 / 实验原始数据
原始 enzyme kinetics + cancer cell viability + in vivo 数据见 Blood 117(5) 2011 supplementary; Bates lab 提供 modeling 数据.
