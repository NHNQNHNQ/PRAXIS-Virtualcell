# P10.B2 M3/M4 代谢模块做到满(gem_fba 全子路径 + pathway_scoring)设计 spec

> P10.B(八模块真实接入)的第一个"逐模块做到满"单元。上游:roadmap `docs/superpowers/plans/2026-07-08-phase10-deep-validation-roadmap.md`;复用 B1 基建 spec `docs/superpowers/specs/2026-07-08-phase10b1-real-predictor-mainline-design.md`。

## 一、目标

把 **M3(线粒体能量代谢)+ M4(胞质代谢)** 这对共享引擎(`gem_fba` + `pathway_scoring`)的模块彻底接满主链。B1 已通 `gem_fba gene→growth`(ecoli/yeast KO);本单元补齐这对模块**余下全部真实子路径**:

1. **gem_fba + medium**(微生物碳源切换 growth)→ `run_medium_shift_case`(e_coli_core 真数据)
2. **gem_fba + drug**(微生物抗生素靶抑制 growth)→ `run_antibiotic_case`(iML1515 真数据)
3. **pathway_scoring**(哺乳类代谢通路 tendency)→ `run_metabolic_tendency_case`(Kang 2018 真数据,Cohen's d 评分)

做完后 M3/M4 的所有已实现 runner 都真实跑在 offline 主链,真实覆盖从 ~1–2/8 提到含 M3/M4 完整代谢对。

## 二、架构(纯扩 B1 的 adapter 分发层,不新建 Agent)

B1 已建 `CaseRunnerPredictorAgent`(PredictorAgent 子类,内部按 route engine 分发)+ `case_dispatch`。本单元只**扩 `case_dispatch` 的分发/映射分支** + **把 `pathway_scoring` 加进 `REAL_ENGINES`**,其余(CaseRunner/ModelApplicability 分诊/EnsembleCoordinator/build_runtime 注册)一律不改。

关键:三个新 runner 都返回 `(CaseReport, RouteDecision)`,CaseReport 带 `reliability_decision.disposition`(accept/caution/downgrade/abstain)+ `caution_flags`。B1 的**诚实透传机制直接复用**:disposition=="abstain" → CaseRunner emit `status="rejected"` → 主链经既有 `if not used` 如实 abstain;caution/downgrade → success 且 `caution_flags` 经 `model_cautions` 表面化。**本单元不碰 reliability/critic 裁决逻辑。**

## 三、三个子路径的精确契约(已核 file:line)

路由现实(`agents/route_table.py:47-70`,`normalize_request` 先行):
- `out∈{growth,flux}` 的代谢分支**最先判**:`sp∈微生物 and obj∈{gene,gene_combination,medium,drug}` → `gem_fba/accept`;`sp∈哺乳 and out==flux` → `pathway_scoring/caution`。
- 故 bacteria+drug+growth 命中 gem_fba(在后面 `obj=="drug"→embedding` 之前 return),不冲突。

### 3.1 gem_fba + medium(`predictors/mechanistic/medium_shift.py:48`)
- 触发:`{species:bacteria, perturbation_object:medium, target_output:growth, perturbation_targets:[碳源名]}`。
- CaseReport.raw_output:`{"reference","glucose_growth", "carbon_sources":[{"carbon","in_model","growth","ratio_vs_glucose"},...]}`。
- disposition:全不在模型→abstain;部分→caution(`carbon_not_in_model:[...]`);全在→accept。
- **delta 映射**:`[round(r["ratio_vs_glucose"]-1.0, 4) for r in carbon_sources if r["in_model"]]`(相对葡萄糖的生长变化;不在模型的碳源跳过)。

### 3.2 gem_fba + drug(`predictors/mechanistic/antibiotic.py:41`)
- 触发:`{species:bacteria, perturbation_object:drug, target_output:growth, perturbation_targets:[抗生素名]}`。
- CaseReport.raw_output:`{"wt_growth", "antibiotics":[{"antibiotic","target_rxn","in_model","growth","ratio_vs_wt","growth_arrest"},...]}`;未知抗生素/非代谢靶/靶反应不在模型的项无 `ratio_vs_wt`,disposition 记 abstain/caution。
- disposition:按各项 max(accept<caution<downgrade<abstain)。
- **delta 映射**:`[round(r["ratio_vs_wt"]-1.0, 4) for r in antibiotics if r.get("in_model") and r.get("ratio_vs_wt") is not None]`(靶抑制后相对 WT 的生长变化;未知/非代谢/不在模型的项跳过,不虚构)。

### 3.3 pathway_scoring(`predictors/state/metabolic_tendency.py:60`)
- 触发:`{species:human, perturbation_object:gene, target_output:flux, ...}`(哺乳类 flux → pathway_scoring;runner 对固定代谢 panel 评分,不依赖具体 target)。
- CaseReport.raw_output:`{"pathway_shifts":[{"pathway","cohens_d","n_ctrl","n_stim",...}], "max_abs_cohens_d"}`。
- disposition:缺 ctrl/stim 组→abstain;max|d|≥accept 阈→accept;≥caution 阈→caution;否则 downgrade(`weak_pathway_effect`)。
- **delta 映射**:`[round(s["cohens_d"], 4) for s in pathway_shifts]`(每条通路的效应量 Cohen's d 作为 delta 分量;确定性,继承 raw_output 的 round)。

## 四、要改的文件

- **Modify** `predictors/case_dispatch.py`:
  - `REAL_ENGINES` 加 `"pathway_scoring"`(→ `frozenset({"gem_fba","pathway_scoring"})`)。
  - `dispatch_runner(engine, raw_req)`:gem_fba 分支按 `perturbation_object` 细分——`gene/gene_combination`→growth runner(现状)、`medium`→`run_medium_shift_case`、`drug`→`run_antibiotic_case`;新增 `pathway_scoring`→`run_metabolic_tendency_case`。未覆盖组合仍抛 `UnsupportedEngine`。
  - `map_case_delta(engine, report)`:按 raw_output 形状分支——含 `knockouts`(gene,现状)/`carbon_sources`(medium)/`antibiotics`(drug)/`pathway_shifts`(pathway_scoring)。用 `raw_output` 里的判别键选分支(比传 perturbation_object 更稳)。
- **Modify** `agents/model_applicability.py`:`_REAL_ENGINES` 已 import 自 `case_dispatch.REAL_ENGINES`(B1 单一真源),自动含 pathway_scoring,**无需改代码**;仅需确认分诊对 human+flux 请求把候选切到 CaseRunner。
- **Create** T10.2 cases in `tests/phase10/test_t10_2_module_contracts.py`:M3/M4 各 3 正例 + 2 负例。
- **不改**:CaseRunner adapter、EnsembleCoordinator、build_runtime 注册、reliability/critic、provenance/report(B1 的 model_cautions 通道已覆盖诚实透传)。

## 五、数据流(mock 不变 + 三条新真实路径)

- **mock 请求**(human gene→expression = donor_predictor):route≠REAL_ENGINES → ModelApplicability 走现状 mock 枚举 → **字节等价不变**(B1 已锁,本单元不触碰该路径)。
- **新真实路径**:上述三类请求 → ModelApplicability 判 engine∈REAL_ENGINES → 候选=["CaseRunner"] → CaseRunner dispatch 到对应 runner 真跑 → delta + disposition 诚实透传。

## 六、影响(哪些请求从 abstain/mock → 真实预测)

- bacteria+medium/drug+growth:接入前 dispatch 抛 UnsupportedEngine(B1 只认 gene)→ 现真实 FBA。
- human+gene+flux:接入前走 mock 枚举(多半 abstain)→ 现真实 pathway tendency 评分。
- 受影响既有测试执行时定位;确认变化确由"接入真实 runner"引起(预期语义提升)才更新断言;**若 mock/donor 路径行为变 = 真实回归,停下排查**。

## 七、测试(T10.2 扩充,M3/M4 各 3 正 + 2 负)

**正例**(真实 FBA/评分):
- M3/M4-P1 bacteria medium 切换(如 `["acetate"]`):accept,delta=`ratio_vs_glucose-1` 合理(乙酸生长 < 葡萄糖 → 负)。
- M3/M4-P2 bacteria antibiotic(如已知靶抗生素):accept,靶抑制 delta 负;`growth_arrest` 真值。
- M3/M4-P3 human flux pathway tendency:disposition 按 max|d| 真裁决;delta=各通路 cohens_d。
- (B1 已覆盖 gene→growth 正例,复用不重复)。

**负例**(诚实 abstain/caution):
- M3/M4-N1 bacteria medium 全不在模型(如 `["unobtainium"]`):abstain → 主链 abstain=True/prediction=None(B1 机制)。
- M3/M4-N2 bacteria 未知抗生素(如 `["fakedrugX"]`):abstain,`unknown_antibiotic` 经 model_cautions 表面化。

**契约断言**:确定性(真实请求 3 跑 structured_report/trace 字节稳)、disposition 诚实(abstain→models_rejected+abstain / caution→model_cautions)、provenance 可追溯(tool/model/engine)。

## 八、红线(继承 B1 + Phase 10)

- 核心+根 tests/ 零触碰;reliability/critic 裁决逻辑零改(honest abstain 靠既有 `if not used`)。
- 真实预测确定性(cobra FBA / 固定 panel 评分均确定性)。
- adapter 诚实透传不伪造(runner 已判 disposition,adapter 只如实映射)。
- 不 push;commit trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- pathway_scoring 的 downgrade disposition 只经 model_cautions 表面化(advisory),不改写 reliability 裁决数值(与 B1 一致)。

## 九、完成标准

1. 三条新子路径 offline 端到端真实跑通(medium/drug 真实 FBA、pathway 真实 Cohen's d 评分),各带真实 delta + 诚实 disposition。
2. mock 请求(donor/AHR)字节等价不变;真实请求 3 跑字节稳。
3. T10.2 M3/M4 各 3 正 + 2 负全绿;全量回归 0 failed。
4. `map_case_delta`/`dispatch_runner` 分支按 raw_output 判别键清晰、每分支有单测。
5. ruff 全绿;台账勾账(控制器);记忆更新。

## 十、Self-review 覆盖

- 三 runner 契约均已核 file:line(medium_shift/antibiotic/metabolic_tendency 的 raw_output 键、disposition 逻辑、route 触发条件),无占位。
- delta 映射对每 runner 的判别键(carbon_sources/antibiotics/pathway_shifts)明确,None/不在模型项跳过策略与 B1 一致。
- 未越界:不接 M6/M7/M2/M1/M5/M8(留后续单元);不碰 reliability/provenance/report 逻辑;communication 孤儿引擎的模块映射不在本单元(留 M7 或专门处理)。
