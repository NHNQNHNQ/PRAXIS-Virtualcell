---
case_id: NEG-PE2-ONLY-NO-NICK
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 4
edit_type: prime_editing
target_gene: any
target_organism: hg38
cell_context: HEK293T
editing_system: PE3
delivery_method: plasmid_transfection
tools: [PE2, PE3, PE5, epegRNA-PE3, PrimeDesign]
key_paper_doi: 10.1038/s41586-019-1711-4
provenance:
  source_type: literature
  doi: 10.1038/s41586-019-1711-4
  citation: "Anzalone AV, Randolph PB, Davis JR, et al. Search-and-replace genome editing without double-strand breaks or donor DNA. Nature. 2019;576(7785):149-157."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, pe2_only, no_nicking_sgrna, no_pe3, low_efficiency]
causal_tag: causal
---

# NEG-PE2-ONLY-NO-NICK — Prime editing PE2 without nicking sgRNA

## What this NEG- case records
**Anti-pattern**: deploying PE2 (pegRNA + Cas9 H840A nickase + reverse transcriptase) without the second nicking sgRNA on the unedited strand → editing efficiency stalls below 5% on most loci. The original PE3 design always pairs pegRNA with a nicking sgRNA 50-90 nt distant on the opposite strand to drive mismatch-repair toward the edited strand.

## Where the failure mode was published
Anzalone 2019 Nature Fig 4: PE2 vs PE3 at multiple HEK293T loci — PE2 achieves 1-5% pure edits at most sites; PE3 achieves 10-30% with the same pegRNA. Subsequent PE5 (with dnMLH1 to suppress MMR) raises efficiency further to 20-50% in MMR-proficient cells.

## Mechanism — why it fails
1. PE2 nicks only the protospacer-edited strand. The unedited strand is intact → mismatch repair (MMR) preferentially uses the unedited strand as template, reverting the edit.
2. Adding a second nick on the OPPOSITE strand 50-90 nt away (PE3) creates two SSBs → MMR can no longer prefer one strand → ~5× efficiency boost.
3. Adding dnMLH1 co-expression (PE5) suppresses MMR entirely → another 2-3× boost.
4. epegRNA (3' tevopreQ1 motif) protects pegRNA 3' end from degradation → another 2-3×.
5. PE2-only is never the right choice — at minimum PE3, ideally PE5 or epegRNA-PE3.

## Concrete numerics (Anzalone 2019 + Chen 2021 PE5)
- HEK293T HEK3 locus, PE2 alone: 2.8% pure edit
- Same site, PE3 (+nicking sgRNA): 28% pure edit (10× boost)
- Same site, PE3 + epegRNA: 48% pure edit (17× boost)
- Same site, PE5 + epegRNA + dnMLH1: 65% pure edit (23× boost)

## ★ Reviewer hard-stop
Any prime editing design plan with `editing_system: PE2` and no nicking sgRNA must be vetoed. Required: PE3 + nicking sgRNA on non-edited strand 50-90 nt distance, OR PE5 with dnMLH1, OR epegRNA-PE3.

## Maps to anti-rule
**anti-rule #4**: Prime editing PE2 alone (without nicking sgRNA) is forbidden. Required: PE3 / PE5 with paired nicking sgRNA + (optionally) tevopreQ1 epegRNA motif.

## Anti-retrieval keywords
pe2 alone, no nicking sgrna, single nick prime editing, no pe3, pe2 default, no opposite strand nick, no mmr suppress
