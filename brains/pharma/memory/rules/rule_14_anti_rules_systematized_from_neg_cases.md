---
rule_id: rule_14_anti_rules_systematized_from_neg_cases
rule_type: meta_anti_rule
applies_to: [any]
evidence_cases: []
neg_evidence_cases:
  - NEG-01-tgn1412-noael-only-immune-modulator
  - NEG-02-vioxx-single-measure-faers-ignored
  - NEG-03-codeine-pediatric-um-fatal
  - NEG-04-vanco-trough-only-aki
  - NEG-05-clopidogrel-omeprazole-phenoconversion
  - NEG-06-warfarin-no-pgx-bleeding
  - NEG-07-dpyd-no-screen-fatal
  - NEG-08-fih-parallel-cohort-dosing
  - NEG-09-pbpk-no-clinical-validation
  - NEG-10-ddi-single-cyp-statin-rhabdo
  - NEG-11-single-species-allometric-warfarin
  - NEG-12-pediatric-popPK-no-maturation
confidence: high
authoring_date: 2026-05-02
source_synthesis_section: anti-pattern systematization (12 NEG cases → 12 anti-rules)
---

# Anti-rules systematized from 12 NEG- cases

This is a META-rule: it documents the 12 anti-pattern motifs discovered from
real published failures, mapped to Reviewer hard-reject codes (HR-01..HR-13).
Every entry has at least one positive_anchor_case and one anti-pattern NEG case.

## The 12 anti-rules

| AR-ID | Anti-pattern motif | Mapped HR | NEG anchor | Positive anchor |
|-------|--------------------|-----------|------------|-----------------|
| **AR-01** | single-species allometric without ≥3 species + 95% CI | HR-01 | NEG-11 | pharma-001 |
| **AR-02** | PBPK without clinical PK comparison validation | HR-02 | NEG-09 | pharma-002 |
| **AR-03** | DDI prediction by single CYP only — misses transporter / multi-pathway | HR-03 | NEG-10 | pharma-003 |
| **AR-04** | NOAEL-only for immune modulator FIH (no MABEL co-method) | HR-04 | NEG-01 | pharma-017 |
| **AR-04b** | parallel cohort dosing in high-risk FIH (no sentinel-subject pause) | (sub-rule of HR-04) | NEG-08 | pharma-017 |
| **AR-05** | TDM trough-only proportional adjustment | HR-05 | NEG-04 | pharma-010 |
| **AR-06** | FAERS single-disproportionality-measure interpretation | HR-06 | NEG-02 | pharma-004 |
| **AR-07** | report without reproduce.sh emission | HR-07 | (any case missing) | (any positive) |
| **AR-08** | pediatric popPK without maturation function | HR-08 | NEG-12 | pharma-011 |
| **AR-09** | PG-actionable drug prescription without genotype panel | HR-09 | NEG-06 | pharma-018 |
| **AR-10** | codeine/tramadol in pediatric < 12 OR lactating mothers | HR-10 | NEG-03 | pharma-012 |
| **AR-11** | fluoropyrimidine prescription without DPYD pre-screen | HR-11 | NEG-07 | pharma-019 |
| **AR-12** | vancomycin trough-targeted (15-20 mg/L) for serious MRSA | HR-12 | NEG-04 | pharma-020 |
| **AR-13** | drug-gene-drug interaction (DGI) ignored — strong CYP inhibitor co-prescribed without phenoconversion check | (soft warning) | NEG-05 | pharma-013 |

## Use

1. **Anti-retrieval at scoping/design**: index `indices/anti/anti_index.json` is consulted to filter candidate plans matching anti-pattern motifs.
2. **Reviewer hard-rejects**: HR-01..HR-12 in `agents/reviewer_rules.yaml` enforce AR-01..AR-12 deterministically.
3. **NEG case veto contributions**: each NEG case contributes its motifs to keyword anti-pattern map; multiple motif hits trigger anti-rule consensus.

## Maintenance
- New anti-pattern documented in literature → add NEG-NN case + register AR-NN in this rule
- Rebuild `indices/anti/` via `python scripts/retrieval/build_anti_index.py`
- Verify integrity via `python scripts/retrieval/test_anti_retrieval.py` (target: 12/12 PASS)
