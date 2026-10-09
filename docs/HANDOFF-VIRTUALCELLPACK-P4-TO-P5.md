# VirtualCellPack Phase 4.3 → Phase 5 交接

- 收口日期：2026-07-27（Asia/Shanghai）
- P4.3 唯一起始基线：`eaa9a4067518ab80591ffec7f033b248b43ed951`
- 分支：`codex/p4.3`
- 状态：`P4_3_COMPLETE_LOCAL_CANDIDATE — PHASE5_AUTHORIZATION_PENDING`
- 完成提交：由提交后的阶段报告给出；Git commit 不能可靠地自嵌其 SHA。

## 1. 结论

P4.3 已关闭 P4.2 唯一 legacy 失败：坏 MCP server 仍可使用 1 秒 fail-closed
握手预算，正常 FastMCP server 不再被同一测试阈值误杀。此前 P4.1/P4.2 的收口
保持不变。没有实施 Phase 5，没有新增模型、Pack loader、UI、在线 ontology
依赖或跨物种转换。

Phase 5 应在新任务中进行，并且只能使用阶段报告给出的 P4.3 完成 SHA 作为唯一
起始基线。不得继续使用 P4.2 SHA `eaa9a406...`。

## 2. P4.3 legacy/MCP 收口

### 根因

旧测试把 pool 级 `startup_timeout_s=1.0` 同时施加给不讲 MCP 协议的 slow
server 和正常 FastMCP echo server。当前本机正常 server 冷启动实测约
`3.15–3.34s`，因此 good 也进入 `TimeoutError` audit；这不是 slow server
fail-closed 本身失效。

### 最小修复

- `MCPServerSpec` 新增可选 `startup_timeout_s`；
- `PRAXIS_MCP_SERVERS_JSON` 可为每个 server 声明独立启动预算；
- 未声明时继续使用 pool 原有 10 秒默认值；
- 布尔值、字符串、非正数、非有限值和无法转换为有限 float 的超大整数均
  fail-closed 为 `ValueError`；
- initialize 与 list-tools 使用同一个 per-server 预算；
- slow fixture 保持 1 秒，good fixture 使用 10 秒；测试中的 pool fallback
  故意设为 0.01 秒，证明代码确实读取了 server 预算，而非仅让测试碰巧变绿。

没有引入并发启动、后台重连或新的生命周期抽象。

## 3. P4.2 历史收口内容

### C1：registry 版本分支与验证快照一致

`PackRegistry.register()` 先取得 `validate_pack()` 的已验证 manifest，再据该对象
决定是否进入 v0.2 语义 loader；v0.2 最终登记 loader 实际返回的 manifest 快照。
候选 manifest 在 v0.1/v0.2 间变化时不能再借旧分支登记未通过 H5AD 语义门的对象。

### C2：canonical key 覆盖 Pack 级科学语义

`CanonicalOmicsView.canonical_key` 在原有 selection 语义之外，固定 schema、
taxon、assembly、modality、feature namespace/version、feature ID 语义、完整
local-term 定义、condition/perturbation catalog 和 split/leakage 声明。未被
observation 使用的 perturbation 仍属于 Pack 声明身份。

source column 名、display-only symbol 和 matrix 数值继续排除；manifest 声明顺序
保持原样，不静默排序、去重或归一。

### C3：P1 validated domain JSON 递归不可变

`vc.request.v2`、独立 domain objects 和 model I/O bundles 中的 JSON mapping 在
Pydantic 验证后递归冻结，嵌套 mapping/list 不能原位修改。显式 legacy adapter
从序列化副本构造旧对象，不把可变引用泄漏回已验证对象。

### C4：Cellosaurus accession 格式收紧

标准 identity 只接受正式 `CVCL_XXXX` accession；非标准
`cellosaurus:XXXX` 不再被当作标准术语接受。仍不联网确认 accession 是否存在。

### C5：YAML 异常保持 Pack 边界

不可哈希 YAML mapping key 现在被转换成稳定的 `PackManifestError`，不再泄漏原始
`TypeError`。

### C6：manifest symlink 不得逃逸

`validate_pack()` 对 `manifest.yaml` 使用与资产相同的 root containment 检查；
解析目标必须留在 Pack root 内。

### C7：P0 报告哈希可执行冻结

P0 structured report 与 9-section Markdown 的两个 SHA-256 现在由 baseline test
直接断言，不再只存在于文档。

## 4. P4.1 历史收口内容

### B1：identity/state/context 角色边界

- `LocalTermSpec` 新增必填 `role: identity | state | context`；
- 标准 identity 只接受 `CL:` 与 Cellosaurus ID；
- 标准 context 只接受 `UBERON:`；
- state 使用 manifest 中显式声明为 state 的本地 CURIE；
- 本地术语只能用于其声明角色；
- 不查询网络、不猜测术语角色、不自动改写。

human、mouse、bacteria 三份 fixture 已补充显式 local-term role。旧的“列不同但
术语可互换”路径现在 fail-closed。

### B2：canonical metadata identity

`CanonicalOmicsView.canonical_key` 现在包含：

- taxonomy、assembly；
- observation/feature ID；
- condition 与 split partition；
- cell identity/state/context；
- perturbation ID、kind、target mapping；
- matched control、dose、time；
- named split、shape、matrix location/format。

display-only feature symbol 与 matrix 数值仍明确排除。selection 后的
perturbation kind/target 也按 observation 顺序返回，不做去重或重排。

### H1：v0.2 registry 不再授予较弱有效状态

`PackRegistry.register()` 对 v0.2 强制走现有 `load_anndata_view()` 完整语义门；
包含未知 condition/perturbation/control/target 等 H5AD 语义错误的 Pack 不可登记。
缺少 `omics` extra 时直接拒绝，不 fallback 到仅 manifest/path/size/hash 验证。

v0.1 继续保持原有 manifest/asset 验证合同和冻结 fingerprint，不被强制要求
AnnData 依赖。

### M1：v0.1/v0.2 split 字段隔离

v0.1 manifest 只要出现 `split.name` 或 `split.leakage_guard` 就拒绝，包括显式
`null` 和空数组。解析器不再接受后于 `to_dict()` 静默删除。

### M2：Ensembl canonical 格式

`ensembl_gene` 现在要求 11 位数字 stable-ID 主体，并允许显式数字版本后缀；
`ENSG1` 等宽松 Ensembl-like 值不再通过。仍不做 symbol lookup、在线存在性查询、
taxon/assembly 自动推断或 ortholog projection。

## 5. 测试证据

P4.3 在 `eaa9a406...` 上先稳定复现原失败：

```text
tests/test_mcp_pool.py::test_pool_slow_server_startup_timeout_skipped
1 failed
```

新增 per-server 配置契约在旧实现上的红灯：

```text
7 failed / 12 passed
```

超大整数异常边界单独先得到：

```text
1 failed / 18 passed
```

最小实现后：

```text
MCP 配置 + slow/good 定向：
20 passed / 0 failed

锁文件目标顶层版本 mcp 1.28.1 / anyio 4.14.2 的 MCP 定向：
37 passed / 0 failed

python3.13 -m ruff check . --no-cache：
All checks passed

python3.13 -m pytest praxis_virtualcell/tests \
  -m "not llm" -o addopts='' -p no:cacheprovider -q -ra
1104 passed / 43 skipped / 9 deselected / 0 failed

python3.13 -m pytest tests \
  -m "not (integration or llm or remote)" \
  -o addopts='' -p no:cacheprovider -q -ra
1147 passed / 58 skipped / 105 deselected / 0 failed
```

P0 代表性报告哈希保持不变：

```text
structured_report:
27a16eef2493bf953c4e572f3480d9c80e4013b5f92ebca4b8bfe0f59722228b

9-section Markdown:
ed4b03d12e9618a7685a19106609f2ec0b0461ccf533c6beec20e7318ec7898a
```

P4.2 的 `1139 passed / 1 failed` 是历史证据；P4.3 未删除、skip 或放宽该断言，
而是保留 slow 的 1 秒预算并使完整 legacy 口径全绿。

## 6. 文件范围

实现：

- `praxis2/mcp/config.py`
- `praxis2/mcp/pool.py`

测试：

- `tests/test_mcp_config.py`
- `tests/test_mcp_pool.py`

文档：

- `docs/TESTING.md`
- `docs/P0-BASELINE.md`
- 本交接文件

未修改 VirtualCell 确定性 runtime、governance、Report、ActiveLearning、model
zoo、模型、权重、UI、P0 报告字节/hash 值、main/tag 或 `.53`。

## 7. 已知限制

- 标准 ontology 仍只做离线前缀/格式/角色检查，不证明术语在线存在或 ontology 版本；
- Ensembl 校验冻结格式，不证明 feature 与 taxon/assembly 的数据库对应关系；
- `pack_valid` 不推导 `model_compatible` 或 `scientifically_validated`；
- source mapping column 名、display symbol 与 matrix 数值不属于 canonical metadata key；
- registry 保存已验证内存快照，但不提供跨进程文件系统事务或 Pack 签名；
- target namespace/kind 到模型输入的映射仍是 Phase 5 设计，不在本次兼容修复中；
- MCP servers 仍按配置顺序启动；本阶段只隔离每个 server 的超时预算，不实现并发启动；
- 真实第三方 MCP、远端服务和运行中崩溃恢复仍属于显式 integration/remote 门；
- 锁版本 MCP 定向使用临时 system-site venv 覆盖顶层 `mcp/anyio`，不是完整 fresh
  hash-lock 环境；完整当前环境 legacy 与 core 已分别执行；
- 本地 Git 仍有既存 AppleDouble pack-index 警告；未授权修改 `.git`；
- 既有 cross-task `close_all()` cancel-scope 降级边界未在本阶段重构。

## 8. 三端边界

P4.3 开始时：

- 本地 P4.3 基线：`eaa9a4067518ab80591ffec7f033b248b43ed951`；
- GitHub `HEAD/main`：`8e0d06348ebdf22e076037e6d661094ae877c5d1`；
- `.53` `codex/deploy-v1.6.0`：同为 `8e0d063...`，既存 untracked `vc_api.log`；
- 旧 T7 dirty 工作树：`24475f2eb14c27c7cfbb82b016b881e88e98b17c`。

本阶段没有 push，没有修改 main/tag，没有同步或写入 `.53`，没有修改旧 T7 用户文件。

## 9. Phase 5 授权模板

提交后的阶段报告会把下列占位符替换为精确 SHA：

```text
授权以 <P4.3 完成 SHA> 作为 Phase 5 唯一起始基线，开始实施 Phase 5。
```

精确迁移关系：

```text
expected_old_sha=eaa9a4067518ab80591ffec7f033b248b43ed951
→ new_sha=<P4.3 完成提交 SHA>
```
