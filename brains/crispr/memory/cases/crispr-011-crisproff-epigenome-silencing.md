---
case_id: crispr-011-crisproff-epigenome-silencing
schema_version: 1
edit_type: epigenome_silencing
target_gene: any
target_organism: hg38
cell_context: K562
editing_system: dCas9-KRAB-DNMT3A
delivery_method: lentivirus
tools:
- CRISPRoff (dCas9-ZNF10-KRAB-DNMT3A-DNMT3L)
- CRISPRon (TET1-CD)
- amplicon-bisulfite-seq
- RNA-seq
key_paper_doi: 10.1016/j.cell.2021.03.025
status: validated
provenance:
  source_type: literature
  doi: 10.1016/j.cell.2021.03.025
  citation: Nuñez JK et al. (2021) Cell 184:2503-2519 — Genome-wide programmable transcriptional
    memory by CRISPR-based epigenome editing
  extracted_at: '2026-04-29'
  source: praxis_seed_v0.2
cell_context_list:
- K562
- iPSC
- HEK293T
editing_system_list:
- dCas9-KRAB-DNMT3A
- dCas9-KRAB
- dCas9-VP64
tags:
- epigenome_silencing
- CRISPRoff
- K562
- dCas9-KRAB-DNMT3A
- DNA_methylation
- heritable
- indel_free
- multiplexable
---

# CRISPRoff — heritable epigenome silencing without DNA cuts

## Background
Conventional Cas9 KO leaves permanent indels but only works at one allele at a time, requires DSB repair, and is limited by chromatin accessibility. CRISPRoff (Nuñez 2021) uses a **dCas9 fusion of ZNF10-KRAB + DNMT3A-DNMT3L** to **methylate CpG islands** at any sgRNA-targeted promoter, producing **heritable transcriptional silencing** maintained for >50 cell divisions after the editor itself is no longer expressed. CRISPRon (dCas9 + TET1 catalytic domain) reverses the silencing.

This is **DSB-free editing** — no double-strand break, no off-target translocations, no NHEJ vs HDR competition. The trade-off: silencing is **probabilistic per cell** (not all-or-nothing) and only works at promoter regions with CpG content.

## What I actually did
1. **Target**: >6,000 protein-coding genes screened genome-wide; promoter CpG island within 200 nt of TSS.
2. **sgRNA**: tile 5 sgRNAs per promoter; SpCas9 NGG PAM (dead-Cas9 still uses normal sgRNA).
3. **Delivery**: transient lentivirus expressing CRISPRoff + sgRNA cassette; single transient pulse establishes heritable silencing.
4. **Readout**: bulk RNA-seq day 14, day 30, day 50; amplicon-bisulfite-seq at TSS to confirm CpG methylation.
5. **Reversibility**: re-targeting same locus with **CRISPRon** (TET1-CD) reactivates the silenced gene.
6. **Genome-wide screen**: 5-sgRNA library against ~20k human genes → identify which genes are silenceable (CpG-island-positive) vs refractory.

## ★ 排除/不做的事
- **Genes lacking promoter CpG island** — CRISPRoff requires CpG substrate for DNMT3A; ~30% of human genes refractory.
- **Targeting gene body / 3' UTR** — silencing efficiency drops sharply outside the TSS ±200 nt window.
- **Bare KRAB-only (no DNMT3A)** — KRAB silencing is **transient** (decays after editor removal); the DNMT3A fusion is what makes it heritable.
- **Stable lentivirus expression of CRISPRoff** — long-term Cas9 fusion expression risks epigenome-wide off-target methylation; **transient** delivery is the design intent.
- **Single sgRNA in heterochromatic regions** — chromatin accessibility limits dCas9 binding; tile ≥3 sgRNAs.
- **Using CRISPRoff for protein KO assays before validating silencing depth** — typical 80-95% silencing, not full loss; allelic mosaicism remains.

## ★ 失败模式
- **Genes with active enhancers bypassing TSS silencing** — distal enhancers can rescue expression; CRISPRoff at TSS only.
- **Methylation drift over passages** — heritability is high but not perfect; ~5-15% reactivation at 50+ divisions in some loci.
- **Off-target methylation** — dCas9 binds promiscuously to similar sgRNA-protospacer sequences; methylation footprint may extend beyond intended TSS.
- **Cell-type-dependent efficiency** — iPSC less efficient than K562; primary cells ~30-50% silencing.
- **Confounded with cell-cycle arrest** — CRISPRoff at essential genes silences them → cells stop dividing → readout selects for incompletely silenced cells.
- **Spurious CpG methylation in gene body** — DNMT3A can occasionally methylate downstream sequences; amplicon-bisulfite-seq across gene body is recommended QC.

## Lessons → seeds for rules
1. **Epigenome editing is DSB-free** — choose CRISPRoff/CRISPRon over indel-based KO when (a) reversibility desired, (b) translocation risk unacceptable, (c) chromatin readout integrity needed (no DSB repair scars).
2. **Target promoter CpG island within ±200 nt of TSS** — required substrate for DNMT3A.
3. **Transient delivery (lentiviral pulse → puromycin select → drop)** is the design intent — long-term editor expression risks off-target methylation.
4. **Tile ≥3 sgRNAs per locus** — dCas9 binding is chromatin-dependent; redundant guides ensure coverage.
5. **Validate silencing by amplicon-bisulfite-seq at TSS** — pure RNA-seq doesn't distinguish CRISPRoff (heritable methylation) from KRAB-only (transient).
6. **Reversibility test** — apply CRISPRon (TET1-CD) at same locus; reactivation confirms epigenetic (not genetic) mechanism.
