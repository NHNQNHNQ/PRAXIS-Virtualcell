---
case_id: NEG-MIXCR-OOF-NOT-REPORTED
schema_version: 1
status: validated
source: praxis_seed_NEG
task: tcr_repertoire_analysis
immuno_task: tcr_repertoire_analysis
antigen_class: tumor_neoantigen
hla_class: n/a
hla_alleles: []
peptide_length_bin: n/a
disease_indication: cancer_general
target_protein: TCR repertoire
target_protein_uniprot: []
tools: [TCR-seq pipeline that does not report out-of-frame (OOF) rate; no QC gate]
key_paper_doi: 10.1038/nm.4051
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, TCR-seq, OOF, QC, MiXCR]
unverified_details: []
---

# NEG: TCR-seq output without OOF rate → silent loss of productive clonotypes

## Background
Productive TCR sequences (in-frame, no premature stop) typically constitute 60-80% of TCR-seq reads. Out-of-frame (OOF) rate is the canonical QC metric — a sample with OOF > 30% indicates either degraded RNA, library prep failure, or contamination. Pipelines that do not report OOF cannot detect such samples → downstream diversity / clonality metrics computed on garbage data.

## ★ 排除/不做的事
- ❌ TCR-seq output without explicit OOF rate field
- ❌ Cross-sample diversity comparison without rarefaction
- ❌ MiXCR/TRUST4 output → diversity metrics without QC gate

## ★ 失败模式
- **Sample with OOF > 30% silently passes** → false low diversity (most reads dropped)
- **Cross-sample comparison without rarefaction** → batch effects masquerade as biology

## ★ 方法选择决策链
- Always emit OOF rate (TRUST4 / MiXCR canonical output)
- Hard QC gate: OOF < 30%
- Rarefy ALL samples to common depth before cross-sample comparison
- Tool family: MiXCR (license needed) OR TRUST4 (academic free) — both report OOF

## Lessons → ANTI-RULES generated
- **anti-rule 19**: TCR/BCR-seq pipeline without OOF rate reporting → block (rule 05)
- **anti-rule 20**: Cross-sample TCR diversity comparison without rarefaction → block
