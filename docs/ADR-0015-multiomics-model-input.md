# ADR-0015：Typed Multi-omics Model Input 合同

- 状态：Accepted（P18 engineering contract complete；real multi-omics model acceptance pending）
- 日期：2026-08-06
- 唯一起始基线：`f253664239e4b1c9665301cf1bdf4e117a3e9c31`
- Completion code SHA：`626c71ffd1ce18a5adc200f6a6e376e57b269beb`
- Completion tree：`2b570398caff6cf955d789c3cb4a7a77dc13a082`
- 分支：`codex/p18-multiomics-cell-state`
- 前置：ADR-0006、ADR-0008、ADR-0009、ADR-0010、ADR-0011、ADR-0012、ADR-0013、ADR-0014
- 状态码：`P18_CONTRACT_COMPLETE_REAL_MULTIOMICS_MODEL_ACCEPTANCE_PENDING`

## 背景

P5 已冻结 `vc.pack.v0.3` 的多组学数据语义，P13 已提供 adapter identity，P17 已完成
contract-only Virtual Cell Brain。P18 的职责不是再建一套 request、Pack、Broker 或 registry，
而是在这些既有边界之间定义一个真正联合、可寻址、不可静默造数的多组学模型输入。

既有 `vc.request.v2` 的 `input_modality` 是单值字段，不能把 RNA、protein、ATAC 等多个
modality 塞入其中，也不能用“至少命中一个 modality”冒充联合输入。P18 因此增加独立的
typed bundle：request 仍精确描述 primary/target modality；联合输入合同显式列出有序的
required/optional modality slots，并逐层绑定 feature alignment、observation membership、
join、missingness 与实际矩阵内容。

本阶段没有获准使用外置数据或权重，也没有真实 multi-omics candidate、单组学 baseline、
ablation、CI、external 或 OOD 结果。Registry 在 completion code 上仍是 5 releases、0 native、
0 production-promoted。因此 P18 只能完成工程合同，不能声称真实模型、科学能力或生产执行
已经验收。

## 决策

### 1. 保持 `vc.pack.v0.3` 与 exact request，不扩写单值 modality

实现位于 `praxis_virtualcell/multiomics_input.py`。编译入口只接受：

- exact、重新 strict-validate 的 `VirtualCellRequestV2`；
- exact `RegisteredPack`，其 embedded manifest 必须是 `vc.pack.v0.3`；
- exact、backed `CanonicalMuDataView` 及 exact ordered modality views；
- exact `MultiOmicsInputContractV1`；
- exact `AdapterIdentity`。

Request 的 species scientific name/taxonomy、task、outputs 与 primary input modality 必须与
Pack、target slot 和输入合同一致。Pack 的 `perturbations.target_modality` 必须精确指向合同的
target slot。P18 不修改 `vc.request.v2`、Pack schema、CapabilityRegistry、ExecutionPlan、Broker、
Adapter SDK、API 或 JobStore。

### 2. 联合输入使用有序 required/optional slots

P18 冻结以下 strict/frozen schemas：

| Schema | 作用 |
|---|---|
| `vc.multiomics-modality-slot.v1` | 固定 slot key、required/optional、modality ontology、representation 与 feature contract |
| `vc.multiomics-input-contract.v1` | 固定 model reference、species/assembly、task/outputs、target slot、join/missingness policy 与 ordered slots |
| `vc.multiomics-layer-input.v1` | 固定一层真实 membership、mask、alignment report、matrix/content/storage identity 与 shapes |
| `vc.multiomics-observation-semantics.v1` | 固定 condition、split、cell semantics、perturbation、control、dose/time 与单位 |
| `vc.multiomics-model-input.v1` | 交叉绑定 request、Pack、view semantics、adapter marker、layers、join/missingness 与 abstention |

合同至少包含两个不同的 ordered slots。每个 required slot 在 join 前独立检查；不能用已存在
modality 的 intersection 掩盖缺失 required modality。Target slot 必须显式存在且为 required。
Optional slot 只有在 adapter 所拥有的 exact joint contract 把它声明为 optional 时才能缺失；
缺失时保留 typed absent layer，但不产生 matrix、alignment report、shape 或 data identity。

### 3. 每层独立 feature alignment，禁止 fill 与隐式变换

每个 present slot 复用既有 `align_features`，并保留独立 `AlignmentReport`。合同和 report
共同绑定：

- taxonomy、assembly、modality ontology；
- feature namespace name/version 与 ID format；
- source/target feature IDs、source/target shapes；
- alias、aggregate、drop、reorder 的 canonical operation order；
- mapping asset ID/path/SHA-256，并与 embedded Pack JSON asset 交叉核对；
- feature contract 与 alignment report fingerprints。

P18 对任意 `fill` rule 或 `fill` alignment step 一律 fail closed，包括填 0。它不执行 library
size、log、scale 或其他 normalization，不做 imputation，不自动补 feature，也不跨 namespace、
assembly、taxon 或 modality 猜 mapping。

Request 的 genetic target 另有更窄的 source-target gate：只接受 `gene` 或
`gene_combination`，映射到 Pack 明示的 `genetic` perturbation；targets 必须按 exact order 匹配
Pack declaration，并存在于 target modality 的 source feature identity。若 target 在 alignment
中只有一条一对一 identity/alias 路径，request source target 才能确定性映射到 model target
feature。涉及 aggregate、
drop、多对一、未知、歧义或反向猜测时一律 fail closed。

### 4. Observation join 与 missingness 不造行

P18 只支持两组封闭策略：

| Join | Missingness | 行为 |
|---|---|---|
| `required_inner` | `reject` | 对所有 present layers 取真实 shared observation rows；每层按相同 joined order 切片 |
| `global` | `explicit_mask` | 保留各层真实 local rows，并为 joined/global identity 生成显式 membership mask |

其他策略组合全部拒绝。Global observation IDs 必须等于各 modality membership 的 union；
paired views 要求每层都有相同 observations；partially-paired views 只能使用真实 shared rows
或显式 mask。真实数值为 0 的 row 仍是 observation，不得被当作 missing；P18 从不 padding、
zero-fill、impute 或制造 observation。

Join 与 missingness 分别有独立 fingerprint，且 model-input identity 同时包含 ordered layer、
source/input observation IDs、mask、feature order、shapes 与 policy。任何 stale hash、重排、
伪造 membership 或 mask 都会 fail closed。

### 5. View semantics 与矩阵内容都进入可重放 identity

Root-free serialized bundle 嵌入 observation semantics，并重新验证 `vc.pack.v0.3` 子集视图中
可验证的规则：condition signature、control self-match、可见 matched-control context、声明过的
condition/perturbation、dose/time 单位白名单，以及 `target_ids` split leakage guard。Embedded
semantics、global membership、source modality/feature/storage identity 与 Pack fingerprint 共同
形成 view identity；只保留孤立的 caller-supplied view hash 不足以通过解析。

矩阵本身不序列化进 JSON。每个 present layer 保存包含 storage、dtype、shape 与 canonical bytes
的 matrix fingerprint。Runtime `PreparedMultiOmicsModelInput` 立即把 dense/CSR/CSC 转成内部
byte-backed snapshot；每次公开访问都重新 materialize，因此调用方修改返回的 sparse object
不会改变内部 snapshot。Replay 时逐层复核 key/order、shape、storage 与 content fingerprint。
矩阵值变化会改变 model-input identity；矩阵内容 fingerprint 是 runtime-bound reference，只有
配对 snapshot 验证后才形成完整 runtime input。

### 6. Adapter/Broker 字段是 contract-only marker，不是执行证明

Adapter identity 只证明 caller 提供的 exact identity 在结构上拥有相同 joint input contract
fingerprint、task 与 outputs。Serialized bundle 明示：

~~~text
broker_agent=ModelBrokerAgent
broker_resolution=identity_only_not_registry_evaluated
executable=false
execution_performed=false
execution_step_created=false
abstain=true
abstain_reason=contract_only_execution_not_authorized
~~~

P18 编译器不调用 ModelBrokerAgent、CapabilityRegistry、model registry、wrapper、model 或 LLM，
也不创建 ExecutionPlan 或 execution step。`model_fingerprint` 与 adapter output-contract
fingerprint 仍是 caller-declared references，不是 artifact/release/environment 的自验证证明。
因此 P18 不能被解释为 registry compatibility、adapter readiness 或模型可执行性已经通过。

## 验证结果

Completion code 的本地安全验证为：

- focused P18 suite：44 passed；
- adjacent suites：259 passed；
- safe broad gate：1,531 passed，48 skipped，387 deselected；
- Ruff、format、`py_compile`、`git diff --check`：passed；
- optional MuData collection：因本地未安装 `mudata` 而 unavailable；
- global `pip check`：polluted environment 中存在既有 invalid/conflicting distributions，不能作为 gate。

这些结果只证明 deterministic engineering contract 与 fail-closed conformance，不含模型预测、
benchmark 或科学证据。

## Packaging evidence 与限制

Exact completion code commit 的两个独立 clean `git archive` offline builds byte-identical：

~~~text
wheel size       1,132,811 bytes
wheel SHA-256    015724a90656706c0441e4f4f873ee51f8db87dfaae9de35a3e841e7c70b2b7c
entries          367
React static     14
tests            0
AppleDouble      0
P18 module       present
~~~

Official strict offline script 因隔离 cache 缺 locked `packaging==26.2` 而 fail closed。Clean
no-deps smoke 因缺 `pydantic` 失败；继承 polluted system-site 的 smoke 通过，但不是权威 clean
install 证据。该 wheel 没有 push、publish、release 或 deploy。

## 后果与边界

P18 状态为：

~~~text
contract_defined=true
implementation_complete=true
tests_passed=true
artifact_ready=true
real_multiomics_model_acceptance=pending
science=NOT_RUN
product_policy=NO_NEW_DECISION
production_promoted=false
published_or_released_artifact=false
~~~

`artifact_ready=true` 仅指 exact code commit 的本地可重复工程 artifact。Registry 保持
5 releases / 0 native / 0 promoted，未生成 validation evidence、operator decision、promotion、
Virtual Cell release 或产品能力声明。

P18 全程未访问网络或外置资产，未运行 GPU、training、调参、wrapper、model 或科学任务，
未操作 `.53`、服务或端口，未 push、release、deploy，也未运行 Golden/GEM/Norman science。
真实 multi-omics acceptance 仍需另行授权的固定数据/模型、单组学 baseline、ablation、主指标、
CI、external 与 OOD gates；未通过时只能保留本合同及诚实负结果。

P19 后续合同状态与当前下一 gate 以 [P19 completion report](../reports/phase19/PHASE19_COMPLETION.md)
和 [documentation index](INDEX.md) 为准；该后续工作不回写或提升 P18 的科学结论。
