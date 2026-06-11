---
case_id: crispr-014-pig-perv-xeno-ko
schema_version: 1
edit_type: xenotransplantation_multi_ko
target_gene: any
target_organism: hg38
cell_context: in_vivo_organ
editing_system: SpCas9
delivery_method: plasmid_transfection
tools:
- SpCas9 multi-sgRNA cocktail
- pig fibroblast electroporation
- SCNT (somatic cell nuclear transfer) cloning
- ddPCR for PERV copy number
- WGS for off-target characterization
key_paper_doi: 10.1126/science.aan4187
status: validated
provenance:
  source_type: literature
  doi: 10.1126/science.aan4187
  citation: Niu D, Wei H-J, Lin L et al. (2017) Science 357:1303-1307 — Inactivation
    of porcine endogenous retrovirus in pigs using CRISPR-Cas9
  extracted_at: '2026-04-29'
  source: praxis_seed_v0.2
tags:
- xenotransplantation_multi_ko
- pig
- PERV
- SpCas9
- SCNT
- 62-cuts
- multiplex_extreme
- translocation_risk
---

# Pig PERV inactivation — extreme multiplex CRISPR for xenotransplantation

## Background
Porcine endogenous retroviruses (PERVs) are present at **25 active genomic copies** in the pig genome (3 subtypes: PERV-A, -B, -C). They pose a barrier to pig→human xenotransplantation because they can theoretically infect human cells in the recipient. **Niu/Yang 2017** (eGenesis) used CRISPR-Cas9 with two sgRNAs targeting conserved PERV pol gene to **simultaneously inactivate all 25 copies** in pig fibroblasts, then used somatic cell nuclear transfer (SCNT) to clone live PERV-knockout piglets.

This case is the **most extreme multiplex CRISPR** documented (62 simultaneous cuts in some clones; >100% inactivation efficiency required since both sgRNAs hit each of 25 loci). It establishes both the feasibility and the failure modes of high-multiplicity Cas9 editing.

## What I actually did
1. **Target choice**: 2 sgRNAs (sgRNA-1 and sgRNA-2) against the conserved *pol* catalytic core of PERV. Both sgRNAs hit ALL 25 active PERV copies simultaneously (62 total cuts per cell).
2. **Cell platform**: PFF (porcine fetal fibroblast); easier to electroporate + clone via SCNT than germline editing.
3. **Delivery**: plasmid electroporation (SpCas9 + sgRNA-1 + sgRNA-2 + selection); 1-week puromycin selection; clone isolation.
4. **Screening**: ddPCR with PERV-pol-specific probe → quantify residual functional PERV copies; aim for **0/25 active**.
5. **SCNT cloning**: PERV-null PFF → enucleated oocyte → embryo transfer → live piglets ("Laika" the pig).
6. **Validation**: WGS of cloned animals → confirm PERV inactivation + characterize off-target indels and translocations.
7. **Final efficiency**: 100% PERV inactivation in newborn piglets; 1000× reduction in PERV viral particle release (in vitro pig→human cell co-culture).

## ★ 排除/不做的事
- **Single sgRNA against 25 copies** — too many escape mutants; redundant 2-sgRNA design ensures all copies hit.
- **Direct in vivo / germline editing** — too risky given translocation rate; the SCNT approach allows clone selection before whole-animal generation.
- **Stable lentiviral Cas9 for multiplex** — months of expression accumulates off-target damage exponentially; transient electroporation only.
- **In vivo / direct-edit large animals** — 25-locus multiplex translocation rate is high (~50% of clones have detectable translocations); selection in cell culture is mandatory.
- **PERV-only KO without other xeno-incompatibility KOs** — also need GGTA1, CMAH, β4GalNT2 KOs to address α-Gal antigens; PERV alone doesn't make a transplant-ready pig.
- **Skipping WGS off-target characterization** — 62 simultaneous DSBs produce extensive translocation landscape; amplicon-seq alone misses chromosomal rearrangement.

## ★ 失败模式
- **Cell death from too-many DSBs** — clones with all 25 PERV inactivated were rare (~5% survival post-electroporation) due to cellular stress from massive simultaneous DNA damage.
- **Translocations between PERV loci** — Niu 2017 reported translocations in some surviving clones; they were excluded from SCNT.
- **SCNT inefficiency** — porcine cloning is intrinsically low (1-5% live births); compounding with pre-clone CRISPR selection makes the pipeline slow.
- **PERV reactivation in vivo** — long-term studies needed to confirm null state is stable across pig generations and tissues.
- **Off-target editing in essential pig genes** — extensive WGS revealed off-target indels at sites with PAM-proximal sequence similarity to PERV-pol.
- **Incomplete xeno-compatibility** — even PERV-null pigs require multiple additional KOs (GGTA1, CMAH, β4GalNT2) and human transgene knock-ins (CD46, CD55, thrombomodulin) for actual organ transplantation; PERV KO is necessary but far from sufficient.

## Lessons → seeds for rules
1. **Extreme multiplex (>10 simultaneous cuts) requires SCNT-like clone selection** — direct in vivo editing produces unmanageable translocation landscape.
2. **Redundant sgRNA design for repeat-element KO** — two non-overlapping sgRNAs ensure all copies hit even with escape mutants.
3. **Translocation amplicon-seq + WGS are mandatory** for >5-locus multiplex; standard amplicon-seq misses chromosomal rearrangement.
4. **Transient delivery (electroporation, not lentiviral)** for any multiplex — accumulated off-target damage scales with editor exposure.
5. **Multi-KO pipeline staging** — PERV KO → next-round GGTA1/CMAH/β4GalNT2 KO → next-round human transgene KI; sequential rather than simultaneous to control complexity.
6. **WGS-level off-target characterization** is mandatory for clinical xenotransplantation — IND filing requires it.
