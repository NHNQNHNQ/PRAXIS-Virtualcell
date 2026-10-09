# K562 CRISPRa blinded acquisition and custody inquiry

Status: sendable capability inquiry; human-readable and non-authoritative.

The authoritative machine records are:

- `data/golden/norman_2019/k562_crispra_acquisition_plan.json`
- `data/golden/norman_2019/k562_crispra_blinded_intake_contract.json`
- `reports/science/k562-crispra-formal-validation-status.json`

If this document conflicts with a machine record, the machine record governs. No
message has been sent and no budget, price, schedule, purchase, or capacity has
been committed.

## Purpose and claim ceiling

We are screening laboratories and independent data custodians for two new,
write-new K562 CRISPRa single-cell whole-transcriptome bundles. This inquiry is
about technical feasibility and blinded custody only. Do not send expression
matrices, outcome deltas, differential-expression results, plots, prediction
scores, or prior Golden-test results in response.

Even a conforming delivery is not scientific evidence. Value-free intake can
reach at most `READY_FOR_ESCROW`; it does not authorize evaluation. Until the
separate pair closure, trusted pins, evaluation lock, and formal gates pass,
`benchmark_status` remains `NOT_RUN`, `scientifically_validated` remains false,
and promotion, production, and default-route changes remain prohibited.

## Two required, mutually independent roles

| Role | Frozen condition scope | Frozen readout |
|---|---|---|
| `replacement_primary_holdout` | 68 single-gene conditions plus 36 frozen former-training gene pairs, with matched non-targeting controls | 10x Genomics 3′ whole-transcriptome Gene Expression plus CRISPR Guide Capture |
| `independent_external_dataset_and_platform` | The same 68 single-gene conditions plus 36 separately frozen, value-free unseen gene pairs, with matched non-targeting controls | Parse Biosciences Evercode Whole Transcriptome plus CRISPR Detect |

The two roles must have different `custodian_id`, `dataset_fingerprint`,
`laboratory_id`, and `platform_fingerprint`. They must use independent cultures,
transductions, libraries, datasets, custodians, and outcome access. One provider
may not fill both roles. A proposed non-10x substitute for Parse is not an
on-the-day equivalent: it requires a versioned acquisition-plan refreeze before
any data are generated.

## Non-negotiable experiment and acceptance floor

- Human K562, Cellosaurus `CVCL_0004`, authenticated by STR and negative for
  mycoplasma both before transduction and at harvest.
- Gene-targeted dCas9-SunTag CRISPR activation using the specified cassette
  architecture and the machine-frozen target and condition definitions. Exact
  guide sequences and construct bytes are not frozen at the quote stage; they
  must be frozen write-new after feasibility review and before data generation.
  The target axis is 68 Ensembl 84 genes; its ordered identity is governed by
  the machine plan.
- `t0` is the documented completion of transduction washout. Sorting occurs at
  `t0 + 72 h`; harvest occurs at `t0 + 120 h`, with a maximum deviation of
  ±15 minutes. Timestamps and deviations must be retained per replicate.
- Single-gene, gene-pair, and matched non-targeting-control conditions are all
  required. No condition may be silently dropped, substituted, relabelled, or
  pooled across roles.
- Three biological replicates per role. Each replicate is an independent
  transduction, culture, and library—not a technical split.
- Acceptance requires at least 100 post-QC singlets for every
  condition × replicate and at least 1,000 post-QC matched non-targeting-control
  singlets per replicate. Capacity planning must target at least 2× those
  accepted-singlet floors; the provider must translate that target into its own
  justified loading and capture plan.
- The formal paired unit is the biological condition, not the cell. Extra cells
  do not replace missing biological replicates.
- Whole-transcriptome scRNA counts and single-cell perturbation assignments are
  required. The sealed preprocessing output must expose the exact ordered 5,045
  Ensembl 84 feature axis required by the machine contract; the evaluation
  client may perform no projection, reorder, fill, or imputation.
- Chemistry, capture sequence, reagent versions, reference, preprocessing code,
  environment, guide-calling method, QC rules, and all thresholds must be frozen
  before data generation.

Any applicable `NO`, blank answer, or qualified substitute below is a rejection.
Any later design change requires a version bump and refreeze before data
generation; retrospective waivers are not accepted.

The current package is quote-only. Before wet-lab authorization, each role must
add a versioned, outcome-blind execution policy that freezes the exact guide and
construct bytes; MOI; transduction exposure and washout; selection and sorting
gates; guide-assignment and multiplet rules; viability, singlet, UMI, feature,
mapping, depth, saturation, and CRISPRa-activity thresholds; reference and
software identities; and the failed-condition/write-new-rerun rule. A
provider may use a technical compatibility pilot to propose these values, but
the pilot cannot inspect candidate performance or condition-level expression
outcomes, and its choices must be frozen before the formal data are generated.

## Yes/no capability questionnaire

Please identify exactly one proposed role, then answer every applicable item
`YES` or `NO` and attach only value-free documentary evidence.

| # | Required `YES` confirmation |
|---|---|
| 1 | We can execute exactly one named role and will not execute or hold custody for the other role. |
| 2 | The experiment and all outcomes will be newly generated and have not been used for candidate training, tuning, selection, calibration, or prior evaluation. |
| 3 | We will disclose the executing laboratory, custodian, platform, dataset, subcontractors, and conflicts so all four cross-role independence fields can be verified as different. |
| 4 | We can keep outcome-bearing assets inaccessible to the PRAXIS candidate/evaluation team until the frozen evaluation lock authorizes access, while maintaining a complete access log and chain of custody. |
| 5 | We can use authenticated K562 `CVCL_0004` and provide STR and negative-mycoplasma records both before transduction and at harvest. |
| 6 | We can reproduce the specified dCas9-SunTag CRISPRa architecture, document vector/capture compatibility, and freeze exact guide and construct bytes before data generation. |
| 7 | We can run all 68 frozen single-gene conditions, the role-specific 36 frozen gene-pair conditions, and matched non-targeting controls without outcome-informed selection. |
| 8 | We can run three independent transduction/culture/library biological replicates for every condition. |
| 9 | We can define `t0` as completion of transduction washout, sort at 72 h, and harvest at exactly 120 h ±15 min, with auditable timestamps. |
| 10 | We can meet the post-QC floor of 100 singlets per condition × replicate and 1,000 matched-control singlets per replicate, planning capture at approximately 2× those counts. |
| 11 | For `replacement_primary_holdout`, we will use 10x Genomics 3′ whole-transcriptome Gene Expression plus CRISPR Guide Capture and will name the exact chemistry, capture sequence, reagent, and Cell Ranger versions in writing. |
| 12 | For `independent_external_dataset_and_platform`, we will use Parse Evercode Whole Transcriptome plus CRISPR Detect and will name the exact kit, vector compatibility, reagent, and pipeline versions in writing. |
| 13 | We can deliver genome-wide raw counts, cell-level perturbation assignments, replicate/condition metadata, and a sealed exact 5,045-feature Ensembl 84 outcome representation with zero evaluation-client adaptation. |
| 14 | We can lawfully transfer or escrow the required artifacts and provide a source locator, media type, license statement, byte size, and SHA-256 for each declared asset. |
| 15 | We accept that failed QC cannot be repaired by dropping a condition, pooling biological replicates, changing the endpoint, switching platforms, imputing features, or opening outcomes. |
| 16 | We will not send outcome-bearing data or summaries during capability screening and will follow the custodian handoff below if selected. |

Reply fields:

- Proposed role:
- Executing laboratory legal name:
- Independent custodian legal name:
- Exact assay platform and chemistry:
- Answers 1–16 (`YES`/`NO`) with value-free evidence links:
- Conflicts, subcontractors, or exceptions (`none` if none):

## Blinded custodian delivery

A blinded provider-side processing operator must first run the pre-frozen
machine pipeline to materialize the exact-axis assets and `outcome_delta`;
machine processing is allowed, but human outcome review, summarization, and
disclosure are not. The selected custodian then receives that already
materialized outcome-bearing bundle privately and runs the repository's
value-free verifier without semantically decoding it. The private root contains
the required scope and custody records plus exactly ten declared opaque assets:
the seven scientific payload roles in the acquisition plan and the three
byte-bound identity/receipt roles required by the intake v2 contract:

1. `raw_counts`
2. `cell_metadata`
3. `feature_metadata`
4. `condition_metadata`
5. `preprocessing_code`
6. `preprocessing_environment`
7. `outcome_delta`
8. `guide_map`
9. `construct_identity`
10. `wet_lab_execution_record`

The custodian hashes and seals bytes without decoding or reporting the outcome.
The first public handoff is only the value-free consumer manifest. Outcome bytes,
derived values, plots, descriptive statistics, and pass/fail hints remain private
until the pair is closed, exact identities are trusted-pinned, and the evaluation
lock is frozen.

## First-contact template—no outcomes

**Subject:** Capability screen: blinded K562 SunTag CRISPRa single-cell study

> We are assessing capability for one of two independent, write-new K562
> dCas9-SunTag CRISPRa studies. This first contact is a technical and custody
> screen only; pricing and scheduling are intentionally deferred.
>
> The proposed role is `[replacement_primary_holdout / independent_external_dataset_and_platform]`.
> Hard requirements include 68 frozen singles, 36 role-specific frozen pairs,
> matched non-targeting controls, three independent biological replicates,
> t0 at transduction washout, sorting at 72 h, harvest at 120 h ±15 min, the
> stated post-QC cell floors, and the role-specific 10x or Parse readout.
>
> Please reply only with the completed YES/NO capability questionnaire and
> value-free evidence of platform, CRISPRa, timing, QC, and blinded-custody
> capability. Do not send expression matrices, outcome deltas, differential
> expression, plots, prior study results, or other outcome-bearing material.

## Official inquiry routes

These are capability candidates, not prequalified vendors.

### Priority pair

- **Cellecta — primary 10x candidate.** Its official
  [single-cell CRISPR screening service](https://cellecta.com/products/single-cell-crispr-screening-service)
  describes an in-house 10x Chromium workflow, and its
  [contact page](https://cellecta.com/pages/company-contact-us) is the inquiry
  route. Written confirmation of SunTag CRISPRa, paired guides, the exact timing,
  three replicates, and blinded custody is still required.
- **Karolinska Institutet CRISPR Functional Genomics — external candidate.** KI's
  [pooled CRISPR screening service](https://ki.se/en/research/research-infrastructure-and-environments/core-facilities-for-research/crispr-functional-genomics/pooled-crispr-screening)
  explicitly covers CRISPRa and single-cell transcriptomic readouts; use its
  [facility information and contact route](https://ki.se/en/research/research-infrastructure-and-environments/core-facilities-for-research/crispr-functional-genomics/cfg-about-us).
  This role qualifies only if KI or its named subcontractor confirms Parse
  Evercode Whole Transcriptome plus CRISPR Detect in writing. A 10x readout does
  not satisfy the external-platform role. Parse lists current
  [certified service providers](https://www.parsebiosciences.com/service-providers/).

### Backups

- **Columbia Genome Engineering Core plus Single Cell Analysis Core.** The
  [Genome Engineering Core](https://systemsbiology.columbia.edu/genome-center/genome-engineering-core)
  covers CRISPRa and scRNA-seq; the
  [Single Cell Analysis Core](https://systemsbiology.columbia.edu/genome-center/single-cell-analysis-core)
  documents 10x Gene Expression and CRISPR barcoding. This is a primary-role
  backup, not a Parse external-role substitute.
- **Broad Genetic Perturbation Platform.** The official
  [GPP page](https://www.broadinstitute.org/genetic-perturbation-platform)
  covers CRISPRa and links its contact route; the
  [platform inquiry page](https://www.broadinstitute.org/platform-faqs-contact)
  explains external collaboration. Eligibility depends on written confirmation
  of the complete role-specific platform and custody scope.

Platform compatibility must be checked against the official
[10x CRISPR experimental-planning guide](https://www.10xgenomics.com/support/universal-three-prime-gene-expression/documentation/steps/sample-prep/chromium-single-cell-gene-expression-crispr-screening-experimental-planning-guide),
[10x guide-RNA compatibility note](https://www.10xgenomics.com/support/universal-three-prime-gene-expression/documentation/steps/sample-prep/guide-rna-specifications-compatible-with-feature-barcoding-technology-for-crispr-screening),
and [Parse CRISPR Detect documentation](https://www.parsebiosciences.com/products/crispr-detect/).

### Original-team protocol and material contacts

The following routes may be used only to ask for protocol, construct, guide,
material, or independent-laboratory referrals:

- [Thomas Norman Lab, MSK](https://www.mskcc.org/research/ski/labs/thomas-norman)
- [Maximilian Horlbeck, Harvard Medical School](https://genetics.hms.harvard.edu/faculty-staff/maximilian-horlbeck)
  and the [Horlbeck Lab contact page](https://horlbecklab.org/contact/)
- [Jonathan Weissman, Whitehead Institute](https://wi.mit.edu/people/member/weissman)
  and the [Whitehead Functional Genomics Platform](https://wi.mit.edu/core-facilities/fgp)
- [UCSF CRISPR Bridge](https://cancer.ucsf.edu/research/cores/crispr-bridge)
  and its [services request page](https://cancer.ucsf.edu/research/cores/crispr-bridge/services)

Their involvement does not automatically qualify as independent external
validation. Any participation in the original Norman/Golden source, candidate
development, condition selection, outcome access, or custody must be disclosed.
Original or outcome-exposed teams cannot serve as the independent-external lab
or blinded custodian under this inquiry. Do not request or accept their prior
expression or outcome data.
