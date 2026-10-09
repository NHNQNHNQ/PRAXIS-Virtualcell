# Negative / fuzz 测试体系 — 设计文档

> 日期 2026-07-03 · 归属 v0.7 测试体系(计划 §4.4) · 状态:已 brainstorm(自主定,无重大 UX 决策),待写实现计划。

## 1. 背景与目标

计划 §4.4:重点测「不要乱答」——错输入/不适用场景下,系统应 **SchemaError / clarification / abstain / caution**,绝不静默 accept 或编造。把这类拒绝行为固化为声明式 negative fixtures + runner,与切片 1(golden 正向)互补。核心 KPI:**没有任何 negative case 得到静默 accept/成功**。

## 2. 现有拒绝路径(已实跑 grounding)

三层各司其职,均纯确定性、无重依赖、Mac/CI 必可跑:

1. **normalize 层** `species_schema.normalize_request(raw)` → 未知 species/perturbation_object/target_output、非 medium 的空 targets、非 dict 输入 **抛 `SchemaError`**(不静默补默认)。
2. **validate 层** `run_virtualcell_query.validate_candidate(cand)` → 返 `{schema_valid, missing_fields, errors, normalized}`;未知词汇进 `errors`(`unsupported_species:x` / `unsupported_perturbation_type:x` / `unsupported_task:x`),缺字段进 `missing_fields`(`species` / `perturbation_targets` 等),`schema_valid=False`。
3. **route 层** `route(normalize_request(req))` → 良构但不适用(错物种×任务、data-gated)返 `disposition ∈ {abstain, downgrade, caution}`,**绝不 accept**。

## 3. 边界(诚实,不测不存在的行为)

- **不存在的基因名**(如 FAKEGENE):normalize 接受任意基因符号(仅大写归一),**路由层不拒绝**——gene-existence 校验在下游机制模型(GEM:gene-not-in-model→downgrade/abstain,见 test_ecoli_gem_case,cobra-gated)。故本 negative 套件**不**为「路由层拒绝假基因」编造测试(该行为不存在)。改为固化路由层真实能捕获的**错物种基因**(如 bacteria + 人类基因 → abstain,治理经路由弃权而非编造)。
- **药物无法映射**:normalize 接受任意药名,route→embedding/**caution**(诚实:会试但签名噪声大,非 accept);真正的映射失败在下游 predictor。故断言 caution(非 accept),不断言 reject。
- **cell_type 不在白名单**:后端 cell_type 是自由字符串、**无白名单**(见 report.md 切片 `_CELL_TYPE_EXAMPLES` 仅示例)。cell_type 不支持的降级发生在全工作流 reliability 层(需 model_applicability,非声明式)。故本套件不含 cell_type 白名单测试。

## 4. Negative 数据格式

`praxis_virtualcell/tests/negative_cases/*.yaml`,每 case 声明 `layer` 决定断言机制:

```yaml
cases:
  - case_id: unknown_species_schema_error
    layer: normalize          # normalize | validate | route
    description: 未知物种 → SchemaError
    input: {species: martian, perturbation_object: gene, target_output: expression, perturbation_targets: [X]}
    expect: {schema_error: true}
  - case_id: validate_unknown_species
    layer: validate
    input: {species: martian, perturbation_type: gene, perturbation_targets: [X], task_type: predict_delta_expression}
    expect: {schema_valid: false, error_contains: "unsupported_species"}
  - case_id: wrong_species_gene_abstain
    layer: route
    input: {species: bacteria, perturbation_object: gene, target_output: expression, perturbation_targets: [TP53]}
    expect: {disposition: abstain}
```

`expect` 字段按 layer:
- normalize:`schema_error: true`(断言抛 SchemaError)。
- validate:`schema_valid: false`(必填);可选 `error_contains`(子串命中 errors 任一)、`missing_contains`(命中 missing_fields)。
- route:`disposition`(abstain/caution/downgrade;runner 额外硬断言 != accept)。

分文件:`schema_rejections.yaml`(normalize + validate 层)、`routing_rejections.yaml`(route 层)。

## 5. 14 个 negative case(期望值均已 grounding)

normalize 层(5,抛 SchemaError):unknown_species / unknown_object / unknown_output / empty_gene_targets / non_dict_input。
validate 层(5):unknown_species→`unsupported_species`;unknown_ptype→`unsupported_perturbation_type`;missing_species→missing `species`;empty_targets→missing `perturbation_targets`;bad_task→`unsupported_task`。
route 层(4,非 accept):wrong_species_gene(bacteria+TP53)→abstain;unmappable_drug(human+notarealdrug)→caution;yeast_communication→abstain;yeast_gene_state→abstain。

## 6. Runner:`praxis_virtualcell/tests/test_negative_cases.py`

1. `_load_cases()`:glob `negative_cases/*.yaml`(跳过 `._*`),展平。
2. `test_negative_case_count`:≥12。
3. `test_negative[case]`(parametrized)按 `layer` 分派:
   - normalize:`pytest.raises(SchemaError)` 包 `normalize_request(input)`。
   - validate:`v=validate_candidate(input)`;断言 `v["schema_valid"] is False`;有 `error_contains` 则 `any(sub in e for e in v["errors"])`;有 `missing_contains` 则在 `v["missing_fields"]`。
   - route:`d=route(normalize_request(input))`;断言 `d.disposition == expect["disposition"]`。
4. `test_negative_never_silently_accepts`(KPI):遍历全部——normalize 层必抛、validate 层 `schema_valid=False`、route 层 `disposition != "accept"`;任一「静默成功」即失败。

## 7. 验收

- `pytest praxis_virtualcell/tests/test_negative_cases.py` 全绿,≥14 case,KPI 无静默 accept。
- 全量 `praxis_virtualcell/tests` 无回归(≥255 passed,0 failed)。
- CI 口径(无 .env)无回归。

## 8. 边界(不做)

- 不改 normalize/validate/route 任何逻辑(只读断言现有拒绝行为);若某拒绝路径实际不拒绝=真实 gap,停下报告,不改测试迁就。
- 不测下游机制模型(GEM gene-existence)——cobra-gated,属另一层。
