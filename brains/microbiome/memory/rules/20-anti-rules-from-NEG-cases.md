---
rule_id: 20-anti-rules-from-NEG-cases
rule_type: anti_rule_consolidated
applies_to: {microbiome_task: ALL, sample_type: ALL}
confidence: high
evidence_cases: [NEG-OTU-CLUSTERING, NEG-SINGLE-CLASSIFIER, NEG-SINGLE-BINNER, NEG-PICRUST-SHOTGUN, NEG-RAREFY-DA, NEG-TTEST-RAW, NEG-SILVA-FUNGI, NEG-PEARSON-NETWORK, NEG-NO-BLANK-LOWBIOMASS, NEG-NO-REPRODUCE, NEG-COPY-NUMBER-IGNORED, NEG-PRIMER-BIAS-IGNORED]
schema_version: 2
---

# Rule 20: Twelve Hard-Stop Anti-Patterns (consolidated from NEG- case library)

This rule consolidates all 12 anti-patterns formalized in `memory/cases/_neg/`. Each anti-pattern has:
- A trigger condition on the `design_plan`
- A `MICROBIOME_REVIEW_*` block label that the Reviewer agent emits
- A pointer to the NEG- case + the positive-direction rule (`01-..12-`) that supersedes it
- A confidence label that downgrades to `low` if the agent proceeds despite the block

## How the Reviewer uses this rule

```
for design_plan in queue:
    for anti in ANTI_PATTERNS:
        if anti.matches(design_plan):
            emit(anti.review_block)        # HARD BLOCK
            cite(anti.neg_case_id)          # show the user the failure precedent
            cite(anti.recovery_rule_id)     # show the positive rule
            require_user_override = True    # cannot proceed without explicit override
```

## The 12 anti-patterns

### Anti-rule 1 — OTU clustering when DADA2 available
- Trigger: `task ∈ {amplicon_16s, amplicon_its, amplicon_18s}` AND `pipeline.tools ∋ {vsearch_cluster, usearch, mothur_cluster}`
- Block: `MICROBIOME_REVIEW_OTU_WHEN_DADA2`
- NEG case: `NEG-OTU-CLUSTERING` — DOI 10.1038/nmeth.3869 (DADA2 paper)
- Recovery rule: `01-asv-over-otu`
- Skill: `amplicon_dada2_qiime`

### Anti-rule 2 — Single-classifier shotgun taxonomy
- Trigger: `task = shotgun_taxonomy` AND `len(pipeline.classifiers) == 1`
- Block: `MICROBIOME_REVIEW_SINGLE_CLASSIFIER`
- NEG case: `NEG-SINGLE-CLASSIFIER` — DOI 10.1186/s13059-019-1891-0 (Wood 2019 Kraken2)
- Recovery rule: `02-dual-classifier-shotgun`
- Skill: `shotgun_taxonomy`

### Anti-rule 3 — Single-binner MAG assembly
- Trigger: `task = mag_assembly` AND `len(pipeline.binners) == 1` AND `dastool` not in `pipeline.refinement`
- Block: `MICROBIOME_REVIEW_SINGLE_BINNER`
- NEG case: `NEG-SINGLE-BINNER` — DOI 10.1186/s40168-020-00990-y (DAS_Tool Sieber 2018)
- Recovery rule: `03-multi-binner-consensus`
- Skill: `mag_assembly_pipeline`

### Anti-rule 4 — PICRUSt2 on shotgun data
- Trigger: `pipeline.data_source = shotgun` AND `pipeline.tools ∋ picrust2`
- Block: `MICROBIOME_REVIEW_PICRUST_FOR_SHOTGUN`
- NEG case: `NEG-PICRUST-SHOTGUN` — DOI 10.7554/eLife.65088 (Beghini 2021 HUMAnN3)
- Recovery rule: `04-shotgun-uses-humann-not-picrust`
- Skill: `humann_functional`

### Anti-rule 5 — Rarefaction before differential abundance
- Trigger: `pipeline.normalization ∋ {rarefy, rarefaction, subsample_depth}` AND `pipeline.tools ∋ {ancombc, ancom-bc2, maaslin2, deseq2, edger, aldex2}`
- Block: `MICROBIOME_REVIEW_RAREFY_BEFORE_DA`
- NEG case: `NEG-RAREFY-DA` — DOI 10.1371/journal.pcbi.1003531 (McMurdie & Holmes 2014)
- Recovery rule: `12-no-rarefy-before-da`
- Skill: `da_compositional`

### Anti-rule 6 — t-test/Wilcoxon on raw or relative abundance
- Trigger: `task = differential_abundance` AND `pipeline.statistics.method ∈ {ttest, wilcoxon, mannwhitneyu, kruskal}` AND `input.units ∈ {raw_count, relative_abundance, proportion, percent}`
- Block: `MICROBIOME_REVIEW_TTEST_RAW_COUNT`
- NEG case: `NEG-TTEST-RAW` — DOI 10.3389/fmicb.2017.02224 (Gloor 2017)
- Recovery rule: `05-compositional-aware-da`
- Skill: `da_compositional`

### Anti-rule 7 — SILVA classifier on fungal ITS
- Trigger: `pipeline.amplicon_target ∈ {ITS, ITS1, ITS2}` AND `pipeline.reference_db ~= silva`
- Block: `MICROBIOME_REVIEW_SILVA_FOR_FUNGI`
- NEG case: `NEG-SILVA-FUNGI` — DOI 10.1093/nar/gky1022 (UNITE)
- Recovery rule: `06-unite-for-fungi`
- Skill: `its_fungal_pipeline`

### Anti-rule 8 — Pearson/Spearman on relative abundance for network
- Trigger: `task = network_inference` AND `pipeline.method ∈ {pearson, spearman, correlation}` AND `input.units ∈ {relative_abundance, proportion}`
- Block: `MICROBIOME_REVIEW_PEARSON_NETWORK`
- NEG case: `NEG-PEARSON-NETWORK` — DOI 10.1371/journal.pcbi.1002687 (Friedman & Alm 2012)
- Recovery rule: `08-compositional-network-methods`
- Skill: `cooccurrence_network`

### Anti-rule 9 — Low-biomass without negative control
- Trigger: `scoping.sample_type ∈ {skin, bal, biopsy, placenta, air, blood, neonatal, tissue, low_biomass}` AND `scoping.negative_control_plan ∈ {missing, none, false}`
- Block: `MICROBIOME_REVIEW_NO_NEG_CONTROL_LOW_BIOMASS` (HARD BLOCK)
- NEG case: `NEG-NO-BLANK-LOWBIOMASS` — DOI 10.1186/s12915-014-0087-z (Salter 2014)
- Recovery rule: `11-negative-control-low-biomass`
- Skill: any (pre-condition for all)

### Anti-rule 10 — No reproduce.sh + no env yml + no DB version
- Trigger: `report.reproducibility.script_path` missing OR `environment_yml` missing OR unpinned versions OR `reference_db_version` missing
- Block: `MICROBIOME_REVIEW_NO_REPRODUCE_SH` (HARD BLOCK)
- NEG case: `NEG-NO-REPRODUCE` — DOI 10.1038/s41587-023-01931-4
- Recovery rule: (none — this is a meta-rule that ALL skills must emit)
- Skill: any (orchestrator-level requirement)

### Anti-rule 11 — 16S read counts treated as cell counts
- Trigger: `pipeline.amplicon_target ∈ {16S, 16S_V3V4, 16S_V4}` AND `pipeline.copy_number_correction ∈ {missing, false, none}` AND `task ∈ {alpha_diversity, beta_diversity, differential_abundance, quantitative_comparison}`
- Block: `MICROBIOME_REVIEW_COPY_NUMBER_IGNORED`
- NEG case: `NEG-COPY-NUMBER-IGNORED` — DOI 10.1093/femsre/fuy016 (Stoddard rrnDB)
- Recovery rule: (microbiome-specific; report flag in scoping output)
- Skill: `amplicon_dada2_qiime` post-processing OR switch to `shotgun_taxonomy`

### Anti-rule 12 — Cross-primer 16S meta-analysis without bias acknowledgment
- Trigger: (cross-study) `pipeline.input_studies` has ≥2 distinct `primer_pair` AND `pipeline.primer_bias_acknowledgment ∈ {missing, false}` OR (single-study) `pipeline.amplicon_primers = V1V2` AND target organism includes `bifidobacterium|akkermansia`
- Block: `MICROBIOME_REVIEW_PRIMER_BIAS_IGNORED`
- NEG case: `NEG-PRIMER-BIAS-IGNORED` — DOI 10.1186/s40168-018-0521-5
- Recovery rule: (microbiome-specific; stratify-by-primer or shotgun)
- Skill: `amplicon_dada2_qiime` (config-level check)

## How agents downgrade confidence on override

If the user explicitly overrides any anti-rule block:

```
override_count = sum(1 for anti in triggered if user.overrode(anti))
if override_count >= 1:
    report.confidence_label = "low"           # cannot be high regardless of other signals
if override_count >= 2:
    report.confidence_label = "cold_start"    # essentially uninterpretable
report.overrides = [anti.id for anti in overrides]   # always recorded
```

## Implementation pointer

- All anti-rules are detected at design_plan validation time in `agents/orchestrator.py::reviewer_gate()`
- Detection logic in `agents/reviewer.py::check_anti_patterns(design_plan)`
- NEG- cases retrieved at `scripts/retrieval/anti_pattern_retrieval.py` (filters cases by `case_type=anti_pattern` AND tags match design_plan)
- Per-skill `SKILL.md` MAY also include an `excludes_anti_patterns:` list to short-circuit skill selection BEFORE design lock-in
