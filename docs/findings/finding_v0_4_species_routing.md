# finding v0.4 W1 — 代表物种 schema + route table + case validator(纯 Mac)

> 目标:把 request 词汇扩到代表物种 × 代表应用,建立 (species × object × output) → 引擎的声明式路由,并把"每 case 必须真实分析(7 部分)"做成可执行门。证据类型:`[Mac确定性]` + `[能力矩阵]`(路由是能力有/无,**非**性能)。
> 对应 `docs/PLAN-v0.4-species-applications.md` 步骤 W1.1 / W1.2 / W1.3。测试:Mac **137 passed + 25 skipped**(+32 v0.4 新测试)。

## 1. species-aware request schema(W1.1)

`praxis_virtualcell/agents/species_schema.py`:
- 词汇:`SPECIES`={human,mouse,yeast,bacteria};`PERTURBATION_OBJECTS`={gene,gene_combination,drug,medium,ligand};`TARGET_OUTPUTS`={expression,growth,flux,state,communication}。
- `normalize_request(raw)`:gene/ligand→大写、drug→小写;可选 cell_type/medium/dose 去空格透传;**未知词汇 / 缺必需字段 / gene 类空 targets 一律抛 `SchemaError`,不静默补默认**。
- 测试 `test_species_schema.py`(11 passed):五类代表输入(human gene / mouse gene / ecoli KO growth / yeast deletion growth / human drug)归一 + 四类非法输入报错。

## 2. route table + applicability rules(W1.2)

`praxis_virtualcell/agents/route_table.py`:`route(req) → RouteDecision{engine, disposition, reason, caution_flags, data_gated}`。
- 引擎:`donor_predictor`(哺乳类 scRNA delta-expr)/ `gem_fba`(机制代谢模型)/ `embedding`(药物·配体 signature)/ `reject`。
- disposition:accept / caution / downgrade / abstain。

**覆盖矩阵(实跑输出)**:

| species | object | output | engine | disposition | reason |
|---|---|---|---|---|---|
| human | gene | expression | donor_predictor | accept | human_native_scrna_predictor |
| mouse | gene | expression | donor_predictor | **caution** | human_predictor_transfer_to_mouse_requires_ortholog |
| bacteria | gene | growth | **gem_fba** | accept | bacteria_metabolic_gem_fba |
| yeast | gene | growth | **gem_fba** | accept | yeast_metabolic_gem_fba |
| bacteria | gene | expression | reject | **abstain** | mammalian_scrna_predictor_not_applicable |
| human | drug | expression | embedding | **downgrade** | drug_signature_model_data_gated(data-gated) |
| human | gene | growth | gem_fba | downgrade | mammalian_flux_model_not_wired(data-gated) |

**applicability 铁律(已测)**:哺乳类 scRNA predictor **绝不**路由到 bacteria/yeast growth(→ gem_fba);微生物 expression 无适用 predictor → abstain;data-gated 引擎真跑前恒 downgrade/abstain,**不假装 accept**。测试 `test_route_table.py`(9 passed)。

## 3. case report 7 部分 validator + 3 routing-prototype case(W1.3)

`praxis_virtualcell/agents/case_report.py`:`CaseReport`(7 字段)+ `validate_case_report`(缺/空任一 → `CaseReportError`)+ `routing_case(id, raw_req)`(schema 归一 + route → 7 部分真实填充)。

**3 个 routing-prototype case(实跑决策)**:

| case | 输入 | engine | disposition | caution | 说明 |
|---|---|---|---|---|---|
| C3 mouse ortholog | mouse gene Trp53→expression | donor_predictor | caution | `ortholog_required` | 跨物种迁移带 caution,预测需降级 |
| C4 E. coli KO | bacteria gene b0720→growth | gem_fba | accept | — | 路由到机制模型;**生长数值 pending W2 GEM 真跑** |
| C5 yeast deletion | yeast gene YAL001C→growth | gem_fba | accept | — | 同上,数值 pending W2 |

- **诚实边界**:C4/C5 本步只验证"路由到正确引擎(gem_fba)",boundary 明确标 `生长数值 pending W2 GEM 真跑,不声称生长数值`;C3 的分析输出 = 治理路由行为本身(真实,非 mock)。
- 测试 `test_v04_case_schema.py`(12 passed):validator 拒绝 7 部分任一缺失 + 3 routing case 方向正确且 7 部分齐全。

## 4. 诚实标注

- 路由表是**声明式能力图** `[能力矩阵]`,证明"系统能按物种/对象/输出识别适用性并路由/降级/弃权",**非**预测性能。
- routing-prototype case 完成 = 治理行为正确;**真实数值预测**(GEM growth、drug signature)是后续 T/D 类步骤(W2/W3),需真跑工具,本步未做、未假装。
- 未接入真 GEM/embedding 前,gem_fba(microbe growth 除外)与 embedding 引擎均标 data_gated。
