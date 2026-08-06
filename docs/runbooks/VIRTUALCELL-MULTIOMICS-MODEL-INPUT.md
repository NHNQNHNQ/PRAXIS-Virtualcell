# Typed Multi-omics Model Input 本地合同运行手册

本 runbook 只用于 P18 `vc.multiomics-model-input.v1` 的 contract-only 构造、静态审计与安全
测试。它不下载数据或权重，不启动服务，不调用 Broker/Registry/wrapper/model，不运行 GPU、
training、benchmark 或科学任务，也不执行 evidence、promotion、push、release、deploy 或
`.53` 操作。

## 1. 固定身份与允许的状态解释

从仓库根只读检查：

~~~bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git branch --show-current
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git status --short
~~~

P18 completion code identity：

~~~text
starting SHA          f253664239e4b1c9665301cf1bdf4e117a3e9c31
completion code SHA   626c71ffd1ce18a5adc200f6a6e376e57b269beb
completion tree       2b570398caff6cf955d789c3cb4a7a77dc13a082
branch                codex/p18-multiomics-cell-state
status                P18_CONTRACT_COMPLETE_REAL_MULTIOMICS_MODEL_ACCEPTANCE_PENDING
~~~

后续 docs closure 或其他 phase 会改变 HEAD/tree；不要回退工作树去匹配旧 SHA。P18 code、
focused tests 与 wheel evidence 绑定 completion code SHA。

允许的结论只有：typed multi-omics input contract complete、real multi-omics model acceptance
pending、science NOT_RUN、policy NO_NEW_DECISION。不得写成真实模型可执行、baseline beaten、
scientifically validated、promotion eligible、published、released 或 deployed。

## 2. Contract-only 输入链

P18 的唯一链路是：

~~~text
exact VirtualCellRequestV2
  + exact RegisteredPack / embedded vc.pack.v0.3 manifest
  + exact backed CanonicalMuDataView
  + exact ordered MultiOmicsInputContractV1
  + caller-provided exact AdapterIdentity
  -> per-layer feature alignment
  -> deterministic observation join / explicit missingness
  -> root-free MultiOmicsModelInputV1
  -> byte-backed PreparedMultiOmicsModelInput snapshots
  -> fixed abstention; no execution step
~~~

只读定位实现：

~~~bash
rg -n '^class (MultiOmics|Prepared)|^def compile_multiomics' \
  praxis_virtualcell/multiomics_input.py
~~~

不要把 `broker_agent=ModelBrokerAgent` 当成调用记录。必须同时看到
`broker_resolution=identity_only_not_registry_evaluated`、`executable=false`、
`execution_performed=false`、`execution_step_created=false` 与 `abstain=true`。

## 3. 最小 contract-only 使用方式

调用方必须先通过既有 Pack registry/loader 获得 exact `RegisteredPack` 与 backed
`CanonicalMuDataView`，再显式构建：

1. 至少两个 ordered modality slots；
2. 每个 slot 的 required/optional、ontology、namespace 与 exact feature contract；
3. target slot、join policy、missingness policy；
4. owning adapter identity，其 input-contract fingerprint 精确等于 joint contract fingerprint；
5. exact request，其 species/task/output/primary modality/genetic targets 与合同和 Pack 一致。

允许调用的 API 是：

~~~python
from praxis_virtualcell.multiomics_input import compile_multiomics_model_input

prepared = compile_multiomics_model_input(
    request,
    registered_pack,
    backed_mudata_view,
    multiomics_input_contract,
    adapter_identity,
)

model_input = prepared.model_input       # root-free、无 matrix payload
runtime_layers = prepared.matrices       # 每次访问重新 materialize snapshot
reports = prepared.alignment_reports     # 每个 present layer 的独立 report
~~~

该片段只编译并验证输入，不授权把 `runtime_layers` 交给 wrapper/model。不要在本 runbook 中补写
Broker、execution plan、model invocation 或 prediction 示例。

## 4. Required/optional 与 target 审计

审计 joint contract 时逐项确认：

- slots 保持声明顺序，key 与 modality ontology identity 唯一；
- 至少两个不同 present modalities 才能形成 joint input；
- 每个 required slot 在 join 前独立满足；
- target slot 存在、required 且 present；
- optional 缺失产生 typed absent layer，但没有 matrix/report/shape/data fingerprint；
- request primary modality 精确匹配 target slot；
- request 只接受 `gene` 或 `gene_combination`，显式映射 Pack `genetic` declaration；
- request source targets 按 exact order 匹配 Pack，并只能经 identity 或一对一 alias 映射；
- aggregate、drop、多对一、未知或歧义 target 立即 fail closed。

任一 required slot 缺失时，没有 execution step，也不能用其余 modality 的 intersection 放行。
Optional 并非自动可丢弃；其缺失资格来自 adapter 所拥有的 exact joint contract。

## 5. Feature alignment 与 mapping 审计

每个 present layer 都必须有独立 `vc.alignment-report.v1`，并核对：

- report contract fingerprint 等于该 slot feature-contract fingerprint；
- source/target feature IDs 与 source/aligned/input width 一致；
- taxonomy、assembly、modality、namespace version 与 ID format 完全一致；
- alias/aggregate/drop/reorder steps 为 canonical order，且能精确推出 target feature order；
- mapping reference 与 Pack 中同一个 JSON asset 的 ID/path/SHA-256 一致；
- alignment report fingerprint 可由 embedded report 重算。

以下行为必须拒绝：

~~~text
fill rule 或 fill step（包括 value=0）
自动补 feature
未声明的 alias/aggregate/drop/reorder
跨 taxon / assembly / namespace / modality 猜 mapping
隐式 normalization、scale、log transform 或 imputation
~~~

不要为让测试通过而新建 mapping 文件、修改 Pack root 或读取外置资产。

## 6. Join、missingness 与 no-fabrication 检查

只允许：

- `required_inner + reject`：取所有 present layers 的真实 shared observations，并按 joined order
  选择真实行；
- `global + explicit_mask`：各层保留真实 local rows，missingness 只由显式 boolean membership
  mask 表达。

审计时检查：

- global observations 是 modality union，顺序来自 canonical view；
- paired view 每层 observations 完全相同；
- partially-paired view 的 inner rows 确实存在于每层；
- global policy 不把 local matrix pad 到 global shape；
- `source_observation_ids`、`input_observation_ids`、mask、shape 与 matrix row order 一致；
- 真实全零 row 保留为 observation，不能当作 missing；
- join/missingness fingerprints 能从 embedded identities 重算。

任何 fabricated row、zero-padding、implicit fill、mask/order tamper 或 empty join 都是合同错误。

## 7. Observation semantics 与 view identity

Serialized model input 嵌入 `vc.multiomics-observation-semantics.v1`。只读重放必须重新检查：

- condition、split、perturbation 与 matched-control IDs 都来自 Pack declarations；
- 同一 condition 的 perturbation、control、cell identity/state/context、dose/time 与 split signature
  一致；
- control condition self-matches；
- 子集视图中可见的 matched control 使用 control perturbation 且 context/time/split 相同；
- dose units 只在 `1/M/mM/uM/nM/pM/g/L/mg/L/ug/mL`；
- time units 只在 `s/min/h/d`；
- Pack 声明 `target_ids` leakage guard 时，同一 target 不跨 split；
- semantics fingerprint 与 view identity fingerprint 都可从 embedded data 重算。

子集视图可以未选中某个 matched-control row 或某个完整 partition；这不等于允许伪造 control。
完整 Pack 的全量 foreign-key/partition 验证仍由原 `vc.pack.v0.3` loader 负责。

## 8. Matrix identity、snapshot 与 replay

Serialized JSON 不含矩阵值，只保存每层 matrix fingerprint 与 storage/shape identity。Runtime
准备阶段必须：

1. 只接受 non-empty、finite numeric dense/CSR/CSC；
2. sparse indices 已排序且无重复；
3. 复制为 immutable bytes snapshot；
4. 重放时核对 layer key/order、shape、storage 与 matrix fingerprint；
5. 每次 `prepared.matrices` 访问重新 materialize，外部 sparse attribute 替换不影响内部 snapshot。

因此 matrix fingerprint 是 runtime-bound reference；单独解析 JSON 不能证明矩阵值存在。只有
`PreparedMultiOmicsModelInput` 成功绑定对应 snapshots，才可以声称 runtime input replay 完整。
即便如此，P18 仍固定 abstain，不得执行模型。

## 9. 安全测试与静态 gate

Focused gate：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  praxis_virtualcell/tests/test_multiomics_model_input.py

python -m ruff check \
  praxis_virtualcell/multiomics_input.py \
  praxis_virtualcell/tests/test_multiomics_model_input.py

python -m ruff format --check \
  praxis_virtualcell/multiomics_input.py \
  praxis_virtualcell/tests/test_multiomics_model_input.py

python -m py_compile praxis_virtualcell/multiomics_input.py
git diff --check
~~~

Completion validation：

- focused：44 passed；
- adjacent：259 passed；
- safe broad：1,531 passed，48 skipped，387 deselected；
- Ruff / format / `py_compile` / diff：passed。

Safe broad gate 必须继续排除 Golden/GEM/Norman science 与其他未授权真实科学入口。不要为了
扩大 pass count 而运行模型、training、GPU 或外置数据。

Optional `test_mudata_alignment` collection 因本地没有安装 `mudata` 而 unavailable；不要联网
安装。Global `pip check` 在 polluted environment 中报告既有 invalid/conflicting distributions，
不能作为 P18 authoritative gate。

## 10. Packaging 复核

Exact code commit 的 reproducible wheel evidence：

~~~text
wheel size       1,132,811 bytes
wheel SHA-256    015724a90656706c0441e4f4f873ee51f8db87dfaae9de35a3e841e7c70b2b7c
entries          367
React static     14
tests            0
AppleDouble      0
P18 module       present
~~~

两个独立 clean archive 的 offline builds byte-identical。Official strict offline script 因 cache
缺 `packaging==26.2` fail closed；clean no-deps smoke 因缺 `pydantic` 失败；polluted system-site
smoke 虽通过，但不是 clean-install proof。不得据此 push、publish、release 或 deploy。

## 11. 失败语义与停止条件

下列任一情况必须返回 `MultiOmicsInputError`/contract error，不得降级、补值或继续：

- request/Pack/view/contract/adapter 不是 exact canonical type 或 identity mismatch；
- required/target modality 缺失，或 present modality 少于两个；
- feature、mapping、alignment、target source 映射不精确；
- join 为空/歧义，membership、mask、semantics、storage 或 content hash 不一致；
- 发现 fill、padding、imputation、normalization 或 fabricated observation；
- serialized object 含 unknown field、subclass、`model_construct` bypass 或 stale fingerprint；
- runtime matrix 非 finite、非 numeric、shape/storage/content 不匹配。

出现以下任一外部行为立即停止并记录越界：

- Broker/Registry/wrapper/model/LLM/GPU/science 被执行；
- 启动 API、服务、端口或操作 `.53`；
- 访问网络、下载外置资产或权重；
- training、调参、baseline/ablation/CI/external/OOD science 未经单独授权即运行；
- 创建 evidence、operator decision、promotion、release、push 或 deploy。

最终状态必须保持：

~~~text
P18_CONTRACT_COMPLETE_REAL_MULTIOMICS_MODEL_ACCEPTANCE_PENDING
science=NOT_RUN
policy=NO_NEW_DECISION
registry=5 releases / 0 native / 0 promoted
~~~

工程合同完成不等于真实 multi-omics model acceptance。只有后续独立授权和全部预注册科学 gates
通过后，才可讨论 evidence 或 promotion；P18 本身不能生成这些结论。
