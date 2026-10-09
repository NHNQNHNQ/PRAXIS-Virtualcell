# Phase 5:主动学习 v1(EvidenceLevelAgent E0–E5 + ActiveLearningAgent + learning_queue + 接管线 + report 扩段)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增两个**读运行时确定性信号的薄层 advisory agent**:①`EvidenceLevelAgent`(插点 C)—— 读现有 `reliability_decision`(reliability/abstain/disagreement/downgrade)+ `learned_reliability`(reliability_score/abstain_decision/fallback)+ OOD proxy(runtime `seen_in_train`,多为 None → 退回 caution_flags/非母种代理)+ `module_plan` 信号,映射到证据等级 **E0–E5**(决策 B:治理层之上的薄映射,**不重写治理**;E2=匹配扰动数据 in-domain→accept 与现有 disposition 对齐);②`ActiveLearningAgent`(插点 D)—— 用 disagreement/OOD/证据等级信号算 information gain,产 **learning_queue**(该测什么的优先队列,advisory 规划产物)。两者产物**只挂进 `report.provenance`**(`evidence_level` / `learning_queue`),**绝不碰 prediction / verdict 终决 / provenance ledger / reliability 决策**(红线:主动学习不改裁决,只建议下一步实验)。同时把两 agent **接进 `run_workflow` 固定管线**(插点 C 在 reliability 信号可读之后、插点 D 在 Provenance/Report 之后),沿用 Phase 4 的旁路挂载惯例,**OFFLINE 字节等价**(零 LLM、确定性信号)。report_markdown 渲染器扩两段("证据记录"/"验证计划"),现有 9 段结构不变。Phase 5 完成 = **v1.2 里程碑**(active-learning)。

**Architecture:** 全部**净新增 + 复用,不推倒**。新子包 `praxis_virtualcell/active_learning/`(`acquisition.py` 纯函数 information-gain / `learning_queue.py` 队列数据结构 / `active_learning_agent.py` 进 bus 的 ActiveLearningAgent);`governance/` **扩**加 `evidence_level.py`(E0–E5 映射纯函数)+ `agents/evidence_level_agent.py`(进 bus 的 EvidenceLevelAgent 薄包装)。**不改**现有 reliability / critic / provenance / predictor / route_table / ModulePlan / Phase 3/4 任何**逻辑**;仅 `workflows/predict_delta_expression.py` 增量注册两 agent、`core/runtime.py` 加两个**可选**旁路插点(OFFLINE 分支与现在字节等价 —— 两 agent 是确定性零 LLM,OFFLINE 也注册,但只往 `report.provenance` 追加 `evidence_level`/`learning_queue` **新键**,不动任何现有键)、`io/report_markdown.py` 加两段渲染(读新 provenance 键,缺则标 N/A,不崩)。EvidenceLevel/ActiveLearning 与治理引擎的关系严格是**读信号 → 映射 → advisory 输出**:E-level 读 `reliability_decision`/`learned_reliability`/`module_plan` 映射 E0–E5 但**不回写 verdict**(verdict 仍由现有 reliability + ModulePlan.synthesize_verdict 定);learning_queue 用 disagreement/OOD/证据等级排序候选实验但**不改任何裁决**。

**Tech Stack:** Python 3.13 / pytest 参数化 / dataclasses(标准库)/ 复用现有 `core/bus.py:MessageBus`、`core/agent.py:BaseAgent`、`core/message.py:AgentMessage`。**零 LLM、零 torch、零 cobra**(主动学习/证据等级全用 v0.8 已有的确定性信号:reliability/disagreement/downgrade/learned_reliability/caution_flags/module_plan)。信号来源全部来自管线已产出的 `report` dict 字段与 `reliability_decided` payload,不新引入外部依赖。

---

## 铁律(每个 task 验收都要守)

- **纯新增 + 复用,不改现有逻辑**:只新增 `active_learning/`(子包)、`governance/evidence_level.py`、`agents/evidence_level_agent.py`、新测试;`workflows/predict_delta_expression.py` 仅**增量注册**两 agent(不改现有注册);`core/runtime.py` 仅在 `run_workflow` 加**两个可选旁路插点**(OFFLINE 分支必须与现在字节等价:两 agent 是确定性零 LLM 节点,只往 `report.provenance` 追加 `evidence_level`/`learning_queue` **新键**,不动任何现有键与预测/治理路径);`io/report_markdown.py` 仅**追加两段**(读新 provenance 键,现有 9 段结构与字节输出对既有 job 不变)。**不改** reliability / critic / provenance / predictor / route_table / ModulePlan / Phase 3/4 任何 agent 的逻辑。若发现现有行为与预期不符 → **真实 bug,停下报告,不改代码/不改测试迁就**(红线 5)。
- **红线 1:OFFLINE 默认零 LLM 不变**。默认 `mode=OFFLINE`、`llm_enabled=False`,核心 case/预测/治理零 token 可跑。EvidenceLevel/ActiveLearning **全是确定性信号映射,零 LLM**,故 OFFLINE 也注册(与 Phase 4 的 SpeciesContext/ModuleRouter 同惯例)。它们不 import `agents_llm`/`llm_orchestration`,不调任何 LLM。
- **红线 2:`assert_llm_boundaries` 三 flag 恒 False**。Phase 5 不碰 config、不加枚举、不动守卫。EvidenceLevel/learning_queue **不碰** prediction / hard-rule / learned-reliability 终决 / provenance ledger:evidence_level 是**读信号映射的薄层**(不重写治理,不回写 verdict);learning_queue 是 **advisory 不改裁决**(只建议下一步实验)。**专门契约测试**钉死:E-level agent 产物只进 `report.provenance.evidence_level`、learning_queue 只进 `report.provenance.learning_queue`,二者都不改 `report.abstain`/`report.reliability`/`report.prediction`/`report.provenance` 里任何现有键。
- **红线 4:unsafe-accept = 0 / 无静默 accept**。原 route/module golden + negative 的 KPI 每 task 后仍绿;E-level 的 accept 级(E2+)**只在现有 disposition 已 accept 且信号 in-domain 时给出**(E-level 不得把 abstain/downgrade 抬成 accept —— 决策 B:E2=匹配扰动数据 in-domain→accept **与现有 disposition 对齐**,不领先于治理)。
- **红线 6:信号缺失/退化不静默**。runtime `seen_in_train` 多为 None(实读 `reliability.py:136` 注释)→ OOD proxy fail-closed 退回 caution_flags/非母种代理,并在 evidence_level 里记 `ood_signal: unknown`(不假装 in-domain);learning_queue 无有效候选 → 返回空队列 + note,不虚构实验。
- **测试口径** = `praxis_virtualcell/tests`(**绝不碰根 `tests/`**)。Phase 5 起点基线(当前分支 `feat/v0.9-phase0-module-core`,含 Phase 0/1/2/3/4)**实跑核实 = 509 passed / 25 skipped / collected 534**(2026-07-04 `pytest --junit-xml` 实测)。`-q` 不打印精确 passed;精确数用 `--junit-xml` 属性换算:**passed = tests(collected) − skipped − failures − errors**(junit `tests` 属性是 collected 含 skipped,不是 passed)。**Phase 5 全部测试确定性离线跑(计入 passed,不新增 `@pytest.mark.llm`/`@pytest.mark.remote`),skip 基线 25 恒定不破**。验收只认:**failures=0 errors=0 skipped=25** + 每 task 新增测试条数正确。
- **每 task 全量回归绿**后再 commit:`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`;commit 前 `find . -name '._*' -delete`(外置盘 AppleDouble);commit message 末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`;当前分支 `feat/v0.9-phase0-module-core`,**不 push**。
- **v1.2 里程碑 tag**:Phase 5 是 v1.2 里程碑(路线图 §5)。**只在最后一个 task(5.8)全绿 + 红线核验通过后打 tag**(`git tag v1.2-...`),tag 不 push(房规:当前分支不 push;tag 打在本地由人决定何时推)。中间 task 不 tag。

---

## 数据契约(已实跑核实,计划代码与之对齐)

以下是 Phase 5 依赖的**真实接口**(2026-07-04 实读源码核实,非路线图旧描述):

- **`agents/reliability.py:ReliabilityAgent`**(实读):emit `reliability_decided`,payload = `{**p, "reliability_decision": asdict(rd)}` + 可选 `"learned_reliability"`。`ReliabilityDecision`(`core/message.py:36`)= `{reliability: "high"|"medium"|"low", abstain: bool, reasons: list[str], failed_checks: list[str], model_disagreement: dict|None}`。`reasons` 含 `"downgrade:*"` 前缀项(如 `downgrade:model_disagreement_too_high`/`downgrade:cell_type_not_supported`)。`model_disagreement`(非空时)= `{**dis, "threshold": float, "triggered": bool}`,`dis` 含 `score`(float|None)、可选 `n_zero_vector_pairs`。**这是 E-level/AL 读的 disagreement + reliability 主信号。**
- **`learned_reliability`**(实读 `reliability.py:126` + `report.py:32`):`{reliability_mode, reliability_score(float), abstain_score, abstain_decision("accept"|"downgrade"|"abstain"), features_used, model_version, feature_schema_version, artifact_sha256, abstain_artifact_sha256, fallback(bool)}`。`fallback=True` 表示退回 rule(learned artifact 缺失/schema 不匹配)→ E-level 记 `learned_signal: fallback`。
- **OOD 信号(runtime 真实情况,重要校正)**:runtime `seen_in_train` **多为 None**(实读 `reliability.py:136` 注释:"runtime 多为 None → predict_dp 用训练均值填")。`governance/ood_enrichment.py` 是**离线 ledger 分析模块**(`evaluate_ood(entries)` 读 ledger 的 `seen_in_train` flag 齐全时算 enrichment/odds-ratio),**不是 runtime bus 信号**——路线图 §4 说"插点 C 读运行时 OOD 信号"需校正为:runtime OOD 主要靠 `seen_in_train`(多 None),**None 时退回确定性 OOD proxy**:`caution_flags` 含 ortholog/cross-species 类 flag、或 `species != "human"`(非母种 → 更可能 OOD)。E-level fail-closed:OOD 未知就记 `ood_signal: unknown`,不假装 in-domain。
- **`report`(`agents/report.py:14` 产、`run_workflow` 返回)dict 键**(实读):`{request_id, abstain(bool), reliability("high"|"medium"|"low"|None), prediction(dict|None), models_used, models_rejected, models_failed, abstain_reasons(list,不含 downgrade:前缀), downgrade_reasons(list,downgrade:前缀), failed_checks, model_disagreement(dict|None), critic_violations, caution_flags(dict {target:flag}), learned_reliability(dict|None), provenance(dict)}`。**E-level/AL agent 读的就是这份 report(或等价的 reliability_decided payload)。**
- **`core/runtime.py:AgentRuntime.run_workflow`**(实读,Phase 4 已接管线):节点顺序 `InputInterpreter → BioObjectNormalizer → SpeciesBrain → ModelApplicability →[module_plan 旁路:SpeciesContext→(LLMModulePlanner?)→ModuleRouter]→[LLMRouter?]→ predictor fan-out → EnsembleCoordinator → Reliability → Critic → ProvenanceAgent → Report →[sidecar 挂载:llm_route_suggestion/module_plan/llm_cross_module_notes]→[LLMCritic?][LLMReport?]`。**Phase 4 已确立"sidecar 挂载"惯例**(`runtime.py:100-105`):`report.setdefault("provenance", {})["X"] = ...`,gated by `if "AgentName" in self._agents`。`_dispatch_collect(message, expected_type)` 派发并取 `bus.latest(expected_type)`。`rel = self._dispatch_collect(m, "reliability_decided")` 在 `runtime.py:92` 已拿到 reliability payload;`report` 在 `runtime.py:99` 组装。**Phase 5 插点 C(E-level)在 Report 之后读 report 组装 evidence_level;插点 D(AL)在 evidence_level 之后读它 + report 组装 learning_queue。均 sidecar 挂 `report.provenance`。**
- **`core/agent.py:BaseAgent`**:抽象 `handle(message, bus)->None`,`name` 类属性,只经 `bus.send` 产出。
- **`core/bus.py:MessageBus`**:`send(msg)`、`latest(message_type)->AgentMessage|None`、`get_messages`、`has_message_type`、`trace`。
- **`core/message.py:AgentMessage`**:`message_id/sender/receiver/message_type/payload/timestamp/parent_message_id`(默认 None)。
- **`biological_modules/module_plan.py`**(实读,Phase 3/4):`ModulePlan.to_dict()` 键=`{species, request, primary, secondary, overall_verdict, entries, notes}`;`entries[i]` 键=`{module, display_name, role, engine, route_disposition, species_support, species_verdict, caution_flags, data_gated, pillars, available_models, reason, mismatch, verdict}`。**AL 用 entries 的 module/species_support/verdict/data_gated 判"哪些模块弱/gated → 该补实验"。** `_SEVERITY = {accept:0, caution:1, downgrade:2, abstain:3, reject:3}`(module_plan.py:15 / module_consistency.py:17),Phase 5 复用同映射不重定义。
- **`biological_modules/modules.py`**(实读):`MODULE_ORDER` = `["membrane_system","genetic_hub","mitochondrial_energy_metabolism","cytoplasmic_metabolism","biosynthetic_network","cytoskeletal_framework","stress_processor","degradation_machinery"]`(M1..M8)。
- **`io/report_markdown.py:render_report_md(job)`**(实读):纯函数 9 段(`## 1. Question`..`## 9. Reproducibility`),读 `job["report"]`/`job["request"]`/`report["provenance"]`,缺字段标 `N/A`,零 LLM,可复现,byte-identical。`_verdict(report)` 据 abstain/downgrade_reasons/caution_flags 派生展示 verdict(**只展示不写回**)。**Phase 5 在 §6(Evidence and Provenance)之后 §7 之前插一段"证据记录"(读 `prov["evidence_level"]`),在 §8(Limitations)之后 §9 之前插一段"验证计划"(读 `prov["learning_queue"]`)—— 或作为 §6/§8 的子块,判断见决策 R2。缺键标 N/A,不崩,现有 9 段与既有 job 字节输出不变。**
- **`agents/module_rules.py`**(实读):`pick_primary(req)->str`(human gene→expression 命中 `genetic_hub`)、`pick_secondary(req, primary)->list[str]`、`mismatch_query_for(req, module)->str|None`。纯函数、零 LLM(AL 若需生成"该测哪个模块"的候选可复用,但本 Phase AL 从 module_plan.entries 派生候选,不重造)。
- **`tests/conftest.py`**(实读,gating 机制):`@pytest.mark.llm` 无 `DEEPSEEK_API_KEY` 自动 skip;`@pytest.mark.remote` 无 torch 自动 skip。**当前 25 skip 即由这些 marker + 无 key/torch 构成。Phase 5 不新增任何 marker 测试(全确定性离线),保 skip 恒 25。**
- **`tests/test_report_markdown.py`**(实读):`_SECTIONS` 断言 9 段齐全;`_ACCEPT`/`_ABSTAIN`/`_DOWNGRADE` 三个 job fixture;`test_reproducible_byte_identical` 钉死 byte-identical;`test_no_llm_import_in_module` 钉死渲染器不 import LLM。**Phase 5 扩此文件:加"证据记录"/"验证计划"段的断言,并保持现有 9 段 + byte-identical + no-LLM 断言全绿。**
- **`docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md`**(实存):台账文件;Phase 2/3/4 台账已在其尾部(实读第 71/84/98 行有 Phase 2/3/4 段)。Phase 5 追加 Phase 5 段。

**与路线图旧描述的四处校正(已在计划代码对齐):**
1. **runtime OOD 信号 ≠ ood_enrichment.py**。路线图 §4 说"插点 C 读运行时 OOD 信号(OOD/ood_enrichment)"。实读 `governance/ood_enrichment.py` 是**离线 ledger 分析**(`evaluate_ood(entries)` 需 ledger `seen_in_train` flag 齐全),**不在 runtime bus 上**。runtime 真实 OOD 信号是 payload 里的 `seen_in_train`(实读 `reliability.py:136` 注释:runtime 多为 None)。**校正:E-level 的 OOD 输入 = `seen_in_train`(优先)+ None 时的确定性 proxy(caution_flags 的 ortholog/cross-species flag、`species != human`),fail-closed 记 `ood_signal: unknown`。不调 ood_enrichment(那是离线分析,不进 runtime)。**
2. **EvidenceLevel(E0–E5)归 Phase 5**。Phase 3 计划把它留给"Phase 4/5";Phase 4 计划(插点归置决策)明确把它归 Phase 5;`governance/module_consistency.py:10` 注释亦写"evidence level(E0–E5)不在此校验(留 Phase 4/5;那时管线带 reliability/OOD 信号)"。**本 Phase 归置 = Phase 5**,理由:E0–E5 读运行时 reliability/OOD/disagreement 信号做映射,与主动学习**同源同时机**(AL 也读这些信号 + 用 E-level 排序候选),两者证据链耦合,一起落地最自然。已在下方"EvidenceLevel 归属判断"段展开。
3. **决策 B:E-level 不重写治理、E2 与 disposition 对齐**。路线图 §6-B:证据等级是治理层之上的薄映射;E2=匹配扰动数据 in-domain→accept 与现有 disposition 对齐。**校正实现**:E-level 读 `report.abstain`/`report.reliability`/`report.downgrade_reasons`/`report.caution_flags`/`learned_reliability` **不回写 verdict**;E-level 的 accept 级只在现有 disposition 已 accept(非 abstain、无 downgrade)且信号 in-domain 时给出——即 E-level **不领先于治理**(不能把 downgrade 抬成 E4/E5)。见"EvidenceLevel E0–E5 映射契约"段。
4. **report 扩段是否属 Phase 5**。路线图 §8 report tests 标 "5/8"(Phase 5 或 8)。**本 Phase 归置:与 evidence_level/learning_queue 直接相关的两段("证据记录"/"验证计划")属 Phase 5**(因数据源是本 Phase 新产出的 provenance 键);Phase 8 的 report 扩容(网站发行相关的其他段)留 Phase 8。故本 Phase report 扩段只加这两段 + 相应测试,不做 Phase 8 的全面扩容。

---

## EvidenceLevel(E0–E5)是否归 Phase 5 的判断(与理由)

**判断:EvidenceLevelAgent(E0–E5,插点 C)归 Phase 5,与 ActiveLearning 一起落地。**

**理由(按依赖 + 红线合理归置):**
1. **信号同源**:E0–E5 映射读的是运行时 `reliability_decision`(reliability/abstain/disagreement/downgrade)+ `learned_reliability`(reliability_score/abstain_decision/fallback)+ OOD proxy(seen_in_train/caution_flags)——这些正是 ActiveLearning 算 information gain 要读的同一批信号。两者共用信号解析层,分开做会重复解析、增维护面。
2. **证据链耦合**:learning_queue 用 E-level 排序候选(证据等级越低 = information gain 越高 = 越该优先测)。E-level 是 AL 的排序输入之一,先有 E-level 再有 AL 的合理排序,一起做逻辑闭环。
3. **前置 Phase 明确留后**:Phase 3 计划将 E-level 留"Phase 4/5";Phase 4 计划插点归置决策明确"归 Phase 5(与主动学习一起)";`module_consistency.py:10` 源码注释亦写"留 Phase 4/5;那时管线带 reliability/OOD 信号"。管线现在(Phase 4 后)已带这些信号,时机成熟。
4. **红线不越界**:E-level 是"治理层之上的薄映射"(决策 B),**不重写治理、不回写 verdict**——与 AL 的"advisory 不改裁决"同性质(都是读信号出 advisory 挂 provenance),归一个 Phase、共用一套"不碰裁决"的契约测试,红线守得更干净。

**边界**:E-level **只映射不裁决**(不回写 `report.verdict`/`report.reliability`/`report.abstain`);其"accept 级"与现有 disposition 对齐、不领先(决策 B)。它是 AL 排序的输入 + report"证据记录"段的数据源,不是新的治理引擎。

---

## EvidenceLevel E0–E5 映射契约(决策 B:治理层之上的薄映射,不重写治理)

**E0–E5 语义(读现有信号映射,不新增裁决):**

| 等级 | 语义 | 触发条件(读现有信号,fail-closed 保守) |
|---|---|---|
| **E0** | 无证据 / 拒绝 | `report.abstain=True` 且 abstain_reasons 含硬拒(species_not_supported / all_predictors_rejected / no_perturbation_specified);或 module_plan.overall_verdict ∈ {reject} |
| **E1** | 弃权 / 极弱 | `report.abstain=True`(其余 abstain);或无 models_used |
| **E2** | in-domain 匹配 → accept(**与现有 disposition 对齐**) | 非 abstain、无 downgrade_reasons、`reliability="high"` 且 OOD in-domain(`seen_in_train=True`)且 disagreement 未触发 —— 这是决策 B 的"E2=匹配扰动数据 in-domain→accept" |
| **E3** | accept 但有 caution(跨物种/ortholog/OOD 未知) | 非 abstain、无 downgrade、`reliability ∈ {high, medium}` 但 OOD 未知(seen_in_train=None)或有 caution_flags 或非母种 |
| **E4** | downgrade(可靠性降级) | 非 abstain 但有 downgrade_reasons(model_disagreement/cell_type_not_supported/learned_low_reliability) |
| **E5** | 高不确定 / learned fallback / 强分歧未 abstain | disagreement triggered 且未 abstain、或 learned fallback、或 reliability="low" 非 abstain |

> **注**:表按"从 E0(最弱)到 E5(最不确定但仍出预测)"排,**不是线性 accept 强度**——E2/E3 是 accept 级(证据充分度递减),E4/E5 是降级/高不确定级。映射函数按**保守优先**:命中多个条件时取"证据最弱/最不确定"的等级(fail-closed)。**关键红线守卫**:E2(accept 级)**只在现有 disposition 已 accept(非 abstain、无 downgrade)时可能给出**——即 E-level 不得把 abstain/downgrade 的请求映射成 E2/E3 accept 级(不领先于治理,决策 B)。

**`governance/evidence_level.py`(纯函数,不进 bus、无 LLM 依赖):**
- `derive_ood_signal(report) -> str`:读 `seen_in_train`(优先)→ `"in_domain"`/`"ood"`/`"unknown"`;None 时看 `caution_flags` 含 ortholog/cross-species 或 `species != human` → `"unknown"`(不假装 in_domain,红线 6)。
- `map_evidence_level(report) -> dict`:按上表映射,返回 `{"level": "E0".."E5", "rationale": [信号串], "ood_signal": "...", "aligned_with_disposition": bool}`。`aligned_with_disposition` 钉死"E-level 未领先治理"(E2/E3 时现有 disposition 必须已 accept)。
- **不回写 verdict**:函数只**读** report,返回新 dict,不 mutate report。

**`agents/evidence_level_agent.py:EvidenceLevelAgent`(进 bus,薄包装):**
- `name = "EvidenceLevelAgent"`。
- `handle`:读 `payload["report"]` → `map_evidence_level(report)` → emit `evidence_level_ready` payload `{evidence_level: {...}}`,receiver="ActiveLearningAgent"。
- **红线**:只出 evidence_level dict(挂 provenance),不改 report 任何键。

---

## ActiveLearning + learning_queue 契约设计(信号来源 / 排序 / 如何守"不碰裁决")

**learning_queue 语义**:主动学习产"**该测什么**"的优先队列(advisory 规划产物),用 disagreement/OOD/证据等级/module 弱支持算 **information gain** 排序。它是**建议下一步实验**,**绝不碰 prediction/verdict 终决/provenance ledger/reliability 决策**(红线:主动学习不改裁决)。

**信号来源(全来自管线已产出、v0.8 已有的确定性信号)**:
1. **disagreement**:`report.model_disagreement.score`(vs threshold;triggered)—— 分歧越高 → information gain 越高。
2. **OOD**:`derive_ood_signal(report)` —— OOD/unknown → information gain 高(未见扰动最该测);in_domain → 低。
3. **证据等级**:`evidence_level.level` —— E4/E5(降级/高不确定)> E3(caution)> E1/E0(abstain,不产候选,已弃权无需"再测")> E2(in-domain accept,gain 最低)。
4. **module 弱支持 / data_gated**:`module_plan.entries` 里 `species_support ∈ {weak, unsupported}` 或 `data_gated=True` 的模块 —— 弱支持模块该补数据。

**acquisition(纯函数,`active_learning/acquisition.py`)**:
- `information_gain(signals) -> float`:确定性加权(disagreement 权重 + ood 权重 + evidence 权重 + module_weakness 权重),**可复现、无随机**。权重是常量(见实现),不引入学习/随机。
- **诚实**:information_gain 是**启发式优先级分**(deterministic heuristic),**不是**贝叶斯期望信息增益的真实计算 —— docstring 明确标注"v1 启发式排序,非严格 EIG";避免过度承诺(路线图诚实红线)。

**learning_queue(数据结构,`active_learning/learning_queue.py`)**:
- `LearningQueueItem`(dataclass):`{candidate: str(该测什么,如 "genetic_hub@human:AHR"), module: str, information_gain: float, drivers: list[str](哪些信号驱动:disagreement_high/ood_unknown/evidence_E4/module_weak), rationale: str}`。
- `LearningQueue`(dataclass):`{items: list[LearningQueueItem](按 information_gain 降序), notes: list[str]}`;`to_dict()`。
- 构造即按 information_gain 降序;空候选 → 空 items + note(红线 6,不虚构)。

**`active_learning/active_learning_agent.py:ActiveLearningAgent`(进 bus)**:
- `name = "ActiveLearningAgent"`。
- `handle`:读 `payload["report"]` + `payload.get("evidence_level")` + `report.provenance.get("module_plan")` → 从 module_plan.entries + report 信号派生候选 → 每候选算 `information_gain` → 组装 `LearningQueue`(降序)→ emit `learning_queue_ready` payload `{learning_queue: queue.to_dict()}`,receiver="client"。
- **红线守卫(不碰裁决)**:agent 只**读** report/evidence_level,**只 emit learning_queue**;不改 `report.abstain`/`reliability`/`prediction`/`provenance` 里任何现有键、不新增 provenance ledger 条目、不回写 verdict。abstain 的请求(E0/E1)→ 候选来自 module_plan 的弱模块(建议"补哪个模块的数据"),但**不把 abstain 改 accept**。**专门契约测试**钉死:跑 AL 前后 `report` 的 abstain/reliability/prediction 逐字节不变。

**转 AgentMessage 链**:Report 产 report → EvidenceLevelAgent 读它出 `evidence_level_ready`(AgentMessage)→ ActiveLearningAgent 读 report+evidence_level 出 `learning_queue_ready`(AgentMessage)→ runtime sidecar 挂 `report.provenance.evidence_level` / `report.provenance.learning_queue`。全程 bus 消息,advisory,不进 prediction/裁决。

---

## 接 runtime 管线的方案(插点 C/D 位置 + OFFLINE 字节等价怎么保证)

- **插点 C(EvidenceLevel)+ 插点 D(ActiveLearning)接在 Report 之后的 sidecar 挂载段**(`runtime.py:99` 组装 `report` 之后、`llm_route_suggestion`/`module_plan` 挂载附近),复刻 Phase 4 已确立的 sidecar 惯例(`report.setdefault("provenance", {})["X"] = ...`,gated by `if "AgentName" in self._agents`)。理由:E-level/AL 读的是**已组装完成的 report**(含 reliability/abstain/disagreement/downgrade/caution_flags/learned_reliability/module_plan)——Report 之后是这些信号全齐的最早时机。放这里既拿到全部信号,又**完全不碰** predictor fan-out/ensemble/reliability/critic/provenance 的输入契约(零回归风险)。
- **顺序**:先 C(EvidenceLevel,产 evidence_level)再 D(ActiveLearning,读 report + evidence_level 产 learning_queue)。两者都把产物 sidecar 挂进 `report.provenance`。
- **OFFLINE 字节等价怎么保证**:
  1. 两 agent 是**确定性零 LLM 节点**(不 import agents_llm/llm_orchestration,只读 report dict 字段做映射/排序),故 OFFLINE 也注册(与 Phase 4 SpeciesContext/ModuleRouter 同惯例)。它们**只往 `report.provenance` 追加 `evidence_level`/`learning_queue` 两个新键**,不动任何现有 provenance 键、不动 `report` 顶层任何键、不碰 prediction/裁决。
  2. runtime 插点 gated by `if "EvidenceLevelAgent" in self._agents`;若未注册(如直接构造裸 runtime 的单测),分支不进,`report` 与现在字节等价。
  3. 现有 report 输出对比:Phase 5 前 `report.provenance` 无 `evidence_level`/`learning_queue` 键;Phase 5 后多这两键。**这是可见的新增**(v1.2 交付"证据等级 + 验证计划进 provenance 可见")。现有严格断言 provenance 键集的测试(应是宽松 `in`/`>=`)不受影响;若某测试严格断言 provenance **恰好只有旧键集** → 那是过严测试,停下报告(红线 5,不改核心逻辑迁就)。**执行者在 Task 5.6 全量回归时特别核对**现有 e2e/report 测试是否严格键集断言。
  4. `run_virtualcell_query.run_query`(实读 `run_virtualcell_query.py:163`)返回的 `provenance = report.get("provenance", {})` 自动带上新键,服务层无需改。

---

# Phase 5:主动学习 v1 · 任务

## Task 5.1:evidence_level 纯函数 `governance/evidence_level.py`(E0–E5 映射,决策 B)

**决策说明:** 先落 E0–E5 映射内核(纯函数,不进 bus、无 LLM 依赖):`derive_ood_signal`(runtime OOD proxy,fail-closed)+ `map_evidence_level`(读现有 report 信号映射 E0–E5,不回写 verdict,E2/E3 accept 级只在现有 disposition 已 accept 时给出 —— 决策 B 不领先治理)。先建映射,后续 task 的 agent/AL 调它。

**Files:**
- Create: `praxis_virtualcell/governance/evidence_level.py`
- Test: `praxis_virtualcell/tests/test_evidence_level.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_evidence_level.py`:

```python
"""Phase 5:evidence_level —— E0–E5 映射(纯函数,零 LLM)。
决策 B:治理层之上的薄映射,不重写治理、不回写 verdict;E2/E3 accept 级只在现有 disposition
已 accept 时给出(不领先治理);OOD 未知 fail-closed 记 unknown(红线 6)。"""
from praxis_virtualcell.governance import evidence_level as EL


def _report(**kw):
    base = {"abstain": False, "reliability": "high", "prediction": {"delta": [0.3]},
            "models_used": ["MockLinear", "MockCPA"], "abstain_reasons": [],
            "downgrade_reasons": [], "model_disagreement": {"score": 0.2, "triggered": False},
            "caution_flags": {}, "learned_reliability": None,
            "request": {"species": "human"}, "seen_in_train": True,
            "provenance": {}}
    base.update(kw)
    return base


def test_ood_signal_in_domain():
    assert EL.derive_ood_signal(_report(seen_in_train=True)) == "in_domain"


def test_ood_signal_ood():
    assert EL.derive_ood_signal(_report(seen_in_train=False)) == "ood"


def test_ood_signal_unknown_when_none_and_human_no_caution():
    # seen_in_train=None + human + 无 caution → 仍 unknown(runtime seen_in_train 多 None,不假装 in_domain)
    assert EL.derive_ood_signal(_report(seen_in_train=None)) == "unknown"


def test_ood_signal_unknown_when_cross_species():
    r = _report(seen_in_train=None, request={"species": "mouse"})
    assert EL.derive_ood_signal(r) == "unknown"


def test_e2_in_domain_accept():
    """E2:非 abstain、无 downgrade、high、in_domain、disagreement 未触发 → E2(与 disposition accept 对齐)。"""
    out = EL.map_evidence_level(_report(seen_in_train=True))
    assert out["level"] == "E2"
    assert out["ood_signal"] == "in_domain"
    assert out["aligned_with_disposition"] is True


def test_e3_accept_with_caution_or_unknown_ood():
    """E3:accept 但 OOD 未知/有 caution/非母种。"""
    out = EL.map_evidence_level(_report(seen_in_train=None, reliability="high"))
    assert out["level"] == "E3"


def test_e4_downgrade():
    out = EL.map_evidence_level(_report(reliability="medium",
                                        downgrade_reasons=["downgrade:model_disagreement_too_high"]))
    assert out["level"] == "E4"


def test_e5_disagreement_triggered_not_abstain():
    out = EL.map_evidence_level(_report(reliability="low",
                                        model_disagreement={"score": 0.9, "triggered": True}))
    assert out["level"] == "E5"


def test_e5_learned_fallback():
    out = EL.map_evidence_level(_report(reliability="low",
                                        learned_reliability={"fallback": True}))
    assert out["level"] == "E5"


def test_e1_abstain():
    out = EL.map_evidence_level(_report(abstain=True, prediction=None, models_used=[],
                                        abstain_reasons=["model_disagreement_too_high"]))
    assert out["level"] == "E1"


def test_e0_hard_reject():
    out = EL.map_evidence_level(_report(abstain=True, prediction=None, models_used=[],
                                        abstain_reasons=["species_not_supported"]))
    assert out["level"] == "E0"


def test_e_level_does_not_lead_disposition():
    """红线/决策 B:downgrade 请求不得被映射成 E2/E3 accept 级。"""
    out = EL.map_evidence_level(_report(seen_in_train=True, reliability="high",
                                        downgrade_reasons=["downgrade:cell_type_not_supported"]))
    assert out["level"] in ("E4", "E5")   # 有 downgrade → 不得 E2/E3
    assert out["aligned_with_disposition"] is True


def test_map_does_not_mutate_report():
    """不回写:map 只读不改 report。"""
    r = _report()
    snap = dict(r)
    EL.map_evidence_level(r)
    assert r == snap
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_evidence_level.py -q`
Expected: FAIL(ModuleNotFoundError: praxis_virtualcell.governance.evidence_level)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/governance/evidence_level.py`:

```python
"""evidence_level:E0–E5 证据等级映射(治理层之上的薄映射,纯函数,零 LLM/bus 依赖)。

决策 B(路线图 §6-B):证据等级读现有 reliability/OOD/disagreement/learned 信号映射 E0–E5,
**不重写治理、不回写 verdict**;E2=匹配扰动数据 in-domain→accept **与现有 disposition 对齐**
(不领先治理:abstain/downgrade 请求不得映射成 E2/E3 accept 级)。

runtime OOD 真实情况(实读 reliability.py:136):seen_in_train 多为 None → OOD proxy fail-closed
退回 caution_flags/非母种代理,None 时记 unknown(不假装 in_domain,红线 6)。
"""
from __future__ import annotations

# 硬拒 abstain 原因(→ E0)
_HARD_REJECT = {"species_not_supported", "all_predictors_rejected",
                "no_perturbation_specified", "no_successful_predictor"}
# 提示跨物种/OOD 的 caution flag 关键词
_OOD_CAUTION_KEYS = ("ortholog", "cross_species", "cross-species", "projected")


def derive_ood_signal(report: dict) -> str:
    """runtime OOD 信号:in_domain / ood / unknown。
    seen_in_train 优先(True=in_domain,False=ood);None → 看 caution/物种 → unknown(不假装 in_domain)。"""
    seen = report.get("seen_in_train")
    if seen in (True, 1):
        return "in_domain"
    if seen in (False, 0):
        return "ood"
    # None:runtime 常态 → 保守 unknown(即使 human 无 caution 也不当 in_domain)
    return "unknown"


def _has_ood_caution(report: dict) -> bool:
    flags = report.get("caution_flags") or {}
    blob = " ".join(str(v).lower() for v in flags.values())
    if any(k in blob for k in _OOD_CAUTION_KEYS):
        return True
    species = str((report.get("request") or {}).get("species", "")).lower()
    return bool(species) and species != "human"


def map_evidence_level(report: dict) -> dict:
    """读 report 现有信号 → E0–E5(保守优先,不回写 verdict)。返回新 dict,不 mutate report。"""
    abstain = bool(report.get("abstain"))
    reliability = report.get("reliability")
    downgrade = list(report.get("downgrade_reasons") or [])
    abstain_reasons = list(report.get("abstain_reasons") or [])
    dis = report.get("model_disagreement") or {}
    dis_triggered = bool(dis.get("triggered"))
    learned = report.get("learned_reliability") or {}
    learned_fallback = bool(learned.get("fallback"))
    ood = derive_ood_signal(report)
    rationale: list[str] = []

    # abstain 分支(E0/E1)
    if abstain:
        if any(r in _HARD_REJECT for r in abstain_reasons):
            rationale.append("hard_reject_abstain")
            level = "E0"
        else:
            rationale.append("abstain")
            level = "E1"
        return {"level": level, "rationale": rationale, "ood_signal": ood,
                "aligned_with_disposition": True}

    # 非 abstain:先处理降级/高不确定(E4/E5,不得被抬成 accept 级)
    if dis_triggered:
        rationale.append("disagreement_triggered")
    if learned_fallback:
        rationale.append("learned_fallback")
    if downgrade:
        rationale.append("downgrade")

    if dis_triggered or learned_fallback or reliability == "low":
        # 强分歧未 abstain / learned 退回 / 低可靠 → 最不确定的 accept 级
        rationale.append("high_uncertainty")
        level = "E5"
    elif downgrade:
        level = "E4"
    else:
        # accept 级(E2/E3):现有 disposition 已 accept(非 abstain、无 downgrade)
        if ood == "in_domain" and not _has_ood_caution(report) and reliability == "high":
            rationale.append("in_domain_high_reliability")
            level = "E2"
        else:
            rationale.append("accept_with_caution_or_unknown_ood")
            level = "E3"
    return {"level": level, "rationale": rationale, "ood_signal": ood,
            "aligned_with_disposition": True}
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_evidence_level.py -q`
Expected: 13 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 522 passed / 25 skipped / 0 failed(509 + 13 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/governance/evidence_level.py praxis_virtualcell/tests/test_evidence_level.py
git commit -m "feat(phase5): evidence_level E0–E5 映射内核(读现有 reliability/OOD/disagreement/learned 信号,不重写治理、不回写 verdict,决策 B)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5.2:EvidenceLevelAgent `agents/evidence_level_agent.py`(进 bus,薄包装)

**决策说明:** `EvidenceLevelAgent` extends `BaseAgent` 进 bus,薄包装 `map_evidence_level`。收 `evidence_level_request`(payload `{report}`)→ `map_evidence_level(report)` → emit `evidence_level_ready`(receiver="ActiveLearningAgent")。**只读 report、只出 evidence_level dict,不改 report 任何键**(红线 2)。

**Files:**
- Create: `praxis_virtualcell/agents/evidence_level_agent.py`
- Test: `praxis_virtualcell/tests/test_evidence_level_agent.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_evidence_level_agent.py`:

```python
"""Phase 5:EvidenceLevelAgent(进 bus,薄包装 map_evidence_level)。
红线:只出 evidence_level_ready,不改 report 任何键。"""
from praxis_virtualcell.agents.evidence_level_agent import EvidenceLevelAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _report(**kw):
    base = {"abstain": False, "reliability": "high", "prediction": {"delta": [0.3]},
            "models_used": ["MockLinear"], "abstain_reasons": [], "downgrade_reasons": [],
            "model_disagreement": {"score": 0.2, "triggered": False}, "caution_flags": {},
            "learned_reliability": None, "request": {"species": "human"},
            "seen_in_train": True, "provenance": {}}
    base.update(kw)
    return base


def _run(report):
    bus = MessageBus()
    EvidenceLevelAgent().handle(AgentMessage(
        message_id="c1", sender="Report", receiver="EvidenceLevelAgent",
        message_type="evidence_level_request", payload={"report": report},
        timestamp="t1"), bus)
    return bus.latest("evidence_level_ready")


def test_emits_evidence_level_ready():
    msg = _run(_report())
    assert msg is not None
    assert msg.message_type == "evidence_level_ready"
    assert msg.receiver == "ActiveLearningAgent"
    assert msg.payload["evidence_level"]["level"] == "E2"


def test_agent_does_not_mutate_report():
    r = _report()
    snap = dict(r)
    _run(r)
    assert r == snap                      # 只读,不改 report


def test_downgrade_report_maps_e4_or_e5():
    msg = _run(_report(reliability="medium",
                       downgrade_reasons=["downgrade:model_disagreement_too_high"]))
    assert msg.payload["evidence_level"]["level"] in ("E4", "E5")


def test_abstain_report_maps_e0_or_e1():
    msg = _run(_report(abstain=True, prediction=None, models_used=[],
                       abstain_reasons=["species_not_supported"]))
    assert msg.payload["evidence_level"]["level"] == "E0"


def test_no_llm_import_in_module():
    import praxis_virtualcell.agents.evidence_level_agent as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_client" not in src
    assert "llm_orchestration" not in src
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_evidence_level_agent.py -q`
Expected: FAIL(ModuleNotFoundError: ...evidence_level_agent)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/agents/evidence_level_agent.py`:

```python
"""EvidenceLevelAgent(插点 C,进 message bus):薄包装 governance.evidence_level.map_evidence_level。

收 evidence_level_request({report})→ map_evidence_level(report) → emit evidence_level_ready
(交 ActiveLearningAgent)。铁律:只读 report、只出 evidence_level dict(挂 provenance),
不改 report 任何键、不回写 verdict(决策 B:治理层之上的薄映射)。零 LLM。
"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.governance.evidence_level import map_evidence_level


class EvidenceLevelAgent(BaseAgent):
    name = "EvidenceLevelAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload.get("report", {}) or {}
        ev = map_evidence_level(report)
        bus.send(AgentMessage(
            message_id=message.message_id + ":evlvl",
            sender=self.name, receiver="ActiveLearningAgent",
            message_type="evidence_level_ready",
            payload={"evidence_level": ev},
            timestamp=message.timestamp, parent_message_id=message.message_id))
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_evidence_level_agent.py -q`
Expected: 5 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 527 passed / 25 skipped / 0 failed(522 + 5 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/agents/evidence_level_agent.py praxis_virtualcell/tests/test_evidence_level_agent.py
git commit -m "feat(phase5): EvidenceLevelAgent(进 bus 薄包装 map_evidence_level,只读 report 出 evidence_level_ready,不改裁决)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5.3:acquisition 纯函数 `active_learning/acquisition.py`(information gain 启发式)

**决策说明:** 先落 information gain 打分内核(纯函数,不进 bus、无 LLM):`information_gain(signals)` 确定性加权(disagreement/OOD/evidence/module_weakness),可复现无随机。**诚实标注:v1 启发式优先级分,非严格 EIG**(避免过度承诺)。同时建 `active_learning/__init__.py` 空包。

**Files:**
- Create: `praxis_virtualcell/active_learning/__init__.py`
- Create: `praxis_virtualcell/active_learning/acquisition.py`
- Test: `praxis_virtualcell/tests/test_acquisition.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_acquisition.py`:

```python
"""Phase 5:acquisition —— information gain 启发式(纯函数,确定性,零 LLM/随机)。
诚实:v1 启发式优先级分,非严格 EIG。disagreement/OOD/evidence 越差 → gain 越高。"""
from praxis_virtualcell.active_learning import acquisition as AQ


def test_high_disagreement_higher_gain():
    lo = AQ.information_gain({"disagreement_score": 0.1, "disagreement_triggered": False,
                              "ood_signal": "in_domain", "evidence_level": "E2",
                              "module_weak": False})
    hi = AQ.information_gain({"disagreement_score": 0.9, "disagreement_triggered": True,
                              "ood_signal": "in_domain", "evidence_level": "E2",
                              "module_weak": False})
    assert hi > lo


def test_ood_higher_than_in_domain():
    ind = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": False})
    ood = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "ood", "evidence_level": "E2", "module_weak": False})
    assert ood > ind


def test_unknown_ood_between_or_above_in_domain():
    ind = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": False})
    unk = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "unknown", "evidence_level": "E2", "module_weak": False})
    assert unk > ind                      # 未知 OOD 比 in_domain 更值得测


def test_worse_evidence_higher_gain():
    e2 = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                             "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": False})
    e5 = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                             "ood_signal": "in_domain", "evidence_level": "E5", "module_weak": False})
    assert e5 > e2


def test_module_weak_adds_gain():
    strong = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                                 "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": False})
    weak = AQ.information_gain({"disagreement_score": 0.2, "disagreement_triggered": False,
                              "ood_signal": "in_domain", "evidence_level": "E2", "module_weak": True})
    assert weak > strong


def test_deterministic_reproducible():
    s = {"disagreement_score": 0.5, "disagreement_triggered": True, "ood_signal": "ood",
         "evidence_level": "E4", "module_weak": True}
    assert AQ.information_gain(s) == AQ.information_gain(s)


def test_missing_signals_fail_safe_zero_base():
    # 全缺 → 不崩,返回有限 float(不 NaN)
    g = AQ.information_gain({})
    assert isinstance(g, float)
    assert g == g                          # 非 NaN
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_acquisition.py -q`
Expected: FAIL(ModuleNotFoundError: praxis_virtualcell.active_learning)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/active_learning/__init__.py`:

```python
"""主动学习子包(Phase 5,v1.2):acquisition(information gain 启发式)+ learning_queue(优先队列)
+ ActiveLearningAgent(进 bus,产 learning_queue)。

铁律:主动学习产"该测什么"的 advisory 优先队列,用现有 disagreement/OOD/证据等级/module 弱支持
信号(v0.8 已有,确定性零 LLM)排序;**绝不碰 prediction/verdict 终决/provenance ledger/reliability
决策**(不改裁决,只建议下一步实验)。OFFLINE 默认零 LLM,本子包不 import agents_llm/llm_orchestration。
"""
```

写 `praxis_virtualcell/active_learning/acquisition.py`:

```python
"""acquisition:information gain 启发式优先级分(纯函数,确定性,零 LLM/随机)。

诚实(避免过度承诺):这是 **v1 启发式优先级分**(deterministic heuristic),**不是**贝叶斯期望
信息增益(EIG)的严格计算。用现有确定性信号加权:分歧越高、越 OOD、证据越弱、模块越弱 → 越该优先测。
可复现(无 wall-clock/随机),缺信号 fail-safe 到 0 基线(不崩、不 NaN)。
"""
from __future__ import annotations

# 权重常量(确定性;调参留 v1.2.x,当前为可解释的等权量级)
_W_DISAGREEMENT = 1.0
_W_DIS_TRIGGERED = 0.5
_W_OOD = {"ood": 1.0, "unknown": 0.6, "in_domain": 0.0}
# 证据等级 → gain 贡献(E2 最低=最该少测,E5 最高=最该测;E0/E1 abstain 由 agent 侧决定是否入队)
_W_EVIDENCE = {"E0": 0.2, "E1": 0.3, "E2": 0.0, "E3": 0.4, "E4": 0.8, "E5": 1.0}
_W_MODULE_WEAK = 0.5


def information_gain(signals: dict) -> float:
    """确定性加权。signals 键(全可选,缺则 fail-safe 到 0 贡献):
    disagreement_score(float)、disagreement_triggered(bool)、ood_signal(str)、
    evidence_level(str E0..E5)、module_weak(bool)。"""
    dis = signals.get("disagreement_score")
    dis = float(dis) if isinstance(dis, (int, float)) else 0.0
    g = _W_DISAGREEMENT * max(0.0, min(1.0, dis))
    if signals.get("disagreement_triggered"):
        g += _W_DIS_TRIGGERED
    g += _W_OOD.get(str(signals.get("ood_signal", "")), 0.0)
    g += _W_EVIDENCE.get(str(signals.get("evidence_level", "")), 0.0)
    if signals.get("module_weak"):
        g += _W_MODULE_WEAK
    return round(g, 6)
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_acquisition.py -q`
Expected: 7 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 534 passed / 25 skipped / 0 failed(527 + 7 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/active_learning/__init__.py praxis_virtualcell/active_learning/acquisition.py praxis_virtualcell/tests/test_acquisition.py
git commit -m "feat(phase5): active_learning 子包 + acquisition information gain 启发式(确定性加权 disagreement/OOD/evidence/module,诚实标注非严格 EIG)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5.4:learning_queue 数据结构 `active_learning/learning_queue.py`

**决策说明:** 落 learning_queue 数据结构(纯 dataclass,可序列化):`LearningQueueItem`(候选 + information_gain + drivers + rationale)+ `LearningQueue`(items 按 information_gain 降序 + notes + to_dict)。构造即排序;空候选 → 空 items + note(红线 6 不虚构)。

**Files:**
- Create: `praxis_virtualcell/active_learning/learning_queue.py`
- Test: `praxis_virtualcell/tests/test_learning_queue.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_learning_queue.py`:

```python
"""Phase 5:learning_queue 数据结构。items 按 information_gain 降序;空候选 → 空 + note(不虚构);
to_dict 可序列化。advisory 规划产物,不碰裁决。"""
from praxis_virtualcell.active_learning.learning_queue import LearningQueue, LearningQueueItem


def _item(cand, gain, module="genetic_hub"):
    return LearningQueueItem(candidate=cand, module=module, information_gain=gain,
                             drivers=["disagreement_high"], rationale="x")


def test_items_sorted_by_gain_desc():
    q = LearningQueue(items=[_item("a", 0.3), _item("b", 0.9), _item("c", 0.6)])
    gains = [it.information_gain for it in q.items]
    assert gains == sorted(gains, reverse=True)
    assert q.items[0].candidate == "b"


def test_empty_queue_has_note_not_fabricated():
    q = LearningQueue(items=[], notes=["no_actionable_candidates"])
    assert q.items == []
    assert "no_actionable_candidates" in q.notes


def test_to_dict_serializable():
    q = LearningQueue(items=[_item("a", 0.9)], notes=["n1"])
    d = q.to_dict()
    assert d["items"][0]["candidate"] == "a"
    assert d["items"][0]["information_gain"] == 0.9
    assert d["items"][0]["drivers"] == ["disagreement_high"]
    assert d["notes"] == ["n1"]
    import json
    json.dumps(d)                          # 可 JSON 序列化(挂 provenance 需要)


def test_item_to_dict_keys():
    d = _item("a", 0.5).to_dict()
    assert set(d) == {"candidate", "module", "information_gain", "drivers", "rationale"}


def test_stable_order_for_equal_gain():
    """等 gain 保持稳定序(可复现)。"""
    q1 = LearningQueue(items=[_item("a", 0.5, "genetic_hub"), _item("b", 0.5, "stress_processor")])
    q2 = LearningQueue(items=[_item("a", 0.5, "genetic_hub"), _item("b", 0.5, "stress_processor")])
    assert [it.candidate for it in q1.items] == [it.candidate for it in q2.items]
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_learning_queue.py -q`
Expected: FAIL(ModuleNotFoundError: ...learning_queue)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/active_learning/learning_queue.py`:

```python
"""learning_queue:主动学习的"该测什么"优先队列(纯数据结构,可序列化,零 LLM/bus 依赖)。

advisory 规划产物 —— 建议下一步实验,**不碰 prediction/verdict 终决/provenance ledger/裁决**。
items 按 information_gain 降序(等 gain 保持插入序,可复现);空候选 → 空 items + note(不虚构实验)。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class LearningQueueItem:
    candidate: str                 # 该测什么(如 "genetic_hub@human:AHR")
    module: str                    # 归属模块(MODULE_ORDER 之一)
    information_gain: float        # acquisition.information_gain 打分
    drivers: list[str] = field(default_factory=list)   # 驱动信号(disagreement_high/ood_unknown/evidence_E4/module_weak)
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LearningQueue:
    items: list[LearningQueueItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # 按 information_gain 降序;等 gain 用负号保持稳定插入序(Python sort 稳定)
        self.items = sorted(self.items, key=lambda it: it.information_gain, reverse=True)

    def to_dict(self) -> dict:
        return {"items": [it.to_dict() for it in self.items], "notes": list(self.notes)}
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_learning_queue.py -q`
Expected: 5 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 539 passed / 25 skipped / 0 failed(534 + 5 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/active_learning/learning_queue.py praxis_virtualcell/tests/test_learning_queue.py
git commit -m "feat(phase5): learning_queue 数据结构(items 按 information_gain 降序 + notes + to_dict,空候选不虚构)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5.5:ActiveLearningAgent `active_learning/active_learning_agent.py`(进 bus,产 learning_queue)

**决策说明:** `ActiveLearningAgent` extends `BaseAgent` 进 bus。收 `learning_queue_request`(payload `{report, evidence_level}`)→ 从 `report.provenance.module_plan.entries` + report 信号派生候选(每个 module 一个候选,弱/gated/降级模块 information_gain 高)→ 算 `information_gain` → 组装 `LearningQueue`(降序)→ emit `learning_queue_ready`。**只读、只 emit learning_queue,不改 report 任何键**(红线 2:不碰裁决)。

**Files:**
- Create: `praxis_virtualcell/active_learning/active_learning_agent.py`
- Test: `praxis_virtualcell/tests/test_active_learning_agent.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_active_learning_agent.py`:

```python
"""Phase 5:ActiveLearningAgent(进 bus,产 learning_queue)。
红线:advisory 不碰裁决 —— 只读 report/evidence_level,只 emit learning_queue_ready,不改 report。
learning_queue 用 disagreement/OOD/evidence/module 弱支持排序(information gain 降序)。"""
from praxis_virtualcell.active_learning.active_learning_agent import ActiveLearningAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _module_plan(entries=None):
    entries = entries or [
        {"module": "genetic_hub", "role": "primary", "species_support": "strong",
         "verdict": "accept", "data_gated": False},
        {"module": "stress_processor", "role": "secondary", "species_support": "weak",
         "verdict": "caution", "data_gated": True},
    ]
    return {"species": "human", "primary": "genetic_hub",
            "secondary": ["stress_processor"], "overall_verdict": "caution", "entries": entries}


def _report(**kw):
    base = {"abstain": False, "reliability": "high", "prediction": {"delta": [0.3]},
            "models_used": ["MockLinear"], "abstain_reasons": [], "downgrade_reasons": [],
            "model_disagreement": {"score": 0.3, "triggered": False}, "caution_flags": {},
            "learned_reliability": None, "request": {"species": "human",
                                                     "perturbation_targets": ["AHR"]},
            "seen_in_train": True,
            "provenance": {"module_plan": _module_plan()}}
    base.update(kw)
    return base


def _run(report, evidence_level=None):
    bus = MessageBus()
    ActiveLearningAgent().handle(AgentMessage(
        message_id="c1", sender="EvidenceLevelAgent", receiver="ActiveLearningAgent",
        message_type="learning_queue_request",
        payload={"report": report, "evidence_level": evidence_level or {"level": "E3"}},
        timestamp="t1"), bus)
    return bus.latest("learning_queue_ready")


def test_emits_learning_queue_ready():
    msg = _run(_report())
    assert msg is not None
    assert msg.message_type == "learning_queue_ready"
    assert msg.receiver == "client"
    q = msg.payload["learning_queue"]
    assert "items" in q and "notes" in q


def test_weak_gated_module_ranks_higher():
    """弱支持 + data_gated 的 stress_processor 该排在 strong genetic_hub 之前(information gain 高)。"""
    msg = _run(_report())
    items = msg.payload["learning_queue"]["items"]
    mods = [it["module"] for it in items]
    assert "stress_processor" in mods and "genetic_hub" in mods
    assert mods.index("stress_processor") < mods.index("genetic_hub")


def test_does_not_mutate_report():
    """红线:AL 不碰裁决 —— 跑前后 report 逐键不变。"""
    r = _report()
    snap = {"abstain": r["abstain"], "reliability": r["reliability"],
            "prediction": dict(r["prediction"]), "provenance_keys": set(r["provenance"])}
    _run(r)
    assert r["abstain"] == snap["abstain"]
    assert r["reliability"] == snap["reliability"]
    assert r["prediction"] == snap["prediction"]
    assert set(r["provenance"]) == snap["provenance_keys"]   # AL 不往 report.provenance 塞键(由 runtime sidecar 挂)


def test_abstain_report_no_fabricated_accept():
    """abstain 请求:AL 可建议补数据(候选来自弱模块),但绝不把 abstain 改 accept。"""
    r = _report(abstain=True, prediction=None, models_used=[],
                abstain_reasons=["model_disagreement_too_high"])
    msg = _run(r, evidence_level={"level": "E1"})
    assert r["abstain"] is True            # 不被改
    q = msg.payload["learning_queue"]
    assert isinstance(q["items"], list)    # 空或含"补数据"候选,不虚构 accept


def test_no_module_plan_empty_queue_with_note():
    """无 module_plan(不可路由请求)→ 空队列 + note,不崩不虚构(红线 6)。"""
    r = _report(provenance={})
    msg = _run(r)
    q = msg.payload["learning_queue"]
    assert q["items"] == []
    assert q["notes"]                      # 有 note 说明为何空


def test_high_disagreement_drives_gain():
    """分歧触发 → 相关候选 information_gain 更高 + drivers 记 disagreement。"""
    msg = _run(_report(model_disagreement={"score": 0.95, "triggered": True},
                       reliability="medium",
                       downgrade_reasons=["downgrade:model_disagreement_too_high"]),
               evidence_level={"level": "E4"})
    items = msg.payload["learning_queue"]["items"]
    assert items                           # 有候选
    drivers = [d for it in items for d in it["drivers"]]
    assert any("disagreement" in d for d in drivers)


def test_no_llm_import_in_module():
    import praxis_virtualcell.active_learning.active_learning_agent as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_client" not in src
    assert "llm_orchestration" not in src
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_active_learning_agent.py -q`
Expected: FAIL(ModuleNotFoundError: ...active_learning_agent)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/active_learning/active_learning_agent.py`:

```python
"""ActiveLearningAgent(插点 D,进 message bus):产 learning_queue(该测什么的优先队列)。

收 learning_queue_request({report, evidence_level})→ 从 report.provenance.module_plan.entries
+ report 信号(disagreement/OOD/evidence/module 弱支持)派生候选 → acquisition.information_gain
打分 → LearningQueue(降序)→ emit learning_queue_ready。

铁律(不碰裁决):只读 report/evidence_level,只 emit learning_queue;不改 report 任何键、
不回写 verdict、不新增 provenance ledger 条目。abstain 请求可建议补弱模块数据,但不把 abstain 改 accept。
无 module_plan / 无候选 → 空队列 + note(不虚构,红线 6)。零 LLM。
"""
from __future__ import annotations

from praxis_virtualcell.active_learning.acquisition import information_gain
from praxis_virtualcell.active_learning.learning_queue import LearningQueue, LearningQueueItem
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.governance.evidence_level import derive_ood_signal

# 弱支持判据(该补数据)
_WEAK_SUPPORT = {"weak", "unsupported"}


class ActiveLearningAgent(BaseAgent):
    name = "ActiveLearningAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload.get("report", {}) or {}
        ev = message.payload.get("evidence_level", {}) or {}
        ev_level = ev.get("level", "")
        plan = (report.get("provenance") or {}).get("module_plan") or {}
        entries = plan.get("entries") or []
        species = str((report.get("request") or {}).get("species", "")).lower()
        targets = [str(t).strip() for t in
                   ((report.get("request") or {}).get("perturbation_targets") or []) if str(t).strip()]
        target_tag = ",".join(targets) if targets else "unspecified"

        dis = report.get("model_disagreement") or {}
        dis_score = dis.get("score")
        dis_triggered = bool(dis.get("triggered"))
        ood = derive_ood_signal(report)

        items: list[LearningQueueItem] = []
        notes: list[str] = []
        if not entries:
            notes.append("no_module_plan_no_candidates")   # 不可路由请求 → 无有意义候选(红线 6)
            queue = LearningQueue(items=[], notes=notes)
            self._emit(message, bus, queue)
            return

        for e in entries:
            mid = e.get("module")
            weak = (e.get("species_support") in _WEAK_SUPPORT) or bool(e.get("data_gated"))
            signals = {
                "disagreement_score": dis_score,
                "disagreement_triggered": dis_triggered,
                "ood_signal": ood,
                "evidence_level": ev_level,
                "module_weak": weak,
            }
            gain = information_gain(signals)
            drivers: list[str] = []
            if dis_triggered:
                drivers.append("disagreement_high")
            if ood in ("ood", "unknown"):
                drivers.append(f"ood_{ood}")
            if ev_level in ("E3", "E4", "E5"):
                drivers.append(f"evidence_{ev_level}")
            if weak:
                drivers.append("module_weak")
            items.append(LearningQueueItem(
                candidate=f"{mid}@{species}:{target_tag}",
                module=mid, information_gain=gain, drivers=drivers,
                rationale=f"module={mid} support={e.get('species_support')} "
                          f"gated={bool(e.get('data_gated'))} evidence={ev_level} ood={ood}"))
        if report.get("abstain"):
            notes.append("request_abstained_candidates_are_data_gap_suggestions")  # 不改 abstain,仅建议补数据
        queue = LearningQueue(items=items, notes=notes)
        self._emit(message, bus, queue)

    def _emit(self, message: AgentMessage, bus: MessageBus, queue: LearningQueue) -> None:
        bus.send(AgentMessage(
            message_id=message.message_id + ":alq",
            sender=self.name, receiver="client",
            message_type="learning_queue_ready",
            payload={"learning_queue": queue.to_dict()},
            timestamp=message.timestamp, parent_message_id=message.message_id))
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_active_learning_agent.py -q`
Expected: 7 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 546 passed / 25 skipped / 0 failed(539 + 7 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/active_learning/active_learning_agent.py praxis_virtualcell/tests/test_active_learning_agent.py
git commit -m "feat(phase5): ActiveLearningAgent(进 bus,从 module_plan+report 信号产 learning_queue,advisory 不碰裁决,无候选不虚构)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5.6:接管线 —— runtime 旁路挂 evidence_level + learning_queue(插点 C/D)+ build_runtime 注册

**决策说明:** 把 EvidenceLevelAgent(插点 C)+ ActiveLearningAgent(插点 D)接进 `run_workflow`,复刻 Phase 4 sidecar 惯例:Report 组装 `report` 之后,gated by `if "EvidenceLevelAgent" in self._agents` 跑 C 产 evidence_level 挂 `report.provenance.evidence_level`;再 gated by `if "ActiveLearningAgent" in self._agents` 跑 D(读 report + evidence_level)产 learning_queue 挂 `report.provenance.learning_queue`。`build_runtime` **OFFLINE 也注册两 agent**(确定性零 LLM)。OFFLINE 字节等价:只往 provenance 追加两新键,不动现有键与预测/裁决路径。

**Files:**
- Modify: `praxis_virtualcell/workflows/predict_delta_expression.py`
- Modify: `praxis_virtualcell/core/runtime.py`
- Test: `praxis_virtualcell/tests/test_runtime_active_learning.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_runtime_active_learning.py`:

```python
"""Phase 5:接管线 —— evidence_level + learning_queue 旁路挂 report.provenance(插点 C/D)。
OFFLINE 零 LLM;不改 prediction/裁决;无 evidence/AL agent 时不挂(gated)。"""
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime
from praxis_virtualcell.core.request import VirtualCellRequest

_HUMAN = {"request_id": "al_ahr", "species": "human", "cell_type": "K562",
          "perturbation_type": "gene", "perturbation_targets": ["AHR"],
          "task_type": "predict_delta_expression",
          "output_modality": "delta_expression"}


def test_offline_report_has_evidence_level_and_learning_queue():
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    prov = report["provenance"]
    assert "evidence_level" in prov
    assert prov["evidence_level"]["level"].startswith("E")
    assert "learning_queue" in prov
    assert "items" in prov["learning_queue"]


def test_offline_registers_evidence_and_al_agents_zero_llm():
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    ns = set(rt._agents)
    assert "EvidenceLevelAgent" in ns and "ActiveLearningAgent" in ns
    # OFFLINE 零 LLM:无任何 LLM 节点
    assert not any(n.startswith("LLM") for n in ns), ns


def test_evidence_level_does_not_change_prediction_or_verdict():
    """插点 C/D 不改 prediction/abstain/reliability(advisory 不碰裁决)。"""
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    # 与不接主动学习的核心字段一致性:prediction 由 ensemble 定,abstain=False(有效 human gene 请求)
    assert report["abstain"] is False
    assert report["reliability"] in ("high", "medium", "low")
    assert report["prediction"] is not None


def test_learning_queue_reads_evidence_level():
    """AL 读到 evidence_level(证据等级进 AL 排序信号)。"""
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    q = report["provenance"]["learning_queue"]
    # 有 module_plan(Phase 4 已挂)→ 有候选
    assert isinstance(q["items"], list)


def test_abstain_request_evidence_e0_e1_no_accept():
    """空 perturbation_targets → abstain → evidence E0/E1,不被抬成 accept 级。"""
    rt = build_runtime(RuntimeConfig(mode=Mode.OFFLINE))
    req = dict(_HUMAN, request_id="noab", perturbation_targets=[])
    report = rt.run_workflow(VirtualCellRequest.from_dict(req))
    assert report["abstain"] is True
    assert report["provenance"]["evidence_level"]["level"] in ("E0", "E1")
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_runtime_active_learning.py -q`
Expected: FAIL(`KeyError: 'evidence_level'` / agent 未注册)。

- [ ] **Step 3: build_runtime 注册两 agent**

在 `praxis_virtualcell/workflows/predict_delta_expression.py`。

找到(imports 区):

```python
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
```

在其后加:

```python
from praxis_virtualcell.agents.evidence_level_agent import EvidenceLevelAgent
from praxis_virtualcell.active_learning.active_learning_agent import ActiveLearningAgent
```

找到:

```python
    # Phase 4:module-aware 路由两节点(OFFLINE 也注册 → 产确定性 module_plan,零 LLM)
    for a in (SpeciesContextAgent(), ModuleRouterAgent()):
        rt.register_agent(a)
```

在其后加:

```python
    # Phase 5:证据等级 + 主动学习两节点(OFFLINE 也注册 → 确定性 advisory 产物挂 provenance,零 LLM)
    for a in (EvidenceLevelAgent(), ActiveLearningAgent()):
        rt.register_agent(a)
```

- [ ] **Step 4: runtime 加插点 C/D(sidecar 挂载)**

在 `praxis_virtualcell/core/runtime.py` 的 `run_workflow`。

找到(现有 Phase 4 sidecar 挂载段):

```python
        report = rep.payload["report"]
        if llm_route is not None:
            report.setdefault("provenance", {})["llm_route_suggestion"] = llm_route
        if module_plan is not None:
            report.setdefault("provenance", {})["module_plan"] = module_plan
        if llm_cross_module is not None:
            report.setdefault("provenance", {})["llm_cross_module_notes"] = llm_cross_module
```

在其后(`if "LLMCritic" in self._agents:` 之前)插入:

```python
        # Phase 5:证据等级(插点 C)+ 主动学习(插点 D)旁路挂载。确定性零 LLM,advisory 不碰裁决。
        # 读已组装完成的 report(reliability/abstain/disagreement/downgrade/caution/learned/module_plan
        # 信号全齐的最早时机)→ 只往 report.provenance 追加 evidence_level/learning_queue 两新键,
        # 不动任何现有键、不改 prediction/裁决。gated:agent 不在册则分支不进(OFFLINE 字节等价)。
        evidence_level = None
        if "EvidenceLevelAgent" in self._agents:
            em = self.mk_message("Report", "EvidenceLevelAgent",
                                 "evidence_level_request", {"report": report}, rep.message_id)
            evidence_level = self._dispatch_collect(em, "evidence_level_ready").payload["evidence_level"]
            report.setdefault("provenance", {})["evidence_level"] = evidence_level
        if "ActiveLearningAgent" in self._agents:
            am = self.mk_message("EvidenceLevelAgent", "ActiveLearningAgent",
                                 "learning_queue_request",
                                 {"report": report, "evidence_level": evidence_level}, rep.message_id)
            report.setdefault("provenance", {})["learning_queue"] = \
                self._dispatch_collect(am, "learning_queue_ready").payload["learning_queue"]
```

- [ ] **Step 5: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_runtime_active_learning.py -q`
Expected: 5 passed。

- [ ] **Step 6: 全量回归(确认零回归 + skip 仍 25)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 551 passed / 25 skipped / 0 failed(546 + 5 新)。**特别核对**所有现有 e2e/report/服务层测试(`test_report_markdown.py` 尚未扩,应仍绿;`run_virtualcell_query` 相关测试仍绿 —— provenance 多了两键,若某测试严格断言 provenance **恰好只有旧键集** 而失败 → 那是过严测试,停下报告,不改核心逻辑迁就,红线 5)。

- [ ] **Step 7: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/workflows/predict_delta_expression.py praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/test_runtime_active_learning.py
git commit -m "feat(phase5): 接管线 —— EvidenceLevel(插点C)+ActiveLearning(插点D)旁路挂 report.provenance.evidence_level/learning_queue(OFFLINE 零 LLM,不改 prediction/裁决)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5.7:report_markdown 扩两段(证据记录 + 验证计划)+ 契约测试

**决策说明(R2):** report_markdown 加两段:**"证据记录"**(读 `prov["evidence_level"]`:level/rationale/ood_signal)插在 §6(Evidence and Provenance)之后、§7 之前;**"验证计划"**(读 `prov["learning_queue"]`:top-N items 的 candidate/module/information_gain/drivers)插在 §8(Limitations)之后、§9 之前。**现有 9 段编号与结构不变**(新段用不带编号的 `### ` 子标题,附着在相邻主段之后,避免打乱 `## 1..9` 编号 — 见实现)。缺键标 N/A,不崩,byte-identical + no-LLM 断言仍绿。这是决策 R2:**加子段不改 9 段编号**,保持既有测试对 `## 1..9` 的断言全绿。

**Files:**
- Modify: `praxis_virtualcell/io/report_markdown.py`
- Test: `praxis_virtualcell/tests/test_report_markdown.py`(扩)

- [ ] **Step 1: 写失败测试(扩现有 test_report_markdown.py)**

在 `praxis_virtualcell/tests/test_report_markdown.py` 末尾追加(不改现有测试):

```python

# ===== Phase 5:证据记录 + 验证计划两段 =====

_WITH_AL = {
    "mode": "offline",
    "request": {"request_id": "al_ahr", "species": "human", "cell_type": "K562",
                "perturbation_type": "gene", "perturbation_targets": ["AHR"],
                "task_type": "predict_delta_expression"},
    "report": {
        "request_id": "al_ahr", "abstain": False, "reliability": "medium",
        "prediction": {"delta": [0.2]}, "models_used": ["MockLinear", "MockCPA"],
        "models_rejected": [], "models_failed": [],
        "abstain_reasons": [], "downgrade_reasons": ["downgrade:model_disagreement_too_high"],
        "failed_checks": ["model_disagreement"],
        "model_disagreement": {"score": 0.8, "triggered": True},
        "critic_violations": [], "caution_flags": {}, "learned_reliability": None,
        "provenance": {
            "n_messages": 24, "rules_referenced": ["r1.yaml"], "rules_hit": [],
            "ortholog_cautions": {}, "rejection_reasons": {},
            "evidence_level": {"level": "E4", "rationale": ["downgrade"],
                               "ood_signal": "unknown", "aligned_with_disposition": True},
            "learning_queue": {"items": [
                {"candidate": "stress_processor@human:AHR", "module": "stress_processor",
                 "information_gain": 1.4, "drivers": ["disagreement_high", "module_weak"],
                 "rationale": "x"},
                {"candidate": "genetic_hub@human:AHR", "module": "genetic_hub",
                 "information_gain": 0.8, "drivers": ["disagreement_high"], "rationale": "y"}],
                "notes": []},
        },
    },
}


def test_evidence_record_section_present():
    from praxis_virtualcell.io.report_markdown import render_report_md
    md = render_report_md(_WITH_AL)
    assert "证据记录" in md or "Evidence Record" in md
    assert "E4" in md                      # evidence level 出现
    assert "ood_signal" in md or "OOD" in md


def test_validation_plan_section_present():
    from praxis_virtualcell.io.report_markdown import render_report_md
    md = render_report_md(_WITH_AL)
    assert "验证计划" in md or "Validation Plan" in md
    assert "stress_processor@human:AHR" in md    # top 候选出现
    assert "1.4" in md                            # information_gain 出现


def test_nine_sections_still_present_with_al():
    from praxis_virtualcell.io.report_markdown import render_report_md
    md = render_report_md(_WITH_AL)
    for s in _SECTIONS:
        assert s in md, f"缺段:{s}"       # 现有 9 段编号不被打乱


def test_missing_evidence_and_queue_shows_na():
    """缺 evidence_level/learning_queue(如旧 job)→ 标 N/A,不崩,9 段仍在。"""
    from praxis_virtualcell.io.report_markdown import render_report_md
    md = render_report_md(_ACCEPT)          # _ACCEPT 无 evidence_level/learning_queue 键
    assert "证据记录" in md or "Evidence Record" in md
    assert "验证计划" in md or "Validation Plan" in md
    assert "N/A" in md
    for s in _SECTIONS:
        assert s in md
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_report_markdown.py -q`
Expected: FAIL(新 4 条失败 —— "证据记录"/"验证计划" 段未渲染;现有 8 条仍绿)。

- [ ] **Step 3: 写实现(report_markdown 加两段渲染)**

在 `praxis_virtualcell/io/report_markdown.py`。

找到 §6 段落结尾(`## 7. Biological Interpretation` 之前):

```python
    if learned:
        w(f"- reliability model_version: `{learned.get('model_version', _NA)}`")
        w(f"- feature_schema_version: `{learned.get('feature_schema_version', _NA)}`")
        w(f"- artifact_sha256: `{learned.get('artifact_sha256', _NA)}`")
        w(f"- abstain_artifact_sha256: `{learned.get('abstain_artifact_sha256', _NA)}`")
    w("")

    # 7. Biological Interpretation
```

在 `w("")` 之后、`# 7. Biological Interpretation` 注释之前插入:

```python
    # 证据记录(Phase 5:evidence_level E0–E5,附 §6 之后。缺键标 N/A,不崩)
    ev = prov.get("evidence_level") or {}
    w("### 证据记录(Evidence Record)")
    w("")
    w(f"- evidence_level: `{ev.get('level', _NA)}`")
    w(f"- ood_signal: `{ev.get('ood_signal', _NA)}`")
    w(f"- rationale: `{_fmt_list(ev.get('rationale'))}`")
    w(f"- aligned_with_disposition: `{ev.get('aligned_with_disposition', _NA)}`")
    w("")
    w("_证据等级是治理层之上的薄映射(读现有 reliability/OOD/disagreement 信号),"
      "不重写裁决;E2=in-domain accept 与现有 disposition 对齐。_")
    w("")

    # 7. Biological Interpretation
```

找到 §8 段落结尾(`## 9. Reproducibility` 之前):

```python
    for x in limits:
        w(f"- {x}")
    w("")

    # 9. Reproducibility
```

在 `w("")` 之后、`# 9. Reproducibility` 注释之前插入:

```python
    # 验证计划(Phase 5:learning_queue,附 §8 之后。advisory 建议下一步实验,不改裁决。缺键标 N/A)
    lq = prov.get("learning_queue") or {}
    lq_items = lq.get("items") or []
    w("### 验证计划(Validation Plan · 主动学习建议)")
    w("")
    if not lq_items:
        w(f"- 优先实验候选:`{_NA}`(无可执行候选或缺 learning_queue)")
    else:
        w("- 优先实验候选(按 information gain 降序,advisory 不改裁决):")
        for it in lq_items[:5]:            # top-5
            w(f"  - `{it.get('candidate', _NA)}` · module=`{it.get('module', _NA)}` · "
              f"information_gain=`{it.get('information_gain', _NA)}` · "
              f"drivers={_fmt_list(it.get('drivers'))}")
    lq_notes = lq.get("notes") or []
    if lq_notes:
        w(f"- notes: {_fmt_list(lq_notes)}")
    w("")
    w("_验证计划是主动学习的 advisory 产物:建议下一步该测什么(用 disagreement/OOD/证据等级排序),"
      "不碰 prediction/verdict 终决/provenance ledger。_")
    w("")

    # 9. Reproducibility
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_report_markdown.py -q`
Expected: 12 passed(现有 8 + 新 4)。**特别核对** `test_reproducible_byte_identical`(byte-identical 仍绿:两段是确定性渲染)、`test_no_llm_import_in_module`(渲染器仍不 import LLM)、`test_accept_has_all_nine_sections`/`test_minimal_job_does_not_crash`(9 段编号未被打乱)全绿。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 555 passed / 25 skipped / 0 failed(551 + 4 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/io/report_markdown.py praxis_virtualcell/tests/test_report_markdown.py
git commit -m "feat(phase5): report_markdown 加证据记录 + 验证计划两段(读 prov.evidence_level/learning_queue,不打乱 9 段编号,缺键 N/A,byte-identical)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5.8:Phase 5 完成闸门 —— 红线核验 + 台账 + v1.2 tag

**决策说明:** Phase 5 是 **v1.2 里程碑**(路线图 §5)。本 task 不写新功能,只做:①红线全量核验(assert_llm_boundaries 三 flag 恒 False、OFFLINE 零 LLM、evidence/learning_queue 不碰裁决、原 route/module golden + negative KPI 仍绿、skip 恒 25);②精确回归数(junit);③台账追加 Phase 5 段;④打 **v1.2 tag**(本地,不 push)。

**Files:**
- Modify: `docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md`(尾部追加 Phase 5 完成台账段)

- [ ] **Step 1: 红线核验 —— evidence/AL 不碰裁决 + 边界**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_evidence_level.py praxis_virtualcell/tests/test_evidence_level_agent.py praxis_virtualcell/tests/test_active_learning_agent.py praxis_virtualcell/tests/test_runtime_active_learning.py -q`
Expected: 全绿。evidence 不回写 verdict、AL 不改 report、abstain 不被抬成 accept、E-level 不领先 disposition —— 全钉死。

- [ ] **Step 2: 红线核验 —— 原 route/module golden + negative KPI 仍绿**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_golden_cases.py praxis_virtualcell/tests/test_negative_cases.py praxis_virtualcell/tests/test_module_golden_cases.py praxis_virtualcell/tests/test_module_consistency.py -q`
Expected: 全绿。route/module golden unsafe-accept=0、negative 无静默 accept 不变(Phase 5 未碰 route_table/治理引擎/ModulePlan 合成/reliability 逻辑)。若 `test_module_golden_cases.py` 文件名不同,先 `ls praxis_virtualcell/tests | grep -i golden` 核对实际文件名再跑。

- [ ] **Step 3: 红线核验 —— OFFLINE 零 LLM(build_runtime OFFLINE 注册 evidence/AL 但无 LLM 节点)**

Run: `PYTHONPATH=$PWD .venv/bin/python -c "from praxis_virtualcell.core.config import Mode, RuntimeConfig; from praxis_virtualcell.workflows.predict_delta_expression import build_runtime; rt=build_runtime(RuntimeConfig(mode=Mode.OFFLINE)); ns=set(rt._agents); assert 'EvidenceLevelAgent' in ns and 'ActiveLearningAgent' in ns, ns; assert not any(n.startswith('LLM') for n in ns), ns; print('OFFLINE evidence/AL registered, zero LLM:', sorted(ns))"`
Expected: 打印 OFFLINE 注册表含 EvidenceLevelAgent/ActiveLearningAgent、**不含任何 LLM 节点**。若含 LLM 节点 → 违规,停下修正。

- [ ] **Step 4: 红线核验 —— evidence/AL 模块不 import LLM**

Run: `PYTHONPATH=$PWD .venv/bin/python -c "
import praxis_virtualcell.governance.evidence_level as a
import praxis_virtualcell.agents.evidence_level_agent as b
import praxis_virtualcell.active_learning.acquisition as c
import praxis_virtualcell.active_learning.learning_queue as d
import praxis_virtualcell.active_learning.active_learning_agent as e
for m in (a,b,c,d,e):
    src=open(m.__file__,encoding='utf-8').read()
    assert 'agents_llm' not in src and 'llm_client' not in src and 'llm_orchestration' not in src, m.__file__
print('evidence/AL modules zero LLM import OK')"`
Expected: 打印 zero LLM import OK。

- [ ] **Step 5: 全量回归(精确数)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q --junit-xml=/tmp/junit_phase5.xml`
然后取精确数:
Run: `python3 -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/junit_phase5.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; t,f,e,k=int(s.get('tests')),int(s.get('failures')),int(s.get('errors')),int(s.get('skipped')); print('collected=%d failures=%d errors=%d skipped=%d passed=%d'%(t,f,e,k,t-f-e-k))"`
Expected: `failures=0 errors=0 skipped=25 passed=555`(509 基线 + 13+5+7+5+7+5+4 = 46 新 = 555)。**关键:failures=0 errors=0 + skipped=25(未破 skip 基线)+ passed=555**。

- [ ] **Step 6: 台账更新**

用 Edit 在 `docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md` 尾部追加:

```markdown

---

## Phase 5 完成台账(2026-07-04,主动学习 v1 + 证据等级 E0–E5 — v1.2 里程碑)

- **交付**:`governance/evidence_level.py`(E0–E5 映射纯函数,决策 B)+ `agents/evidence_level_agent.py`(进 bus 薄包装,插点 C)+ `active_learning/` 子包(`acquisition.py` information gain 启发式 / `learning_queue.py` 优先队列数据结构 / `active_learning_agent.py` ActiveLearningAgent,插点 D)+ 接管线(`workflows/predict_delta_expression.py` 注册 + `core/runtime.py` 旁路挂 evidence_level/learning_queue)+ `io/report_markdown.py` 加证据记录/验证计划两段 + 测试。
- **EvidenceLevel 归属**:E0–E5 归 Phase 5(与主动学习同源:读同一批 reliability/OOD/disagreement/learned 信号;证据链耦合 —— learning_queue 用 E-level 排序;Phase 3/4 计划 + module_consistency.py 源码注释均留此)。
- **证据等级契约(决策 B)**:治理层之上的薄映射,读现有 reliability/abstain/disagreement/downgrade/caution/learned/OOD 信号映射 E0–E5,**不重写治理、不回写 verdict**;E2=in-domain(seen_in_train=True)+high+无 disagreement→accept **与现有 disposition 对齐**(不领先治理:abstain/downgrade 不得映射成 E2/E3 accept 级)。runtime OOD 校正:seen_in_train 多 None → OOD proxy fail-closed 记 unknown(不假装 in_domain);ood_enrichment.py 是离线 ledger 分析,不进 runtime。
- **learning_queue 契约(不碰裁决)**:主动学习产"该测什么"advisory 优先队列,用 disagreement/OOD/证据等级/module 弱支持算 information gain(v1 启发式,非严格 EIG,已诚实标注)降序排序;**绝不碰 prediction/verdict 终决/provenance ledger/reliability 决策**;abstain 请求可建议补弱模块数据,但不把 abstain 改 accept;无 module_plan/无候选 → 空队列 + note(不虚构)。
- **红线守住**:①OFFLINE 默认零 LLM(evidence/AL 是确定性信号映射,OFFLINE 也注册但零 LLM;build_runtime OFFLINE 不含任何 LLM 节点)②assert_llm_boundaries 三 flag 恒 False(Phase 5 不碰 config/守卫)③evidence/learning_queue 只挂 report.provenance 两新键,不改 prediction/abstain/reliability/现有 provenance 键(专门契约测试钉死)④原 route/module golden unsafe-accept=0、negative 无静默 accept 不变⑤信号缺失 fail-closed(OOD unknown / 空队列 + note)。509 基线零回归 → **555 passed / 25 skipped / 0 failed**(skip 基线 25 未破:全确定性离线,未新增 marker 测试)。
- **接管线(最小侵入)**:EvidenceLevel(插点 C)+ ActiveLearning(插点 D)在 Report 之后 sidecar 挂 `report.provenance.evidence_level`/`learning_queue`,**不改 predictor fan-out/ensemble/reliability/critic/provenance 输入契约**。OFFLINE 字节等价(只追加两新键)。
- **report 扩段**:证据记录(§6 后)+ 验证计划(§8 后)两子段,不打乱现有 §1..9 编号;缺键标 N/A,byte-identical + no-LLM 断言仍绿(Phase 5 只做这两段;Phase 8 网站发行相关的其他 report 扩容留 Phase 8)。
- **v1.2 里程碑**:Phase 5 完成 = v1.2(active-learning)。打 tag `v1.2-active-learning`(本地,不 push)。
- **待控制器确认的核心决策**:①information gain 权重常量(acquisition._W_*,当前等权量级可解释;真调参/引入贝叶斯 EIG 留 v1.2.x)②learning_queue 候选粒度(当前 = 每 module 一候选;更细的"module×扰动目标×细胞类型"网格候选留 v1.2.x)③evidence_level 是否进而反馈 ledger 触发再训练(当前只 advisory 挂 provenance,不写 ledger;闭环再训练留 Phase 7 自训模型)。已在计划落最小可测集并标注。
```

- [ ] **Step 7: 提交(不 push)**

```bash
find . -name '._*' -delete
git add docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md
git commit -m "docs(phase5): Phase 5 完成台账 + 红线核验(555 passed,主动学习 v1 + 证据等级 E0–E5 交付)

Phase 5 交付主动学习 v1:governance/evidence_level.py(E0–E5 映射,决策 B)+ EvidenceLevelAgent(插点C)
+ active_learning/ 子包(acquisition + learning_queue + ActiveLearningAgent,插点D)+ 接管线旁路挂
report.provenance.evidence_level/learning_queue + report 加证据记录/验证计划两段。
证据等级读现有 reliability/OOD/disagreement 信号映射不重写治理、不回写 verdict;learning_queue
advisory 不碰裁决;三 flag 恒 False、OFFLINE 零 LLM、fail-closed。509 基线零回归 → 555 passed。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 8: 打 v1.2 tag(本地,不 push)**

Phase 5 = v1.2 里程碑(路线图 §5)。全绿 + 红线核验通过后打 tag:

```bash
git tag -a v1.2-active-learning -m "v1.2: active-learning — EvidenceLevelAgent(E0–E5)+ ActiveLearningAgent + learning_queue, 接管线旁路挂 report.provenance. 555 passed / 25 skipped. OFFLINE zero-LLM, 三 flag 恒 False, advisory 不碰裁决. Phase 5 done."
git tag --list "v1.2*"
```

Expected: tag `v1.2-active-learning` 出现。**不 push**(房规:当前分支不 push;tag 推送由人决定)。

**Phase 5 验收:**
- ✅ evidence_level.py:E0–E5 映射(决策 B 不重写治理、不回写 verdict、E2 与 disposition 对齐、OOD fail-closed unknown)。
- ✅ EvidenceLevelAgent(进 bus,薄包装 map_evidence_level,只读 report 出 evidence_level_ready)。
- ✅ acquisition.py:information gain 启发式(确定性加权,诚实标注非严格 EIG)。
- ✅ learning_queue.py:优先队列数据结构(降序 + notes + to_dict,空候选不虚构)。
- ✅ ActiveLearningAgent(进 bus,从 module_plan+report 信号产 learning_queue,advisory 不碰裁决)。
- ✅ 接管线:EvidenceLevel(插点C)+ActiveLearning(插点D)旁路挂 report.provenance;OFFLINE 零 LLM 且核心 prediction/裁决等价。
- ✅ report_markdown 加证据记录 + 验证计划两段(不打乱 9 段编号,缺键 N/A,byte-identical)。
- ✅ 主动学习 tests 30(路线图 §8:learning queue 结构 + information gain)→ 实际 acquisition 7 + learning_queue 5 + active_learning_agent 7 + runtime_active_learning 5 + evidence_level 13 + evidence_level_agent 5 = 42(超 30 目标)。report tests(证据/验证两段)4。
- ✅ 509 基线零回归 → 555 passed / 25 skipped(skip 基线未破)→ 打 v1.2 tag(本地不 push)。

---

## Self-Review(写完对照路线图 + 真实代码)

- **路线图覆盖(§4/§5/§6/§7/§8)**:
  - §4 插点 C(EvidenceLevelAgent E0–E5 读运行时 reliability/OOD/artifact 信号映射证据等级)→ Task 5.1(evidence_level 映射)+ 5.2(EvidenceLevelAgent 进 bus)+ 5.6(接插点 C)完整落地。插点 D(ActiveLearningAgent 产 learning_queue)→ Task 5.3(acquisition)+ 5.4(learning_queue)+ 5.5(ActiveLearningAgent)+ 5.6(接插点 D)完整落地。
  - §5 依赖:Phase 5 依赖 Phase 1 证据/模块结构(实读 module_plan/registry 已在,Task 5.5 从 module_plan.entries 派生候选 ✓),可早做 v1(只需 disagreement/OOD 信号,v0.8 已有 —— 实读 reliability_decision.model_disagreement + seen_in_train ✓);Phase 5 = v1.2(Task 5.8 打 tag ✓)。
  - §6 决策 B(证据等级是治理层之上的薄映射,不重写治理:evidence_level 读现有 reliability/OOD/artifact 信号映射 E0–E5,E2=匹配扰动数据 in-domain→accept 与现有 disposition 对齐)→ Task 5.1 `map_evidence_level` 只读不回写 verdict + `aligned_with_disposition` 钉死 E-level 不领先治理 + E2 判据(in_domain+high+无 disagreement)与 accept disposition 对齐 ✓。决策 F(目录落位:active_learning/ 作为 praxis_virtualcell/ 下新子包,governance/ 扩加 evidence_level)→ Task 5.1(governance/evidence_level.py)+ 5.3(active_learning/ 子包)✓。
  - §7 红线全适用:①OFFLINE 默认零 LLM(Task 5.6 build_runtime OFFLINE 注册 evidence/AL 但零 LLM 节点 + Task 5.8 gated/grep 核验)②assert_llm_boundaries 三 flag(Phase 5 不碰 config/守卫,Task 5.8 声明)③evidence/learning_queue 不碰 prediction/hard-rule/learned-reliability 终决/provenance ledger(Task 5.1/5.2 evidence 不回写 verdict + Task 5.5/5.6 AL 不改 report + 契约测试 `test_does_not_mutate_report`/`test_evidence_level_does_not_change_prediction_or_verdict` 逐条钉死)④unsafe-accept=0(Task 5.8 原 golden/negative KPI 仍绿 + E-level 不把 downgrade 抬成 accept)⑥信号缺失不静默(Task 5.1 OOD unknown fail-closed + Task 5.5 空队列 + note)✓。
  - §8 测试目标:active learning tests 30(新;learning queue 结构 + information gain)→ Task 5.3(acquisition 7)+ 5.4(learning_queue 5)+ 5.5(active_learning_agent 7)+ 5.6(runtime 5)+ 5.1(evidence_level 13)+ 5.2(evidence_level_agent 5)= 42,超 30 ✓;report tests(证据/验证两段)→ Task 5.7(+4,扩 test_report_markdown)✓。**判断:report 扩容属 Phase 5 的部分 = 与 evidence_level/learning_queue 直接相关的两段**(数据源是本 Phase 新产出),Phase 8 网站发行相关的其他 report 扩容留 Phase 8(已在校正4 说明)。

- **EvidenceLevel(E0–E5)归 Phase 5 的判断**:已在"EvidenceLevel 归属判断"段展开 —— 归 Phase 5,理由:信号同源(读同一批 reliability/OOD/disagreement/learned 信号)、证据链耦合(learning_queue 用 E-level 排序)、前置 Phase 明确留后(Phase 3/4 计划 + module_consistency.py:10 注释)、红线不越界(与 AL 同性质的 advisory,共用"不碰裁决"契约测试)。

- **与路线图旧描述不符的真实代码情况(逐条校正)**:
  1. **runtime OOD 信号 ≠ ood_enrichment.py**(实读 `ood_enrichment.py` 是离线 ledger 分析 `evaluate_ood(entries)`,`reliability.py:136` 注释 runtime `seen_in_train` 多 None)。路线图 §4 说"插点 C 读运行时 OOD 信号(OOD/ood_enrichment)"。校正:E-level OOD 输入 = `seen_in_train`(优先)+ None 时确定性 proxy(caution_flags ortholog/cross-species、非母种),fail-closed 记 unknown,**不调 ood_enrichment**(那是离线分析)。已在数据契约段校正1 + Task 5.1 `derive_ood_signal` 落实。
  2. **EvidenceLevel 归属**:Phase 3 计划留"Phase 4/5",Phase 4 计划归 Phase 5,`module_consistency.py:10` 源码注释亦写"留 Phase 4/5"。本 Phase 归置 = Phase 5。已在校正2 + 归属判断段展开。
  3. **E-level 决策 B 实现细节**:E-level 读现有 report 信号**不回写 verdict**、accept 级(E2/E3)只在现有 disposition 已 accept 时给出(不领先治理)。已在校正3 + Task 5.1 `aligned_with_disposition` + `test_e_level_does_not_lead_disposition` 落实。
  4. **report 扩段归属**:路线图 §8 标 "5/8"。本 Phase 只加与 evidence_level/learning_queue 直接相关两段(数据源本 Phase 产出),Phase 8 其他扩容留后。已在校正4 + Task 5.7 决策 R2 落实。
  5. **runtime 已有 Phase 4 sidecar 挂载惯例**(实读 `runtime.py:99-105` `report.setdefault("provenance", {})["X"]=...`,gated by `if "AgentName" in self._agents`)。Phase 5 插点 C/D 复刻此惯例(在 Report 之后、LLMCritic 之前挂 evidence_level/learning_queue),最小侵入、OFFLINE 字节等价。已在接管线段 + Task 5.6 落实。

- **无占位符**:每 task 每 step 含完整可跑测试代码 + 实现代码 + 确切命令 + 期望数。`evidence_level.py`(derive_ood_signal + map_evidence_level 完整)、EvidenceLevelAgent 完整、acquisition.information_gain 完整、LearningQueue/LearningQueueItem 完整、ActiveLearningAgent 完整 handle、runtime 插点 C/D 精确 old→new 插入、report_markdown 两段精确插入、契约测试 40+ 条全给出,非 "similar to above"。

- **类型一致性**:`map_evidence_level(report) -> dict` 返回键 `{level, rationale, ood_signal, aligned_with_disposition}`(Task 5.1 定义),EvidenceLevelAgent 挂 `evidence_level_ready.payload["evidence_level"]`(5.2)、runtime 挂 `report.provenance.evidence_level`(5.6)、report_markdown 读 `prov["evidence_level"]["level"/"ood_signal"/"rationale"/"aligned_with_disposition"]`(5.7)、AL 读 `evidence_level.get("level")`(5.5)—— 五处键一致。`information_gain(signals) -> float` signals 键 `{disagreement_score, disagreement_triggered, ood_signal, evidence_level, module_weak}`(5.3 定义),AL 构造同键(5.5)一致。`LearningQueueItem` 键 `{candidate, module, information_gain, drivers, rationale}`(5.4 定义),AL 构造(5.5)、report_markdown 读(5.7 `it.get("candidate"/"module"/"information_gain"/"drivers")`)、测试断言(5.4/5.5/5.7)一致。`LearningQueue.to_dict()` 键 `{items, notes}`(5.4),runtime 挂(5.6)、report 读(5.7)一致。消息类型链:`evidence_level_request`→`evidence_level_ready`(5.2/5.6)、`learning_queue_request`→`learning_queue_ready`(5.5/5.6)一致。`derive_ood_signal`(5.1 定义)在 evidence_level(5.1)+ active_learning_agent(5.5)两处 import 一致。`_SEVERITY` 映射复用 Phase 3 module_plan(不重定义)。

- **铁律段完整**:纯新增+复用(governance 加 evidence_level、active_learning 新子包、workflow 仅增量注册、runtime 仅加可选插点、report_markdown 仅加两段)、OFFLINE 默认零 LLM(红线 1,gated + grep 核验)、assert_llm_boundaries 三 flag 恒 False(红线 2,Phase 5 不碰守卫)、evidence/learning_queue 不碰裁决(红线 2,契约测试钉死)、unsafe-accept=0(红线 4)、信号缺失 fail-closed(红线 6)、测试口径 praxis_virtualcell/tests + junit passed=collected−skipped 精确口径 + 起点基线 509 passed/25 skipped/collected 534(实跑核实)、全确定性离线保 skip 恒 25、每 task 删 ._* + Co-Authored-By trailer + 当前分支不 push、Phase 5=v1.2 里程碑才打 tag —— 全写进头部铁律段并逐 task 执行。

- **累计测试数核对(以真实 passed 509 起算)**:509(基线)→ 522(5.1 +13)→ 527(5.2 +5)→ 534(5.3 +7)→ 539(5.4 +5)→ 546(5.5 +7)→ 551(5.6 +5)→ 555(5.7 +4)→ 555(5.8 台账,+0)。Phase 5 新增 46 条,509→555,skip 恒 25。标注数与各 task 代码块 `def test_` 实数一致(5.1=13 / 5.2=5 / 5.3=7 / 5.4=5 / 5.5=7 / 5.6=5 / 5.7=4)。关键 failures=0 errors=0 skipped=25。

---

## 下一步(Phase 6/7 展开时机)

Phase 5 全绿(555 passed)+ v1.2 tag 后,回主路线图 §9,把 **Phase 6(公开模型接入:GEARS/scGPT 产品化成 ModelBroker 插件)** + **Phase 7(自训模型第一批)** 展开(两者可并行,都依赖 Phase 2 broker 契约)。Phase 5 产出的 learning_queue(挂 report.provenance)+ evidence_level 为 Phase 7 的"闭环再训练"铺路(learning_queue 建议的实验 → 采数据 → 自训模型),但本 Phase 只做 advisory 挂载,不写 ledger、不触发再训练(那是 Phase 7)。Phase 6/7 完成后 Phase 8(网站 + Linux release)→ v1.3。
