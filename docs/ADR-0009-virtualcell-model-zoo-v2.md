# ADR-0009：Virtual Cell Model Zoo v2 分层身份与状态治理

- 状态：Accepted（Phase 12 engineering complete）
- 日期：2026-08-02
- 唯一起始基线：`b19c896202bea56f894d0ad540501331af42a40c`
- Completion code SHA：`1a5464fb0d2d9e105058f6797d92efd69783e5b2`
- 分支：`codex/p12-model-registry-v2`
- 前置：ADR-0004、ADR-0007、ADR-0008
- 范围：Phase 12；不实施 Phase 13 Adapter SDK，不作 operator promotion 决定

## 背景

P6 已冻结 `vc.model-card.v1`、`vc.environment.v1`、computed compatibility 和
deterministic execution plan，并保持 `scientifically_validated=false`。P8 又证明
Pack、model card、asset 和 job identity 可以被产品面只读展示；P9 则保留了一个
能运行但未胜简单 baseline 的真实负结果。这些边界继续有效。

现有 model card 同时承载 capability、asset 声明、资源要求和历史 provenance，
但尚不能独立指认：

- 某一组精确模型 artifact bytes；
- 可重放的 package/runtime/environment；
- 某一版本 adapter 的合同身份；
- 与 exact Pack、model、environment、adapter 和 protocol 绑定的 evidence；
- 引用 exact evidence 的 operator product-policy decision。

因此 `available`、本地文件存在、一次成功执行或 card fingerprint 都不能被当成科学
验证或产品 promotion。P12 补齐这些身份和迁移边界，并让 Pack-aware
`CapabilityRegistry` 把 exact evidence 和 policy 纳入执行硬门；本阶段不下载或运行
权重、不训练、不重做 P8/P9 科学分析。无 Pack 的 legacy 路径保持为明确标记的兼容
边界，不得被描述为 v2 治理路径。

## 决策

### 1. 保持 v1，新增独立不可变记录

`vc.model-card.v1` 原样兼容，不把 P12 字段塞回旧 card，也不修改旧 card fingerprint。
P12 新增以下 canonical JSON 合同；所有合同严格拒绝未知字段和类型强制转换，使用
UTF-8、递归 JSON-safe、key 排序、无空白、`allow_nan=false` 的 bytes 计算小写
SHA-256 fingerprint：

| 合同 | schema | 唯一职责 |
|---|---|---|
| `ArtifactIdentity` | `vc.model-artifact.v1` | 可选受限 URI、必填相对 cache key、size、SHA-256、media type、license、source 和安全加载策略 |
| `EnvironmentIdentity` | `vc.model-environment.v1` | Python/native PEP 503 canonical package 版本、CPU architecture、lockfile 或 image digest、resource/accelerator 声明和 adapter fingerprints；legacy 可保留原 module names |
| `AdapterIdentity` | `vc.model-adapter.v1` | adapter 名称、版本、纳入 record identity 的 implementation locator、task/input/output 合同引用；不是 Adapter SDK |
| `ValidationEvidence` | `vc.model-validation-evidence.v1` | exact Pack×model×environment×adapter×protocol、baseline、primary metric 和 result hash |
| `OperatorPolicyRecord` | `vc.model-operator-policy.v1` | 具名 operator 对 exact capability fingerprint 和 evidence 作出的版本化决定 |
| `ModelReleaseRecord` | `vc.model-release.v1` | 组合 card、artifact、environment、adapter、evidence 和 policy 引用；native release 只绑定一个 exact Pack，legacy release 另保留结构化 `legacy_status` |
| `RegistryLifecycleEvent` | `vc.model-registry-event.v1` | 对 exact release 的 append-only catalog/readiness/revoke/supersede 事实 |
| `RegistryState` | `vc.model-registry-state.v1` | 从完整 event chain 归约出的四个 registry 状态 |
| `ModelRegistryV2` | `vc.model-registry.v2` | 保存分层 records、release bindings 和 lifecycle history 的不可变根合同 |
| Public catalog | `vc.model-registry-catalog.v2` | `ModelRegistryV2.public_catalog()` 产生的路径脱敏只读投影 |
| `ComposedModelRegistryV2` | `vc.model-registry-composition.v1` | 只读、有序的 base/domain source identity；不伪造第三条 lifecycle authority |
| Composed public catalog | `vc.model-registry-catalog.v3` | composition identity 与两份 source fingerprint 的路径脱敏只读投影 |
| `LegacyMigrationReceipt` | `vc.model-registry-legacy-receipt.v1` | 保留 repo-relative source/hash、nullable availability 和原始科学状态；永远 `binding_status=unbound` |
| `LegacyMigrationReport` | `vc.model-registry-legacy-migration-report.v1` | 汇总五张旧卡与 receipts；固定不 admission evidence、不 promotion |
| Environment snapshot | `vc.environment.v2` | 把 legacy/P17 runtime snapshot 与 exact `EnvironmentIdentity` 绑定；`vc.environment.v1` 保持 legacy |
| Direct-v2 snapshot budget | `vc.artifact-snapshot-budget-policy.v1` + `vc.model-environment.v2` + `vc.environment.v3` | write-new `EnvironmentIdentityV2` 把每次执行的私有 artifact snapshot payload/entry 上限纳入 release capability identity；只供 direct-v2，不能改写 v1/v2 bytes |
| Compatibility report | `vc.compatibility-report.v2` | 绑定 request、Pack、release、artifact、environment、adapter、evidence 和 policy 的当次计算 |
| Execution step | `vc.execution-step.v2` | 只承载已通过 v2 硬门的完整 execution binding；step/plan identity 排除 runtime paths |
| Execution plan | `vc.execution-plan.v2` | 只包含所有 v2 硬门均通过的 step；否则保存完整拒因并空计划 |
| Job execution identity | `vc.job-execution-identity.v2` | 从 v2 plan 固化 request、Pack、environment snapshot、各 release/component/evidence/policy fingerprints 和所列 snapshot verdicts |

同一合同 bytes 必须产生相同 fingerprint；任一有意义字段或绑定 fingerprint 改变都
产生新 identity。fingerprint 只证明 canonical record 内容，不证明其外部引用真实、
资产可取用、模型可执行或科学有效。

除 `schema_version` 外，`ModelRegistryV2` 根 record collections 固定为：

```text
artifacts / environments / adapters / evidence_records
policy_records / releases / lifecycle_events
```

公开的不可变操作包括 `from_dict()`、`to_dict()`、`fingerprint()`，按 fingerprint
查询 artifact/environment/adapter/evidence/policy/release，按 release fingerprint
归约 `state()`，构造 `public_catalog()`，以及返回新 registry 的 `append(event)`。
`from_v1_cards(cards)` 是旧卡兼容迁移入口；历史小型文件另由
`legacy_migration_report(registry, receipts)` 保留为 unbound receipts，不按名称猜测
缺失绑定。

Artifact 的 `cache_key` 必须是 canonical relative POSIX path。若声明 URI，只接受有
authority、无内嵌 credential 的 `https`、`s3`、`gs` 或 `hf`；`file:`、absolute path、
path traversal 和其他 scheme 一律拒绝；整个 registry 内 NFC-normalized、case-folded
后碰撞的 cache keys 也拒绝。Native environment 必须声明 Python version、CPU
architecture、使用 canonical PEP 503 lowercase spelling 且经 PEP 503 normalization
后无碰撞的显式 package versions，并至少绑定 lock digest 或 image digest。Legacy
environment 可精确保留 `torch_geometric`/`foo.bar` 一类 v1 import-module name，只按
raw exact string 检查重复；不得用 PEP 503 normalization 合并或改写它们，且缺口必须
显式标记。

当前 in-process runtime 只接受 `safe_load_policy=data_only`；
`restricted_deserializer`、`isolated_runtime` 和 `unavailable` 都必须 abstain，且
instantiate 前再次核对。`data_only` 仍只是 artifact record 的具名声明，P12 尚未以
类型系统证明每个 wrapper loader 只执行 data-only 操作；这是已知限制，也是本阶段不
创建真实 promoted release 的原因之一。

### 2. 执行相关身份必须双向绑定

一条可执行 release chain 至少显式引用：

```text
model-card fingerprint
artifact fingerprints
environment fingerprint
adapter fingerprints
validation-evidence fingerprints
operator-policy fingerprint
release fingerprint
```

Native release 的 `pack_fingerprints` 尽管为数组字段，也必须 exact length=1；它不能用
一条 policy 聚合多个 Pack scope。每条 evidence 的 Pack 必须等于该唯一 Pack。

Evidence 必须同时绑定 Pack、model card、environment、adapter、benchmark protocol、
baseline、metric/direction 和 result bytes，再由 release 反向引用。缺一项或任一
fingerprint 错绑时，历史结果只能保留为 unbound migration receipt，不能进入
`ValidationEvidence` 或静默补值。

Operator policy 必须引用 `ModelReleaseRecord.capability_fingerprint()` 所代表的 exact
scope 和至少一个 exact evidence fingerprint；release 再用 `policy_fingerprint` 绑定
该 policy，避免把 policy fingerprint 自身放进 capability hash 形成循环。任何
`production_promoted=true` 都要求被引用 evidence 本身明确满足所需科学门；operator
不能把 evidence 中的 `false` 或 unavailable 改写成 `true`。P12 只冻结并验证 schema，
不创建新的真实 operator-policy record。

Registry 根合同还要求 graph closure：environment 只能引用已知 adapters；evidence
只能引用已知 environment/adapters；policy 只能引用已知 evidence 和 release
capability；每条 evidence/policy record 必须被某个 release 精确引用。孤立 record
不能靠“尚未接线”留在 root 中制造伪状态。

### 3. 五类状态永久分层

```text
Pack:
  pack_valid

Registry:
  cataloged / artifact_ready / revoked / superseded

Computed per request:
  model_compatible / adapter_compatible / environment_compatible / executable

Scientific evidence:
  benchmark_passed / scientifically_validated / promotion_eligible

Product policy:
  production_promoted
```

这些字段不是自动递进枚举：

- `cataloged` 只表示 exact release identity 已登记；
- `artifact_ready` 只表示声明的 artifact bytes 已按 size/hash 重验可取用；
- `revoked`/`superseded` 只限制未来选择，不修改历史 job、evidence 或 release bytes；
- `model_compatible` 仍由每次 exact request×Pack×model scope 计算；
- `adapter_compatible` 独立计算 exact adapter task/output 与 environment binding；
- `environment_compatible` 在 environment identity、runtime/resource、artifact、wrapper
  readiness 和 adapter gate 上计算；
- `executable` 还必须加入 exact evidence×policy 与 lifecycle 硬门；这些都不能存成
  registry 真相；
- evidence state 只能来自冻结 protocol/result；
- `production_promoted` 只能来自独立 operator policy。

Registry event、migration、CLI/API projection 和 LLM 均不得把一个层的状态推导为另一
层。`production_promoted=false` 在 P12 migration 中只表示没有可用的 positive
operator-policy record，不是一项新的 operator 决定。

### 4. Registry history 是 append-only

Registry 状态由有序事件归约得到，不原地修改 release 或既有事件。每个事件用
`release_fingerprint` 绑定被操作 release，并绑定动作、全局 sequence、RFC3339
`recorded_at`、operator/reason、前序事件 fingerprint 和自身 fingerprint。允许动作只
覆盖：

- 登记 exact identity；
- 记录 exact artifact readiness；
- revoke exact release；
- 用另一个已知 exact release supersede 它；replacement 使用
  `target_release_fingerprint` 显式绑定。

同一 identity/version 对应不同 bytes、断裂的前序 fingerprint、对未知 release 的
revoke、self-supersede、缺 replacement identity 或会改写旧事件的输入全部拒绝。
Supersede target 必须在此前已 cataloged，且尚未 revoked 或 superseded。
Revoke/supersede 后旧记录和历史 execution identity 仍可审计；任何后续恢复或新版本
必须创建新 release identity 并追加新的 catalog event，closed 旧 release 不再接受
事件，且不能删除或覆盖历史。

P12 不提前实现 P22 的多用户、签名、远端同步或 operator-curated 持久 registry。
本阶段只需不可变 record 与确定性 append/reduce 合同；公开 CLI/API 保持只读。

### 5. v1 迁移保留原始事实，不补齐缺口

迁移使用现有五张 `vc.model-card.v1` 以及已经提交的 P8/P9 小型证据文件作
legacy/incomplete/no-promotion fixture。历史 P8/P9 文件只生成
`LegacyMigrationReceipt`/`LegacyMigrationReport`，不进入 `ValidationEvidence`。
Receipt 记录 `receipt_id`、repo-relative `source_path`、size/hash、可用的 declared Pack
fingerprint、nullable `available` 和三项保守迁移科学状态（允许 `null` 表示历史未记录）、
`binding_status=unbound` 和 reason codes；report
固定 `evidence_admitted=false`、`production_promoted=false`。映射固定为：

| v1/历史输入 | P12 结果 | 明确不产生 |
|---|---|---|
| 合法 model card | 保留原 card bytes/fingerprint；生成 catalog identity | `artifact_ready`、positive compatibility/execution 或 science |
| `status=planned/missing` | 原值写入结构化 `legacy_status` 并原样展示 | available/executable |
| `status=available` | 仅写入结构化 `legacy_status=available` | v2 artifact readiness 或 promotion |
| 缺 size/source/load-policy 的 asset 声明 | legacy/incomplete | 完整 artifact identity |
| 缺 package versions、lock/image digest 的环境声明 | legacy/incomplete | environment compatibility |
| P8 Golden manifest/result inventory | 保留 source hash 和已记录状态 | 新 benchmark/scientific verdict |
| P9 external result | 保留 `available=false`、`scientifically_validated=false` 和 reason codes | `benchmark_passed=true`、`promotion_eligible=true` |
| 无 exact operator policy | policy 缺席、`production_promoted=false`、Pack-aware `executable=false` | 虚构 no-promotion operator record |

Migration 不访问原始大数据、模型 cache、`.53` 或 remote，不重算 P8/P9 数值。无法
满足 P12 完整绑定的历史 evidence 保留为 `legacy_incomplete`，而不是猜测缺失的
Pack/model/environment/adapter/protocol identity。
P8 receipt 保持 `available=null`、`benchmark_passed=null`、
`promotion_eligible=null`，仅保留历史已有的 `scientifically_validated=false`；`null`
不得被转换为失败裁决。P9 receipt 保留 `available=false` 和三项已有的 `false` 科学
负状态。

迁移在内部保留 legacy card 的 exact raw `model_version`。若该值不适合作为公开
path-safe identifier，则 `release_id` 使用 model fingerprint 派生的安全 suffix，public
catalog 的 `model_version` 输出 `null`；不得改写原 card bytes 或回显不安全文本。

### 6. Registry catalog 公开投影只使用字段白名单

P12 复用既有产品入口：

```text
praxis-vc pack list
GET /api/packs
```

不新增写入型 CLI/API，也不新增专用模型管理服务。两条入口消费同一个确定性 public
projection，只公开非敏感声明、分层 fingerprints 和独立状态。外层继续使用
`vc.pack-catalog.v1`；其 `model_registry` key 保存完整
`vc.model-registry-catalog.v2`，每个 `model_capabilities[*].registry_releases` 保存按该
model name 过滤的同一 release 白名单投影。两处不能分别推导或改写状态。

Registry catalog projection 禁止返回 raw registry record，并至少排除：

```text
uri
cache_key
local_path / resolved_path / registry_path
asset_paths
source / safe_load_policy / implementation / packages
包含绝对路径的 source_note/provenance
```

实现必须按字段白名单构造 catalog response，不能先序列化 raw record 再依赖字符串
替换；公开的 identifier 本身必须是 canonical path-safe text。所有产品 payload 的
runtime `asset_paths` 必须在返回前删除，拒绝或异常消息也不得包含本地根目录。即使
source record 含 POSIX、Windows、UNC、`file:` URI 或 symlink-resolved path，CLI/API
输出都不能泄漏。

### 7. Pack-aware 执行必须通过 v2 evidence×policy gate

P6 `vc.model-card.v1`、历史 `vc.compatibility-report.v1`、
`vc.execution-plan.v1` 和既有 job bytes 继续可解析，不能被迁移重写。P12 产品
CLI/API/runtime 的 Pack-aware 入口无论使用默认、显式或环境变量 registry path，都
强制启用 v2 report/step/plan，并按同一个 exact release 逐项验证：

```text
request fingerprint
× RegisteredPack fingerprint
× ModelReleaseRecord fingerprint
× every ArtifactIdentity fingerprint and current readiness
× EnvironmentIdentity fingerprint
× required AdapterIdentity fingerprints
× exact-scope ValidationEvidence fingerprints
× exact-scope positive OperatorPolicyRecord fingerprints
× lifecycle state not revoked/superseded
```

任一引用缺失、错绑、hash 不符、scope 不符、environment 不匹配、evidence 未通过、
policy 缺席或 `production_promoted=false`，都必须令 report
`executable=false`、plan 无对应 step，并沿现有可靠性路径明确 abstain。Executable
必须同时要求 `model_compatible` 和独立的 `adapter_compatible`；Catalog
presence、legacy `available`、artifact readiness 或一次成功执行均不能绕过此门。

无 Pack 调用仍走显式标记的 legacy adapter，以保持既有兼容；该路径没有 v2 的完整
identity/evidence/policy 保证，不能被称为 P12-compliant、production-promoted 或
符合新的准确产品承诺。为保持 P8 library benchmark 兼容，直接构造低层
`ModelZooRegistry(custom_path)` 默认仍可得到 v1 registry；这是已知 legacy/test
boundary，不是获支持的 P12 产品执行入口。产品入口不得借 custom path 或环境变量绕过
v2。移除这些兼容边界需要独立授权和迁移计划。

JobStore 继续解析并保留 `vc.job-execution-identity.v1`；遇到 v2 plan 时写入
`vc.job-execution-identity.v2`，保存 plan/request/Pack/environment snapshot、每个
release/component/evidence/policy fingerprint，以及当次 lifecycle、science、promotion
与 executable snapshot。它不从 job history 重新查询当前 registry，也不因后来
revoke/supersede 改写旧 job identity。

### 7.1 U1 本地修订：research-only direct-v2 execution（未发布）

本修订不改写本 ADR 的历史 v1/v2/v3 record、fingerprint 或 production gate。它只为
新的通用 direct-v2 单模型技术执行定义一个**独立的、write-new**本地合同：

```text
vc.model-operator-policy.v2
  research_execution_authorized=true
  × research_execution_scope=research_only
  × exact Pack/release/artifact/environment/adapter/evidence/policy/lifecycle identity
→ vc.direct-v2-execution.v1
→ vc.job-execution-identity.v4
```

`OperatorPolicyRecordV2` 的 research authorization 与 `production_promoted` 互斥。
它不会把 `benchmark_passed`、`scientifically_validated`、`promotion_eligible` 或
`production_promoted` 从 false 变为 true。当前本地 synthetic fixture 的可执行结果如实显示
`scientifically_validated=false` 和 `execution_scope=research_only`；这不是把该 fixture 的
状态改写成通用 production 合同。未来 production execution 仍必须使用原有全正向 evidence +
`production_promoted=true` 门，不能借 v2 policy 绕过。

完成态 direct-v2 v4 要求严格 `vc.request.v2`、exact Pack、plan/report/receipt/per-call hash
一致，以及只含三段父链和 payload hash 的公开 trace（不含 payload、asset path 或 model input）。
缺 Pack 可写入 v4 hard-abstain，且 `pack=null`；它不能形成 completed result 或绕过 Pack gate。
v4 读取必须使用 request/report/provenance/trace 全部重算；缺任一 companion 即公开为 unavailable。
历史 v1–v3 的解析、签名、投影和 replay 语义保持不变。

这是 U1 的本地通用合同候选，不是发布、GitHub CI、wheel/archive、科学验证或生产授权；
它没有新增任何 AMR、MIC、物种或任务硬编码。

### 7.1a U2 本地修订：显式多模型 output reducer（未发布）

U2 不放宽 U1 的 `vc.execution-plan.v2`/`vc.job-execution-identity.v4` 单步骤语义。
只有 Broker 在 **wrapper、adapter 和 Pack 内容准备之前**解析到精确、显式注册的通用
`vc.output-reducer-policy.v1` 时，才把 provisional V2 多步骤计划写为
`vc.execution-plan.v3`。V3 将 callable-free `vc.output-reducer-binding.v1` 纳入 canonical plan
ID；policy 本身绑定 task、output-contract fingerprint、按顺序的
model/model-fingerprint/release-fingerprint/adapter-fingerprint，以及实现源码 fingerprint。没有
policy、顺序不匹配、共享 adapter/output contract 不精确，均返回 V2 空计划
`output_reducer_required`，绝不选择默认 mean 或子集执行。

V3 运行边界从当前 registry 再解析同一 binding；policy 被撤销、替换或实现源码漂移时，
prepared callable 不得继续运行，必须 hard-abstain。公开 binding、版本与 step receipt 的 model name
均为 path-safe public identifiers；非法 archive 值只投影为 unavailable，绝不回显路径。
direct-v2 public provenance 是 closed allowlist：V2 只允许 plan/reports/Pack view/adapter receipts/per-call
hash 与可选 domain identity，V3 仅额外允许 reducer receipt；未知字段在写入前拒绝。V4/V5 archive 的
trace 必须始终是三段 payload-free hash spine；损坏 trace 只公开为空数组并令 identity unavailable。

V3 运行逐步复核 wrapper、artifact、Pack、adapter input 与 output；任一步准备或执行失败即为
V3 空计划/硬弃权，不能丢弃失败步骤后继续 reduction。成功的
`vc.output-reducer-receipt.v1` 只包含 ordered step/input/output hash 与 reduced-output hash；
不公开 callable、entrypoint、source、path、payload 或数值输入。V3 只能带
`vc.direct-v2-execution.v1` 写入独立的 `vc.job-execution-identity.v5`；V3 缺 marker、
receipt/step 顺序/输出 hash 漂移均不可降级为 v2/v4 identity。v4 和更早 identity bytes/验证规则不改。

这一能力只由 generic synthetic scalar conformance 覆盖；它不是融合的科学验证、production
promotion、领域 policy、AMR/MIC 能力或临床输出。U2 仍是本地未发布候选。

### 7.2 U1 本地修订：base/domain registry composition（未发布）

`ComposedModelRegistryV2` 只接受两份已经独立验证的 `ModelRegistryV2`，以显式、
有序的 `base` 和 `domain` 角色组成只读 lookup view。它的
`vc.model-registry-composition.v1` fingerprint 仅绑定两份 source registry fingerprint；
源 registry 的 `to_dict()`、fingerprint、`vc.model-registry-catalog.v2` 和 lifecycle event
chain 完全不变。

组合时，artifact/environment/adapter/evidence/policy 只有 exact fingerprint 相同时才能
去重；任何不同 fingerprint 的 semantic ID、artifact cache key、双 lifecycle release owner
或相同 model/version/fingerprint/Pack routing key 都必须拒绝。没有 base 优先级、覆盖、
自动发现或 fallback。`ModelZooRegistry.from_components(base, domain)` 只接收已经加载和
验证的 source，card/legacy entry 同名但不完全相同也必须拒绝。

组合对象没有合并后的 lifecycle event chain，也不能 `append()`；状态查询按唯一 release
owner 委派给 source。若需要公开展示，使用独立的
`vc.model-registry-catalog.v3`，不得把 composition 冒充为 v2 catalog。现有 Pack product、
curated registry 与 P17 contract-only compilation 尚未适配 v3，继续只接受单一 v2 source。
此接缝是通用内核本地候选，不加载领域插件、不新增 AMR/MIC 规则，也不提升任何科学或
promotion 状态。

### 7.3 U1 本地修订：最小 domain extension veto（未发布）

direct-v2 可显式注入 `DomainExtension`，但仅按 request 的精确 `NCBITaxon:<digits>`
匹配。extension 的 brain provider 和 module-policy provider 只产生严格、有限 JSON 的
`vc.domain-brain-context.v1` 与 `vc.domain-module-policy.v1`；它们的原始 context 永远不
进入 adapter input、wrapper、evidence、promotion、legacy runtime 或公开 trace。

运行时仅保留无 context 的 `vc.domain-extension-identity.v1`：domain/taxon、brain 与 policy
的 id/version/fingerprint、allow/deny 与 canonical reason codes。其 id/version 均为 path-safe
public identifier；损坏或路径式 archive identity 只投影为 unavailable，绝不回显。provider 异常、
输出非合同、identity taxon 不匹配或 Broker 回显漂移均 fail-closed。deny 在 wrapper/adapter
实例化前将 v2 plan 收敛为空计划；它不能修改任何数值结果或将 science/promotion 状态升级。

有 extension 的 direct-v2 job 会把该 redacted identity 纳入 provenance；v4/v5 identity 会重验
identity taxon 与 submitted request，且 request fingerprint 已精确绑定 execution plan。其
structured-report fingerprint 与 replay companion 重算因此绑定这些字节。无 extension 的 generic
core 路径保持不变。此处不是 domain plugin loader，也不是 AMR/MIC 实现；领域包必须自行提供
精确 taxon、Pack、adapter、wrapper、ModelCard 与 policy，缺任一项仍为空计划。

### 7.4 U1 本地修订：显式 direct-v2 submission selector（未发布）

`vc.request.v2` 本身不等同于“执行模型”。为保留 P17
`vc.virtual-experiment-compilation.v1` 的既有 contract-only 语义，HTTP `POST /api/jobs`
只有在 transport-level `submission_contract=vc.direct-v2-execution.v1` 时才选择新的
direct-v2 提交缝；未给出该 selector 的 v2 请求仍走原有 P17 编译路径。selector 不进入
科学 request、ModelCard、evidence、policy 或 execution-plan fingerprint，不能用来升级
科学状态。

选择 direct-v2 时，入口必须同时要求严格 `vc.request.v2`、exact Pack identity、
`mode=offline` 与 `enable_llm_report=false`。ASGI host 必须显式注入已构造的
`DirectV2RuntimeFactory`；基础 API 不会从环境变量、entry point、请求字段或安装包自动
发现 factory、Pack、wrapper、adapter、domain extension 或领域插件。没有 factory 时返回
稳定的 fail-closed `503 direct_v2_factory_unconfigured`，且不写入伪造的 JobStore identity。

Python、HTTP 与 CLI 都只调用 `submit_direct_v2_job_from_factory()`，它为每个 job 新建一个
runtime 后复用唯一的 `submit_direct_v2_job()` 持久化缝。CLI 仅通过宿主以
`main(argv, direct_v2_factory=...)` 显式注入；`praxis-vc direct-v2 run` 不提供模块路径、
自动 plugin discovery 或动态 factory-loading 参数。旧 `praxis-vc run` 与 `pack run` 保持
legacy/P17 边界，不因看到 v2 marker 而静默转为 direct-v2。

direct-v2 在 wrapper 前以本地文件系统 `mkdir` 原子 reservation 占用 job ID；重复 ID 不得
执行第二次 wrapper。唯一允许的失败状态迁移是 `reserved → failed`：runtime 或持久化失败时
保留该状态锚点，非 `done` job 不可读取为 result 或 replay；进程中断遗留的 `reserved` 也不会
自动复用或恢复。该转换在 POSIX 上由已 no-follow 打开的 job 目录 inode 的 `POSIX flock` 覆盖
`reserved` 检查、所有写入和终态替换；缺少该平台能力时 reservation 在创建目录前 fail-closed，
不以线程锁伪装跨进程协调。初始 `status=reserved` 写入失败时保留原始异常，并尽力以
`unknown` 标记该不可复用孤儿；即使 marker 也无法写入，现存目录仍永久占用该 ID，读取只会
得到 `unknown`，不会被恢复为可执行 reservation。

普通 write-new `JobStore.save()` 在目录已创建后失败时同样保留 `failed` 审计锚点，而不删除
目录后把它作为重试槽；这是一项本地 write-new 行为变化，不追溯改写 v1–v3 历史 archive。
同一 job_id 不可重试；必须使用新的 job_id。它仍不是 lease、队列或跨主机协调系统。

LLM 不参与 record parsing、fingerprint、迁移、event ordering、状态归约、evidence
或 policy verdict。测试中的 synthetic record 只证明合同，不能成为科学 evidence
或产品 policy。

### 7.5 U1 本地修订：path-free Pack identity view（未发布）

direct-v2 Broker 在生成可执行 prepared input 前会重新验证已注册 Pack 的 manifest、
schema view 与声明资产；当前字节、`pack_id`、`pack_version` 或 fingerprint 任一漂移都会
把计划收敛为空计划，并以 `pack.integrity_drift` hard-abstain 结束，adapter 与 wrapper
不得被调用。这不改写 Pack registry 的历史 identity。

对不读取数值的路径及 `vc.pack.v0.1`–`v0.3`，Broker 只向 adapter 传递
`vc.prepared-pack-view.v1` 和 `vc.prepared-pack-view-receipt.v1`：它们绑定精确
Pack/taxon/assembly 与无路径的 declared asset id、media type、SHA-256、size；不含 `root`、
relative path 或 raw bytes。v1 保持其既有 identity-only 语义，不能被静默扩展为数据输入合同。
下节唯一的 v0.4 路径使用 write-new 的 v2 view/receipt，额外绑定精确 selected-content asset
与 split descriptor。Runtime 与 JobStore 会把 receipt 与 plan 的 Pack identity 交叉校验，公开
provenance 只保留该无路径 receipt。因而 adapter 不再获得本地 Pack 文件系统能力，注册后文件
变化也不能改变已发出的 identity view。

identity view 本身**不是**数值输入 reader。除下节唯一的 v0.4 合同外，
`pack_data_required=true` 的 adapter 仍以
`pack.selected_content_materializer_unavailable` fail-closed；任何 adapter 都不得自行从
bytes、path、自由数组或 legacy projection 构造数值输入。不得把本地 identity view 写成完整
Pack 数值绑定、发布、科学验证或可重放数据资产闭环。

### 7.6 U1 本地修订：generic selected-content v0.4（未发布；synthetic conformance only）

为验证 Broker 能安全提供一小段 Pack 数值输入，内核新增唯一、窄范围的
`vc.pack.v0.4`/`vc.pack-selected-csv.v1`：一个已声明且哈希绑定的 UTF-8 LF CSV record-vector。
Pack 注册时同时校验 manifest、资产 SHA/size 和严格 CSV grammar；运行时再次从同一已验证 bytes
读取。该格式不是 AnnData/MuData reader，不做 feature mapping、reorder、drop、fill、隐式单位、
默认 record 或自动选择。

request 可选的 `vc.pack-input-selector.v1` 只表达一个 exact `record_id`。adapter 首先只能返回
value-free 的 `vc.selected-content-request.v1`（exact feature contract）；Broker/PackRegistry 才能
materialize 一条有限向量，并在 adapter/wrapper 构造前后复验 Pack。公开
`vc.prepared-pack-view.v2`/`vc.prepared-pack-view-receipt.v2` 仅用于该 v0.4 路径：它们把
manifest 指定的 selected-content asset 与 split 名称、可用值和 fingerprint 绑定到 path-free Pack view。
`vc.selected-content-receipt.v1` 再绑定 request、exact model id/version、该 v2 view、该**唯一** asset 的
id/media/SHA/size、record split 与其 fingerprint、选择/数值 hash、feature/alignment/unit，但不含 root、
relative path、record id 或 values；私有 values 仅进入已注册 adapter 的 prepared input。Runtime 在执行前
由 core 重新 materialize 同一 selector，因此即使私有 handoff 伪造为另一合法 split 或另一 declared asset，
也会 hard-abstain，wrapper 不执行。

数据型执行必须使用 write-new `vc.adapter-input-receipt.v2`，把 v1 的 prepared-input identity 与
selected-content receipt 交叉绑定。Capability、Runtime 与 JobStore v4 都复核该 receipt 对 Plan、
exact model、Pack view asset 和公开 trace 的绑定；data-required private handoff 缺 content、v2 Pack view 或
降级为 v1 receipt 同样 hard-abstain。selector、CSV grammar/hash、feature order/unit、NaN/Inf、adapter
篡改、split/asset 绑定不一致或 materialize 后 Pack 漂移任一失败都生成空 plan/hard-abstain，wrapper 不执行。
`vc.pack.v0.1`–`v0.3`、无 selector 或无 v0.4 reader 的数据型 adapter 保持 fail-closed。

这一候选只用非领域 synthetic scalar 测试验证，未新增 AMR、MIC、taxon、drug 或 clinical 逻辑，
也没有 ModelCard、artifact、evidence 或可执行 `predict_mic` capability。它不是 release、GitHub CI、
wheel/archive、科学验证或生产授权；MIC 仍需其独立的 assay/censoring/isolate/profile Pack 合同与
immutable upstream release。`vc.selected-content-receipt.v1` 与 v2 Pack-view 均仍是本地未发布
合同；record-split fingerprint 在发布前已写入其规范。若未来已有公开 receipt，后续字段变化必须
write-new 或有显式迁移，不能借 v1 名称静默改变已发布 identity。

## U1 本地 direct-v2 发布可验证性补充（未发布）

当前 U1 候选只增加通用的发布前可验证性，不构成 release、科学验证或 production promotion。
Python、CLI 与 HTTP 仅经 `submit_direct_v2_job_from_factory()` 提交；HTTP host 必须显式注入
`DirectV2RuntimeFactory`。对结构合法的 `vc.direct-v2-execution.v1` 请求，缺 factory 必须返回
`503 direct_v2_factory_unconfigured`，且不得创建 JobStore 目录或伪造 job identity。

U1 V2 仍只执行一个 generic step；U2 V3 只允许精确、显式注册的 source-fingerprinted generic
reducer policy。没有该 policy 的多 step plan 仍以 `output_reducer_required` 收敛为空计划，不能为
领域任务临时绕过。本地 release verifier 在未来 clean wheel 的 checkout 外运行时，会先检查上述无
factory 的负向 HTTP 合同；它不注入模型、Pack、adapter 或领域插件。

同一 `AgentRuntime` 的 bus context、trace、确定性 clock/ID 和 Broker prepared handoff 都是该实例的
可变状态。因此 direct-v2、legacy structured request 和 text request 的顶层执行使用同一 re-entrant
per-runtime execution context；direct-v2 提交还把 `trace_start → execution → redacted trace slice` 放在
同一临界区内。它只保证**同一进程中同一 runtime 实例**不交错，不是跨 runtime、跨进程、集群队列或
lease 协议。常规 factory 每个 job 建立新 runtime；由于同一 factory 复用 registry 与 adapter instance，
它把同一个 re-entrant execution context 注入所有其创建的 runtime，防止 stateful adapter 跨 job 交错。
该锁不改变 public plan/job schema。

direct-v2 的 artifact wrapper 必须显式声明 `artifact_snapshot_supported = True`，并保留基类的
`ModelWrapper.from_capability()` factory。Broker 在 wrapper construction 前经 no-follow directory descriptor
一次性读取 exact cache bytes，并把 private `ArtifactSnapshot` 交给 wrapper；core 不会回退传递 artifact path。
未声明支持或覆写该 factory 的既有 wrapper 在构造期以 `model.wrapper_initialization` 收敛为空计划。Runtime 只接受
同一、完整的 private snapshot handoff；随后 cache path 被替换不会改变 wrapper 实际消费的 bytes。Pack 仍在执行前
重验；callback 与 snapshot bytes 不进入 bus payload，asset path 只可存在于 core 的 private broker plan payload，且
不进入 public Plan、receipt 或公开 trace。direct-v2 现在只接受 write-new
`vc.environment.v3` + exact `EnvironmentIdentityV2`；其必填
`vc.artifact-snapshot-budget-policy.v1` 限定一次 canonical Broker 执行中 sealed snapshot 的声明
payload bytes 与 entry count，并声明/绑定 `retention_scope=execution_only`。Broker 在 snapshot 的 `os.read`、selected-content、adapter
和 wrapper 前对完整 plan 聚合检查；单 step 的 Capability/Cache 也从 release-bound identity 复核同一上限。
这不是 RSS、cgroup、进程隔离或安全擦除保证；它不是 production **memory/retention budget**，也不表示规划阶段的 artifact SHA availability check 从不读取字节。
默认正向 **synthetic-only** fixture 使用 4096 bytes/4 entries，其他 synthetic 边界值只用于拒绝测试。
Golden research-only release 另行精确绑定其三件 artifact 的 4,374,098 bytes/3 entries；它不包含 2.28GB Pack，
也不是 production memory、并发或部署隔离决策。真实 production/release budget 仍是 U1 release gate。

## 被拒绝的方案

- **直接升级 `vc.model-card.v1`**：会改变既有 fingerprint 并破坏 P6 兼容。
- **把 `available` 映射为 `artifact_ready/executable`**：把声明、环境和请求计算混为
  一谈。
- **把缺少 policy 映射成伪造的 operator rejection**：会创建不存在的 operator
  身份和决定。
- **原地修改 YAML 状态**：会丢失撤销和 supersede 历史。
- **新增开放 Marketplace、管理 API 或下载器**：属于 P22/发布或独立外部动作，超出
  P12。
- **迁移时重算 P8/P9**：需要外置资产并可能改写冻结科学结论。
- **只建 catalog、以后再接执行门**：会继续允许缺 evidence/policy 的 Pack-aware
  release 进入计划，违反 P12 fail-closed 目标。

## 后果与限制

- Model Zoo 可独立描述 artifact、environment、adapter、evidence 和 policy 身份，
  同时保持 v1 card 和历史 job identity。
- 当前五张卡仍只是 legacy catalog records；没有 exact positive evidence/policy 的
  v2 Pack-aware 规划全部 abstain。P12 不新增可预测物种、任务、权重或
  production-promoted capability。
- P8 fixture 仍不授予科学验证；P9 负结果保持不变并继续要求 abstain。
- 当前 registry 不是签名供应链、远端 object store、多主数据库或 Marketplace。
- `data_only` 是当前唯一可进入 in-process runtime 的 safe-load policy，但 wrapper
  loader 的 data-only 行为尚无类型级证明；当前没有真实 promoted release。
- 低层 direct custom-registry 构造仍保留 P8 v1 benchmark compatibility；只有强制
  `enable_v2` 的产品 Pack-aware 入口满足 P12 execution gate。
- Adapter identity 只是 metadata；真正的多 task/output SDK 与 conformance 属于
  Phase 13。
