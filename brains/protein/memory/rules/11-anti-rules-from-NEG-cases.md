---
rule_id: 11-anti-rules-from-NEG-cases
schema_version: 1
applies_to:
  design_tasks: ["ALL"]
  fold_classes: ["ALL"]
evidence_cases:
  - "NEG-ESMFOLD-MONOMER-FALSE-POSITIVE"
  - "NEG-NO-HOTSPOT-BINDER"
  - "NEG-NO-PAIRED-MSA-MULTIMER"
  - "NEG-NO-SPECIFICITY-PANEL"
  - "NEG-ANTIBODY-VIA-GENERIC-AF"
  - "NEG-ESMFOLD-MULTIMER"
  - "NEG-SINGLE-DDG-PREDICTOR"
  - "NEG-NO-ACTIVE-SITE-FREEZE"
  - "NEG-RAW-COMPUTE-NO-DE"
  - "NEG-SINGLE-MODALITY-VALIDATION"
  - "NEG-CDR-H3-LONG-TRUST"
  - "NEG-SYMMETRY-NO-TIED-MPNN"
  - "NEG-AF-MODEL-DDG-SOLO"
  - "NEG-IPTM-AS-AFFINITY"
confidence: high
causal_tag: causal
last_updated: 2026-05-04
---

## 规则
**12 条 anti-rule** — 任何候选触发以下任一条即被 Reviewer gate **vetoed (hard-stop, no override)**。这些 anti-rule 来源于 14 份 NEG- 反例案例 + 跨 33 个正例案例的失败模式 meta-analysis。

可由 `scripts/retrieval/test_anti_retrieval.py` 复现验证（每条 anti-rule 必须能从 NEG cases 反向召回）。

## 12 anti-rule 清单

| # | Anti-rule | NEG anchor | Veto trigger |
|---|---|---|---|
| **1** | ESMFold pLDDT-only as binder quality bar | NEG-ESMFOLD-MONOMER-FALSE-POSITIVE, protein-034 | Pipeline outputs binder ranked by ESMFold pLDDT without AF2-Multimer 5-metric verify |
| **2** | RFdiffusion binder without explicit hotspot | NEG-NO-HOTSPOT-BINDER, protein-002, 010 | `ppi.hotspot_res=[]` or empty in scoping |
| **3** | AF-Multimer / AF3 without paired MSA | NEG-NO-PAIRED-MSA-MULTIMER, protein-001, 007 | multimer prediction with `--use_paired_msa=false` |
| **4** | Binder design without paralog negative panel | NEG-NO-SPECIFICITY-PANEL, protein-002, 010, 034 | binder report missing PD-L2 / family negative target iPTM |
| **5** | Antibody modeled with generic AF/ESMFold | NEG-ANTIBODY-VIA-GENERIC-AF, protein-005, 025, 026 | `design_task=antibody_*` + tool=AF/ESMFold (not IgFold/ImmuneBuilder/AbLang2) |
| **6** | ESMFold for multimer / complex prediction | NEG-ESMFOLD-MULTIMER, protein-008 | ESMFold + multi-chain input |
| **7** | Single ΔΔG / fitness predictor for stability/mutation | NEG-SINGLE-DDG-PREDICTOR, protein-003, 004, 023, 024, 027, 028 | mutation_effect_scan with single predictor + lab recommendation |
| **8** | ProteinMPNN redesign without active-site freeze | NEG-NO-ACTIVE-SITE-FREEZE, protein-003, 020, 023, 029, 030 | empty `--fixed_positions_jsonl` for catalytic / functional redesign |
| **9** | Pure de novo design shipped without directed evolution | NEG-RAW-COMPUTE-NO-DE, protein-011, 012, 020, 029, 030 | enzyme/binder report missing `directed_evolution_plan` for industrial-grade claim |
| **10** | Single-modality validation for fold-only design | NEG-SINGLE-MODALITY-VALIDATION, protein-013, 014, 015, 022, 029, 031, 033 | hallucination/cyclic/symmetric/enzyme report < 3 modality, "fold confirmed" claim |
| **11** | Trust IgFold/ImmuneBuilder on long CDR-H3 (> 15 aa) | NEG-CDR-H3-LONG-TRUST, protein-005 | antibody design with H3 > 15 aa + missing low_confidence flag |
| **12** | Symmetric design without tied-position MPNN | NEG-SYMMETRY-NO-TIED-MPNN, protein-009, 019, 031, 033 | symmetric_design_pipeline with empty `--tied_positions_jsonl` |
| **(bonus)** | AF model + 单一方法 ddG (例如 PyRosetta cartesian_ddg) single-channel mutation rank | NEG-AF-MODEL-DDG-SOLO, protein-023, 024 | maps to anti-rule 7 (single ΔΔG) on AF-predicted models |
| **(bonus)** | iPTM treated as quantitative binding affinity | NEG-IPTM-AS-AFFINITY, protein-001, 002, 010, 034 | maps to anti-rule 1 (single-channel signal misuse for ranking) |

## 依据
- 14 份 NEG cases 是 anchor evidence
- 33 份 positive cases 提供 cross-validation
- protein-034 (PRAXIS self-generated) 直接量化 ESMFold-vs-AF2-Multimer gap (91.5% pre-filter → 32% real PASS)
- 5 distilled positive rules (rule 01-05) + 5 newer (rule 06-10) 是 positive 镜像; 本条 rule 11 是 negative consolidation

## 边界 (★ 必填)
- **explicit override**：用户可显式 `--explore-anti-rule N` flag (only in research mode, never default); 触发时 confidence label 强制降到 `low`
- **research / sanity-test mode**：跑测试时可允许触发，但必须在 reporting 中显式写明 "anti-rule N triggered for test purposes"
- **NEG cases 不参与 evidence_cases counting for positive rule promotion** — 只参与 anti-retrieval index

## How to apply

### Scoping
- Reviewer gate 在 `scoping_plan.candidate_strategies` 中扫描 anti-rule trigger
- 触发即返回 `{passed: false, required_repairs: [...], notes: "anti-rule N: ..."}`

### Design
- `design_plan.computational_pipeline` 必须不含 anti-rule trigger 的工具调用
- `excluded_positions` 必须含 catalytic/active site (anti-rule 8)
- `paired_msa: true` 强制 (anti-rule 3)
- `hotspot_res` 非空 (anti-rule 2)
- `tied_positions_jsonl` 强制 for symmetric (anti-rule 12)

### Execution
- skill runners 中 hard-enforce: empty critical inputs → ERROR
- multi-method consensus required: count of method = ≥ 2 (anti-rule 7)

### Reporting
- 报告必须显示 `anti_rule_check: passed` table
- 触发任一 anti-rule 但通过 (research mode) 必须显式 `anti_rules_overridden: [N, ...]` + reasoning

### Reviewer
- Schema check: 12 anti-rule each is a queryable predicate against the design_plan + execution_results
- Block any output where any anti-rule predicate evaluates True without explicit override

## RMCP integration
- 新 NEG cases 写到 `memory/cases/_proposed/NEG-*.md`
- QA 通过后进 `memory/cases/`，并自动重建 `indices/anti/`
- anti-rule 升级（添加 13/14/...）需要 ≥ 1 NEG case + ≥ 2 positive case evidence + 跨 ≥ 2 family
