---
rule_id: 12-no-rarefy-before-da
rule_type: case_distilled
applies_to: {microbiome_task: [da_analysis, multiomics, network], sample_type: ALL}
confidence: high
evidence_cases: [microbiome-005-ancombc-da]
schema_version: 2
---

# Rule 12: Don't rarefy before differential abundance — use count-aware models

## Statement
Rarefaction (subsampling all samples to the minimum library size) discards information and reduces statistical power. Modern DA methods (ANCOM-BC2, MaAsLin2, LinDA, ALDEx2) explicitly model count data + library size as a covariate — rarefaction is unnecessary and harmful (McMurdie & Holmes 2014, "Waste Not, Want Not"; reinforced by Lin & Peddada 2020, 10.1038/s41467-020-17041-7).

## Why
Rarefaction throws away the genuine count information from deeply-sequenced samples and adds noise via random subsampling. Library-size variation is information, not bias — count-aware models incorporate it as offset. Rarefaction is acceptable for some specific diversity analyses (e.g., classic alpha diversity at fixed depth) but not for DA.

## How to apply
- Reviewer gate `MICROBIOME_REVIEW_RAREFY_BEFORE_DA`: trigger when `differential_abundance.preprocessing` contains `rarefy | subsample_to_min_depth`.
- Skill `da_compositional/run.py` rejects `--rarefy` flag explicitly.
- Acceptable use of rarefaction: alpha-diversity at fixed depth for cross-study comparison (and even then, prefer Hill numbers).

## Evidence
- microbiome-005: explicit anti-pattern — "Rarefy before DA → 信息损失，统计 power 低".

## Anti-patterns
- ❌ phyloseq::rarefy_even_depth before any DA method
- ❌ "We rarefy to be safe" (no, you lose power)
- ❌ Skipping covariate adjustment because samples were rarefied

## Implementation pointer
`skills/workflows/da_compositional/run.py`
