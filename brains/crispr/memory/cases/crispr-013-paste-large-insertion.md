---
case_id: crispr-013-paste-large-insertion
schema_version: 1
edit_type: large_insertion_paste
target_gene: any
target_organism: hg38
cell_context: HEK293T
editing_system: PASTE
delivery_method: plasmid_transfection
tools:
- PASTE (PE + Bxb1 integrase)
- epegRNA with attB landing pad
- donor plasmid with attP
- long-read PacBio amplicon-seq
- FACS GFP/mCherry quantification
key_paper_doi: 10.1038/s41587-022-01527-4
status: validated
provenance:
  source_type: literature
  doi: 10.1038/s41587-022-01527-4
  citation: Yarnall MTN, Ioannidi EI, Schmitt-Ulms C et al. (2023) Nat Biotechnol
    41:500-512 — Drag-and-drop genome insertion of large sequences without double-strand
    DNA cleavage using CRISPR-directed integrases
  extracted_at: '2026-04-29'
  source: praxis_seed_v0.2
editing_system_list:
- PASTE
- PE3
- SpCas9-Bxb1
cell_context_list:
- HEK293T
- K562
- iPSC
- hepatocyte_in_vivo
delivery_method_list:
- plasmid_transfection
- LNP+mRNA
- dual_AAV
tags:
- large_insertion_paste
- HEK293T
- PASTE
- PE3
- Bxb1_integrase
- attB_attP
- kilobase_insertion
- DSB_free
---

# PASTE — programmable kilobase-scale insertion without DSB

## Background
Existing knock-in methods are limited to small inserts: HDR works for <1.5 kb (efficiency drops sharply beyond), and even AAV donors max around 4.5 kb cargo. **PASTE** (Yarnall/Anzalone 2022) extends programmable insertion to **>36 kb** by combining prime editing (which inserts a short ~46 bp Bxb1 attB landing pad at any genomic site) with **Bxb1 large-serine integrase** (which then catalyzes site-specific recombination between attB and an attP-flanked donor plasmid). The result: **insert any sequence at any genomic site without any double-strand break**.

PASTE is **DSB-free** (avoiding translocation risk) and **insert-size-agnostic** (limited only by Bxb1 efficiency, not cargo size). The trade-off: efficiency is moderate (~5-50% for kb-scale inserts in HEK293T; lower in primary cells), and the design has **two failure modes** (PE step + integrase step) that compound multiplicatively.

## What I actually did
1. **Target site choice**: any locus accessible to PE3 (most NGG PAM regions); pre-validate with a smaller PE3 edit before attempting PASTE.
2. **PE step (epegRNA design)**: epegRNA encodes a 46-bp Bxb1 attB sequence as the inserted edit. PBS 13-15 nt; RT template includes attB + downstream homology. Tm 30 °C target.
3. **Donor plasmid**: contains attP-flanked cargo of interest (e.g., 5 kb GFP-PuroR cassette + tissue-specific promoter). attP must be on plasmid in correct orientation.
4. **Co-delivery**: PE3 + epegRNA + Bxb1 integrase + attP donor — all four components transfected together (or expressed from same vector if size permits).
5. **Selection**: include puromycin resistance in donor → select for integrants 7-14 days.
6. **Validation**: 5'/3' junction PCR (both required); long-read amplicon (PacBio / Nanopore) for full-length insert verification; FACS for fluorescent reporter; copy number qPCR.
7. **Typical efficiency**: HEK293T 30-50% for 1-3 kb insert; iPSC 5-15%; hepatocyte (in vivo, LNP delivery) 1-5% (Yarnall 2022 SI).

## ★ 排除/不做的事
- **HDR donor for >5 kb insertion** — efficiency <1% at this size; PASTE is the alternative when AAV cargo is also exhausted.
- **PASTE without first validating PE3 at target site** — if PE3 alone fails to insert the 46 bp attB, PASTE cannot proceed; pre-test simpler edit.
- **attP donor without selection cassette** — integrant frequency 5-50% but plasmid retention is high; selection separates true integrants from episomal donor.
- **Single junction PCR for PASTE validation** — both 5' AND 3' junctions required (false positive risk with episomal donor); add long-read confirmation.
- **PASTE in actively dividing cells without thinking about copy number** — Bxb1 is catalytic; multiple integrants per cell possible if attB landing pads accumulate.
- **AAV-only PASTE delivery** — Bxb1 (1.4 kb) + PE3 (~6 kb) + epegRNA + donor exceeds AAV cargo; use plasmid or split-vector.

## ★ 失败模式
- **PE step fails to install attB** — null efficiency at target site; switch to alternative sgRNA or epegRNA design.
- **Bxb1 unidirectional integration but multi-copy** — in dividing cells, repeated PE→attB→integration cycles can produce tandem integrants; copy-number qPCR is mandatory QC.
- **attB pseudosite recombination** — Bxb1 has cryptic recognition at non-attB sequences (rare but documented); off-target integration possible.
- **Donor plasmid backbone integration** — if donor isn't properly minicircle-purified, plasmid backbone may co-integrate; minimize backbone or use minicircle prep.
- **Cell-type-dependent efficiency** — HEK293T high; iPSC ~10×lower; primary T cell or hepatocyte even lower; PE3 efficiency dominates.
- **Insert orientation** — attB and attP must be in compatible orientations; reverse-orientation integration is non-functional and ~50% of events.

## Lessons → seeds for rules
1. **PASTE for kilobase-scale insertion** — when HDR (<1.5 kb) and AAV donor (<4.5 kb) are both insufficient.
2. **Sequential validation**: (a) PE3 alone installs attB at target → (b) integrase + donor produces integrant → (c) long-read confirmation of full insert + correct orientation.
3. **Selection cassette in donor is mandatory** for clean line generation — episomal background is high.
4. **Copy-number qPCR + long-read amplicon** are the validation pair; junction PCR alone is insufficient (episomal donor produces false 5' or 3' junction signals).
5. **Cell-type efficiency drops 10-100× outside HEK293T** — pre-pilot in target cell type before scaling.
6. **DSB-free advantage** — PASTE avoids the translocation/large-deletion risk of HDR + Cas9 cuts; preferred for therapeutic large-insert applications where genomic instability is a concern.
