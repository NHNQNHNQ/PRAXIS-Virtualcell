# ADR-0016：Controlled Pack Factory 合同

- 状态：Accepted（P19 engineering contract complete；real external ingestion and operator acceptance not run）
- 日期：2026-08-07
- 唯一起始基线：`871c5a8a4265f5b8fe5c2c6e35d418644bf1c4be`
- Completion code SHA：`42eabe63ea1a444d8b2ad14cecba6c9d6fa351d5`
- Completion tree：`b4bd63833adc89bd1e30e9595d2cb6b38a3e005f`
- Source date epoch：`1786034362`
- 分支：`codex/p19-controlled-pack-factory`
- 前置：ADR-0003、ADR-0005、ADR-0007、ADR-0009、ADR-0010、ADR-0014、ADR-0015
- 状态码：`P19_CONTRACT_COMPLETE_REAL_EXTERNAL_FIXTURE_OPERATOR_SCIENCE_POLICY_NOT_RUN`

## 背景

P7 已把上传文件原样写入 quarantine，并生成 `vc.upload-receipt.v1`；P8 已提供可逐次
重验的 Pack product index；P12–P18 已把模型、adapter、execution 与 multi-omics 输入
合同分层。此前仍缺一条受控且不可跳级的数据接入路径：任意有效 Pack 路径可以直接写入
本地 index，却没有强制绑定原始 receipt、完整 metadata/mapping review、strict validation
report 和具名 registration-only operator decision。

P19 只补齐该工程治理链。它不把上传变成数据真相，不处理矩阵，不选择或训练模型，也不
创建 checkpoint、model card、benchmark、scientific evidence、promotion eligibility 或
production promotion。本阶段只使用仓库 tiny deterministic engineering fixtures；计划中的
Git 外真实 tiny fixture 和独立 write-new output root 没有获得 exact 授权，状态均为
`NOT_RUN`。

## 决策

### 1. 生命周期身份必须分层且逐级显式

唯一受支持的写入链为：

~~~text
immutable quarantine receipt
→ candidate Pack identity
→ exact metadata/mapping review
→ deterministic strict validation report
→ named registration-only operator decision
→ factory-registered Pack
→ optional append-only supersession
~~~

各层使用独立 canonical JSON fingerprint。Receipt、candidate、review、validation、decision、
registration 和 supersession 不合并为一个可覆写状态，也不允许下游布尔值反向制造上游
事实。`factory_registered=true` 只表示该 exact 链完成受控登记；它不蕴含
`model_compatible`、`environment_compatible`、`adapter_compatible` 或 `executable`。

### 2. Receipt 只绑定原始字节，species 只作路由提示

Factory 重新读取 P7 quarantine directory，要求其中只有 regular、non-symlink 的 `payload`
和 `receipt.json`，并重新核对 upload UUID、receipt bytes、payload size 和 SHA-256。Candidate
必须把 receipt fingerprint、receipt-bytes hash、upload ID、payload size/hash 完整绑定，并
让原始 payload 的 exact bytes 成为 Pack 实际 matrix 或 multi-omics data asset；不能用一个
未被消费的附加 asset 冒充来源。

P7 `species` 的 human、mouse、yeast、bacteria 值全部只是 routing hint，不是 exact taxon
truth。Exact taxon 只来自 candidate manifest，并由 reviewer 对 exact taxon claim 单独确认。
尤其 coarse `bacteria` receipt 不能自动推断为 *Escherichia coli* 或任一
NCBI Taxonomy identity。`taxon_review_binding` 只证明 manifest taxon 与 reviewer-confirmed
claim 一致，不证明 receipt 已提供 exact taxonomy。

### 3. Candidate 只能声明，不得静默转换或推断

`vc.pack-candidate.v1` 接受 operator-authored `vc.pack.v0.2` 或 `vc.pack.v0.3` root，并冻结
完整文件树、manifest、source asset、metadata claims 和 mapping summaries。每个 claim 明示
`operator_declared` 或 `inferred_candidate` origin；两者都必须由 reviewer 对 exact claim
fingerprint 逐项确认，inferred candidate 不会自动升级为数据真相。

必须逐项确认 taxon、assembly、cell identity、modality、feature namespace、value semantics、
condition、control、unit、split、leakage group 和 feature mapping。Mapping document 必须是
Pack 内声明的 JSON asset，绑定 ID/version/path/size/hash、source/target namespace、完整有序
feature 集及 unmapped/duplicate/out-of-domain/order report。Registration gate 只接受 exact
identity-only、order-preserving mapping；P19 不做 normalization、fill、imputation、
deduplication、reordering、random split 或 identifier conversion。

### 4. Validation report 必须完整，warning 不能当作 pass

`vc.pack-validation-report.v1` 使用完整、固定顺序的 checks，包括：

- exact metadata review；
- immutable receipt bytes 和 candidate tree；
- modern Pack schema 与 actual source payload binding；
- `taxon_review_binding`；
- metadata/manifest、unit 和 feature-mapping binding；
- full `PackRegistry`/canonical view validation；
- manifest-declared files only；
- no forbidden transformations。

`pack_valid` 只对应底层 strict Pack validation；只有所有 checks 通过且 warnings 为空时，
`passed=true` 与 `registration_allowed=true` 才成立。失败报告被保留，但不会写入可消费
registration。

### 5. 具名 operator decision 只覆盖 registration

`vc.pack-operator-decision.v1` 必须绑定 exact candidate、review、validation report、Pack
ID/version/fingerprint，并使用 `decision_scope=pack_registration_only`。具名 ID 和 reason 是
本地 append-only artifact 的一部分，但该 decision 固定
`scientific_evidence_decision=false`、`product_promotion_decision=false`。测试 fixture 中的
synthetic reviewer/operator 只证明合同，不是一次真实组织审批。

### 6. Store 与 index 必须显式注入并采用 fail-closed commit

Registration library 和 CLI 必须同时接收：

- 显式传入、已通过 exact marker 验证的 `PackFactoryStore`；
- 显式 absolute `PackIndex` 路径，其 parent 已存在且 canonical。

Store 只能由 `PackFactoryStore.create()` 在不存在的 write-new directory 初始化。Create 使用
exclusive/non-following write 生成并 fsync exact `.factory-store.json` marker，再 fsync store
directory；marker 的唯一内容是 `{"schema_version":"vc.pack-factory-store.v1"}\n`。`open()` 必须逐字节验证
regular、non-symlink marker，拒绝任意普通既存目录，避免 CLI 把用户目录误当输出 root。
Absolute/canonical/write-new 要求属于 supported `create()` 初始化入口；`open()` 会 resolve
显式路径并按 marker 验证。Marker 是 capability marker，不是对具备 filesystem write 权限者的
密码学 provenance proof，因此不得手工创建 marker。

初始化后的 Store 以 content-addressed canonical JSON append-only 保存生命周期 artifacts。Index 先写入
Pack identity、factory registration fingerprint 和 exact store root，随后 store 才 append
registration commit。该短暂状态按 `pending → committed` 理解：在 registration artifact
落盘前，任何 index consumer 都必须回查 store 并把记录判为 invalid/fail closed；只有 index
与 store 双向一致后才可消费。相同 exact chain 可安全重试完成 commit，不能人工放宽或把
pending 当成功。

### 7. Pack index v2 兼容读 v1，但旧写入口退役

`vc.pack-index.v2` 增加 `factory_registration_fingerprint` 与 `factory_store_root`。Reader 同时
接受 v1/v2；旧 v1 entry 被投影为两字段均为 `null`，保持 legacy readable，但不会被追认成
factory-approved。任何新写都使用 v2。

旧 `PackIndex.register(pack_root)` path-only 写法已退役并 fail closed。唯一 CLI register
入口要求 upload directory、Pack root、candidate/review/validation/decision JSON、显式 index
和显式 store；`inspect`、`validate`、`list`、`compatibility` 与 `run` 的只读/执行边界不变。

### 8. 公共 API/UI 只读、root-free 且 free-text redacted

公共面只增加 `GET /api/pack-factory`。没有 POST/PUT/PATCH/DELETE authoring 或 register
route，`write_api_enabled=false`。Projection 分开 receipt、candidate、review、validation、
decision、registration、supersession，并明确 quarantine、candidate、factory-registered、
model-compatible、executable 五层。

Projection 不返回本地 root/directory，也不返回 reviewer/operator 原始 ID、rationale、reason
等 free text；operator identity 仅以 fingerprint 表达，validation 只返回 canonical check
codes/status。Factory registered records固定 `model_compatible=null`、`executable=false`、
`scientifically_validated=false`、`production_promoted=false`。前端只读取该投影，没有管理
写控件。

## 验证结果

最终 completion commit 的本地 gates：focused P19 `23 passed / 1 skipped`；combined focused+
adjacent four-file gate `108 passed / 1 skipped`；safe Python gate
`1,554 passed / 49 skipped / 387 deselected`；legacy gate
`1,143 passed / 58 skipped / 105 deselected`；frontend typecheck/lint/build、Ruff check、P19
changed-file format、`py_compile` 与 `git diff --check` 均通过。Skip/deselect 保持可选依赖和
external/science 边界；本地未安装的 `mudata` 没有联网补装，也没有记为 pass。

已冻结的解释边界是：所有 tiny fixtures 仅证明 deterministic contract conformance；没有
真实外置数据接入、模型调用、预测质量或 operator/science/policy acceptance。

## Packaging evidence 与限制

P19 没有改变 product SemVer、API/runtime protocol、release tag 或 publication state。以
`SOURCE_DATE_EPOCH=1786034362` 对 exact completion code 作两个独立 offline clean-archive
build，wheel byte-identical：`1,154,421` bytes、SHA-256
`1231f948e6f519b9cea66e5ab0e7ccb41b3b7f5a7aa73efdd7dbaf885bfa969f`、`368` entries、
React `14`、tests `0`、AppleDouble `0`。Source/wheel `pack_factory.py` SHA-256 均为
`06fb5267c47e8fcf8bcc596e18c9d12e3cb429b0670b662eb0b2ae448b560508`，ZIP integrity passed。
这不是依赖闭包/clean-install proof，也不构成 push、publish、release 或 deploy。

## 后果与边界

P19 状态为：

~~~text
engineering_contract=COMPLETE
real_external_fixture=NOT_RUN
authorized_new_output_root=NOT_RUN
real_operator_action=NOT_RUN
science=NOT_RUN
product_policy=NO_NEW_DECISION
training_performed=false
checkpoint_created=false
evidence_created=false
production_promoted=false
~~~

P19 没有访问 network 或外置真实 fixture，没有启动真实 ingestion window，没有训练、调参、
GPU、checkpoint、model card、benchmark、external/OOD science、evidence 或 promotion，也没有
操作 `.53`、push、release 或 deploy。其完成只使 P20 contract-only Training Pipeline 成为
下一 eligible 本地工程 gate；P20 的实际 starting SHA 必须从 P19 docs-closure 后的 Git
history 读取，P19 completion code SHA 不能代替未来 docs-closure identity。
