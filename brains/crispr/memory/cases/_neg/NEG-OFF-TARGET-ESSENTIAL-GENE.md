---
case_id: NEG-OFF-TARGET-ESSENTIAL-GENE
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 8
edit_type: knockout_indel
target_gene: any
target_organism: hg38
cell_context: any
editing_system: SpCas9
delivery_method: any
tools: [DepMap CKE list, Cas-OFFinder, CFD, MIT score]
key_paper_doi: 10.1016/j.cell.2017.05.061
provenance:
  source_type: literature
  doi: 10.1016/j.cell.2017.05.061
  citation: "Hart T, Tong AHY, Chan K, et al. Evaluation and Design of Genome-Wide CRISPR/SpCas9 Knockout Screens. G3 (Bethesda). 2017;7(8):2719-2727."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, off_target_essential, depmap_cke, toxicity, false_phenotype]
causal_tag: causal
---

# NEG-OFF-TARGET-ESSENTIAL-GENE — sgRNA with off-target hit on a DepMap CKE essential gene

## What this NEG- case records
**Anti-pattern**: shipping an sgRNA whose cumulative CFD score across all in-silico off-targets exceeds 0.5 AND whose top off-target overlaps a DepMap pan-essential gene (CKE — Core Common Essential, Hart 2017 / DepMap 23Q4). Cell death in the experiment is then unattributable to the intended target — the off-target essential gene is also being knocked out.

## Where the failure mode was published
Hart T et al. (2017) G3 + DepMap 23Q4 release together define the "core common essential" (CKE) gene list (~1500 genes essential across nearly all cell lines, including ribosomal proteins, RNA polymerase II subunits, DNA replication and proteasome subunits). Multiple CRISPR screens have shown that any off-target with CFD > 0.5 overlapping a CKE produces dropout that mimics on-target essentiality, confounding hit-calling.

## Mechanism — why it fails
1. Cas9 cleaves both intended target and high-CFD off-target.
2. If the off-target falls in a CKE gene's CDS, the cell dies regardless of the intended phenotype.
3. The user concludes "intended gene is essential" → false-positive phenotype.
4. CRISPR screens with such off-targets produce 5-15% false-positive essentiality calls (Hart 2017 estimate).
5. Single-gene CRISPR experiments produce confounded readouts — viability change is not attributable.

## Concrete numerics (Hart 2017 + DepMap)
- DepMap CKE gene set: ~1500 genes (POLR2A, RPL3-RPS4X, MCM2-7, PSMA1-PSMD2, EIF3A, MYC, ACTB, TUBB, …)
- Genome-wide guide design: ~3% of guides have ≥ 1 off-target in CKE with CFD > 0.5 (Doench 2016 Brunello library design)
- Without CKE filter: 5-15% of "essentiality hits" in pooled screen are CKE off-target artifacts
- With CKE filter on guide design: false-positive rate drops to < 1%

## ★ Reviewer hard-stop
Any sgRNA candidate with `cum_cfd > 0.5` AND any off-target overlapping a DepMap CKE gene must be vetoed at design-plan time. Required: filter all candidate guides against `tests/baselines/depmap_k562_essentials_subset.tsv` (or full DepMap CKE) BEFORE shipping.

## Maps to anti-rule
**anti-rule #8**: sgRNAs with off-targets in DepMap CKE essential genes (cum CFD > 0.5) are forbidden. Required: explicit CKE-overlap filter at design time.

## Anti-retrieval keywords
off target essential gene, depmap cke off target, off target polr2a, off target ribosomal, no cke filter, essential gene off target hit, off target tumor suppressor
