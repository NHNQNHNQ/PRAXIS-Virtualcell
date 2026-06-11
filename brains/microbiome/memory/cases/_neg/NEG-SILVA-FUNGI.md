---
case_id: NEG-SILVA-FUNGI
case_type: anti_pattern
microbiome_task: amplicon_its
failure_mode: SILVA (16S/18S rRNA) used to classify fungal ITS sequences leaves >80% Unassigned
maps_to_anti_rule: 7
maps_to_reviewer_block: MICROBIOME_REVIEW_SILVA_FOR_FUNGI
evidence_doi: 10.1093/nar/gky1022
evidence_quote: "UNITE is the canonical reference database for fungal ITS1/ITS2 species hypotheses (SH). SILVA contains 18S rRNA, NOT ITS, and shares essentially zero sequence with ITS amplicon products — using it for ITS classification yields >80% unassigned reads."
status: validated_neg
schema_version: 2
---

# NEG-SILVA-FUNGI — SILVA classifier on fungal ITS amplicons

## Pattern
A user runs ITS1 or ITS2 amplicon sequencing for fungal community profiling but classifies the resulting ASVs against the **SILVA 138** taxonomy database (which contains 16S/18S rRNA, not ITS). Often happens when the user copies a 16S pipeline and forgets to swap the reference database.

## Why it fails
- SILVA 138 contains 16S (bacteria/archaea) + 18S (eukaryote) rRNA gene sequences
- ITS1/ITS2 are the **internal transcribed spacers** between 18S and 28S rRNA — **a different genomic region**, hypervariable in length and sequence, NOT present in SILVA
- Naive Bayes classifier trained on SILVA will return "Unassigned" or completely wrong taxonomy for ITS reads (random 18S k-mer matches at low confidence)
- UNITE (Nilsson 2018, currently v9.0 / 2024-04) is the reference database designed for ITS, with curated species hypotheses (SH) at 97% / 98.5% / 99% similarity thresholds
- Without UNITE, downstream alpha-diversity / DA / network analyses use mostly Unassigned features → uninterpretable

## Real failure example
A 2019 wheat-rhizosphere study amplified ITS2, ran QIIME2's classify-sklearn against SILVA 132, and reported "fungal community dominated by Unassigned (87%)." Reviewers initially accepted "high novel diversity" claim. After correction with UNITE 8.0, the SAME ASVs resolved to *Fusarium*, *Mortierella*, *Trichoderma*, *Mycosphaerella* — well-known wheat rhizosphere fungi at >95% confidence. The "novelty" was a database-mismatch artifact.

## Anti-pattern detector
- `design_plan.computational_pipeline.amplicon_target` ∈ {`ITS`, `ITS1`, `ITS2`}
- AND `design_plan.computational_pipeline.reference_db` matches `silva|SILVA`
- → MICROBIOME_REVIEW_SILVA_FOR_FUNGI

## Recovery
- Switch reference DB to **UNITE** (download from unite.ut.ee — current canonical = `sh_qiime_release_29.11.2022` or newer)
- For 18S protistan amplicons SILVA IS appropriate (PR2 also good)
- For ITS classification: `qiime feature-classifier classify-sklearn --i-classifier unite-ver9-...qza` OR `vsearch --usearch_global --db unite_dynamic.fasta`
- Cite `microbiome-006-amplicon-its` + `06-its-with-unite-not-silva` + `NEG-SILVA-FUNGI`
