---
case_id: synth-010-bgcs-natural-product
task: biosynthetic_gene_cluster_mining
target_data: Streptomyces genome → novel antibiotic discovery
tools: [antiSMASH 7, BiG-SCAPE, BGCFlow, MIBiG database, NPlinker, DeepBGC]
key_paper_doi: 10.1093/nar/gkaa978
status: validated
---

# antiSMASH BGC mining：从 genome 找 novel natural product

## Background
Microbial genome 中 ~5-10% 编码 secondary metabolite（NRPS / PKS / terpene / RiPP）。antiSMASH 是 BGC（biosynthetic gene cluster）prediction 主要工具。**目标**：找 novel scaffolds → wet lab clone + heterologous express → 发现新 antibiotic / 抗肿瘤药 etc.

## What I actually did
1. **Genome input**：Streptomyces sp. genome FASTA
2. **antiSMASH 7 detection**：识别 NRPS / PKS / terpene / RiPP / hybrid clusters
3. **Output**：每 BGC 含 location + biosynthetic class + predicted substrate (NRPS A-domain 推 amino acid)
4. **BiG-SCAPE clustering**：跨 genomes BGC similarity 网络 → BGCs 归 family
5. **MIBiG database 比对**：family 中是否含已 characterized compound（known scaffold） vs novel family
6. **Novel BGC priority**：novel family（无 MIBiG match）+ NRPS 长 + class diversity → 高 priority
7. **Heterologous expression plan**：BGC > 50 kb 通常 split + clone 进 Streptomyces venezuelae expression host
8. **DeepBGC** as alternative: ML-based detection，pick novel architectures

## ★ 排除/不做的事
- **Single tool**：antiSMASH + DeepBGC 互补
- **Novel family blindly trust**：分析 phylogeny + 周围 gene 看 functional context
- **不 cross-check MIBiG**：可能已被 characterized 但作者用不同名称
- **不评估 expression feasibility**：BGC > 100 kb cloning 极难
- **Forget regulator gene**：BGC 内 regulator 是 silenced 的关键，需 activate (over-express PathwaySpecificRegulator)
- **Heterologous host mismatch**：Streptomyces vs E.coli expression 兼容性不同

## ★ 失败模式
- **antiSMASH 假阳**：non-functional gene cluster 被 predict 为 BGC
- **Silent BGC**：genome 含 BGC 但 lab condition 不表达；needs activation
- **Tailoring enzyme miss**：post-PKS modification enzyme 在 BGC 边界外 → predicted compound structure 错
- **Strain dereplication**：分离的 compound 已知 (rediscovery rate ~80%)；MIBiG + Dictionary of Natural Products 必查
- **Cluster splitting**：长 cloning 易 break；Cas9-assisted in vitro assembly 替代
- **Expression toxicity**：heterologous host 经常被 product 杀

## Lessons → seeds for rules
1. **antiSMASH + DeepBGC consensus**
2. **MIBiG cross-ref** for novelty assessment
3. **BiG-SCAPE family analysis**
4. **Pathway regulator activate** for silent BGC
5. **Heterologous expression host choice**：Streptomyces venezuelae / coelicolor 是 default
6. **Dereplication** before claiming novelty
7. **Cas9-assisted assembly** for long cluster cloning
