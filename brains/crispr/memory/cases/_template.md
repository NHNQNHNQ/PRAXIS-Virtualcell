---
case_id: crispr-NNN-short-descriptor
schema_version: 1
edit_type: knockout_indel | base_editing_a_to_g | base_editing_c_to_t | prime_editing | knock_in_hdr | multiplex_knockout | pooled_crispr_screen_analysis | rna_targeting | in_vivo_gene_therapy | saturation_genome_editing_sge | off_target_landscape
target_gene: HGNC_SYMBOL    # e.g. TP53, KRAS, BCL11A
target_organism: hg38       # whitelist: hg38 | hg19 | mm10 | mm39 | macFas5 | rheMac10 | rn6 | danRer11 | sacCer3
cell_context: HeLa          # HeLa | HSC | iPSC | primary_T | hepatocyte_in_vivo | HAP1 | K562 | Panc1 | etc.
editing_system: SpCas9      # whitelist: SpCas9 | SaCas9 | AsCas12a | enAsCas12a | ABE8e | CBE4max | PE3 | PE5 | RfxCas13d | ...
delivery_method: lentivirus | RNP_electroporation | AAV | LNP+mRNA | plasmid_transfection | mRNA_electroporation
tools: [CRISPOR, CHOPCHOP, CRISPResso2, ...]    # actual tools used in the paper
key_paper_doi: 10.xxxx/xxxxx
status: validated | partial | failed | preregistered
provenance:
  source_type: literature
  doi: 10.xxxx/xxxxx
  citation: "Author et al. (Year) Journal volume:pages"
  extracted_at: 2026-04-29
  source: praxis_seed
tags: [edit_type, cell_context, editing_system, ...]
---

# {Title}

## Background
{Why this edit_type / target / cell context matters; what's the biological / clinical motivation}

## What I actually did
1. **Target choice**: {how was target site selected — exon, splice variant, etc.}
2. **Guide / pegRNA design**: {tool, scoring, top picks}
3. **Off-target evaluation**: {CFD, CHANGE-seq, etc.}
4. **Validation**: {amplicon-seq, functional assay}
{... method details with concrete numbers}

## ★ 排除/不做的事 (MANDATORY)
- {Off-target rules excluded — e.g., CFD_cum > 0.5, GC outliers}
- {Cell-context exclusions — e.g., polyploid single guide}
- {Editor-version exclusions — e.g., ABE7.10 instead of ABE8e}

## ★ 失败模式 (MANDATORY)
- {Mosaic editing, off-target translocation, etc.}
- {Cell-type insufficient HDR / immune response}
- {Failed validation outcomes}

## Lessons → seeds for rules
1. {Transferable rule with applicability constraints}
2. {Rule referencing what was excluded / failed and why}
