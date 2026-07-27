# VirtualCellPack Phase 4.1 → Phase 5 交接

- 收口日期：2026-07-27（Asia/Shanghai）
- P4.1 唯一起始基线：`f983518a09954fecbb799553ca47d7a50bd7c13d`
- 分支：`codex/p4.1`
- 状态：`P4_1_COMPLETE_LOCAL_CANDIDATE — PHASE5_AUTHORIZATION_PENDING`
- 完成提交：由提交后的阶段报告给出；Git commit 不能可靠地自嵌其 SHA。

## 1. 结论

P4 审查发现的 B1、B2、H1、M1、M2 已按“先失败测试、后最小实现”收口。
没有实施 Phase 5，没有新增模型、Pack loader、UI、在线 ontology 依赖或跨物种转换。

Phase 5 应在新对话中进行，并且只能使用阶段报告给出的 P4.1 完成 SHA 作为唯一
起始基线。不得继续使用旧 P4 SHA `f983518a...`。

## 2. 收口内容

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

## 3. 测试证据

红灯阶段，在 `f983518a...` 的旧实现上新增契约得到：

```text
11 failed / 45 passed
```

另一个完整 canonical-key 字段合同单独确认失败，随后才修改实现。

收口后：

```text
Pack/P2/P3/P4/P4.1 定向：
82 passed / 0 failed

python3.13 -m ruff check .：
All checks passed

python3.13 -m pytest praxis_virtualcell/tests \
  -m "not llm" -o addopts='' -q -ra
1093 passed / 43 skipped / 9 deselected / 0 failed

python3.13 -m pytest tests \
  -m "not (integration or llm or remote)" -o addopts='' -q -ra
1139 passed / 58 skipped / 105 deselected / 1 failed
```

P0 代表性报告哈希保持不变：

```text
structured_report:
27a16eef2493bf953c4e572f3480d9c80e4013b5f92ebca4b8bfe0f59722228b

9-section Markdown:
ed4b03d12e9618a7685a19106609f2ec0b0461ccf533c6beec20e7318ec7898a
```

legacy 唯一失败仍为继承测试：

```text
tests/test_mcp_pool.py::test_pool_slow_server_startup_timeout_skipped
```

日志仍显示 1 秒窗口内 slow/good MCP server 均握手超时。P4.1 没有修改
`praxis2/mcp/**` 或该测试，因此不能把它报告成 P4.1 回归，也不能报告 legacy 全绿。

## 4. 文件范围

实现：

- `praxis_virtualcell/data_packs/schema.py`
- `praxis_virtualcell/data_packs/manifest.py`
- `praxis_virtualcell/data_packs/anndata_adapter.py`
- `praxis_virtualcell/data_packs/registry.py`

测试与小 fixture：

- `praxis_virtualcell/tests/test_pack_semantics.py`
- `praxis_virtualcell/tests/test_data_packs.py`
- `praxis_virtualcell/tests/fixtures/pack_semantics/{human,mouse,bacteria}.yaml`

文档：

- `docs/ADR-0002-virtualcellpack-p4-standard-semantics.md`
- `docs/VIRTUALCELLPACK-CAPABILITY-MATRIX.md`
- `docs/INSTALL.md`
- `docs/VERSIONING.md`
- 本交接文件

未修改 runtime、governance、Report、ActiveLearning、model zoo、模型、权重、UI、
P0 baseline、main/tag 或 `.53`。

## 5. 已知限制

- 标准 ontology 仍只做离线前缀/格式/角色检查，不证明术语在线存在或 ontology 版本；
- Ensembl 校验冻结格式，不证明 feature 与 taxon/assembly 的数据库对应关系；
- `pack_valid` 不推导 `model_compatible` 或 `scientifically_validated`；
- display symbol 与 matrix 数值不属于 canonical metadata key；
- 本地 Git 仍有既存 AppleDouble pack-index 警告；未授权修改 `.git`；
- legacy MCP startup timeout 是继承缺陷，未纳入 P4.1 范围。

## 6. 三端边界

P4.1 开始时：

- 本地 P4.1 基线：`f983518a09954fecbb799553ca47d7a50bd7c13d`；
- GitHub `HEAD/main`：`8e0d06348ebdf22e076037e6d661094ae877c5d1`；
- `.53` `codex/deploy-v1.6.0`：同为 `8e0d063...`，既存 untracked `vc_api.log`；
- 旧 T7 dirty 工作树：`24475f2eb14c27c7cfbb82b016b881e88e98b17c`。

本阶段没有 push，没有修改 main/tag，没有同步或写入 `.53`，没有修改旧 T7 用户文件。

## 7. Phase 5 授权模板

提交后的阶段报告会把下列占位符替换为精确 SHA：

```text
授权以 <P4.1 完成 SHA> 作为 Phase 5 唯一起始基线，开始实施 Phase 5。
```

精确迁移关系：

```text
expected_old_sha=f983518a09954fecbb799553ca47d7a50bd7c13d
→ new_sha=<P4.1 完成提交 SHA>
```
