---
rule_id: 00-default-bootstrap
schema_version: 1
applies_to:
  design_tasks: ["ALL"]
  fold_classes: ["ALL"]
evidence_cases: []
confidence: cold_start
last_updated: 2026-04-29
---

## 规则
Cold-start fallback rule for protein design tasks: when no case-distilled rule applies, follow the universal protein-engineering checklist before generating any recommendation.

## 依据
- 综合 protein-synthesis §七（统一原则）
- 这条规则在 case 库 < 5 时 always-applies；当 ≥5 cases 后由更具体的 rule 01-05 接管

## 边界 (★ 必填)
- 当具体 rule 触发时不适用：rule 01-05 比 bootstrap 优先
- Cold-start 标签必须保留在所有推荐的 confidence 字段

## How to apply
**所有 stage 都要遵循下面这张 checklist**：

1. **Task identification (Scoping)**：第一步识别 `design_task` ∈ {structure_prediction, complex_prediction, de_novo_binder, stabilization, mutation_effect_prediction, antibody_cdr_modeling, structure_search_homology, high_throughput_structure_prediction, symmetric_oligomer_de_novo, redesign}
2. **Tool routing**：tool 选择必须 task-aware（ESMFold 不跑 multimer；抗体走 IgFold 而非 AF-Multimer；binder 走 RFdiff+MPNN+AF2）
3. **Multi-model consensus (Design + Execution)**：≥ 2 predictor，cross-model agreement 报告
4. **Composite metric (Design)**：≥ 5 metric 联合（pLDDT + pAE_int + iPTM + Rosetta_ddG + SAP），不单一打分
5. **Active site / functional residue freeze**：default 行为；redesign 不允许动
6. **Hotspot mandatory (binder/symmetric)**：design_task ∈ {de_novo_binder, symmetric_oligomer_de_novo} 必填 hotspot
7. **Paired MSA (multimer)**：AF-Multimer/AF3 复合物必须 paired MSA
8. **Specificity panel (binder)**：multi-homolog target 必跑 negative design panel
9. **In silico → in vitro gap (Reporting)**：所有 binder/design 输出**必须**含 5-15% conversion estimate
10. **Confidence label (Reporting)**：每条推荐 cold_start | low | medium | high | domain_knowledge
11. **Provenance (Execution)**：tool / version / seed / hyperparam / simulated 标志全记录
