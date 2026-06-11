---
case_id: NEG-LEGACY-BASE-EDITOR
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 3
edit_type: base_editing_a_to_g
target_gene: any
target_organism: hg38
cell_context: HSC
editing_system: ABE8e
delivery_method: LNP+mRNA
tools: [ABE8e, ABE7.10, CBE3, CBE4max, BE-Hive]
key_paper_doi: 10.1038/s41587-020-0414-6
provenance:
  source_type: literature
  doi: 10.1038/s41587-020-0414-6
  citation: "Richter MF, Zhao KT, Eton E, et al. Phage-assisted evolution of an adenine base editor with improved Cas domain compatibility and activity. Nat Biotechnol. 2020;38(7):883-891."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, abe7.10, cbe3, be3, legacy_editor, low_activity]
causal_tag: causal
---

# NEG-LEGACY-BASE-EDITOR — Using ABE7.10 / CBE3 / BE3 instead of ABE8e / CBE4max

## What this NEG- case records
**Anti-pattern**: defaulting to ABE7.10 (or BE3, CBE3) for clinical or efficiency-critical applications when ABE8e (Richter 2020), CBE4max, or evoBE4max are available with 5-10× higher per-window editing rates and equivalent or better safety profiles.

## Where the failure mode was published
Richter MF et al. (2020) Nat Biotechnol Fig 2-3 directly compares ABE7.10 vs ABE8e on multiple loci: ABE8e achieves 50-80% target-A → G in protospacer position 6 in HSC, while ABE7.10 achieves 5-15% on the same loci. Same paper documents Cas9-independent off-target profiles — ABE8e has SOMEWHAT MORE TadA-mediated transcriptome RNA editing but per-on-target editing is much higher, so net specificity ratio favors ABE8e.

## Mechanism — why it fails
1. ABE7.10 = TadA*-7.10 fused to nCas9; the deaminase domain has lower processivity, so per-window edit rate plateaus at ~15% even with prolonged expression.
2. ABE8e = phage-evolved TadA-8e with ~590× higher in-vitro deamination rate; per-window rate reaches 50-80% even with transient mRNA delivery.
3. For HSC clinical applications (sickle cell, β-thalassemia) the 60% threshold is required for therapeutic HbF induction — ABE7.10 cannot reach it.
4. Same logic for CBE3 vs CBE4max: CBE3 lacks UGI×2 + uracil glycosylase inhibitor → C→T edit rate < 30% with high indel byproduct.

## Concrete numerics (Richter 2020)
- HEK293 BCL11A enhancer +58 GATA1 site, ABE7.10: ~12% target-A→G edit rate
- Same site, ABE8e: ~75% target-A→G edit rate (6× improvement)
- HSC CD34+ same site, ABE7.10: < 5% in vitro; ABE8e: ~60% — clinically therapeutic threshold

## ★ Reviewer hard-stop
Any design plan with `editing_system ∈ {ABE7.10, CBE3, BE3, BE2, BE1}` must be vetoed UNLESS the user explicitly justifies (e.g., "compare to historical baseline"). Default for new designs must be the latest version: ABE8e for A→G; CBE4max / evoBE4max / eA3A-BE4max for C→T.

## Maps to anti-rule
**anti-rule #3**: Legacy base editors (ABE7.10, CBE3, BE3, BE2, BE1) as default choice are forbidden. Required: ABE8e / CBE4max / latest evolved variant.

## Anti-retrieval keywords
abe7.10 default, cbe3 default, be3 base editor, legacy base editor, old abe, low activity editor, no abe8e
