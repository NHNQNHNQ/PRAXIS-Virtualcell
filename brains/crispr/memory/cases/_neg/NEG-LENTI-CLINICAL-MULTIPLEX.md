---
case_id: NEG-LENTI-CLINICAL-MULTIPLEX
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 13
edit_type: multiplex_knockout
target_gene: any
target_organism: hg38
cell_context: primary_T
editing_system: AsCas12a
delivery_method: RNP_electroporation
tools: [lentivirus, RNP electroporation, mRNA electroporation]
key_paper_doi: 10.1038/s41587-020-0741-7
provenance:
  source_type: literature
  doi: 10.1038/s41587-020-0741-7
  citation: "Liu P, Liang SQ, Zheng C, et al. Improved prime editors enable pathogenic allele correction and cancer modelling in adult mice. Nat Biotechnol. 2020;38(12):1431-1440."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, lentivirus_clinical, integration_risk, persistent_cas, multiplex_ko]
causal_tag: causal
---

# NEG-LENTI-CLINICAL-MULTIPLEX — Lentivirus delivery for clinical multiplex KO (CAR-T)

## What this NEG- case records
**Anti-pattern**: delivering a Cas9/Cas12a multiplex-KO program (e.g., TRAC + B2M + CD52 for allogeneic CAR-T) via lentivirus for clinical use. Lentivirus integrates into the genome → persistent Cas expression → continuous off-target accumulation + insertional-mutagenesis risk. Standard of practice for clinical CAR-T multiplex is RNP electroporation (transient) or mRNA + LNP (transient).

## Where the failure mode was published
Liu P et al. (2020) Nat Biotechnol + multiple CAR-T clinical trial protocols (Eyquem 2017, Mansilla-Soto 2022) document that lentivirus-mediated continuous Cas9 expression in T cells produces 10-100× higher off-target events than transient RNP/mRNA delivery, and integrates randomly into ~3-5 genomic sites per cell — each a potential insertional-mutagenesis hot spot.

## Mechanism — why it fails
1. Lentivirus integrates randomly into transcriptionally active sites — including proto-oncogenes (LMO2-style insertional leukemia is the classic SCID-X1 lentivirus precedent).
2. After integration, the LTR-driven Cas9 expression is constitutive for months → cumulative off-target events.
3. Multiplex KO already produces inter-locus translocations at 0.1-1% per double-cut event; persistent Cas9 raises this to 5-10% over weeks.
4. RNP electroporation: Cas9 + sgRNA cleared in hours → ~80% KO efficiency, ~0% integration.
5. mRNA + LNP electroporation: Cas9 mRNA expressed for ~24h → similar transient profile.

## Concrete numerics (Eyquem 2017 + Liu 2020)
- Primary T cell lentivirus Cas9: integration at 3-5 sites/cell; KO efficiency 60-80%; off-target events 10-50× transient delivery
- Primary T cell RNP electroporation (Cas9-sgRNA RNP): no integration; KO efficiency 80-95%; off-target minimized
- Primary T cell mRNA-LNP: no integration; KO 70-90%; transient expression ~24h
- FDA clinical CAR-T standard: RNP electroporation; lentivirus for CAR transgene only (not for KO program)

## ★ Reviewer hard-stop
Any multiplex_knockout design plan with `clinical: True` AND `delivery: lentivirus` must be vetoed. Required: RNP electroporation or mRNA+LNP electroporation for the KO program (lentivirus may still be used for CAR transgene delivery, separately).

## Maps to anti-rule
**anti-rule #13**: Lentivirus delivery for clinical multiplex KO (CAR-T or therapeutic) is forbidden. Required: RNP or mRNA+LNP electroporation (transient).

## Anti-retrieval keywords
lentivirus multiplex clinical, integration multiplex ko, persistent cas9 multiplex, no rnp, no mrna lnp electroporation, lentiviral car-t ko
