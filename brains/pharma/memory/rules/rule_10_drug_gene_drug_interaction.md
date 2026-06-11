---
rule_id: rule_10_drug_gene_drug_interaction
rule_type: case_distilled
applies_to: [ddi, tdm, poppk]
evidence_cases:
  - pharma-003-cyp3a4-ddi
  - pharma-012-cyp2d6-codeine
  - pharma-013-cyp2c19-clopidogrel
  - pharma-014-rifampin-induction-ddi
confidence: high
authoring_date: 2026-04-30
source_synthesis_section: drug-gene-drug interactions (DGI / phenoconversion)
---

# 药物-基因-药物相互作用 (DGI / phenoconversion)

A patient's underlying CYP genotype phenotype can be **functionally converted**
by concomitant CYP inhibitors or inducers. The "effective phenotype" the
patient exhibits at any moment depends on (genotype) × (current concomitant
medications). DDI prediction must account for this.

## Examples
- **CYP2D6**: EM patient + paroxetine (strong CYP2D6 inhibitor) → effective PM.
  Codeine analgesia fails despite EM genotype. Tramadol same.
- **CYP2C19**: EM patient + omeprazole/esomeprazole (strong CYP2C19 inhibitor)
  → effective PM. Clopidogrel platelet inhibition fails.
- **CYP3A4** (case-003): substrate × strong inhibitor → effective null-CYP3A4.
- **CYP3A4 induction** (case-014): rifampin × midazolam → effective UM-like
  for any CYP3A4 substrate, regardless of substrate genotype.

## Mandatory operations

1. **Concomitant medication review at every visit** (rule_05).
2. **Phenoconversion assessment**: if patient on strong inhibitor of the metabolizing
   enzyme, treat as PM regardless of genotype.
3. **DDI dose adjustment**: at minimum, document the phenoconversion + revisit
   prescription decisions when concomitant medication changes.
4. **PPI choice for stent patients**: pantoprazole (negligible CYP2C19 inhibitor)
   over omeprazole/esomeprazole.
5. **Substitution preferred over dose-adjust**: if phenoconversion reduces drug
   efficacy, switch to non-affected drug class rather than escalate dose.

## Reviewer soft-warnings

- DDI prediction without explicit concomitant medication list → flag.
- Genotype-only without phenoconversion check → flag for high-risk drugs.
