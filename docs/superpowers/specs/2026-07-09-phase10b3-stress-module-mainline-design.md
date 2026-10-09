# P10.B3 M7 应激模块诚实接入(真实 drug + IFN-β 状态)+ M6/emt/fate limitation 设计 spec

> P10.B 第三个"逐模块做到满"单元。上游:roadmap `docs/superpowers/plans/2026-07-08-phase10-deep-validation-roadmap.md`;复用 B1 adapter 基建 + B2 窄门套路 spec `docs/superpowers/specs/2026-07-09-phase10b2-metabolic-modules-mainline-design.md`。审计依据见会话内 M6/M7 runner 请求依赖性勘察。

## 一、目标与诚实边界(先讲清"做到满"的真相)

审计确认:M6/M7 的 6 个候选 runner 里,**只有 2 个真请求特异**(drug_signature/drug_dose),cell_state 可窄门到 IFN-β(同 B2 pathway_scoring),**emt/fate/spatial_niche 是固定数据集的"状态刻画"工具,把它们当扰动 delta 预测器接主链是过度声称/类别错误**。故本单元诚实做法:

- **接主链(真实)**:M7 应激的 `embedding`(drug_signature/drug_dose,真实药物扰动签名/剂量响应)+ `state_scoring` 的 cell_state **窄门 human+IFN-β**(真实 ISG 响应)。
- **不接主链(诚实 limitation)**:`emt`/`fate`(M7 的 state_scoring 分支,状态刻画非扰动预测)、`spatial_niche`(M6 骨架,固定乳腺 niche)。它们经既有 abstain 通路诚实弃权,并在覆盖表明确标注"characterization-only,非扰动预测器"。

做完后 **M7 得真实药物扰动 + IFN-β 状态覆盖**;M6 与 emt/fate 作诚实 limitation(符合论文"3-5/8 真实 + 诚实弃权"定位)。

## 二、架构(纯扩 case_dispatch,复用 B1 机制 + B2 窄门)

只改 `predictors/case_dispatch.py` 三处 + 测试:
- `REAL_ENGINES` 加 `embedding` + `state_scoring`(→ `{"gem_fba","pathway_scoring","embedding","state_scoring"}`)。
- `dispatch_runner` 加两个引擎分支,**都 human-guarded**(LINCS/Kang 均 human 数据,防 B2 那种物种泄漏):
  - `embedding` + `species=="human"`:请求带 `dose` 字段 → `run_drug_dose_case`(剂量响应意图);否则 → `run_drug_response_case`(MOA 签名)。两者自带"药不在库→abstain"窄门。
  - `state_scoring` + `species=="human"` + `_is_ifn_beta(targets)`(复用 B2 的 IFN-β 精确别名白名单)→ `run_cellstate_case`;否则落 UnsupportedEngine → abstain(**emt 的 human 非 IFN state、fate 的 mouse state 自然经此诚实弃权,不接**)。
- `map_case_delta` 按 raw_output 判别键加分支(per_drug/dose_response/per_cell_type)。
- 诚实透传复用 B1 机制(abstain→CaseRunner rejected→主链 abstain;caution/downgrade→model_cautions),**不碰 reliability/critic 裁决**。

**delta 语义诚实**:这些 delta(moa_enrichment/spearman/cohens_d)是效应量/富集/单调性量,**非 WT 相对比值**;但各 runner 的 `provenance_boundary`(method/boundary,如"MOA 富集"/"dose-recall Spearman"/"ISG 组间 Cohen's d")经 adapter 透传到 structured_report.provenance,语义可追溯(同 B2 pathway_scoring 先例)。

## 三、三个真实子路径的精确契约(已核 file:line + 端到端真跑)

### 3.1 embedding / drug_signature(`predictors/embedding/drug_signature.py:81`)
- 触发:`{species:human, perturbation_object:drug, 无 dose 字段}`(route `obj==drug → embedding`,route_table.py:89)。
- 真迭代 `norm["perturbation_targets"]`(drug_signature.py:91),逐药 `db.has(drug)` → 不在库 abstain(自带窄门)。
- raw_output:`{"per_drug":[{"drug","in_db","moa","moa_enrichment",...}], "enrichment_threshold"}`。
- disposition(drug_signature.py:105-114):不在库→abstain;无同 MOA 伙伴→downgrade;enr≥1.5→accept;else downgrade;总裁=最保守。
- **delta 映射**:`[round(d["moa_enrichment"],4) for d in per_drug if d.get("in_db") and d.get("moa_enrichment") is not None]`(不在库的药跳过)。**已核**:geldanamycin(HSP90_inhibitor)→ accept、moa_enrichment=2.646 → delta `[2.646]`;notadrug123 → abstain、`drug_not_in_db`。

### 3.2 embedding / drug_dose(`predictors/embedding/drug_dose.py:61`)
- 触发:`{species:human, perturbation_object:drug, 带 dose 字段}`(dose-response 意图)。
- 读 `norm["perturbation_targets"][0]`(drug_dose.py:68),`db.has(drug)` → 不在库 abstain。
- raw_output:`{"drug", "dose_response":{"n_doses","ref_dose","doses","recalls","spearman","insufficient"}}`。
- disposition(drug_dose.py:70-86):不在库→abstain;<3 剂量或数据不足→downgrade;max_recall<0.05→downgrade;spearman≥0.6→accept;≥0.3→caution;else downgrade。
- **delta 映射**:`[round(report.raw_output["dose_response"]["spearman"],4)]`。**已核**:geldanamycin(dose)→ accept、spearman=0.9 → delta `[0.9]`。

### 3.3 state_scoring / cell_state(`predictors/state/cell_state.py:78`,窄门 human+IFN-β)
- 触发:`{species:human, target_output:state}` → route state_scoring(route_table.py:74);**窄门只放行 IFN-β**(cell_state 是固定 Kang IFN-β ISG 数据,无视请求 targets——同 metabolic_tendency,必须窄门)。
- raw_output:`{"marker_coverage","isg_panel_size","ctrl_mean","stim_mean","cohens_d","n_ctrl","n_stim","per_cell_type":[...]}`。
- disposition(cell_state.py:91-100):n_ctrl/n_stim<2→abstain;coverage<0.5→downgrade;|d|≥0.8→accept;≥0.3→caution;else downgrade。
- **delta 映射**:`[round(report.raw_output["cohens_d"],4)]`(整体 ISG 组间效应量;per_cell_type 明细在 raw_output/provenance)。**已核**:human ligand IFNB1 → accept、cohens_d=2.485 → delta `[2.485]`。

## 四、要改的文件

- **Modify** `predictors/case_dispatch.py`:REAL_ENGINES 加 embedding+state_scoring;dispatch_runner 加 embedding(dose 判别,human-guarded)+ state_scoring(cell_state,human+IFN-β 门)分支;map_case_delta 加 per_drug/dose_response/per_cell_type 判别键。
- **Modify** `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`:B3 单元 + 端到端 + limitation 诚实 abstain 测试。
- **不改**:runner 本体、reliability/critic/provenance/report、build_runtime;emt/fate/spatial_niche runner 不接(不动它们)。

## 五、影响(哪些请求语义提升)

- human drug(在库,如 geldanamycin):接入前走 mock 枚举(多半 abstain)→ 现真实 MOA 签名/剂量响应。
- human IFN-β state:接入前 mock/abstain → 现真实 ISG cohens_d。
- **诚实 abstain(新守卫)**:mouse+drug(物种守卫)、human 非 IFN-β state(cell_state 门,含 emt 的 ZEB1 等)、mouse state(fate)、human medium+state(spatial_niche 不接)→ 全部诚实弃权,不虚构。
- 受影响既有测试执行时定位;确认由"接入真实 runner"引起才更新;**mock 的 expression/donor 路径行为变 = 真实回归停下排查**。

## 六、测试(T10.2 扩充)

**正例(真实)**:drug_signature geldanamycin delta[2.646]、drug_dose geldanamycin(dose)delta[0.9]、cell_state IFNB1 delta[2.485],各 abstain False + CaseRunner used + provenance 可追溯。
**诚实 abstain(负例/limitation 守卫)**:drug notadrug123→abstain(自带)、mouse+drug→abstain(物种守卫)、human 非 IFN state(如 ZEB1 gene→state)→abstain(emt 不接/cell_state 门拒)、mouse state→abstain(fate 不接)、human medium+state→abstain(spatial_niche 不接)。
**契约**:确定性(真实请求 3 跑 structured_report/trace 字节稳)、mock expression 不变、disposition 诚实透传。

## 七、红线

- 不碰 reliability/critic 裁决(honest abstain 靠既有 `if not used`)。
- 真实预测确定性(固定数据集评分/LINCS 查询均确定性)。
- adapter 诚实透传不伪造;emt/fate/spatial_niche **绝不**接成扰动 delta 预测器(类别错误),经诚实 abstain + 覆盖表 limitation 标注。
- 全 human 数据的引擎(embedding/state_scoring)均 species 守卫,防物种泄漏(B2 教训)。
- 核心+根 tests/ 零触碰;不 push;trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

## 八、完成标准

1. 三真实子路径 offline 端到端真跑(drug 签名/剂量响应、IFN-β 状态),各带真实 delta + 诚实 disposition。
2. 诚实 abstain 守卫全生效(mouse/非 IFN/emt/fate/spatial 各诚实弃权,不虚构固定数据)。
3. mock expression 字节等价不变;真实请求 3 跑字节稳;全量回归 0 failed。
4. map_case_delta/dispatch_runner 分支按判别键 + human/IFN 门清晰、有单测。
5. ruff 全绿;台账勾账(含 emt/fate/spatial_niche/M6 的 limitation 记录);记忆更新。

## 九、Self-review 覆盖

- 三 runner 契约均已核 file:line + 端到端真跑取确切值(2.646/0.9/2.485),无占位。
- 过度声称预防:cell_state 窄门 IFN-β(同 metabolic_tendency 教训)、全引擎 human 守卫(B2 物种泄漏教训)、emt/fate/spatial 不接(类别错误,诚实 limitation)。
- embedding 双 runner 判别(dose 字段)明确;delta 语义(效应量/富集/单调性 非 WT 比值)经 provenance_boundary 透传诚实。
- 未越界:不接 M2/M1/M5/M8;不碰 reliability/provenance/report 逻辑;不动 emt/fate/spatial runner 本体。
