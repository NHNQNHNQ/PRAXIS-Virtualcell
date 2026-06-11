---
case_id: NEG-NO-BLANK-LOWBIOMASS
case_type: anti_pattern
microbiome_task: amplicon_16s_or_shotgun
failure_mode: Low-biomass sample sequenced without a blank/extraction control — kit-ome contamination becomes the "result"
maps_to_anti_rule: 9
maps_to_reviewer_block: MICROBIOME_REVIEW_NO_NEG_CONTROL_LOW_BIOMASS
evidence_doi: 10.1186/s12915-014-0087-z
evidence_quote: "Reagent and laboratory contamination critically impact sequence-based microbiome studies. In low-biomass samples (skin, lung, placenta, BAL, biopsies), the contaminant taxa from DNA extraction kits and PCR reagents can outnumber true biological signal. Negative extraction blanks and PCR no-template controls are MANDATORY and must be sequenced and analyzed alongside samples."
status: validated_neg
schema_version: 2
---

# NEG-NO-BLANK-LOWBIOMASS — Low-biomass study without negative controls

## Pattern
Sequencing low-biomass samples (skin swabs, BAL, biopsy tissue, placenta, indoor air, blood, ancient DNA, neonatal meconium) WITHOUT including extraction blanks (buffer-only DNA extraction) and PCR no-template controls — and especially without sequencing those controls and subtracting them from the biological samples (e.g., `decontam`, SCRuB).

## Why it fails
- Salter et al. 2014 ("Reagent and laboratory contamination critically impact..."): every commercial DNA extraction kit harbors a characteristic "kit-ome" — *Bradyrhizobium*, *Burkholderia*, *Ralstonia*, *Pseudomonas*, *Acinetobacter* are common
- When biological biomass is low (<10⁴ cells), the kit-ome dominates the read pool — the "microbiome" becomes the kit
- 2014–2018 "placental microbiome" literature was largely retracted because no-blank controls revealed the placenta is sterile in healthy term pregnancy
- Without sequenced blanks, you cannot apply `decontam` (Davis 2018) or SCRuB (Austin 2023) to subtract contamination
- Reviewers (and Reviewer agent) MUST hard-block any low-biomass study without a documented negative-control plan

## Real failure example
A 2017 lung microbiome / cystic fibrosis study sequenced BAL samples (estimated 10²–10³ bacteria) with NO extraction blank. Reported "novel CF airway microbiome dominated by *Bradyrhizobium* + *Burkholderia*." A 2019 follow-up that included blanks showed *Bradyrhizobium* came 100% from the Qiagen kit and *Burkholderia* was kit + cross-well contamination. The actual CF microbiome (after decontam) was *Pseudomonas aeruginosa* + *Staphylococcus* + *Haemophilus* — completely different conclusion.

## Anti-pattern detector
- `design_plan.scoping.sample_type` ∈ {`skin`, `bal`, `biopsy`, `placenta`, `air`, `blood`, `neonatal`, `tissue`, `low_biomass`}
- AND `design_plan.scoping.negative_control_plan` is missing OR set to `none` / `false`
- → MICROBIOME_REVIEW_NO_NEG_CONTROL_LOW_BIOMASS (HARD BLOCK)

## Recovery
- Plan ≥3 extraction blanks (buffer + kit, no sample) per batch + ≥1 PCR no-template control per plate
- Sequence blanks at the same depth as samples
- Run `decontam` (R/Bioconductor, prevalence + frequency methods) OR SCRuB (Python, 2023)
- Report contaminant taxa list + how many ASVs/features were filtered + remaining biomass
- Cite `microbiome-009-negative-control` + `11-negative-control-low-biomass` + `NEG-NO-BLANK-LOWBIOMASS`
