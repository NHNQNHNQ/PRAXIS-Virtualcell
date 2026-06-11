---
rule_id: 10-hi-c-augmented-binning
rule_type: case_distilled
applies_to: {microbiome_task: [hi_c, mag_assembly], sequencing_type: [hi_c]}
confidence: high
evidence_cases: [microbiome-010-meta-hi-c]
schema_version: 2
---

# Rule 10: Hi-C augments (not replaces) standard MAG binning; enables plasmid-host links

## Statement
When Hi-C / Meta3C / proximity-ligation data is paired with standard shotgun, use bin3C / MetaCC to add Hi-C contact-graph clustering on top of MetaBAT2/CONCOCT/MaxBin2 — not in place of. Hi-C uniquely resolves plasmid-host associations and improves strain-level binning.

## Why
Hi-C captures physical proximity in the cell (DNA cross-linked by formaldehyde). The contact map reveals which contigs lived in the same cell — including extra-chromosomal elements (plasmids, phage). Standard binning relies on tetranucleotide composition + coverage, which cannot link a plasmid to its bacterial host. DeMaere & Darling 2021 (bin3C, 10.1038/s41587-021-01057-5) showed Hi-C improves high-quality MAG count by 30–60% on complex metagenomes.

## How to apply
- Skill `meta_hi_c_binning/run.py` (P2 stub) requires paired Hi-C and standard shotgun reads.
- Hi-C library prep introduces restriction enzyme + GC bias — log restriction enzyme used.
- Output: improved MAGs + plasmid-host edge list.

## Evidence
- microbiome-010: explicit decision chain — Hi-C for plasmid-host link not achievable by composition.

## Anti-patterns
- ❌ Replacing MetaBAT2 entirely with bin3C (use both)
- ❌ Hi-C without restriction enzyme metadata
- ❌ Ignoring Hi-C ligation efficiency QC (varies 10–80%)

## Implementation pointer
`skills/workflows/meta_hi_c_binning/run.py` (P2 stub)
