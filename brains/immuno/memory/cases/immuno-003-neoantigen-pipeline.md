---
case_id: immuno-003-neoantigen-pipeline
schema_version: 1
task: tumor_neoantigen_identification
immuno_task: tumor_neoantigen_identification
antigen_class: tumor_neoantigen
hla_class: HLA_I
hla_alleles: []
peptide_length_bin: "9-10"
disease_indication: cancer_melanoma
target_disease: melanoma (TCGA-SKCM)
target_protein_uniprot: []
inputs: [somatic_VCF, RNA-seq_counts, HLA_typing]
tools: [pVACseq, NetMHCpan, MHCflurry, NetChop, NetCTL, prime-2.0, ScanNeo2]
key_paper_doi: 10.1186/s13073-016-0264-5
status: validated
source: praxis_seed
---

# Neoantigen pipeline：从 somatic mutation 到优先级排序

## Background
Tumor neoantigen = somatic mutation 产生的 peptide + 与 patient HLA 结合 + 被免疫识别。是个性化 cancer vaccine 与 TIL therapy 的关键。**完整 pipeline**：VCF → mutated peptide → MHC binding → expression filter → clonality → 排序。

## What I actually did
1. **Input**：matched tumor + normal WES → somatic VCF (Mutect2/Strelka2)；RNA-seq counts；HLA typing (OptiType / arcasHLA)
2. **Variant annotation**：VEP / SnpEff → 保留 missense, frameshift, stop_lost, splice
3. **Peptide generation**：
   - Missense: 9-mer/15-mer surrounding mutation
   - Frameshift: 整段 novel ORF 翻译 → 多 peptide
   - Indel: similar to frameshift
4. **MHC binding**：每 peptide × patient HLA-A/B/C → NetMHCpan rank
5. **Expression filter**：mutated allele 必须 RNA-expressed（VAF in RNA > 0.1）；不表达 = 不 present
6. **Clonality**：CCF (cancer cell fraction) 计算（PyClone / SciClone）；clonal mutation 优先（presented in all tumor cells）
7. **Processing prediction**：NetChop（C-terminal cleavage）+ NetCTL（complete pathway）
8. **Immunogenicity score**：BigMHC-IM / DeepImmuno 评估能否激活 T cell（不只是 binding）
9. **Final ranking**：composite score = MHC × expression × clonality × processing × immunogenicity
10. **Output**：top 20 neoantigen 给 patient-specific vaccine / TIL screen

## ★ 排除/不做的事
- **不 filter expression**：~50% mutated allele RNA 不表达，pure DNA-level prediction noise 大
- **Missense only, ignore frameshift**：frameshift peptide 占 highly immunogenic 大头（novel sequence）
- **Single MHC predictor**：consensus 必步
- **Clonal vs subclonal 不区分**：subclonal mutation 仅部分 cell 有 → vaccine 部分 escape
- **HLA typing 不 4-digit**：2-digit (HLA-A02) 不够，4-digit (A*02:01 vs 02:03) 影响 prediction
- **不评估 self-similarity**：高 self-similar peptide → central tolerance → 弱 immunogenic
- **Driver mutation auto-include**：driver (KRAS G12D 等) 不一定 present (HLA-restricted)

## ★ 失败模式
- **HLA loss of heterozygosity (HLA LOH)**：tumor 丢 1 个 HLA copy → 那个 HLA 的 epitope 不 present；LOHHLA tool 检测必步
- **MHC pathway downregulation**：tumor 主动 downregulate B2M / TAP → 全 pathway 失效
- **TCR repertoire constraint**：predicted high binding 但 patient TCR repertoire 没识别 → 无效
- **Clonal evolution**：treat 时 neoantigen 选择消失（immunoediting）
- **Splice variant**：neoantigen 来自异常 splicing 不在 standard pipeline
- **Peptide proteasome 处理 efficiency**：strong binder 但 processing 弱 → low presentation

## Lessons → seeds for rules
1. **Pipeline 四件套**：VCF → peptide → MHC + expression + clonality + processing
2. **Multi-class peptide**：missense + frameshift + splice 都纳入
3. **HLA LOH detection 必步**（LOHHLA）
4. **Multi-method MHC consensus**
5. **Expression filter** RNA VAF > 0.1
6. **Clonality (CCF) > 0.6** for vaccine target
7. **Immunogenicity score**（BigMHC-IM / PRIME）补充 binding alone
