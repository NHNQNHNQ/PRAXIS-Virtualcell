---
case_id: NEG-RAREFY-DA
case_type: anti_pattern
microbiome_task: differential_abundance
failure_mode: Rarefying counts before differential abundance throws away real reads and inflates variance
maps_to_anti_rule: 5
maps_to_reviewer_block: MICROBIOME_REVIEW_RAREFY_BEFORE_DA
evidence_doi: 10.1371/journal.pcbi.1003531
evidence_quote: "Rarefying microbiome data is statistically inadmissible. It throws away as much as 90% of the data and inflates Type-I and Type-II error rates compared to model-based methods (DESeq2, edgeR, ANCOM-BC) that respect the count structure."
status: validated_neg
schema_version: 2
---

# NEG-RAREFY-DA — Rarefaction before differential abundance

## Pattern
Rarefying (subsampling without replacement to a fixed depth) the count table BEFORE running a differential-abundance test (Wilcoxon / DESeq2 / ANCOM-BC2 / MaAsLin2). Often justified as "controlling for sequencing depth," but it actively destroys statistical power.

## Why it fails
- Rarefying typically discards 30–90% of the reads in the deepest samples — those reads carry real biological signal
- Subsampling INTRODUCES variance (the same sample rarefied twice gives different counts) which model-based DA methods would not have to absorb
- Rarefied counts are still compositional — rarefaction does NOT solve the closure problem that ANCOM-BC2 / ALDEx2 / GMPR are built to handle
- McMurdie & Holmes 2014 simulations: rarefaction has 2–5× worse Type-I+Type-II error than DESeq2/edgeR at every effect size
- Modern tools (ANCOM-BC2, MaAsLin2 2024, ALDEx2) explicitly accept RAW counts and do their own depth normalization via offset/log-ratio

## Real failure example
A 2022 vaginal microbiome study rarefied to 5,000 reads (the minimum sample) before Wilcoxon-on-relative-abundance. Reported "no taxa differed between BV+ and BV- after FDR." Re-analysis with ANCOM-BC2 on RAW counts (same data) found *Gardnerella vaginalis* up 14× (q=3e-5) and *Lactobacillus crispatus* down 9× (q=2e-4) — both well-known BV markers. The rarefaction step had thrown away 75% of the reads from healthy samples (which had 20,000+ reads) and the resulting variance washed out the signal.

## Anti-pattern detector
- `design_plan.computational_pipeline.normalization` contains `rarefy` OR `rarefaction` OR `subsample_depth`
- AND `design_plan.computational_pipeline.tools` contains any of {`ancombc`, `ancom-bc2`, `maaslin2`, `deseq2`, `edger`, `aldex2`}
- → MICROBIOME_REVIEW_RAREFY_BEFORE_DA

## Recovery
- Pass RAW count table directly to ANCOM-BC2 / MaAsLin2 / DESeq2 — they handle depth via offset
- If you MUST rarefy (e.g., for alpha-diversity), do it in a SEPARATE branch and never let rarefied counts enter the DA test
- Cite `microbiome-005-da-compositional` + `12-ancombc-or-maaslin2-on-raw-counts` + `NEG-RAREFY-DA`
- Report read-loss percentage in methods if rarefaction is unavoidable
