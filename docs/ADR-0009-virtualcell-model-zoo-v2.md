# ADR-0009：Virtual Cell Model Zoo v2 分层身份与状态治理

- 状态：Accepted（Phase 12 本地候选）
- 日期：2026-08-02
- 唯一起始基线：`b19c896202bea56f894d0ad540501331af42a40c`
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
| `LegacyMigrationReceipt` | `vc.model-registry-legacy-receipt.v1` | 保留 repo-relative source/hash、nullable availability 和原始科学状态；永远 `binding_status=unbound` |
| `LegacyMigrationReport` | `vc.model-registry-legacy-migration-report.v1` | 汇总五张旧卡与 receipts；固定不 admission evidence、不 promotion |
| Environment snapshot | `vc.environment.v2` | 把当次 runtime snapshot 与 exact `EnvironmentIdentity` 绑定；`vc.environment.v1` 保持 legacy |
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

LLM 不参与 record parsing、fingerprint、迁移、event ordering、状态归约、evidence
或 policy verdict。测试中的 synthetic record 只证明合同，不能成为科学 evidence
或产品 policy。

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
