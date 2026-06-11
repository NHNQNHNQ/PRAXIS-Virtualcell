---
case_id: microbiome-XXX-short-slug
microbiome_task: amplicon_16s|amplicon_its|shotgun_taxonomy|mag_assembly|functional|da_analysis|multiomics|network|strain|hi_c
sequencing_type: 16S|ITS|18S|shotgun_short|shotgun_long|hi_c
sample_type: human_gut|human_oral|human_skin|soil|water_marine|plant_root|mock_community|...
target_organism: "human gut microbiome | rhizosphere | ..."
input_data: "describe input — e.g. paired-end Illumina V3-V4, 250bp, ~30k reads/sample"
reference_db: "SILVA 138.1 | UNITE 10.0 | GTDB R220 | ..."
dataset_accession: PRJNAxxxxx | null
key_paper_doi: 10.xxxx/xxxxx
biomass_estimate: high|medium|low|unknown
tools: [tool1 version, tool2 version, ...]
status: validated
---

# <Title — English + Chinese OK>

## Background
<Why this task / sample / disease matters; what makes it methodologically tricky>

## What I actually did
<Numbered steps. Each step concrete: tool name, key parameter, decision rationale>
1.
2.
3.

## ★ 排除/不做的事 (excluded samples / ASVs / pathways / methods)
<Bullet list: what you filtered out and why; tool choices you rejected>
-
-

## ★ 失败模式 (failure modes encountered or known)
<Bullet list: contamination, primer bias, copy-number bias, strain heterogeneity, batch effects, low biomass kit-ome, ...>
-
-

## ★ 方法选择决策链 (why this method over alternatives)
<Bullet list: DADA2 vs OTU; Kraken+Bracken vs MetaPhlAn alone; ANCOM-BC2 vs MaAsLin2 vs LinDA — cite the tradeoff>
-
-

## ★ Validation (mock community / known biology / negative control)
<Bullet list: how you verified the result is biologically real, not artifact>
- mock community recovery: ...
- known biology check: ...
- negative control treatment: ...

## Lessons → seeds for rules
<5–7 actionable rules future projects should follow>
1.
2.
