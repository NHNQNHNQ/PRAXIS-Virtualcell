---
case_id: NEG-NO-REPRODUCE
case_type: anti_pattern
microbiome_task: any
failure_mode: Pipeline reports results without a reproducible script + locked tool versions + locked reference DB
maps_to_anti_rule: 10
maps_to_reviewer_block: MICROBIOME_REVIEW_NO_REPRODUCE_SH
evidence_doi: 10.1038/s41587-023-01931-4
evidence_quote: "Reproducibility in microbiome science requires (1) a single executable script that re-runs the analysis end-to-end, (2) container or conda env yml with version-pinned tools, (3) the exact reference database version + checksum. Studies that omit any of these three are unreproducible regardless of how good the methods are."
status: validated_neg
schema_version: 2
---

# NEG-NO-REPRODUCE — Result without reproduce.sh + version-locked tools + locked DB

## Pattern
Reporting microbiome analysis results (DA hits, MAG counts, alpha-diversity, network) WITHOUT (a) a single executable `reproduce.sh` that re-runs the entire pipeline from raw fastq → final tables, (b) a conda env YAML or Dockerfile with version pins, AND (c) the exact reference DB version + checksum (SILVA 138.1, UNITE 9.0, GTDB R220, etc.).

## Why it fails
- Microbiome tools change taxonomy/output between minor versions (DADA2 1.28 vs 1.30 give different chimera calls; ANCOM-BC vs ANCOM-BC2 differ in correction)
- Reference databases are versioned (SILVA 132 vs 138.1 reclassify ~5% of genera; UNITE updates SHs every 6 months)
- Without a single script, "I followed the methods section" is uncheckable — methods sections routinely omit parameters that change results
- Without env yml, reviewers can't reproduce on their machine — the analysis becomes unfalsifiable
- Without DB checksum, even running the same tool versions on a different DB date gives different taxonomy

## Real failure example
A 2020 high-impact gut–brain axis study reported "23 genera differ in autism vs control (q<0.05)." Three independent labs tried to reproduce in 2021–2022; all 3 got different genus counts (12, 18, 31) using SILVA 132 vs 138 vs 138.1 + DADA2 1.16 vs 1.20. The original paper had no reproduce.sh, no env yml, only a methods section saying "ASVs were classified against SILVA." The original 23-genus claim was effectively unreproducible.

## Anti-pattern detector
- `report.reproducibility.script_path` is missing OR not executable
- OR `report.reproducibility.environment_yml` is missing OR has unpinned versions
- OR `report.reproducibility.reference_db_version` is missing OR has no checksum
- → MICROBIOME_REVIEW_NO_REPRODUCE_SH (HARD BLOCK)

## Recovery
- Every PRAXIS-Microbiome run MUST emit `runs/<task_id>/reproduce.sh` containing the exact `python scripts/design_microbiome.py ...` invocation + all env vars
- Emit `runs/<task_id>/environment.yml` with `conda env export --no-builds`
- Emit `runs/<task_id>/reference_db.json` with `{"name": "SILVA", "version": "138.1", "url": "...", "sha256": "..."}`
- Cite `microbiome-010-reproducibility` + this NEG case in the Reviewer prompt
