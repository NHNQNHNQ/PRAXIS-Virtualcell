---
rule_id: 03-active-site-freeze
schema_version: 1
applies_to:
  design_tasks: ["stabilization", "redesign", "antibody_cdr_modeling", "antibody_design"]
  fold_classes: ["ALL"]
evidence_cases: ["protein-003-proteinmpnn-thermostab", "protein-005-igfold-antibody-cdr", "protein-008-esmfold-throughput"]
confidence: high
last_updated: 2026-04-29
---

## 规则
Redesign / 稳定化 / 抗体建模任务中，下列残基**默认 freeze**（写入 `excluded_positions[]`）：
1. **Active site 5–6 Å radius**（催化残基本体 + 第一壳层）
2. **二硫键 Cys 对**
3. **跨膜段**（TMHMM / DeepTMHMM 注释为 TM）
4. **N-/O-glycosylation 位点**（NXS/T motif + 邻近 Ser/Thr）
5. **Antibody CDR loops**（H1/H2/H3/L1/L2/L3）—— 抗体 framework redesign 不动 CDR；CDR design 不动 framework
6. **Cofactor 第一壳层**（NADH/FAD/heme 接触残基）

## 依据
- **protein-003 (DHFR ProteinMPNN)**：明文 "freeze active site (6 Å radius rule)"——不 freeze 失活率 50%+；MPNN temperature 0.1 baseline
- **protein-005 (IgFold antibody)**：CDR/framework 必须分开处理；framework 残基号统一用 ANARCI Chothia/Kabat
- **protein-008 (ESMFold cofactor)**：cofactor-dependent 蛋白 apo 形态正确但 holo 状态不同；redesign 时 cofactor 接触面不能动

## 边界 (★ 必填)
- 不适用于纯结构预测（**protein-001 / 008**）—— 没 redesign 没 freeze 概念
- 不适用于 binder de novo（**protein-002**）—— binder 是新 chain，target chain 才有 freeze
- 已知反例：用户显式声明 `redesign_active_site: true` 时绕过（罕见，主要是酶活性扩展场景）

## How to apply
- **Scoping**：identify active_site / disulfide / TM / glycosylation positions（调用 catalytic-site-annotator skill 或 UniProt features）
- **Design**：`design_plan.excluded_positions[]` ★ MANDATORY 字段必填；每条 entry 给 `category` ∈ {active_site, disulfide, transmembrane, glycosylation, epitope_key, ...}
- **Execution**：proteinmpnn_redesign skill input 必含 `freeze_residues: [...]` 非空（runner.py 会校验）
- **Reviewer**：
  - design_task ∈ {stabilization, redesign} 但 design_plan.excluded_positions 为空 → block
  - design_pipeline 含 proteinmpnn_redesign 但 inputs.freeze_residues 为空 → block
