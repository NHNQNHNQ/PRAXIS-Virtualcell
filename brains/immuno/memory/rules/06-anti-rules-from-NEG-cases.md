---
rule_id: 06-anti-rules-from-NEG-cases
schema_version: 1
applies_to:
  immuno_tasks: ["ALL"]
  hla_classes: ["ALL"]
  antigen_classes: ["ALL"]
evidence_cases:
  - NEG-AURORA-MAGE-A3-affinity-enhanced-tcr-titin
  - NEG-HER2-CART-FIRST-PATIENT-DEATH-MORGAN-2010
  - NEG-UNMODIFIED-mRNA-INNATE-IMMUNITY-PRE2005
  - NEG-HLA-LOH-anti-PD1-resistance-Anagnostou-2020
  - NEG-SINGLE-MHC-PREDICTOR-FDR
  - NEG-HLA-2DIGIT-NEOANTIGEN
  - NEG-SELF-CROSS-REACTIVE-VACCINE-AUTOIMMUNE
  - NEG-CLASS-I-MODEL-ON-CLASS-II
  - NEG-GENERIC-PPDOCK-FOR-TCR
  - NEG-SINGLE-CALLER-HLA-TYPING
  - NEG-WHO-ALLERGEN-CRITERIA-ALONE
  - NEG-MIXCR-OOF-NOT-REPORTED
  - NEG-AFFINITY-MATURED-ANTIBODY-NO-IMMUNOGENICITY-CHECK
  - NEG-CLASS-I-ONLY-FOR-CD4-VACCINE
confidence: high
last_updated: 2026-05-02
---

## 规则 (anti-rule 系统化)

22 显式 anti-rule，来自 12 NEG- 反例案例。任何 candidate 触发以下任一条 → Reviewer veto，**不允许作为默认路线、推荐方案、长期经验或 skill** 升级。可由 `scripts/retrieval/test_anti_retrieval.py` 复现验证（22/22 通过）。

### TCR / 抗体免疫原性 anti-rules (1-3, 16, 21)
- **anti-rule 1**: Engineered TCR (esp. affinity-enhanced) shipping without proteome-wide cross-reactivity panel + iPSC vital-tissue cytotoxicity → block. *Source: Aurora MAGE-A3 trial, 2 patient deaths*
- **anti-rule 2**: Affinity-enhanced TCR with Kd < 1 µM without "specificity window" measurement → block
- **anti-rule 3**: Single-cell-line panel as sole specificity evidence for clinical TCR-T → block
- **anti-rule 16**: Generic PP-docker (HADDOCK/ClusPro/PatchDock/ZDOCK) for TCR-pMHC modeling → block. *Source: TCRdock paper Bradley 2024*
- **anti-rule 21**: Therapeutic antibody candidate without HLA-II T-cell epitope screen → block (ADA risk). *Source: Jawa 2017 mAbs*

### CAR-T target safety anti-rules (4-6)
- **anti-rule 4**: CAR target with tumor-IHC-only validation (no multi-source normal expression) → block. *Source: HER2 CAR-T 2010 patient death*
- **anti-rule 5**: High-affinity scFv (Kd < 10 nM) for target with documented low normal expression in essential tissue → block; require affinity de-tuning
- **anti-rule 6**: First-in-human CAR-T at >10^8 cells without dose escalation → block

### mRNA vaccine anti-rules (7-9, 22)
- **anti-rule 7**: mRNA vaccine/therapeutic design without explicit nucleoside modification flag (m1Ψ default) → block. *Source: Karikó-Weissman pre-2005 failures*
- **anti-rule 8**: mRNA design without Cap1 (or equivalent) → warn (block when used in vaccine context)
- **anti-rule 9**: mRNA design with elevated CpG content (> baseline) without justification → warn
- **anti-rule 22**: Vaccine candidate without Class II (CD4 T-help) coverage → warn / block

### Tumor neoantigen anti-rules (10-11)
- **anti-rule 10**: Tumor neoantigen pipeline (esp. for vaccine design) without LOHHLA step → block (rule 02). *Source: Anagnostou 2020 anti-PD-1 resistance*
- **anti-rule 11**: Acquired-resistance setting using only germline HLA without re-typing tumor → block

### MHC prediction & class anti-rules (12-13, 15, 17)
- **anti-rule 12**: Single MHC predictor for clinical/vaccine candidate selection → block (rule 01). *Source: PRAXIS-Immuno 2026-04-30 finding — single-tool 69.2% recall*
- **anti-rule 13**: 2-digit HLA in MHC binding prediction → block (rule 02)
- **anti-rule 15**: Cross-class predictor application (Class I model on Class II input or vice versa) → block (rule 03)
- **anti-rule 17**: Single-caller HLA typing from RNA-seq into clinical-grade neoantigen pipeline → block (rule 02 / 05)

### Vaccine cross-reactivity & allergen anti-rules (14, 18)
- **anti-rule 14**: Vaccine epitope without proteome-wide BLAST → block (rule 04). *Source: Pandemrix narcolepsy, molecular mimicry*
- **anti-rule 18**: WHO allergen criteria alone (no DL classifier consensus) → block (rule 01)

### Repertoire QC anti-rules (19-20)
- **anti-rule 19**: TCR/BCR-seq pipeline without OOF rate reporting → block (rule 05)
- **anti-rule 20**: Cross-sample TCR diversity comparison without rarefaction → block

## 依据 (NEG case → anti-rule mapping)

| NEG case | anti-rule(s) triggered |
|---|---|
| NEG-AURORA-MAGE-A3-... | 1, 2, 3 |
| NEG-HER2-CART-FIRST-... | 4, 5, 6 |
| NEG-UNMODIFIED-mRNA-... | 7, 8, 9 |
| NEG-HLA-LOH-anti-PD1-... | 10, 11 |
| NEG-SINGLE-MHC-PREDICTOR-FDR | 12 |
| NEG-HLA-2DIGIT-NEOANTIGEN | 13 |
| NEG-SELF-CROSS-REACTIVE-VACCINE-... | 14 |
| NEG-CLASS-I-MODEL-ON-CLASS-II | 15 |
| NEG-GENERIC-PPDOCK-FOR-TCR | 16 |
| NEG-SINGLE-CALLER-HLA-TYPING | 17 |
| NEG-WHO-ALLERGEN-CRITERIA-ALONE | 18 |
| NEG-MIXCR-OOF-NOT-REPORTED | 19, 20 |
| NEG-AFFINITY-MATURED-ANTIBODY-... | 21 |
| NEG-CLASS-I-ONLY-FOR-CD4-VACCINE | 22 |

## 边界 (★ 必填)

- **Anti-rules apply unconditionally** unless a `causal_tag = causal` rule explicitly overrides for a specific (immuno_task, hla_class) tuple
- **Override allowed** with explicit `--override-anti-rule <N>` flag + user-supplied justification (logged to memory/_audit/)
- **Pre-clinical / educational simulation** can run with anti-rule violations BUT result must be tagged `simulated: true` + `provenance.anti_rule_violations: [N, M, ...]`

## How to apply

- **Scoping**: candidate_strategies that trigger any anti-rule are filtered out before being presented to user
- **Design**: design_pipeline steps must be cross-checked against anti-rules; violations populate `excluded_strategies[]` field
- **Execution**: real_run skips anti-rule-violating inputs (returns `qc_failure` with anti-rule citation)
- **Reporting**: `clinical_translation_guidance.escape_risk_factors[]` must reference relevant NEG cases for any clinical recommendation
- **Reviewer**: `agents/reviewer.py:validate_*` checks consult anti-rule list before pass/fail
