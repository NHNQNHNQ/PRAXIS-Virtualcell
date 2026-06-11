---
rule_id: 11-anti-rules-from-NEG-cases
schema_version: 1
rule_type: anti_pattern_systematization
applies_to:
  edit_type: ALL
  cell_context: ALL
  editing_system: ALL
confidence: high
causal_tag: causal
n_evidence_neg_cases: 13
created_at: 2026-05-02
last_updated: 2026-05-02
status: active
---

# Rule 11 — 13 anti-rules systematized from NEG- cases

This rule formalizes 13 forbidden patterns extracted from `memory/cases/_neg/NEG-*.md`. Each anti-rule is anchored to ONE NEG- case that documents the failure mode + a published paper. Reviewer hard-stops at design-plan time; anti-retrieval index (`indices/anti/`) vetoes candidate plans at retrieval time.

## The 13 anti-rules (confidence: high; causal_tag: causal)

| # | Anti-rule | NEG- anchor | Required correction |
|---|---|---|---|
| 1 | Single sgRNA on polyploid/aneuploid cell line (HeLa 3n / K562 / U2OS / HCT116 / Panc1 / MOLM13) | `NEG-SINGLE-GUIDE-POLYPLOID` | ≥ 2 sgRNAs (dual-guide exon-spanning) OR single-cell clone screen |
| 2 | In silico CFD/MIT alone for clinical / IND-grade off-target | `NEG-IN-SILICO-ONLY-CLINICAL` | GUIDE-seq + CHANGE-seq (orthogonal wet-lab) |
| 3 | Legacy base editors (ABE7.10 / CBE3 / BE3 / BE2 / BE1) as default | `NEG-LEGACY-BASE-EDITOR` | ABE8e / CBE4max / latest evolved variant |
| 4 | Prime editing PE2 alone (no nicking sgRNA) | `NEG-PE2-ONLY-NO-NICK` | PE3 / PE5 + paired nicking sgRNA + epegRNA optional |
| 5 | HDR donor without PAM destruction | `NEG-NO-PAM-DESTROY-HDR` | Silent codon swap / synonymous mutation breaking NGG |
| 6 | Single-junction PCR alone for KI validation | `NEG-SINGLE-JUNCTION-KI` | 5' AND 3' junction PCR + Southern blot or ddPCR copy-count |
| 7 | BE / PE design without per-window bystander A/C edit-rate prediction | `NEG-NO-BYSTANDER-PRED` | BE-Hive (or equivalent) per-window prediction |
| 8 | sgRNA with off-target in DepMap CKE essential gene (cum CFD > 0.5) | `NEG-OFF-TARGET-ESSENTIAL-GENE` | Filter against `tests/baselines/depmap_k562_essentials_subset.tsv` |
| 9 | Pooled CRISPR screen hit-calling without library QC | `NEG-NO-LIBRARY-QC-SCREEN` | Gini ≤ 0.3 + MOI 0.3 + ≥200x coverage + ≥2 replicates |
| 10 | Pooled screen with single time point | `NEG-SINGLE-TIMEPOINT-SCREEN` | ≥ 2 time points (day-0 reference + day-14+ endpoint) |
| 11 | AAV clinical / NHP in-vivo gene therapy without pre-existing NAb screen | `NEG-AAV-CLINICAL-NO-NAB` | Serum NAb assay protocol + enrollment cutoff |
| 12 | Cas13 (RNA-only) used for DNA editing tasks | `NEG-CAS13-AS-DNA-EDITOR` | Switch to SpCas9 / SaCas9 / Cas12a / ABE / CBE / PE |
| 13 | Lentivirus delivery for clinical multiplex KO (CAR-T / therapeutic) | `NEG-LENTI-CLINICAL-MULTIPLEX` | RNP or mRNA+LNP electroporation (transient) |

## How this rule is used

### Retrieval-time veto (anti-retrieval)
`scripts/retrieval/test_anti_retrieval.py` enumerates the 13 NEG- cases and verifies each blocks its target anti-pattern keyword query. **13/13 self-consistency must pass before any new design plan can use the retrieval pipeline.** The anti-index is rebuilt on every `python scripts/retrieval/build_indices.py` run.

### Reviewer-time hard-stop
Each of the 13 anti-rules maps to a Reviewer check in `agents/prompts/reviewer.md`. If a `design_plan` triggers any anti-rule pattern (e.g., `editing_system: ABE7.10` or `time_points: [single_value]`), Reviewer emits `passed: false` with `required_repairs` enumerating the violated anti-rule + pointing at the corresponding NEG- case for the user to read.

### RMCP write-back exclusion
Per Phase 2 (Triage) of the RMCP pipeline: any `candidate_rule` extracted via `scripts/distill/extract.py` that matches one of the 13 anti-rule patterns is automatically `discard`ed with bucket-tag `failure_mode`. NEVER promotes to `memory/rules/`. Cross-case meta-claims that reduce to "skip step X" where X is a known mitigation get cross-referenced to the corresponding NEG-case's `## Mechanism — why it fails` section.

## Provenance — every anti-rule is anchored to a real-paper-documented failure mode

| # | Anchor paper (DOI) | Year | Journal |
|---|---|---|---|
| 1 | 10.1038/nbt.3026 | 2014 | Nat Biotechnol |
| 2 | 10.1038/nbt.3117 | 2015 | Nat Biotechnol |
| 3 | 10.1038/s41587-020-0414-6 | 2020 | Nat Biotechnol |
| 4 | 10.1038/s41586-019-1711-4 | 2019 | Nature |
| 5 | 10.1038/nature17664 | 2016 | Nature |
| 6 | 10.1038/s41586-018-0326-5 | 2018 | Nature |
| 7 | 10.1016/j.cell.2020.05.037 | 2020 | Cell |
| 8 | 10.1016/j.cell.2017.05.061 | 2017 | G3 / Cell |
| 9 | 10.1038/nprot.2017.016 | 2017 | Nat Protoc |
| 10 | 10.1126/science.1246981 | 2014 | Science |
| 11 | 10.1089/hum.2009.182 | 2010 | Hum Gene Ther |
| 12 | 10.1038/nature24049 | 2017 | Nature |
| 13 | 10.1038/s41587-020-0741-7 | 2020 | Nat Biotechnol |

## Cross-reference to existing positive rules

The 13 anti-rules are the inverse / safety nets for the 10 case-distilled positive rules (`01-edit-type-pipeline-routing` … `10-aav-pre-existing-nab`):

- anti-rule 1 ← rule 05-multi-guide-polyploid (positive: prefer dual guide)
- anti-rule 2 ← rule 03-off-target-clinical-wetlab (positive: GUIDE-seq required)
- anti-rule 3 ← rule 04-latest-editor-version (positive: pick latest)
- anti-rule 5 ← rule 06-pam-destroy-hdr-donor (positive: silent PAM mutate)
- anti-rule 7 ← rule 08-bystander-prediction-be-pe (positive: BE-Hive predict)
- anti-rule 9 ← rule 07-screen-library-qc (positive: Gini + Lorenz)
- anti-rule 11 ← rule 10-aav-pre-existing-nab (positive: NAb pre-screen)
- anti-rules 4, 6, 8, 10, 12, 13 cover failure modes not previously formalized in positive rules — these are PROMPT § "不允许的捷径" + ★失败模式 entries that v0.6 promotes from "review-time hard-stop" to retrieval-time veto.

## Retrieval-time integration

Every retrieve() call now also runs anti-retrieval and emits `vetoed_candidates: [...]` listing any retrieved cases or design candidates that trigger an anti-rule. This is propagated through to the design agent's evidence block and the Reviewer's verdict.
