---
case_id: NEG-OTU-CLUSTERING
case_type: anti_pattern
microbiome_task: amplicon_16s
failure_mode: OTU clustering loses species-level resolution and reproducibility
maps_to_anti_rule: 1
maps_to_reviewer_block: MICROBIOME_REVIEW_OTU_WHEN_DADA2
evidence_doi: 10.1038/nmeth.3869
evidence_quote: "DADA2's resolution at the level of single-nucleotide differences was greater than that achieved by other methods that depend on clustering."
counter_evidence_doi: 10.1038/ismej.2017.119
status: validated_neg
schema_version: 2
---

# NEG-OTU-CLUSTERING — OTU clustering when DADA2/deblur available

## Pattern
Using `vsearch --cluster_fast`, `usearch -cluster_otus`, or `mothur cluster.split` at 97% identity for 16S/ITS/18S amplicon analysis when DADA2 or deblur (ASV inference) is available.

## Why it fails
- OTU clusters at 97% merge biologically distinct strains and species
- Single-nucleotide variants are collapsed; lose strain-level signal
- ASV-based studies cannot integrate OTU-based studies (different OTU centroids per dataset)
- Callahan et al. 2016 showed ASV recovers known mock community composition more accurately at every taxonomic level

## Real failure example
A pre-DADA2 IBD study clustered V3-V4 reads at 97% and claimed *Bifidobacterium* genus reduced in IBD. Re-analysis with ASV showed the "reduction" was driven by a single *B. longum* strain shift; other *Bifidobacterium* species unchanged → OTU clustering masked the strain-level true signal.

## Anti-pattern detector
- `design_plan.computational_pipeline.tools` matches `vsearch_cluster | usearch.*cluster_otus | mothur.*cluster`
- AND `microbiome_task ∈ {amplicon_16s, amplicon_its, amplicon_18s}`
- AND DADA2 binary detected in env

## Recovery
- Use `amplicon_dada2_qiime` (canonical DADA2 R 1.38) or `amplicon_minimal_real` skill
- Cite `microbiome-001-16s-dada2` + `01-asv-over-otu`
