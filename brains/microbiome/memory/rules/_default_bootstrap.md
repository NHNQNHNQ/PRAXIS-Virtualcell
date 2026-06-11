---
rule_id: _default_bootstrap
rule_type: cold_start_defaults
applies_to: {microbiome_task: ALL, sequencing_type: ALL, sample_type: ALL}
confidence: medium
evidence_cases: []
schema_version: 2
---

# Default rules — applied when no case-distilled rule matches (cold-start)

## When this fires
- Library has fewer than 5 cases for the target task × sample-type combination, OR
- The Reviewer cannot find any matching case-distilled rule via retrieval.

## Defaults

### Sequencing & input
1. Always profile read quality (FastQC + multiqc) before any taxonomic/functional step.
2. Remove primers (cutadapt) before DADA2; remove host reads (bowtie2 + hg38) before shotgun classification.
3. Log per-sample read counts pre/post-filter; flag samples with <10k usable reads.

### Reference DB
4. Pin reference DB version explicitly in `design_plan.reference_db_locked`.
5. Default versions: SILVA 138.1 (16S), UNITE 10.0 (ITS), GTDB R220 (shotgun).
6. Re-validate downstream when DB version changes.

### Statistics
7. Microbiome data is compositional — never apply parametric tests on raw counts without transformation.
8. Adjust for known confounders (age, sex, diet, batch) when metadata available.
9. Report effect size + adjusted p-value, not just p.

### Negative control
10. If sample_type is low-biomass (oral, skin, environmental water) OR biomass_estimate is unknown/low, **require** DNA extraction blank + reagent blank.
11. Apply decontam-style filtering before downstream analysis.

### Reproducibility
12. Every run emits `runs/<task_id>/outputs/reproduce.sh` with version-pinned binary calls.
13. Log all reference-DB paths and checksums.
14. Use the remote_exec layer with explicit conda env name in every command.

### Confidence label rules
15. P0 skill ran for real with all QC passing → `high`.
16. P0 skill ran but QC warnings or single-method (no consensus) → `medium`.
17. Any P1/P2 skill returned `simulated:true` → cap overall at `low`.
18. No skill ran (pure literature review) → `domain_knowledge`.
19. Library coverage too sparse to ground recommendation → `cold_start`.
