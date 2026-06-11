---
case_id: NEG-CAS13-AS-DNA-EDITOR
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 12
edit_type: rna_targeting
target_gene: any
target_organism: hg38
cell_context: any
editing_system: RfxCas13d
delivery_method: any
tools: [RfxCas13d, LwaCas13a, PspCas13b, Cas13design]
key_paper_doi: 10.1038/nature24049
provenance:
  source_type: literature
  doi: 10.1038/nature24049
  citation: "Abudayyeh OO, Gootenberg JS, Essletzbichler P, et al. RNA targeting with CRISPR-Cas13. Nature. 2017;550(7675):280-284."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, cas13_as_dna_editor, concept_error, rna_only_enzyme]
causal_tag: causal
---

# NEG-CAS13-AS-DNA-EDITOR — Using Cas13 (RNA-only enzyme) for DNA editing

## What this NEG- case records
**Anti-pattern**: proposing Cas13 (LwaCas13a, PspCas13b, RfxCas13d / CasRx, etc.) as the editing system in a design plan whose `edit_type` is `knockout_indel`, `knock_in_hdr`, `base_editing_*`, `prime_editing`, `multiplex_knockout`, `saturation_genome_editing_sge`, or `in_vivo_gene_therapy` (with the goal being permanent genomic edit). Cas13 is an RNA-targeting nuclease — it does NOT cleave DNA. The design is a fundamental concept error.

## Where the failure mode was published
Abudayyeh OO et al. (2017) Nature established that LwaCas13a + crRNA cleaves single-stranded RNA targets in vitro and in mammalian cells; X-ray structure (Liu 2017 Cell) shows the HEPN domains coordinate two divalent metal ions to attack the RNA backbone — there is no DNA-binding loop. Subsequent Cas13 variants (Cas13b/c/d) are all RNA-only. The Cas13-based "REPAIR" / "RESCUE" tools (Cox 2017) deaminate RNA bases (A→I, read as G) but still do NOT touch DNA.

## Mechanism — why it fails
1. Cas13 HEPN catalytic dyad targets ssRNA via 2'-OH-mediated chemistry; DNA lacks 2'-OH.
2. Cas13-crRNA complex binds RNA via WED-pentaheterosydyad interaction with 2'-OH; DNA cannot fit.
3. No published Cas13 variant has gained DNA-cutting activity through engineering (HEPN domains are mechanistically distinct from RuvC/HNH of Cas9 or RuvC/Nuc of Cas12a).
4. Therefore: Cas13 produces transient, reversible mRNA knockdown; it CANNOT produce a heritable DNA edit.
5. If the user's goal is permanent KO/KI/SNV/insertion → Cas13 is the wrong tool. Use SpCas9/SaCas9/Cas12a/ABE/CBE/PE instead.

## Concrete numerics (Abudayyeh 2017 + follow-up)
- Cas13a/b/c/d in vitro DNA cleavage: 0% (background, never reported)
- Cas13a/b/c/d in vitro RNA cleavage: 50-90% within minutes at 37°C
- mRNA knockdown duration in mammalian cells (transient mRNA delivery): 3-7 days, reverts with mRNA degradation
- Heritable change: 0% (DNA untouched)

## ★ Reviewer hard-stop
Any design plan with `editing_system ∈ {RfxCas13d, LwaCas13a, PspCas13b, ...}` whose `edit_type` is anything OTHER than `rna_targeting` must be vetoed as a concept error. Required: switch editing_system to Cas9/Cas12a/ABE/CBE/PE for DNA work; OR confirm `edit_type: rna_targeting` if RNA knockdown is the actual goal.

## Maps to anti-rule
**anti-rule #12**: Cas13 (RNA-only) used for DNA editing tasks is forbidden (concept error). Required: edit_type must be `rna_targeting` for any Cas13 design; for DNA work, choose SpCas9 / SaCas9 / Cas12a / ABE / CBE / PE.

## Anti-retrieval keywords
cas13 as dna editor, cas13 dna cleavage, casrx dna ko, cas13 knock-in, cas13 base editor dna, cas13 hdr, cas13 prime editing, rna only enzyme on dna
