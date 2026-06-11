---
case_id: crispr-005-cas12a-multiplex
schema_version: 1
edit_type: multiplex_knockout
target_gene: TRAC
target_organism: hg38
cell_context: primary_T
editing_system: AsCas12a
delivery_method: RNP_electroporation
tools:
- CRISPOR (Cas12a mode)
- DeepCas12a
- Cas-OFFinder
- CRISPResso2
key_paper_doi: 10.1038/s41587-020-0741-7
status: validated
provenance:
  source_type: literature
  doi: 10.1038/s41587-020-0741-7
  citation: Liu P et al. (2020) Nat Biotechnol 38:1431-1440 — AsCas12a multiplex CAR-T
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- multiplex_knockout
- primary_T
- AsCas12a
- CAR-T
- TRAC
- B2M
- CD52
- allogeneic
editing_system_list:
- AsCas12a
- LbCas12a
- enAsCas12a
---

# Cas12a multiplex KO：allogeneic CAR-T 三基因同时 KO

## Background
Allogeneic ("off-the-shelf") CAR-T 需 KO TRAC（避 GVHD）+ B2M（避 host HLA 排斥）+ optional CD52（让 alemtuzumab 选择性消除 endogenous T）。**Cas12a 优势**：(1) crRNA array 串联（一条 transcript 多个 spacer，自切割）；(2) staggered cut（5' overhang）增 NHEJ 高效；(3) TTTV PAM AT-rich 区域可达。

## What I actually did
1. **TTTV PAM 选**：每 target gene 在 early constitutive exon 找 PAM
2. **crRNA array 设计**：5'-DR-spacer1-DR-spacer2-DR-spacer3-3'（DR = direct repeat scaffold，~19-20 nt）；Cas12a 自切 array 释放单 crRNA
3. **AsCas12a vs LbCas12a**：AsCas12a TTTV 更严格但 specificity 高；LbCas12a 更宽 PAM 但 off-target 多
4. **enhanced AsCas12a (enAsCas12a)**：拓宽 PAM 到 TYCV/TATV，活性提升
5. **Delivery**：electroporation RNP（protein + crRNA）；mRNA+LNP for in vivo；lentivirus 不推荐（Cas12a 持续表达 off-target 风险）
6. **Triple KO efficiency**：T cell typical 单 KO ~80%，triple KO 三个都 KO ~40-50%（multiplicative）
7. **Validation**：flow cytometry 三 marker（TCR/HLA-I/CD52）三阴性 cell sort + amplicon-seq 各 locus

## ★ 排除/不做的事
- **SpCas9 当 multiplex**：可以但 sgRNA 各自 cassette + U6 启动子 → vector 大；Cas12a array 紧凑
- **TTTV PAM 不严**：松 PAM (TTTN) 增 off-target；en/eAsCas12a 改进版才用宽 PAM
- **Lentivirus delivery 临床用**：integration risk + Cas12a 持续表达 → 改 RNP/mRNA
- **Triple KO 不分析 single-positive 残留**：1% 有 TCR T cell 进体内 = GVHD 风险
- **CD52 KO 不结合 alemtuzumab in vivo plan**：design 时漏 selective survival 设计 = 浪费 KO
- **B2M KO 不补 HLA-E**：完全 HLA-I 消除 → NK cell 杀伤；HLA-E knock-in 同时做避

## ★ 失败模式
- **Triple KO 三阴性 cell pool 小**：从 100% T cell → 40-50% pure triple KO，sort 后才能 expand
- **Translocation**：3 个 Cas12a cut 同时，cross-locus translocation rate 0.1-1%
- **Off-target in essential gene**：Cas12a sgRNA off-target 在 KO panel 中累计
- **TCR γδ residual**：TRAC KO 仅消 αβ T cell；γδ 可能保留产生免疫
- **CRISPResso2 amplicon overlap**：multiplex amplicon-seq 中 amplicon 重叠会混淆
- **Allogeneic CAR-T memory**：KO 是必需但远不够，long-term in vivo persistence 是另一问题

## Lessons → seeds for rules
1. **Multiplex KO 用 Cas12a array** 比 multi-sgRNA Cas9 更紧凑
2. **enAsCas12a** for PAM 灵活性 + specificity 平衡
3. **RNP delivery** for clinical（vs lenti）
4. **Triple KO 必 sort triple-negative**：bulk 不达临床要求
5. **Translocation rate 报告**：单 KO < 0.1%；triple 累计需 amplicon-seq 跨 locus 验证
6. **Side effects 设计**：B2M KO ↔ HLA-E knock-in；TCR KO ↔ γδ residual 评估
