---
case_id: NEG-AAV-CLINICAL-NO-NAB
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 11
edit_type: in_vivo_gene_therapy
target_gene: any
target_organism: hg38
cell_context: hepatocyte_in_vivo
editing_system: SaCas9
delivery_method: AAV
tools: [AAV8, AAV9, AAV-LK03, NAb screening assay, luciferase reporter]
key_paper_doi: 10.1089/hum.2009.182
provenance:
  source_type: literature
  doi: 10.1089/hum.2009.182
  citation: "Boutin S, Monteilhet V, Veron P, et al. Prevalence of serum IgG and neutralizing factors against adeno-associated virus (AAV) types 1, 2, 5, 6, 8, and 9 in the healthy population: implications for gene therapy using AAV vectors. Hum Gene Ther. 2010;21(6):704-712."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, aav_clinical, no_nab_screen, pre_existing_immunity, neutralized_dose]
causal_tag: causal
---

# NEG-AAV-CLINICAL-NO-NAB — AAV in-vivo gene therapy without pre-existing NAb screen

## What this NEG- case records
**Anti-pattern**: deploying an AAV-delivered Cas9 / base editor / prime editor in a clinical trial (or IND-stage NHP study) without first screening patients/animals for pre-existing serum neutralizing antibodies (NAb) against the chosen AAV serotype. NAb-positive patients receive zero therapeutic dose because the capsid is neutralized in circulation.

## Where the failure mode was published
Boutin S et al. (2010) Hum Gene Ther established the seroprevalence baseline: AAV2 NAb-positive in 60-72% of healthy adults; AAV1 in 50-60%; AAV9 in 35-50%; AAV8 in 30-40%; AAV6 in 30-50%. These patients are excluded from AAV gene-therapy enrollment because the dose is neutralized. The Verve VERVE-101 program (case-010) explicitly cited this risk as the reason they pivoted from AAV-Cas9 to LNP+ABE8e mRNA.

## Mechanism — why it fails
1. AAV capsids share epitopes across serotypes (AAV1/AAV6 cross-reactivity; AAV8/AAV9 lower).
2. Childhood exposure to wild-type AAV (often via co-infection with adenovirus) generates persistent IgG NAb.
3. NAb titer ≥ 1:5 typically excludes; titer ≥ 1:20 strongly neutralizes.
4. Dose escalation cannot overcome NAb (capsid is bound, not internalized).
5. Without pre-screen, 30-70% of enrolled patients receive null dose → trial fails.

## Concrete numerics (Boutin 2010 + Verve 2023)
- AAV2 NAb seroprevalence: ~60-72% (highest)
- AAV8 NAb seroprevalence: ~30-40%
- AAV9 NAb seroprevalence: ~35-50%
- AAV-LK03 (engineered): ~5-10% (designed to evade)
- Verve VERVE-101 chose LNP+mRNA precisely to avoid the NAb gating issue
- Macaque NHP studies: NAb pre-screen + exclude positive animals is mandatory

## ★ Reviewer hard-stop
Any in-vivo gene therapy design plan with `delivery: AAV*` AND `clinical: True` (or NHP IND-prep) without `nab_screen_protocol` field must be vetoed. Required: pre-treatment serum NAb assay (luciferase-based or in-vitro neutralization) with explicit titer cutoff for enrollment.

## Maps to anti-rule
**anti-rule #11**: AAV clinical / NHP in-vivo gene therapy without pre-existing NAb screen is forbidden. Required: serum NAb assay protocol + enrollment/exclusion cutoff documented.

## Anti-retrieval keywords
no nab screen, no neutralizing antibody check, aav clinical no pre-screen, aav nab pre-existing, no aav serology, no patient nab assay, aav null dose
