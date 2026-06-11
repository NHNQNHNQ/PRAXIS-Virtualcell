---
case_id: NEG-UNMODIFIED-mRNA-INNATE-IMMUNITY-PRE2005
schema_version: 1
status: validated
source: praxis_seed_NEG
task: mrna_vaccine_sequence_design
immuno_task: mrna_vaccine_sequence_design
antigen_class: viral
hla_class: population_coverage
hla_alleles: []
peptide_length_bin: n/a
disease_indication: infection_general
target_protein: any antigen mRNA
target_protein_uniprot: []
tools: [unmodified U mRNA, naive in vitro transcription, no nucleoside modification]
key_paper_doi: 10.1016/j.immuni.2005.06.008
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, mRNA, m1psi, innate-immunity, TLR, translation-block, Kariko-Weissman]
unverified_details: []
---

# NEG: Pre-2005 unmodified-U mRNA caused massive TLR3/7/8 activation → translation block (Karikó & Weissman 2005)

## Background
Before Karikó & Weissman's 2005 Immunity paper (which 19 years later won the 2023 Nobel Prize in Physiology or Medicine), in vitro transcribed (IVT) mRNA with **unmodified uridine (U)** triggered massive innate immune activation via TLR3 (dsRNA) + TLR7/8 (ssRNA) + RIG-I + MDA5 pathways. Result: PKR phosphorylation → eIF2α inactivation → **translation block**, plus type-I interferon storm. **mRNA therapeutics were stalled for ~20 years** because of this single design oversight: no incorporation of modified nucleosides (m1Ψ, m5C).

## What the field actually did (the wrong way) for ~2 decades
1. Used unmodified U + standard IVT
2. Got massive innate response in cell culture and animals
3. Misattributed to "mRNA is fundamentally too unstable / too immunogenic for therapy"
4. Abandoned for protein/DNA approaches
5. Required TWO (Karikó pseudo-U) and THREE (Karikó N1-methyl-pseudo-U) generations of nucleoside modification before BNT162b2 / mRNA-1273 became viable

## ★ 排除/不做的事 (anti-pattern)
- ❌ Unmodified U mRNA for any therapeutic / vaccine application (innate immunity activation guaranteed)
- ❌ Designing mRNA vaccine workflow without mandatory nucleoside modification step
- ❌ Treating "high CpG content" as innocuous (CpG triggers TLR9 — design must minimize)
- ❌ Skipping cap analog (Cap0/Cap1 vs Cap-2,2,7-trimethyl) — uncapped mRNA is recognized as foreign

## ★ 失败模式 (anti-rule trigger)
- **mRNA without nucleoside modification → TLR3/7/8 + RIG-I + MDA5 activation**
- **Translation block via eIF2α phosphorylation** even when mRNA is intact
- **Type-I IFN storm** confounds the desired antigen-specific immune response
- **Excessive CpG content triggers TLR9** in plasmacytoid dendritic cells

## ★ 方法选择决策链 (what they should have done)
- Always substitute U → m1Ψ (N1-methyl-pseudouridine; canonical for BNT162b2/mRNA-1273)
- Optionally substitute C → m5C (additional dampening of innate response)
- Cap1 structure (m7G + 2'-O-methyl) — not Cap0 / no cap
- Codon optimization should also reduce CpG dinucleotides
- Validate translation efficiency in iPSC + DC ex vivo before in vivo

## ★ Validation
- Field-wide evidence: ~20 years of failed mRNA therapeutics → 2005 Karikó/Weissman Immunity paper → 2020 BNT162b2/mRNA-1273 success
- Direct evidence: Karikó 2008 Mol Ther showed m1Ψ-mRNA is 10x more translatable + ~10x less immunogenic than unmodified
- Vaccine-scale evidence: BNT162b2 / mRNA-1273 use m1Ψ; high translation, controllable innate response

## Lessons → ANTI-RULES generated
- **anti-rule 7**: mRNA vaccine/therapeutic design without explicit nucleoside modification flag (m1Ψ default) → block
- **anti-rule 8**: mRNA design without Cap1 (or equivalent) → warn (block when used in vaccine context)
- **anti-rule 9**: mRNA design with elevated CpG content (> baseline) without justification → warn

## 数据指针
- Source: Karikó K, Weissman D et al. 2005, "Suppression of RNA recognition by Toll-like receptors: the impact of nucleoside modification and the evolutionary origin of RNA"
- Subsequent: Karikó K et al. 2008, "Incorporation of pseudouridine into mRNA yields superior nonimmunogenic vector"
- Real-world payoff: BNT162b2 / mRNA-1273 (2020-2021), Nobel Prize 2023
