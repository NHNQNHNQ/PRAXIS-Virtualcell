---
case_id: immuno-005-bcr-seq-lineage
schema_version: 1
task: bcr_repertoire_lineage_analysis
immuno_task: bcr_repertoire_lineage_analysis
antigen_class: viral
hla_class: n/a
hla_alleles: []
peptide_length_bin: n/a
disease_indication: infection_hiv
target_data: HIV bnAb (broadly neutralizing antibody) lineage tracing
target_protein_uniprot: []
tools: [Immcantation (Change-O / Alakazam / SCOPer / Shazam), MiXCR, IgBLAST, dowser, partis]
key_paper_doi: 10.1093/bioinformatics/btu138
status: validated
source: praxis_seed
---

# BCR-seq lineage：B cell phylogeny + 抗体亲和成熟轨迹

## Background
BCR-seq 与 TCR-seq 类似但加 somatic hypermutation (SHM)——抗原驱动 B cell 在生发中心多轮 mutation + 选择，形成 lineage tree。HIV bnAb（如 VRC01）的发现都靠 longitudinal BCR-seq 追溯 lineage。Vaccine design 关键。

## What I actually did
1. **Sample**：HIV+ patient longitudinal blood B cell BCR-seq（多时间点）
2. **MiXCR / IgBLAST**：V(D)J + CDR3 + germline V gene
3. **Immcantation Change-O**：定义 clone（CDR3 length identical + V gene + J gene + > 90% sequence identity）
4. **Germline reconstruction**：每 clone 从 germline V/D/J 序列推断 ancestor
5. **SHM count**：每 sequence 与 germline 距离（aa + nt）
6. **Lineage tree (dowser)**：clonal phylogeny；时序 sample 给 temporal axis
7. **Selection metrics (BASELINe)**：CDR vs FR mutation ratio → positive selection signal
8. **Mutation hot spots**：AID-targeting motifs (RGYW, WRCY) 富集
9. **Naïve→memory→affinity-matured 轨迹**：观察 SHM 累积 + clone 扩张

## ★ 排除/不做的事
- **TCR pipeline 直接套**：BCR 含 SHM，clone 定义不能要求 100% identity
- **Single time point lineage**：lineage 推断需 multi-time + naive ancestor
- **Germline V gene database 不更新**：IMGT 定期更新，老 reference miss novel allele
- **Clone definition aa-only**：silent mutation 信息丢，纳 nucleotide 重要
- **Selection metric 不区分 CDR vs FR**：CDR positive selection vs FR negative selection 是 functional signal
- **Convergent evolution 误为 same lineage**：跨 patient 同 CDR3 可能 convergent 而非 single ancestor

## ★ 失败模式
- **Sequencing error vs SHM**：single-base diff 是 mutation 还是 noise？UMI / replicate 区分
- **Cell of origin**：peripheral blood B cell ≠ germinal center；lineage 在 GC 但 sample 在 blood
- **Allelic exclusion violation**：rare B cell 表达 2 个 BCR
- **Class switch**：IgM → IgG → IgA 过程，VH 不变 CH 变；分析需考虑
- **Long-read 推荐**：full V gene needed for SHM，short read miss FR1
- **IgH vs IgK/L pairing**：bulk 不 pair；single-cell BCR-seq 才能

## Lessons → seeds for rules
1. **Clone definition**：CDR3 length + V/J + > 90% identity（不强制 100%）
2. **Multi-time longitudinal** for lineage trace
3. **Germline reconstruction + dowser tree**
4. **Selection metric (BASELINe)** for affinity maturation evidence
5. **Single-cell BCR > bulk** for IgH/IgL pair
6. **Class switch 显式分析**（IgM/G/A）
7. **AID motif analysis** for functional context
