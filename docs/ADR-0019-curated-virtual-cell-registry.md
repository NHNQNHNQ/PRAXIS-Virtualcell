# ADR-0019：Curated Virtual Cell Registry 合同

- 状态：Accepted（P22 engineering `COMPLETE — CONTRACT_ONLY`）
- 日期：2026-08-07
- 唯一起始 / documentation parent：`09792e13e29a76b5e4434507f3334eefb947789c`
- P21A 前置 code SHA：`20ecc12542e5df40c90d1fc367dbe86b563478b8`
- Completion code SHA：`bca5ad661856e8d9aa832c47f23c6ad7179ee0c9`
- Completion tree：`f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a`
- Source date epoch：`1786056220`
- 分支：`codex/p22-virtual-cell-registry`
- 前置：ADR-0018
- 工程状态：`COMPLETE — CONTRACT_ONLY`
- Science：`NOT_RUN`
- Policy：`NO_NEW_DECISION`
- P21B / P21C：`AUTHORIZATION_REQUIRED / NOT_RUN`

## 背景

P21A 已建立 benchmark system contract，但没有运行 P21B real candidate，也没有 P21C
operator decision。P22 因此只能建立一个默认空、默认拒绝的本地 curated registry 合同，不能凭
candidate hashes、synthetic fixtures 或 catalog 操作制造已验证、已晋级或可执行的 release。

P22 没有获得任何真实 release、evidence、policy、asset、weight、registry output root、network、GPU
或 runtime 授权。测试中的完整正向 release 只存在于 pytest 临时目录，是 transient synthetic
conformance，不是 scientific evidence、operator policy 或产品 catalog。

## 决策

### 1. v1 只接受 One-Pack / P21B closure

`VirtualCellReleaseV1` 是 strict frozen Pydantic contract 和 canonical JSON SHA-256 identity。它绑定
Virtual Cell context、一个 exact `FactoryRegisteredPackV1`、一个只含单个 native release 且无既有
lifecycle event 的 `ModelRegistryV2`、完整 `BenchmarkEvidenceBundleV1`、P21B composite execution
identity、positive validation evidence、promoted P21C policy、全部 adapter wrapper approval、capability
scope、OOD/abstain policy、license/source/publisher/reviewer 和完整 dependency fingerprints。

所有嵌套对象都按原始 P12/P19/P21A exact contract 重载并重新绑定。P22 只组合已存在的 positive
science/policy truth；它从不创建、提升或改写 `benchmark_passed`、`scientifically_validated`、
`promotion_eligible` 或 `production_promoted`。

此 v1 精确限定为 One-Pack/P21B 路径。Multi-Pack、直接导入 P14–P16 evidence/policy、非 P21B
evidence 路径和其他未来 release closure 均明确延期，不能用任意 fingerprint 列表模拟。

Wrapper approval 记录 reviewed entrypoint 和 source hash，但 registry 不解析或 import entrypoint，不下载
代码，也不安装或执行模型。HTTPS source URI 只允许无 credential、query 或 fragment 的形式；public
projection 不暴露它。Release license/source 只是纳入 exact import identity 的 curated metadata；P22
不 fetch source，也不 live-verify license、publisher 或 source truth。

### 2. Trust 默认拒绝，hash 不构成 authentication

`CuratedRegistryTrustV1.deny_all()` 是默认配置。真实 import 必须由独立 operator trust domain allowlist
exact `vc.curated-virtual-cell-import-identity.v1`；lifecycle decision 必须单独 allowlist exact decision
fingerprint。Entry 保存稳定 authorization reference，绑定 authority ID、authorization kind 和 exact
authorized subject。

Release、decision 或 authorization 的 content hash 只证明 bytes identity，不认证 issuer。调用者自报
allowlist、从待导入 release 推导 trust，或只让对象内部 hashes 自洽都不能形成可信授权。

Trust 还携带由外部独立保存的 monotonic checkpoint。`checkpoint()` 只在完整 verify 后返回当前 head，
不替调用者持久化或推进外部 checkpoint。Checkpoint 之后的 suffix 必须逐 entry 以当前 authority 重新
验证 authorization provenance；更换 authority 的自洽 suffix 仍被拒绝。

Registry local head 可发现普通 tail/truncation，但攻击者若同时回滚 entries 和 head，只有已经在独立
trust domain 推进到相应 revocation 的 checkpoint 才能发现。未推进的旧 checkpoint 不能证明后来
revocation 未被回滚。

### 3. Import 先 quarantine；lifecycle 只改变 catalog metadata

可信 import 先进入 `quarantined`，不会直接进入默认 query。`approve_catalog`、`quarantine`、`revoke`
和 `supersede` decision 的 effect 固定为 `catalog_metadata_only`，并强制
`scientific_state_changed=false`、`policy_state_changed=false`、`assets_installed=false`、
`execution_performed=false`。

同一 Virtual Cell ID/version 永久绑定同一 bytes；即使 revoke 后也不能换 bytes。Revoke 和 supersede
是 terminal。Supersede 只允许 active、同一 Virtual Cell ID、不同 version 的 cataloged release，历史
release bytes 不被改写。

### 4. Registry 是 append-only、write-new local store

`CuratedVirtualCellRegistry.create()` 要求 explicit absolute canonical、当时不存在的 root。初始化在同一
parent 下建立随机 `0700` staging，持有 directory descriptors/inodes，写入并 fsync marker、head、lock
和 entries，再用平台 no-replace atomic rename 发布。发布前失败时 final target 保持不存在，随机
`0700` staging 可能按设计保留；若 no-replace publication 已成功、随后 fsync/post-publish verification
失败，final target 也可能保留。两种残留都不通过不可信 pathname 递归清理。

Append 使用 held stable lock、canonical content-addressed entry、exclusive staging/link、predecessor chain
和 durable head。每次读取都重验 root/entries/lock identity、marker、canonical bytes、strict JSON、sequence、
authorization provenance 和 lifecycle log。只有重试 exact trusted record 且 authorization provenance 相同
时，才可恢复一个已发布但 head 未更新的 tail。

### 5. Public surface 仅为 Python read projection

`public_catalog()`、`query()` 和 `dependency_graph()` 是 Python-only、只读、路径脱敏的 projection，
不是 HTTP API、UI、Data Center/chat/job wiring 或 execution plan。Projection 固定
`write_api_enabled=false`、`executable=false`；`installed`、model/environment/adapter compatibility 均为
unknown (`null`)。默认 registry 不存在；新建空 registry 的 releases 为空。

Public projection 只复制被导入 source truth 的 benchmark/science/policy booleans，永不重新派生；路径、
wrapper entrypoint、source URI、license detail、cache key、operator/reviewer 和 reason 均不公开。Quarantined、revoked 和
superseded release 默认不出现在 query 中，但其 immutable history 可在显式 inactive projection 中查看。

## 验证与完成身份

| Evidence | Frozen value |
|---|---|
| completion code SHA / tree / epoch | `bca5ad661856e8d9aa832c47f23c6ad7179ee0c9` / `f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a` / `1786056220` |
| focused / affected matrix | `35 passed in 43.55s` / `289 passed, 1 skipped in 64.94s` |
| safe / legacy | `1,680 passed, 49 skipped, 387 deselected in 334.23s` / `1,147 passed, 58 skipped, 105 deselected in 60.48s` |
| static checks | full Ruff excluding `old`、targeted format、`py_compile`、`git diff --check` passed |
| reproducible wheel | `1,217,155` bytes；SHA-256 `3f978e9f3eb06ea17017c1838002762f28ae717ee08d987cfb8ea059162a2485`；`372` entries / React `14` / tests `0` / AppleDouble `0`；ZIP passed |
| `curated_registry.py` source / wheel | SHA-256 `9678b2460aff6738935a2728e12abf398985c4475d66be96d37a721a21bf62ff`；exact match |
| two independent builds | byte-identical；explicit npm offline and Python no-isolation/skip-dependency-check |

Toolchain 为 Python `3.13.12` / build `1.5.0` / setuptools `70.2.0` / packaging `26.0`、
Node `25.8.2` / npm `11.11.1` / Vite `8.1.2`。两次 build 都从 completion SHA 的独立
`git archive` 开始，没有 network fallback。这只证明 exact local source/toolchain 的字节可复现性和
wheel content integrity，不是 pinned dependency closure、clean install、publication 或 release 证明。

## 后果与下一 gate

P22 engineering 完成只证明 curated registry contract 在 synthetic fixtures 上 fail closed。真实
import/catalog approval/quarantine/revoke/supersede、P21B/P21C、HTTP/UI/runtime binding、installation、
execution、data/asset/weight access、network、GPU、training、scientific validation、operator promotion、
push、release 和 deploy 均保持 `NOT_RUN` 或不存在。

P23A 是下一 eligible 本地 contract-only work unit；它只能建立 sender→receiver
`interaction_evidence_score`，不得输出 receiver response 或 causal claim。真实 release、interaction
data、asset 或执行仍须满足各自 exact 输入与独立授权门；P23B 继续是可选、独立授权窗口。

详细边界见 [P22 runbook](runbooks/VIRTUALCELL-CURATED-REGISTRY.md)、
[P22 completion report](../reports/phase22/PHASE22_COMPLETION.md) 和
[Phase 12–30 execution plan](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)。
