---
case_id: NEG-WHO-ALLERGEN-CRITERIA-ALONE
schema_version: 1
status: validated
source: praxis_seed_NEG
task: allergenicity_assessment
immuno_task: allergenicity_assessment
antigen_class: plant_protein
hla_class: n/a
hla_alleles: []
peptide_length_bin: n/a
disease_indication: gmo_safety
target_protein: novel transgenic crop / biologic
target_protein_uniprot: []
tools: [WHO criteria alone (80aa window / 35% identity OR 8aa exact), no DL classifier consensus]
key_paper_doi: 10.3390/ijms20030531
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, allergen-prediction, WHO-criteria, false-negative-conformational]
unverified_details: []
---

# NEG: WHO/FAO allergen criteria alone misses ~30% of conformational allergens (Westwood 2019 IJMS)

## Background
WHO/FAO allergenicity assessment (1996, updated 2003) uses two sequence rules: (a) ≥ 35% identity over an 80-aa sliding window vs known allergen, (b) any 8 contiguous aa exact match. These criteria are highly specific (low false-positive) but have ~30% false-negative rate for **conformational allergens** (allergens whose IgE epitopes depend on 3D structure, not contiguous sequence). DL classifiers (AllerCatPro / AlgPred-2.0 / AllerTOP) trained on structural+sequence features catch many of these.

## ★ 排除/不做的事
- ❌ WHO criteria as sole allergen prediction signal for GMO crop / biologic safety
- ❌ "Negative on WHO criteria → ship to market" without conformational epitope assessment
- ❌ Skipping wet-lab IgE-ELISA / basophil activation backup when DL classifier flags risk

## ★ 失败模式
- **Conformational allergen passes WHO criteria** → cleared for market → IgE binding shows up post-launch (rare but documented)
- **Cross-reactive carbohydrate determinants (CCDs)** also missed by sequence-only criteria

## ★ 方法选择决策链
- WHO criteria + ≥ 3 DL classifiers (AllergenOnline + AllerCatPro + AlgPred-2.0 + AllerTOP) consensus
- ≥ 3 tool consensus required for "reject" (rule 01)
- Wet-lab IgE-ELISA on flagged candidates

## Lessons → ANTI-RULES generated
- **anti-rule 18**: WHO allergen criteria alone (no DL classifier consensus) → block (rule 01)
