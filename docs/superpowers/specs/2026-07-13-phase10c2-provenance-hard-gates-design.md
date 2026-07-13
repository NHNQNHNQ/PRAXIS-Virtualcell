# P10.C2 provenance 完整性硬门 + per-call hash + 越界 cell type abstain 设计 spec

## 1. 目标与背景

Phase 10 治理单元 C 的第二子单元(C1 跨模块一致性已收官并 FF 合并本地 main)。roadmap `P10.C` 列三项治理能力(§47):
- ② **provenance 完整性硬门**(缺字段 fail,缺则不进 final report)+ **per-call hash**(name/version/input/output/param/evidence,缺一 fail);
- ③ **越界 cell type abstain 语义**。

用户 2026-07-13 拍板三项**全部走"真门"版**(非纯 advisory):三个治理 gate 都能真触发对外 abstain,复用 C1 已验证的架构模式(逻辑接进 `core/runtime.py` 后处理段,**不碰 reliability/critic agent 裁决数值**,只 override report 对外 abstain/prediction/abstain_reasons,原判记 provenance 供审计)。

论文主张边界不变:PRAXIS-VirtualCell 是"代码治理的多智能体操作层"。本单元强化的正是治理层的**可审计性(per-call hash)**与**fail-closed 拒绝能力(三 gate)**,是 D 阶段 "trace/provenance audit bundle" 交付物的前置。

## 2. 勘察确立的现实约束(设计的事实地基)

控制器 2026-07-13 只读勘察逐条核实(避免 C1 式"建无收益空门/张冠李戴"):

- **per-call hash 真实缺失**:全局 grep 无 `input_hash/output_hash/param_hash`;predictor 的 `provenance` 现状仅 `{"rules":...}`(base.py)或 `{"mock":True}`(mock_linear.py 等),**无 model_version**。可建基础扎实:`model_zoo/registry.yaml` 有真实 `version`(如 `norman_2019`/`e_coli_core-textbook`)与 `sha256` assets;runtime 已有 `hashlib.sha256(json.dumps(sort_keys=True))` 算 trace_id 的现成 canonical-hash 模式;`PredictorResultMessage.provenance: dict` 是现成挂载点。
- **provenance 完整性现状"字段恒不缺"**:`ProvenanceAgent` 组装 11 个固定字段全 `.get(..., 默认)` 兜底;`report.py` 用 `p.get("provenance", {})`。字段由代码构造 → **现状无真实缺失场景**。故硬门定性为**防御性类不变量 fail-closed 断言**(防未来重构漏挂),诚实披露"罕触发"(同 C1 的 module_consistency gate 定性),命名避免暗示高频"多模块结果比对"。
- **cell_type 越界"已部分交付为 downgrade,且是活代码"**:`reliability.py:111-119` 已有 `downgrade:cell_type_not_supported`;`brains/virtualcell/human/model_applicability.yaml` 真声明 `supported_cell_types`(K562/A549/MCF7/HEK293T 等);`test_week6_reliability_critic.py` 有覆盖 → **能真触发,非 C1 式死码**。现状是 downgrade(降一档、仍给预测),roadmap 要 abstain。升级 downgrade→abstain **会撞"reliability 裁决零改"红线** → 用户选 **C1 式 runtime 后处理 gate**(不改 reliability agent,gate 在其上叠加"全越界→对外 abstain")。
- **字节等价不会被 per-call hash 大面积破坏**(关键):`test_offline_rerun_byte_equal` 断言**同请求三跑 hash 一致**(确定性,非跨版本不变);`test_offline_report_provenance_fields_present` 只断言 `rules_referenced/models_used/n_messages` 三键**存在**;`test_golden_cases` 只断言路由裁决(engine/disposition/caution_flags/data_gated)与 `provenance` 非空 —— **无任何测试深比完整 report dict 跨版本不变**。per-call hash 是 input/output 的确定性 sha256 → 三跑仍一致 → 现有确定性红线不破。

## 3. 范围(三 gate + per-call hash 接线,全真门)

**做**:
1. **per-call hash 基础设施** + 全 predictor 补 `provenance.per_call`(model_name/model_version/input_hash/output_hash/evidence_source)。
2. **Gate A**:per-call hash 完整性 fail-closed —— 任一被采纳 model call 缺 hash 字段 → override 对外 abstain。
3. **Gate B**:provenance 完整性硬门 —— 顶层 report + provenance 必需契约缺键/结构非法 → override 对外 abstain(防御性类不变量)。
4. **Gate C**:cell_type 越界 abstain —— 全部被采纳 predictor 都声明 supported_cell_types 且都不含 req cell_type → override 对外 abstain。

**不做(诚实 limitation)**:
- roadmap §47 的 **param hash**:mock/机制 predictor 无独立"超参"概念(引擎参数已在 registry version 里锁);per_call 记 model_version(含 ckpt/数据版本)已覆盖"参数可审计"意图,不强造 param_hash 空字段。
- **reliability agent 内 cell_type downgrade 逻辑不改**(保留现状 downgrade 数值语义,Gate C 只在 runtime 后处理层叠加对外 abstain)。
- 跨请求编排类审计(留 C3/D)。

## 4. 架构设计

**统一模式(全复用 C1)**:新逻辑落 `governance/` 下**纯确定性函数**(如 `module_consistency.py`);`runtime.py` 后处理段调用 + 按返回 override。**不碰 reliability/critic/report agent 本体**;reliability 提取字段(reliability/failed_checks/model_disagreement)原样保留、裁决数值不变;gate 触发时只写 report 对外 `abstain=True`/`prediction=None`/`abstain_reasons.append(...)`,原判 `reliability_original_abstain` 记 provenance 供审计。确定性、零 LLM、`llm_used_for_prediction` 恒 false。

### 4.1 per-call hash 基础设施 + Gate A
- 新建 `governance/provenance_hash.py`:
  - `compute_call_provenance(model_name, model_version, model_input, output, evidence) -> dict`:返回 `{model_name, model_version, input_hash, output_hash, evidence_source}`,input_hash/output_hash = 复用 canonical sha256(`json.dumps(sort_keys=True, ensure_ascii=False, default=str)`)。
  - `check_call_provenance(per_call: dict) -> list[str]`:校验 model_name/model_version/input_hash/output_hash 四键非空且为合法 hash;返回缺失键清单(空=完整)。
- `predictors/base.py`:`_emit` 前给 success/rejected/failed 三种 result 的 `provenance` 追加 `per_call`(纯增量,不改现有 `provenance` 其它键)。`model_version` 来源:predictor 声明 `model_version` 类属性(mock predictor = `"mock:<name>"`,如 `mock:MockLinear`;引擎 predictor 从 CaseReport/registry 取真实 version 如 `norman_2019`/`e_coli_core-textbook`)。
- **Gate A(runtime 后处理,fail-closed)**:遍历 `models_used` 对应 result 的 `per_call`,任一 `check_call_provenance` 非空 → override abstain,`abstain_reasons += "incomplete_call_provenance"`,记 `provenance.provenance_hash_gate`(缺失明细 + gate_abstained + reliability_original_abstain)。
- **接线顺序铁律**:必须先建基础设施(全 predictor 产出 per_call)、再接 Gate A,否则现有 `models_used` 无 per_call → Gate A 全 abstain 打崩回归。

### 4.2 Gate B — provenance 完整性硬门(防御性类不变量)
- 新建 `governance/provenance_completeness.py::check_report_provenance(report: dict) -> list[str]`:定义必需契约 —— 顶层键 `models_used/models_rejected/reliability/provenance` 存在,`provenance` 子结构含 `n_messages/rules_referenced/models_used`(结构合法)。返回缺失/非法键清单。
- **Gate B(runtime 后处理)**:非空 → override abstain,`abstain_reasons += "incomplete_provenance"`,记 `provenance.provenance_completeness_gate`。
- **诚实定性**:字段恒由代码构造 → 罕触发防御性 fail-closed 断言(同 C1)。spec/paper 引用须明标"防御性完整性断言 gate,非高频缺失检测"。

### 4.3 Gate C — cell_type 越界 abstain gate
- 新建 `governance/cell_type_domain.py::check_cell_type_domain(req, brain_context, models_used) -> list[str]`:**独立复用** reliability.py 判据(`declaring` = models_used 中声明 `supported_cell_types` 的;`unsupported` = declaring 中 req cell_type 不在 supported 的;`declaring` 非空且 `len(unsupported)==len(declaring)` → violation)。返回越界 predictor 清单(空=不触发)。**不 import/不改 reliability agent**,判据逻辑独立实现(避免耦合裁决路径)。
- **Gate C(runtime 后处理)**:非空 → override abstain,`abstain_reasons += "cell_type_out_of_domain"`,记 `provenance.cell_type_gate`。
- **与 reliability downgrade 关系**:reliability 的 `downgrade:cell_type_not_supported` 数值语义**完全保留**(降一档、reliability 字段不变);Gate C 在其上叠加"**全越界→对外 abstain**"。窄门:仅"有声明 supported_cell_types 的 used predictor 且全部越界"才触发(与 reliability 判据同源,避免误伤无声明 predictor)。

### 4.4 接线位置 + 多 gate 交互
- 位置:`runtime.py` 后处理段,**C1 gate(module_consistency)之后、evidence_level/learning_queue 旁路之前**。
- 顺序:C1 gate → Gate A → Gate B → Gate C。任一触发 abstain 即 override;`abstain_reasons` **累加不覆盖**(多 gate 同时命中各自 append),各 gate provenance 键**独立**(`cross_module_consistency`/`provenance_hash_gate`/`provenance_completeness_gate`/`cell_type_gate` 互不干扰),`reliability_original_abstain` 每 gate 各自捕获"进入该 gate 前的对外 abstain 态"。
- gated 存在性:三 gate 仅在 `module_plan is not None`(可路由请求)时才有 per_call/裁决可查?**否** —— per_call hash 对所有 predictor result 都产出(不依赖 module_plan);Gate A/B 对所有走完主链的 report 生效;Gate C 依赖 req cell_type 且 models_used 非空。abstain 路径(无 models_used)天然不触发 Gate A/C(遍历空)。
- 下游旁路一致性:gate override abstain 后,后续 evidence_level/learning_queue/llm_critic/llm_report 旁路读的是 **override 后**的 report(反映 gate abstain)—— 与 C1 gate 同构(C1 亦在 evidence_level 之前 override),既有行为,非新增接缝。

### 4.5 为什么这样不违红线
- reliability/critic agent 代码零改:gate 全在 runtime 后处理层读已组装 report,override 只写对外三字段,reliability 提取字段原样透出、裁决数值不变(同 C1,符合 roadmap §127 "触发 abstain 不改裁决数值")。
- ModelApplicability/REAL_ENGINES/route/registry 不改:gate 不参与候选选择。
- 确定性 + 字节:per_call hash 为确定性 sha256,同请求多跑一致(§2 勘察确认现有确定性测试不破);gate 纯函数无 LLM。
- 核心内核 + 根 tests 零触碰;测试落 `praxis_virtualcell/tests/phase10/`。

## 5. 关键风险与前置验证(Task 0)

- **Task 0 基线坐实**:①现有全量 `praxis_virtualcell/tests` 784 passed/40 skipped/0 failed;②现有 report/provenance **无** `per_call`/四 gate 键(接线前提);③mock/引擎 predictor provenance 现状快照(证明 per_call 是新增);④现有 `test_offline_rerun_byte_equal` 通过(确定性基线)。
- **风险 1 — Gate A 接线顺序**:见 §4.1 铁律,Task 1(基础设施)必须先于 Task 2(Gate A)。
- **风险 2 — mock predictor 无 version 误伤**:所有 predictor(含 mock_linear/mock_gears/mock_cpa + CaseRunner 引擎)须声明 `model_version`,否则 Gate A fail-closed 误伤合法路径。Task 1 逐 predictor 补齐 + 测试。
- **风险 3 — Gate C 误伤无声明 predictor**:严守 reliability 同源窄门(仅 declaring 全越界才触发),Task 4 覆盖"部分 predictor 无声明→不触发"负例。
- **风险 4 — 多 gate abstain_reasons 覆盖/provenance 键冲突**:Task 5 专测多 gate 同时命中(reasons 累加、四 provenance 键独立、reliability 数值不变)。

## 6. 红线(全程不可破)
- reliability/critic 裁决逻辑与数值零改(gate 只 override 对外 abstain/prediction/abstain_reasons,提取字段原样保留)。
- ModelApplicability 只读不改候选;REAL_ENGINES 本体/route_table/registry status 不改。
- 核心内核 + 仓库根 `tests/` 零触碰;测试口径 `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`,绝不裸跑 pytest。
- OFFLINE 确定性:per_call hash 为确定性 sha256,同请求多跑字节稳定;`llm_used_for_prediction` 恒 false;gate 纯函数零 LLM。
- 诚实不伪造:per_call 记真实 name/version(mock 明标 `mock:`,引擎明标真实 version);Gate B 诚实披露罕触发防御性定性;Gate C 明标"越界"判据与 reliability downgrade 的关系。
- 不 push;commit trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`;commit 绝不含前端 WIP(base/fonts/themes/tokens.css、.claude/、.playwright-mcp/、string.jpeg)。

## 7. 测试(T10.4 拒绝子集 + per-call hash 审计,落 praxis_virtualcell/tests/phase10)
- per-call hash 基础设施:每 predictor 产出 per_call 四字段;input/output hash 确定性(同输入同 hash);mock 明标 `mock:` version。
- Gate A:构造缺 per_call 字段的 result → 触发 abstain(reasons 含 incomplete_call_provenance);完整 → 零 override + 字节等价(同请求多跑一致)。
- Gate B:构造缺必需 provenance 键的 report → 触发 abstain;正常 report → 活体验证不触发(诚实防御 gate)。
- Gate C:req cell_type 全越界(declaring 全 unsupported)→ 触发 abstain;部分 predictor 无声明 → 不触发(窄门);cell_type 在库 → 不触发。
- **裁决数值不变红线**:gate 触发时 reliability 提取字段(reliability/failed_checks/model_disagreement)与接线前一致(`test_c2_gate_preserves_reliability_numeric_fields`)。
- 多 gate 交互:同时命中多 gate → reasons 累加、四 provenance 键独立、reliability 数值不变。
- 确定性:`llm_used_for_prediction` 恒 false;全量回归绿。

## 8. Self-Review(占位符/一致性/范围/歧义)
- 占位符:无 TBD/TODO。
- 一致性:三 gate 全 C1 模式;§2 字节等价勘察与 §4.5/§6 红线一致(per_call hash 是确定性增量,不破"同请求多跑一致",不声称"跨版本字节不变")。
- 范围:聚焦三 gate + per-call hash,param hash/reliability 内逻辑/跨请求编排明列不做。
- 歧义:Gate C 与 reliability downgrade 关系已明确(downgrade 数值保留 + gate 叠加对外 abstain);"字节等价"精确定义为"同请求多跑一致"非"跨版本不变"。
