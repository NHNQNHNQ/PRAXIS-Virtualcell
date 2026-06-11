---
case_id: crispr-010-aav-in-vivo-delivery
schema_version: 1
edit_type: in_vivo_gene_therapy
target_gene: PCSK9
target_organism: macFas5
cell_context: hepatocyte_in_vivo
editing_system: SaCas9
delivery_method: AAV
tools:
- AAV serotype selection
- dual-AAV strategies
- Verve VERVE-101 case
key_paper_doi: 10.1161/circulationaha.122.062132
status: validated
provenance:
  source_type: literature
  doi: 10.1161/circulationaha.122.062132
  citation: Musunuru K et al. (2023) Circulation 147:1-9 — Efficacy and Safety of
    an Investigational Single-Course CRISPR Base-Editing Therapy Targeting PCSK9 in
    Nonhuman Primate and Mouse Models
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- in_vivo_gene_therapy
- hepatocyte
- SaCas9
- ABE8e
- PCSK9
- AAV
- LNP
- VERVE-101
- macaque
- NAb_screen
editing_system_list:
- SaCas9
- ABE8e
delivery_method_list:
- AAV
- AAV8
- AAV-LK03
- LNP+mRNA
cell_context_list:
- hepatocyte_in_vivo
- hepatocyte_macaque
---

# In vivo CRISPR 肝靶向：PCSK9 编辑（Verve VERVE-101 类比）

## Background
PCSK9 LOF 自然人群（loss of function carrier）显示 LDL 永久下降 + 低心血管风险——是 ideal in vivo gene editing target。Verve Therapeutics VERVE-101（base editor + LNP）+ Intellia NTLA-2001（LNP-Cas9 ATTR）等已进 clinical trial。**关键挑战：(1) delivery 到肝细胞 (2) 长期 safety (3) 免疫原性。**

## What I actually did
1. **Delivery 选择**：
   - **AAV8/AAV-LK03**：肝靶向 capsid，~80% transduction in macaque liver；问题：long-term Cas9 expression → off-target accumulation + immune
   - **LNP + mRNA**：transient Cas9 expression（mRNA 半衰期数小时），integrate-free，liver 自动 trapping
   - **Verve 策略**：LNP + base editor mRNA + sgRNA（ABE8e + PCSK9 splice site disruption）
2. **AAV size 限制**：~4.7 kb cargo；SpCas9 (4.2 kb) + sgRNA + promoter + polyA 极紧；或 dual-AAV split
3. **SaCas9 (3.2 kb)**：紧凑替代，PAM NNGRRT
4. **Editing efficiency 目标**：≥ 50% liver hepatocyte editing → 临床有效 LDL drop
5. **Off-target panel**：在 macaque 肝 amplicon-seq + WGS for translocation
6. **Pre-existing immunity**：~30-70% 人群有 AAV neutralizing antibody → AAV delivery 限制；LNP 没 issue
7. **Long-term safety**：6-24 month follow-up；编辑 permanent，hepatocyte turnover 慢但 long-term off-target accumulation

## ★ 排除/不做的事
- **AAV 不查 pre-existing NAb**：clinical 30%+ patient 不能用 AAV；LNP 替代
- **AAV 的 Cas9 长期表达**：months-years Cas9 in vivo → off-target 累积；mRNA delivery 几天内 clear
- **sgRNA cassette in AAV 用 U6 only**：AAV 替代 promoter（H1, t-RNA）影响表达
- **不做 macaque PK study**：直接进 human 是 anti-pattern；NHP study 是 IND 必需
- **Liver-only delivery 当 universal**：脑/心/肌肉等其他 tissue 需不同 capsid（AAV9 BBB-cross 等）
- **不评估 immunogenicity**：Cas9（细菌 origin）pre-existing T cell 反应在 ~30% 健康人

## ★ 失败模式
- **Hepatocyte turnover**：肝细胞每年部分更新 → editing efficiency 长期 dilute（mitigated by stem cell editing）
- **AAV episomal loss**：non-integrating，cell division 时丢失，editing 终止但 Cas9 表达停
- **Insertional mutagenesis**：AAV 偶 integrate genome，long-term 风险
- **Cytokine response to LNP**：IL-6/TNFα spike post-LNP injection；clinical management 需求
- **Bystander tissue editing**：AAV/LNP 不完全 liver-specific，spleen/kidney 部分 take up
- **Germline editing risk**：肝靶向 LNP 不进 germ cell（safety），但需排除

## Lessons → seeds for rules
1. **Liver in vivo: LNP + mRNA + base editor 是当前 SOTA**（vs AAV-Cas9）
2. **AAV pre-existing NAb screening** 必步
3. **Macaque NHP study 必经**：rodent 不足以 IND
4. **Long-term off-target follow-up** ≥ 12 month
5. **mRNA transient delivery 优于 AAV stable expression** for safety
6. **Immunogenicity panel**：Cas9-specific T cell + cytokine response
7. **Tissue specificity reporting**：editing efficiency in liver vs other organs
