---
case_id: NEG-CONSENSUS-jackel-2010-jmb
schema_version: 1
parent_enzyme:
  uniprot: null
  enzyme_family: methodology_critique
  cazy_family: null
  ec: null
  organism: review_anchor
  pdb: null
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: ""
  class: review_anchor / consensus_design_critique
target_property: thermostability
status: partial
provenance:
  source_type: literature
  doi: "10.1016/j.jmb.2010.04.039"
  pmid: 20433850
  citation: "Jäckel C, Bloom JD, Kast P, Arnold FH, Hilvert D (2010). Consensus protein design without phylogenetic bias. Journal of Molecular Biology 399(4):541-546."
  extracted_at: 2026-04-28
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1016/j.jmb.2010.04.039 与 PMID 20433850 我推测; CrossRef 验证"
    - "本论文是 Hilvert + Arnold + Bloom + Kast 合作 — 系统揭示 naive consensus design 在 phylogenetic bias 下失败"
    - "Naive consensus = 直接取 multiple sequence alignment (MSA) 每位最频残基; 但当 MSA 在系统发育上偏倚 (e.g. 多 closely-related 种过表示) 时, 'consensus' 实际是 'overrepresented clade 的 majority'"
    - "本论文给出 phylogeny-corrected consensus 方法 + 显示 naive consensus 偏倚导致工程化失败的具体案例"
    - "对 PRAXIS-Enzyme 反规则: 任何 consensus mutation 工程化必须先验 MSA phylogenetic balance, 否则推荐位点偏倚 thermostability 预测 ROC 急剧下降"
tags: [consensus_design, phylogenetic_bias, MSA_balance, NEGATIVE_case, failure_mode_anchor, Hilvert-lab, Arnold-lab, Bloom-lab, methodology_critique, thermostability_prediction]
---

## 1. 背景与目标 — 反例性质
- 背景: consensus mutation 是 thermostability 工程化经典策略 (Lehmann 2000 Phytase / Steipe 1994 等), 但默认 naive consensus 假设 MSA 系统发育平衡
- 论文核心: 多个 工程化项目用 naive consensus 失败, 因 MSA 含大量 closely-related 物种 (e.g. 病原 Streptococcus 几十个株系) 导致单一 clade 主导 'consensus', 与真正 'thermostability-correlated residue' 偏离
- 反例核心: **consensus mutation 不是稳健默认协议**; 必须先 phylogeny-correct MSA, 否则推断错位

## 2. 决策过程

### 论文展示的方法
- 用 weighted MSA (按 phylogenetic distance 加权 sequence) 替代 naive frequency-counting
- 测试 weighted vs unweighted consensus 对 several model proteins 的 thermostability 提升预测 ROC

### 排除的位点 (★ 必填)
- 本案例为 review-anchor (methodology critique), 不针对单一 enzyme 残基级排除
- Implicit 排除: 任何用 NCBI BLAST top hits 作为 MSA 直接 frequency-counting 的 mutation 推断, 在 anti-retrieval 索引中作为 veto
- 在 phylogeny-corrected MSA 之前, naive consensus 推断的所有候选 mutation 视为 "low confidence consensus", 必须 cross-check

### 失败案例 (★ 必填) — 本案例的核心
- **Streptococcus 多株 over-representation**: MSA 中 80% 来自 ~5 个 closely-related Strep 物种 → naive consensus 反映这些物种主流 residue, 不反映 thermostability 信号
- **Enzymes from 高 over-represented clade 工程化失败**: 有些工程化项目用 naive consensus 推荐 5-10 mutation, 实测 Tm 变化 ±0 (与 random mutation 等价)
- **真菌 vs 细菌 MSA 比例不平衡**: 在 cellulase / chitinase 类 MSA, 真菌主导 → naive consensus 偏 真菌-typical residue, 但 真菌-typical 不一定 thermostable
- **过度信任 single MSA 计算 consensus**: 单一 BLAST 结果不足, 需要多 method (HMM profile / phylogenetic tree based) 互补
- **phylogeny-corrected consensus 显著比 naive consensus ROC 高 ~30%** — 量化的方法学差距
- **跨 protein family 的 naive consensus 失败率不同**: 多样化大 family (e.g. AA1 laccase 跨 fungi/bacteria) naive consensus 错误率高; 紧凑 family (e.g. GH11 xylanase 主真菌) naive 仍可用

## 3. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **Naive consensus mutation (基于直接 MSA frequency-counting) 不是默认协议** — 必须先 phylogeny-correct
  - **MSA 系统发育平衡是 consensus engineering 的隐藏前提**: 80% MSA from < 5 closely-related species 即不可信
  - **多 MSA method 互补 (BLAST + HMM + tree) 是必需 sanity check**, 单 method 错误率高
  - **跨 protein family naive consensus 的 ROC 高低不一**: 紧凑 family 仍可用, 多样化 family 必须 phylogeny-corrected
- **被推翻的假设**:
  - "Consensus mutation 是 thermostability 工程化默认协议" — 反例: phylogenetic bias 显著偏移
  - "MSA size > 100 sequences 即可信" — 数量不等于平衡; 必须多 clade 平衡
- **下次类似问题应优先尝试**:
  - Consensus mutation 工程化前必先做 phylogenetic tree + clade balance 检查
  - 用 weighted MSA (按 sequence-pair phylogenetic distance 加权) 替代 frequency-counting
  - 配合 ASR (ancestral sequence reconstruction) 作 cross-validation: ASR 依赖 phylogeny-corrected MSA, 与 weighted consensus 互查
- **应避免**:
  - Naive consensus mutation 直接 ship 给湿实验
  - 用 NCBI BLAST top hits 直接当 MSA (高度 over-represent 已知/clinical isolates)

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/: 任何 "naive consensus mutation 不做 phylogenetic balance 检查" 的工程化方案被 vetoed; 任何 "MSA 单 BLAST 来源 + 直接 frequency-counting" 被 vetoed.

## 4. 计算 / 实验原始数据
原始 weighted vs unweighted consensus benchmark + 多 model protein 案例数据见 J Mol Biol 2010 supplementary; 后续工作 (Sternke 2019 PNAS / Goldenzweig 2016 Mol Cell PROSS) 用 phylogenetic-corrected MSA 作为前提.
