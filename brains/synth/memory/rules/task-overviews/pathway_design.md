---
rule_id: task-overview-pathway_design
schema_version: 1
rule_type: landscape
applies_to:
  synth_tasks: [pathway_design]
  host_organisms: [ALL]
  scale: [ALL]
last_updated: 2026-04-29
---

## 异源通路设计景观

**目标**：从目标小分子（KEGG / MetaCyc 化合物）反推 enzyme set + heterologous pathway 装入 host。

**主流工具**（≥3 backend 强制）：RetroPath2.0 (KNIME / Galaxy), Cameo `pathway_prediction`, KEGG REST graph traversal, BioCyc Pathway Tools, novoStoic.

**Pathway class 速查**：
- terpenoid / sesquiterpenoid → MEP (E. coli) / MVA (yeast) precursor，FPP / GPP 关键
- polyketide → AcCoA + malonyl-CoA，PKS modular
- amino acid → 中枢代谢，OptKnock 路线
- alkaloid → 经常 plant P450，host: yeast 优选
- RiPP → ribosomal precursor，post-translational modification

**典型 pipeline**：
1. Retro-search（多 tool consensus）
2. Codon optimize for host（rule 02）
3. P450 配对 CPR（rule 11）
4. FBA 校验 flux feasibility
5. Plasmid assembly（rule 03/04 link）
6. Strain validation（HPLC / MS titer）

**典型陷阱**：
- 终产物 toxicity / 反馈抑制
- Heterologous 蛋白 misfolding（chaperone assistance）
- Cofactor 不平衡（NADPH 短缺常见）
- 强 promoter 过表达 → metabolic burden
