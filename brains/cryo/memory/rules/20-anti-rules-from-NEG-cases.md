---
rule_id: 20-anti-rules-from-NEG-cases
schema_version: 1
rule_type: anti_rule_systematized
applies_to:
  sample_types: [any]
evidence_neg_cases: [
  NEG-PREF-ORIENT-IGNORED, NEG-NO-SYM-IMPOSED, NEG-SINGLE-PICKER, NEG-MEMBRANE-NO-STABILIZER,
  NEG-AF-RIGID-FINAL, NEG-CRYOET-CONTINUOUS-TILT, NEG-PER-MIC-CTF-CRYOET, NEG-FOCUSED-HARD-MASK,
  NEG-MODELANGELO-NO-FASTA, NEG-K1-ON-HETEROGENEOUS, NEG-NO-CTF-REFINE-SUB3A, NEG-MAP-CHERRY-PICK-FSC
]
confidence: domain_knowledge
last_updated: 2026-04-29
---

# Anti-rules systematized from 12 NEG- cases

These 12 anti-rules turn each NEG- case into a machine-checkable veto. Any candidate
pipeline / report / mutation-of-design plan that triggers ANY of them is
**automatically rejected by the Reviewer gate** (no override without explicit user flag).
The mapping is bijective: 1 NEG- case ⇔ 1 anti-rule ⇔ 1 reviewer block code.

| # | Anti-rule (forbidden pattern) | NEG- case anchor | Reviewer block code | Skill-level fail (if any) |
|---|---|---|---|---|
| 1 | Ship final FSC claim without cryoEF + 3DFSC + angular distribution | NEG-PREF-ORIENT-IGNORED | `CRYO_REVIEW_NO_PREF_ORIENT_CHECK` | `PREF_ORIENT_BAD` (warn at < 0.7) / `PREF_ORIENT_SEVERE` (fail at < 0.5) |
| 2 | High-symmetry sample (Cn≥3 / Dn / T / O / I) refined in C1 | NEG-NO-SYM-IMPOSED | `CRYO_REVIEW_NO_SYM_IMPOSED` | — |
| 3 | Single picker, no IoU consensus, no 2D class junk audit | NEG-SINGLE-PICKER | `CRYO_REVIEW_SINGLE_PICKER` | `PICKER_CONSENSUS_LOW_IOU` (warn) |
| 4 | Membrane protein < 200 kDa without stabilizer | NEG-MEMBRANE-NO-STABILIZER | `CRYO_REVIEW_MEMBRANE_NO_STABILIZER` | — |
| 5 | AF model rigid-fit as final cryoEM model (no flexfit, no per-residue source label) | NEG-AF-RIGID-FINAL | `CRYO_REVIEW_AF_NO_FLEXFIT` | `AF_HYBRID_UNLABELED_RESIDUES` |
| 6 | cryoET tilt scheme ≠ dose-symmetric | NEG-CRYOET-CONTINUOUS-TILT | `CRYO_REVIEW_TILT_NOT_DOSE_SYM` | `STA_TILT_SCHEME_NOT_DOSE_SYM` |
| 7 | cryoET CTF estimated per-micrograph (single defocus) instead of per-tilt | NEG-PER-MIC-CTF-CRYOET | `CRYO_REVIEW_PER_TILT_CTF_MISSING` | `STA_PER_TILT_CTF_DISABLED` |
| 8 | Focused refine with sharp-edge mask (soft edge < 6 voxels) | NEG-FOCUSED-HARD-MASK | `CRYO_REVIEW_FOCUSED_HARD_MASK` | `FOCUSED_MASK_HARD_EDGE` |
| 9 | ModelAngelo without sequence FASTA | NEG-MODELANGELO-NO-FASTA | `CRYO_REVIEW_NO_MOLPROBITY` (chained: validation cannot proceed) | `MODELANGELO_NO_SEQUENCE` |
| 10 | K=1 single-class refinement on a heterogeneous sample | NEG-K1-ON-HETEROGENEOUS | `CRYO_REVIEW_HETEROGENEITY_IGNORED` | — |
| 11 | Sub-3 Å target without per-particle CTF refinement AND Bayesian polishing | NEG-NO-CTF-REFINE-SUB3A | `CRYO_REVIEW_NO_POLISHING_AT_HIGH_RES` (soft) | — |
| 12 | Resolution claim at non-gold-standard threshold OR mismatching measured FSC | NEG-MAP-CHERRY-PICK-FSC | `CRYO_REVIEW_FSC_NOT_GOLD_STANDARD` | — (caught at the QA `resolution_method` layer instead) |

## Vetoed-versus-warned distinction

- **Veto** (`pass=false` in Reviewer): the candidate cannot proceed without explicit user override + a written justification.
- **Warn**: the candidate proceeds but the report carries the warning + a confidence label downgrade (`high` → `medium` or `low`).

Anti-rules 1, 5, 6, 7, 8, 9, 10 are veto-level (each maps to a hard-block reviewer code or a skill-level FAIL).
Anti-rules 2, 3, 4 are veto-level when the precondition is met (high symmetry / multi-picker missing / membrane < 200 kDa).
Anti-rule 11 is warn-level for sub-3 Å targets without polishing/CTF-refine; promoted to veto only when claim ≤ 2.0 Å.
Anti-rule 12 is veto-level (resolution overstated → trust collapse).

## Override protocol

If a user MUST proceed with an anti-rule-violating plan:
1. The Reviewer gate emits `passed=false` with the relevant `error_code`.
2. The user passes `--override-anti-rule <code>` to `scripts/design_cryo.py`.
3. The orchestrator records the override in `runs/<task>/audit/overrides.jsonl` (append-only).
4. The downstream report is automatically tagged `confidence_label: low` regardless of other evidence.
5. The override is surfaced at the top of `validation_report.md`.

## How this rule is generated

This file is the systematized form of the 12 NEG- case files in `memory/cases/NEG-*.md`. Each NEG- case carries:
- `case_polarity: negative`
- `anti_rule_triggered: <1..12>`
- `veto_reason: <one-line>`
- `related_positive_cases: [cryo-NNN]`

Anti-retrieval (`scripts/retrieval/anti.py`) uses `anti_rule_triggered` + `veto_reason` to reverse-filter candidate plans: any candidate whose features match the veto pattern is automatically downgraded.

## Verification

`scripts/retrieval/test_anti_retrieval.py` builds a synthetic candidate plan for each NEG- case and asserts the anti-retrieval channel correctly fires the corresponding anti-rule. Current state: **12/12 anti-rules fire as expected**.

```bash
cd /Volumes/T7/newagent/PRAXIS-Cryo
python scripts/retrieval/test_anti_retrieval.py
# Expected: 12/12 PASS
```
