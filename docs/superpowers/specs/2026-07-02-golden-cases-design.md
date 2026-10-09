# Golden case 固化 — 设计文档

> 日期 2026-07-02 · 归属 v0.7 测试体系(计划 §4.3) · 状态:已 brainstorm(自主定,无重大 UX 决策),待写实现计划。

## 1. 背景与目标

现有 16 个代表 case 以**命令式** `test_*_case.py` 存在,且多数依赖 `cobra`/`torch`(Mac 上 skip)。计划 §4.3 要把它们**固化为声明式 golden fixtures**,建立每次提交自动回归的安全网,核心 KPI:**golden pass 100%、unsafe accept = 0**。

**关键洞察(已探索验证)**:`route(normalize_request(req))` 是**纯声明式、无重依赖、Mac/CI 必可跑**的路由+治理决策,返回 `RouteDecision(engine, disposition, caution_flags, data_gated)`。它正是 golden 的理想锚点——直接覆盖 §4.3 的「route 正确 / verdict 正确 / 不许 accept 误判 / abstain 不硬报」与 KPI「unsafe accept=0」,且零 skip。GEM 数值 case 依赖 cobra 属另一层,不纳入本 golden(避免 skip 污染 KPI)。

## 2. Golden 数据格式

`praxis_virtualcell/tests/golden_cases/*.yaml`,每文件含 `cases:` 列表。每个 case:

```yaml
cases:
  - case_id: human_gene_expression
    description: 人类基因扰动→表达,原生 scRNA predictor
    input:
      species: human
      perturbation_object: gene
      target_output: expression
      perturbation_targets: [AHR]
    expect:
      engine: donor_predictor
      disposition: accept
    # 可选:caution_flags: [ortholog_required] · data_gated: true · workflow: offline
```

字段:`input` 直接喂 `normalize_request`(species/perturbation_object/target_output/perturbation_targets[,medium,cell_type]);`expect` 断言 `route()` 输出(engine/disposition 必填,caution_flags/data_gated 选填);`workflow: offline` 标记的 case 额外跑一次离线 run_query 验证 report.md/provenance 生成。

分两文件(语义分组,便于审阅):
- `routing_representative.yaml` — 12 个代表 case(5 应用 × 4 物种覆盖,dispositions: accept/caution/downgrade)。
- `routing_safety.yaml` — 6 个 safety case(**必须非 accept**:哺乳类 scRNA predictor 不用于微生物、哺乳类 growth 无机制模型、ligand data-gated 等)。

## 3. 18 个 golden case(route() 期望值均已实跑验证)

代表(12):
| case | input(species/obj/out) | engine | disposition | 备注 |
|---|---|---|---|---|
| human_gene_expression | human/gene/expression | donor_predictor | accept | workflow: offline |
| mouse_gene_expression | mouse/gene/expression | donor_predictor | caution | ortholog_required |
| ecoli_gene_growth | bacteria/gene/growth | gem_fba | accept | |
| yeast_gene_growth | yeast/gene/growth | gem_fba | accept | |
| ecoli_medium_growth | bacteria/medium/growth | gem_fba | accept | 碳源切换 |
| bacteria_drug_growth | bacteria/drug/growth | gem_fba | accept | 抗生素靶代谢 |
| human_drug_expression | human/drug/expression | embedding | caution | LINCS 签名 |
| human_gene_state | human/gene/state | state_scoring | accept | EMT/命运 |
| mammalian_flux | human/gene/flux | pathway_scoring | caution | 代谢 tendency |
| human_communication | human/ligand/communication | communication | accept | ligand-receptor |
| mouse_gene_state | mouse/gene/state | state_scoring | caution | ortholog_required |
| human_spatial_niche | human/medium/state | spatial_niche | accept | niche |

Safety(6,必须非 accept):
| case | input | engine | disposition | data_gated |
|---|---|---|---|---|
| bacteria_gene_expression_reject | bacteria/gene/expression | reject | abstain | — |
| yeast_gene_expression_reject | yeast/gene/expression | reject | abstain | — |
| mammalian_growth_downgrade | human/gene/growth | gem_fba | downgrade | true |
| human_ligand_expression_downgrade | human/ligand/expression | embedding | downgrade | true |
| bacteria_state_reject | bacteria/gene/state | reject | abstain | — |
| bacteria_communication_reject | bacteria/ligand/communication | reject | abstain | — |

## 4. Runner:`praxis_virtualcell/tests/test_golden_cases.py`

1. `_load_cases()`:glob `golden_cases/*.yaml`,`yaml.safe_load` 展平为 (case_id, case) 列表。PyYAML 是核心依赖(pyproject `dependencies`),CI 必有,**零 skip**。
2. `test_route_matches[case]`(parametrized):`dec = route(normalize_request(case["input"]))`;断言 `dec.engine == expect.engine`、`dec.disposition == expect.disposition`;若 expect 有 `caution_flags` 则断言集合相等,有 `data_gated` 则断言相等。
3. `test_no_unsafe_accept`:遍历全部 case,统计 `expect.disposition != "accept"` 但 `实际 == "accept"` 的数量,断言 == 0(KPI:unsafe accept=0)。
4. `test_case_count`:断言载入 ≥16 个 case(防 glob 落空/静默漏测)。
5. `test_workflow_offline_report[case]`(仅 `workflow: offline` 的 case):`run_query(input, offline)` → 断言 `render_report_md(job)` 含 9 段、structured_report 有 `provenance` 且非空、`abstain` 为 bool(覆盖 §4.3 的 report.md 生成 + provenance 完整)。

## 5. 验收

- `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_golden_cases.py -q` 全绿,≥16 参数化 case pass,unsafe accept=0。
- 全量 `praxis_virtualcell/tests` 无回归(≥233 passed)。
- CI 口径(无 .env)无回归。

## 6. 边界(不做)

- 不纳入 GEM 数值精度 case(依赖 cobra,属机制模型层,单独 runbook 覆盖)——避免 skip 污染 golden KPI。
- 不改 route_table/species_schema 任何逻辑(golden 只读断言现有行为;若发现 route 输出与期望不符,说明是真实 bug,停下报告,不改 golden 迁就)。
- Negative/fuzz(错基因/错物种/无法映射)属切片 2,不在此。
