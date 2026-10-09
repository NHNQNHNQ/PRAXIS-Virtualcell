# K562 CRISPRa external-data eligibility screen (2026-08-17)

## Outcome

No public dataset identified in this metadata-only screen is eligible for the
frozen P16 scientific gate. The strongest candidate, GSE146194/GSM4367986
`exp8`, is useful only for a separately frozen external stress test.

This record does not authorize expression access or execution. No expression
matrix, condition-level expression outcome, Golden test expression, or Golden
test outcome was read for this screen. The authoritative state remains:

| State | Value |
| --- | --- |
| P16 exact external dataset eligible | `false` |
| P16/P21 benchmark run | `NOT_RUN` |
| `benchmark_passed` | `null` |
| `scientifically_validated` | `false` |
| `promotion_eligible` | `false` |
| `production_promoted` | `false` |

The selected model remains the four-file deterministic Candidate-2 artifact,
`norman_additive_ridge_train_only_alpha_0_1`. Its reused Golden development
validation result is immutable at SHA-256
`c0c3ae835541209f1176b855603836d50689998bc0e6fee17d590c6048d7a71e`.
That result is adaptive development evidence, not an independent validation.

## Frozen eligibility requirements

The existing P16 contract requires an independent K562 (`CVCL_0004`) dataset
and platform with:

- gene-targeted CRISPR activation at the exact 5-day time point;
- single-cell RNA output with the exact ordered 5,045 Ensembl 84 features;
- native `condition_mean_X_minus_matched_split_control_mean_X` semantics;
- no feature projection, reordering, filling, imputation, normalization change,
  or other candidate-facing adaptation (`external_adaptation_steps=0`);
- single-gene and combination scopes evaluated separately;
- candidate and additive-ridge comparator run in the same frozen runtime;
- condition-level paired differences, 2,000-replicate percentile bootstrap,
  `numpy.PCG64`, seed 0, interval `(0.025, 0.975)`, with the upper bound below
  zero;
- a complete contamination audit and no outcome-driven tuning.

Because the previously used Golden test can no longer be confirmatory, formal
scientific validation now needs two previously untouched outcome sources: a
replacement primary holdout and a second independent external dataset/platform.
Both must be frozen or escrowed before outcome decoding.

## Screened public datasets

### GSE146194 / GSM4367986 `exp8` — strongest stress-test candidate

Official records: [GSE146194](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE146194),
[GSM4367986](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM4367986),
PRJNA609688, SRP251252, SRX7826831; associated
[paper](https://www.nature.com/articles/s41587-020-0470-y).

- K562 dCas9-SunTag/scFV-VP64 CRISPRa;
- 10x 3' v3 whole-transcriptome RNA plus direct guide capture;
- sampled 8 days after infection, not 5 days;
- 33,862 matrix rows: 33,694 `Gene Expression` features and 168
  `CRISPR Guide Capture` features;
- all 5,045 Candidate-2 features are present and preserve relative order, but
  selecting them from 33,694 `Gene Expression` features is a projection and
  therefore at least one adaptation step;
- four same-ID symbol aliases differ: `KIAA1804/RP5-862P8.2`,
  `C3orf72/FOXL2NB`, `RHOXF2BB/RHOXF2B`, and `C19orf26/CBARP`;
- the paper describes 49 analyzed genes while the condition metadata contains
  63 gene labels; any later evaluator must fail closed on this distinction.

The seven exact Candidate-2 outer-train target overlaps, selected by metadata
before expression access, are:

| Symbol | Ensembl ID | Frozen rank-1 guide condition |
| --- | --- | --- |
| IGDCC3 | ENSG00000174498 | `IGDCC3_-_65670488.23-P1P2_posA` |
| IRF1 | ENSG00000125347 | `IRF1_-_131826619.23-P1P2_posA` |
| KLF1 | ENSG00000105610 | `KLF1_+_12998353.23-P1P2_posA` |
| MAP2K3 | ENSG00000034152 | `MAP2K3_-_21187855.23-P1P2_posA` |
| MAP2K6 | ENSG00000108984 | `MAP2K6_+_67410755.23-P1P2_posA` |
| MAPK1 | ENSG00000100030 | `MAPK1_+_22222272.23-P1P2_posA` |
| PRTG | ENSG00000166450 | `PRTG_-_56035322.23-P1P2_posA` |

Each uses `NegCtrl11_posB`; position-matched posA controls are
`NegCtrl1_posA`, `NegCtrl5_posA`, `NegCtrl8_posA`, and `NegCtrl9_posA`.

Two metadata assets were streamed solely for identity and eligibility checks:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `GSM4367986_exp8.features.tsv.gz` | 321,310 | `b21527757f7b63825868e84a99dbb64f35d9ec50835efc7f1ce3e4bafeef598c` |
| `GSM4367986_exp8.cell_identities.csv.gz` | 2,556,477 | `3c5f90ab2fb7c56292febb3788fc68d91da85707bce5f99386797b9e9cab9c14` |

At the time of this eligibility screen, matrix coordinate entries were not
accessed. They were decoded only after the protocol and evaluator were frozen;
the later execution is recorded in
[`GSE146194-ADDITIVE-EXTERNAL-STRESS-2026-08-17.md`](GSE146194-ADDITIVE-EXTERNAL-STRESS-2026-08-17.md).
Eligibility fails independently on time point and adaptation count. The result
is only an external stress test and keeps all P16/P21/science/promotion claims
false.

### GSE257547 — rejected

Official record: [GSE257547](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE257547),
PRJNA1080204, SRP491598.

K562 dCas9-VPR CRISPRa is measured at 8 days using targeted ECCITE-seq with
about 92 RNA genes. Its four targets have no Candidate-2 outer-train overlap.
It fails the time, full-feature, zero-adaptation, and useful-target gates.

### GSE269946 — rejected

Official record: [GSE269946](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE269946),
PRJNA1124154, SRP514056.

This is a 24-hour bulk RNA-seq SAMD9 dCas9-VPR experiment. SAMD9 is unseen by
Candidate-2, the assay is not single-cell, normalization/projection would be
required, and no doxy-treated non-targeting-guide control separates inducer and
CRISPRa effects.

### Independent registry cross-check

A second metadata/Methods-only search covered GEO, SRA, BioProject, BioStudies,
ArrayExpress, and associated papers. Strict GEO queries returned eight records;
strict BioProject queries returned three, broader CRISPRa queries returned
eleven, and the exact 5-day SRA/BioProject and exact 5,045/Ensembl84 GEO queries
returned zero. No additional eligible source was found.

The strongest additional near-matches were:

- PRJNA1157910 / SRP531204: independent K562 VP64/VPR, 10x 3' v3.1
  whole-transcriptome data, but sampled at day 9 with a high-MOI mixed
  promoter/enhancer library and Ensembl 93 rather than the exact 5,045 axis;
- GSE255608 / PRJNA1075761: K562 dCas9-p300 whole-transcriptome data, but
  sampled at days 9–10 and primarily a regulatory-element epigenome-editing
  experiment, with no exact 5,045 identity declaration.

Both accession families had zero project-local tree, Git-history, and named
external-run-root matches before the search. That is a local exposure check,
not a substitute for a future custodian access log or escrow record.

## Exposure and licensing boundary

The accession families above had zero matches in the current repository, all
Git history, and named external run roots before this screen. The screen was
raw-expression blind and condition-outcome blind, but not paper-result naive:
official abstracts necessarily contain qualitative conclusions.

GEO does not impose a general use or distribution restriction, while warning
that submitters may retain intellectual-property rights. This must be recorded
as “GEO unrestricted by NCBI with submitter-IP caveat,” not as CC0. See the
[GEO disclaimer](https://www.ncbi.nlm.nih.gov/geo/info/disclaimer.html).

## Required acquisition to unblock scientific validation

The minimum viable acquisition is two independently generated or independently
escrowed K562 CRISPRa outcome bundles. Each bundle must be write-new and bind:

1. authenticated K562 identity, exact CRISPRa construct/dose, and 5-day sample;
2. exact guide/condition membership, matched non-targeting controls, and both
   single-gene and combination scopes;
3. the exact ordered 5,045 Ensembl 84 feature axis and native delta semantics;
4. raw data, metadata, preprocessing code, environment, license, file size, and
   SHA-256 identities before outcome decoding;
5. an outcome escrow/access log proving Candidate-2, comparator, metric,
   bootstrap, stopping rule, and contamination audit were frozen first.

Separate engineering is also required before a formal run: Candidate-2's
four-file artifact must receive a P12/P16 multi-artifact release identity, and
the P21 contract must represent deterministic replay honestly instead of
inventing three stochastic seeds.

Until those assets and contracts exist, the scientifically correct terminal
state is `BLOCKED_EXTERNAL / NOT_RUN`, not a failed or passed P16 result.
