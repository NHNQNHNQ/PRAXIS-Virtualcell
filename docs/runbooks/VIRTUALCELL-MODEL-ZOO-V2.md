# Virtual Cell Model Zoo v2 本地只读运行手册

本 runbook 只检查 Phase 12 的分层 identity、v1 迁移、append-only registry history、
Pack-aware evidence×policy 执行硬门和路径脱敏产品投影。它不下载或运行模型、不读取
外置数据、不训练、不调用 GPU/LLM/remote、不修改 registry，也不作 operator
promotion 决定。

## 1. 边界与输入

从仓库根运行，并先核对当前 Git identity：

```bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git branch --show-current
git rev-parse HEAD
git status --short
```

P12 的代码起始身份是：

```text
starting SHA  b19c896202bea56f894d0ad540501331af42a40c
branch        codex/p12-model-registry-v2
```

只读迁移输入来自仓库已有小型文件：

```text
praxis_virtualcell/model_zoo/registry.yaml
data/golden/norman_2019/artifact-manifest.json
data/benchmarks/p9/external-validation.json
```

测试 migration fixture 位于：

```text
praxis_virtualcell/tests/fixtures/model_registry_v2/legacy_migration.json
```

其 envelope schema 是 `vc.model-registry-legacy-migration-fixture.v1`。它只保存上述
输入的 repo-relative identity、SHA-256 和预期
legacy/incomplete/no-promotion 状态，不复制模型卡、科学结果、大数据或权重，也不
授权访问 registry 中记录的 remote/cache 路径。

P8/P9 文件只可解析成 `vc.model-registry-legacy-receipt.v1`，其
`binding_status=unbound`；汇总的
`vc.model-registry-legacy-migration-report.v1` 必须保持
`evidence_admitted=false`、`production_promoted=false`。Receipt 不能加入
`ModelRegistryV2.evidence_records`。
其中 P8 receipt 必须保持 `available=null`、`benchmark_passed=null`、
`promotion_eligible=null` 和历史已有的 `scientifically_validated=false`；unknown 不能
被改写成失败裁决。P9 receipt 则保留 `available=false` 和三项已有的 `false` 科学负
状态。

## 2. 合同和状态如何解释

P12 新增的 record fingerprint 均来自严格 canonical JSON；fingerprint 证明 record
bytes 身份，不证明引用目标存在或可信。

审计时始终分开读取：

| 层 | 字段 | 正确解释 |
|---|---|---|
| Registry | `cataloged` | exact release identity 已登记 |
| Registry | `artifact_ready` | exact asset size/hash 已重验；不是模型质量 |
| Registry | `revoked/superseded` | 禁止未来选择或由新 identity 取代；历史不改写 |
| Computed | `model_compatible` | 每次按 exact request×Pack×model scope 计算 |
| Computed | `adapter_compatible` | 独立检查 exact adapter task/output 与 environment binding |
| Computed | `environment_compatible` | 检查 environment identity、runtime/resource、artifact、wrapper readiness 和 adapter gate |
| Computed | `executable` | 同时要求上述 computed gates、exact evidence×policy 和 active lifecycle |
| Evidence | `benchmark_passed/scientifically_validated/promotion_eligible` | 只来自 exact frozen evidence |
| Policy | `production_promoted` | 只来自引用 exact evidence 的具名 operator record |

`null`/unavailable、`false` 和缺席不是同义词；工具不得用默认值补造未记录的科学
事实。没有 operator policy 时保持 no-promotion，但不能生成一条假的 operator
rejection。

## 3. 检查 v1 兼容迁移

运行 P12 定向测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  -o addopts='' -p no:cacheprovider -q -ra
```

迁移验收至少必须证明：

1. 默认 registry 的五张 `vc.model-card.v1` 全部仍能按原 bytes 加载；
2. 原 card fingerprint 不变；
3. `planned/missing/available` 逐卡保存在结构化 `legacy_status`，并保持原始 legacy
   declaration；
4. 没有完整 size/source/load-policy 验证的 asset 不成为 `artifact_ready=true`；
5. P8 history 不被解释为新 validation verdict；
6. P9 保持 `available=false`、`scientifically_validated=false` 和原 reason codes；
7. 没有生成真实 operator-policy record，`production_promoted` 不会变成 true，
   Pack-aware `executable` 必须为 false；
8. migration 重复运行得到 byte-identical public identities。

任何缺字段、unknown field、坏 SHA-256、重复 identity、身份错绑或状态越级都必须
fail closed；不得修改 source fixture 迎合 loader。

Native release 必须 exact one-Pack scoped；多 Pack 数组、evidence 指向另一 Pack、
environment/evidence/policy 指向未知 component、或未被任何 release 引用的 evidence/
policy record 都必须拒绝。Package name 使用 canonical PEP 503 lowercase spelling；
该要求和 normalized uniqueness 只适用于 native environment。Legacy module name 原样
保留且只按 raw exact string 检查重复；不得把 `foo_bar` 与 `foo.bar` 合并。NFC/case-fold
后冲突的 artifact cache keys 也必须拒绝。

## 4. 检查 append-only history

P12 registry history 是不可变 record/event 合同，不是可由 HTTP 管理的数据库。
定向测试必须覆盖：

- 合法 catalog event 后可归约出 `cataloged=true`；
- artifact readiness event 绑定 exact release，并经该 release 间接绑定 artifact
  fingerprints；
- legacy/incomplete release、空 artifact 引用或 incomplete artifact identity 不能归约成
  `artifact_ready=true`；
- revoke 只改变未来选择状态，旧 release/event fingerprint 不变；
- supersede 必须引用不同、已在此前 cataloged 且未 revoked/superseded 的 replacement
  release；
- event 链的前序 fingerprint 断裂、对未知 release 操作、self-supersede、重复但
  bytes 不同的 identity 全部拒绝；
- 追加事件返回新 history/head，不原地修改旧对象。

不要手工编辑 fixture 来模拟撤销。真实 operator 动作和持久 registry import 属于
后续独立授权；P12 只证明合同和负例。

## 5. 检查 Pack-aware evidence×policy 硬门

P12 产品 CLI/API/runtime 的 Pack-aware compatibility report、execution step 和 plan
必须分别使用 `vc.compatibility-report.v2`、`vc.execution-step.v2` 和
`vc.execution-plan.v2`，并把同一 exact release 的 artifact、environment、adapter、
evidence 和 policy fingerprints 写入 identity。至少验证：

- 合同完整但缺 evidence：`executable=false`、无 step、明确 abstain；
- evidence 存在但 scope/Pack/model/environment/adapter 任一错绑：拒绝；
- evidence 为负或 `promotion_eligible=false`：不得执行；
- exact evidence 存在但 policy 缺席、为负或引用另一 evidence：不得执行；
- in-process runtime 遇到 `safe_load_policy` 不是 `data_only` 时必须 abstain，并在
  instantiate 前重检，不能把 restricted/isolated 声明当作已提供对应 sandbox；
- release 已 revoked/superseded：不得进入新 plan；
- 只有全部 exact refs、科学门和 positive operator policy 同时成立时才允许 step；
- v2 plan 存档为 `vc.job-execution-identity.v2`，保留 exact request/Pack/environment
  snapshot/release/component/evidence/policy fingerprints 以及所列 lifecycle/science/
  promotion/executable snapshot，且 registry 后续事件不改写它；
- synthetic positive record 只可证明测试路径，不能登记为真实 science/policy。

无 Pack 请求继续走显式 legacy adapter，只用于兼容既有调用。低层 direct
`ModelZooRegistry(custom_path)` 默认 v1 仅保留 P8 library benchmark 兼容；它不是
P12 产品入口。产品的 default/custom/environment registry path 都必须显式
`enable_v2=True`。不得把任一 legacy 路径描述成 v2 fully governed 或
production-promoted。

## 6. 只读 CLI/API 投影

P12 不增加模型管理命令或写入 API，继续使用既有入口：

```bash
praxis-vc pack list
```

若本地已单独启动 API，可只读查看同一投影：

```bash
curl --fail --silent http://127.0.0.1:8000/api/packs
```

启动服务、占用端口或访问已部署服务是独立 operator 动作；没有相应授权时只运行
library/测试客户端，不执行上面的 live-service 命令。

CLI/API 结果应继续保留 `vc.pack-catalog.v1` 既有字段。Top-level `model_registry` 必须
是 `vc.model-registry-catalog.v2`；每个 `model_capabilities[*].registry_releases` 必须是
从同一 catalog 按 exact model name 过滤的 release 白名单投影。两处 bytes 应来自同一
状态源，不能各自推导 science/policy。展示 `cataloged`、fingerprint 或 legacy status
不代表某个 request 已 compatible/executable，更不代表 benchmark、science 或
promotion。

## 7. 路径和 secret 泄漏审计

Registry catalog projection 必须从字段白名单构造，且 public identifier 必须为
canonical path-safe text。禁止输出 raw registry record，以及下列字段和值：

```text
uri / cache_key
local_path / resolved_path / registry_path
asset_paths
source / safe_load_policy / implementation / packages
绝对 POSIX、Windows 或 UNC path
file: URI
source_note/provenance 中的 host、cache、checkout 或用户目录
```

建议在测试临时对象中分别放入 `/home/...`、`/Volumes/...`、`C:\\...`、UNC、
`file:///...` 和 symlink-resolved path，然后序列化 CLI/API payload，确认这些 token
均不存在。对 compatibility/plan payload 还要确认每个 step/report 的 `asset_paths` 已在
公开前删除。不要只检查字段名；异常消息也不得回显路径。

P12 nested catalog 只可包含实现中显式列明的 release/model/component fingerprints、
migration/legacy 状态、四个 lifecycle 状态、nullable science 状态，以及 `policy_present`/
`production_promoted` flags；不得借机扩充为 artifact metadata 或 provenance 浏览器。
没有 evidence 时三项 science 状态必须为 `null`，不能伪装成科学负结果。既有外层 Pack
catalog 字段保持其原合同。若无法判断一个字段是否安全，省略它，而不是字符串替换。
Legacy raw `model_version` 若不是 path-safe identifier，公开值必须为 `null`，而不是
改写原 card 或回显不安全字符串。

## 8. 回归与静态检查

P12 完整本地检查按授权范围执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_model_zoo_registry.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_pack_product.py \
  praxis_virtualcell/tests/test_api.py \
  -o addopts='' -p no:cacheprovider -q -ra

ruff check \
  praxis_virtualcell/model_zoo \
  praxis_virtualcell/pack_product.py \
  praxis_virtualcell/cli.py \
  praxis_vc_api \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  --no-cache

python -m pip check
git diff --check
```

随后按阶段授权运行受影响 core、legacy 和 packaging tests。普通 skip/deselect 不得
写成 remote、GPU、LLM、外置资产或科学验证通过。

## 9. 故障处理

| 现象 | 处理 |
|---|---|
| v1 card fingerprint 改变 | 停止；恢复兼容迁移，不更新 fixture 掩盖差异 |
| artifact/evidence bytes 改变但 fingerprint 不变 | 合同破坏；修复 canonical identity |
| identity ref 错绑 | 拒绝 record；不得按名称猜匹配对象 |
| non-`data_only` artifact 进入 in-process step | safe-load gate 破坏；abstain，并在 instantiate 重检 |
| `available` 被映射为 executable/validated | 状态越级；停止迁移 |
| P9 出现 positive science/promotion | 立即停止；保留原负结果 |
| Pack-aware plan 缺 evidence/policy 仍有 step | 执行门破坏；清空 step 并明确 abstain |
| public payload 含本地路径 | 拒绝响应并修复字段白名单 |
| revoke/supersede 改写历史 event/job | append-only 破坏；不得重建历史 |
| 缺 operator policy | `production_promoted=false`、Pack-aware abstain；不得创建占位 operator |

## 10. 允许的更新

修改任一 schema 语义、canonicalization、migration rule、event action 或 public
projection 都必须：

1. 新建不兼容 schema identity，或证明向后兼容；
2. 增加坏 hash、错绑、越级、路径泄漏和历史改写负例；
3. 保持旧 source/evidence bytes 和历史 fingerprint；
4. 不自动运行、下载或训练模型；
5. 不自动生成 scientific evidence 或 operator policy；
6. 只在独立授权下操作外置资产、remote、push、main/tag、`.53` 或服务。
