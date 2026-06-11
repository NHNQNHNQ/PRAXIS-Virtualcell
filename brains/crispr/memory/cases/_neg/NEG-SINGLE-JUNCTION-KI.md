---
case_id: NEG-SINGLE-JUNCTION-KI
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 6
edit_type: knock_in_hdr
target_gene: any
target_organism: hg38
cell_context: iPSC
editing_system: SpCas9
delivery_method: dsDNA_RNP
tools: [primer3, Sanger sequencing, Southern blot, ddPCR]
key_paper_doi: 10.1038/s41586-018-0326-5
provenance:
  source_type: literature
  doi: 10.1038/s41586-018-0326-5
  citation: "Roth TL, Puig-Saus C, Yu R, et al. Reprogramming human T cell function and specificity with non-viral genome targeting. Nature. 2018;559(7714):405-409."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, single_junction_pcr, false_positive_ki, no_southern, random_integration]
causal_tag: causal
---

# NEG-SINGLE-JUNCTION-KI — Single-junction PCR validation for HDR knock-in

## What this NEG- case records
**Anti-pattern**: confirming a knock-in with only a 5' OR 3' junction PCR (one side) and declaring the clone "HDR-positive". Random integration of dsDNA donor produces 5'-junction-only signals (with the donor + flanking landing pad accidentally annealing on one side); single-junction PCR cannot distinguish targeted HDR from random integration.

## Where the failure mode was published
Roth 2018 Nature documented the false-positive problem in pooled-knock-in CAR-T workflows: with dsDNA donor, ~30-50% of clones positive at 5' junction were ALSO positive at random-integration sites (Southern blot revealed 2-3 bands instead of expected 1). Single-junction PCR alone gave a false-positive rate of 30-50%.

## Mechanism — why it fails
1. dsDNA HDR donor with 500-1000 bp homology arms can integrate randomly via NHEJ at any genomic DSB.
2. The 5' junction primer set anneals at the donor's 5' homology arm + an adjacent random-genomic flank → false positive.
3. The 3' junction is independent — random integrations rarely produce both 5' AND 3' correct junctions simultaneously.
4. Southern blot or long-read sequencing reveals additional integration bands that PCR misses.
5. ddPCR with copy-number reference can detect multi-copy random integration.

## Concrete numerics (Roth 2018 + standard HDR workflows)
- HEK293T AAVS1 GFP knock-in, single 5' junction PCR: 80% positive
- Same clones, both 5' AND 3' junction PCR: 50% positive (30% false positive eliminated)
- Same clones + Southern blot single-band: 35% truly clean integrated (15% additional copies eliminated)
- Pure clean clones = 35% / 80% = 44% of single-junction "positives" are actually clean

## ★ Reviewer hard-stop
Any HDR knock-in validation plan with only one junction PCR (5' OR 3', not both) must be vetoed. Required: 5' AND 3' junction PCR (both must be positive) AT MINIMUM; ideally + Southern blot or ddPCR to rule out additional copies.

## Maps to anti-rule
**anti-rule #6**: Single-junction PCR alone for KI validation is forbidden. Required: 5' AND 3' junction PCR (both sides) + (preferably) Southern blot or ddPCR copy-count.

## Anti-retrieval keywords
single junction pcr, only 5 prime junction, only 3 prime junction, no double junction, no southern blot, false positive ki, random integration ki
