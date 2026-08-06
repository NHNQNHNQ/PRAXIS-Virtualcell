# Curated Virtual Cell Registry 本地合同运行手册

本 runbook 只用于 P22 repository-local contract verification 和 pytest `tmp_path` synthetic fixtures。
它不授权真实 release/evidence/policy import、catalog/revoke/supersede、registry output root、HTTP/UI/runtime、
资产安装、模型执行、data/weight、training、GPU、remote、network、promotion、push、release 或 deploy。

## 1. 固定身份与状态

从仓库根只读检查：

~~~bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git branch --show-current
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git status --short
~~~

P22 frozen identity：

~~~text
starting/docs parent   09792e13e29a76b5e4434507f3334eefb947789c
P21A prerequisite     20ecc12542e5df40c90d1fc367dbe86b563478b8
completion code SHA   bca5ad661856e8d9aa832c47f23c6ad7179ee0c9
completion tree       f78476ac1dbe2f865e3c1bcdc71ecc512dbad22a
source date epoch     1786056220
branch                codex/p22-virtual-cell-registry
engineering status    COMPLETE — CONTRACT_ONLY
science               NOT_RUN
policy                NO_NEW_DECISION
P21B / P21C           AUTHORIZATION_REQUIRED / NOT_RUN
real lifecycle        NOT_RUN
~~~

Completion commit 只包含 `curated_registry.py` 和 tests。仓库没有 default populated registry；新建 registry
默认 empty/deny-all。Synthetic positive release、test allowlist 和 pytest 临时路径都不是可信 import 或
completion artifact。

## 2. v1 唯一允许的 closure

~~~text
exact Virtual Cell context
→ one exact P19 FactoryRegisteredPackV1
→ one native P12 ModelRegistryV2 release with no prior lifecycle
→ one exact P21B benchmark bundle + composite execution identity
→ pre-existing positive validation evidence
→ pre-existing promoted P21C operator policy
→ reviewed wrapper approvals for every adapter
→ immutable dependency closure
→ independently allowlisted import identity
→ quarantine-first append-only registry entry
~~~

P22 v1 是 One-Pack/P21B-only。Multi-Pack、直接 P14–P16 evidence/policy route、non-P21B closure 和
任意 plugin route 未实现，不得用未解释 fingerprints 或自定义 wrapper 绕过。

## 3. Release assembly 只组合既有 truth

API shape：

~~~python
from praxis_virtualcell.model_zoo.curated_registry import (
    build_virtual_cell_release,
    compute_curated_import_fingerprint,
)

release = build_virtual_cell_release(
    virtual_cell_id=virtual_cell_id,
    release_version=release_version,
    context=context,
    pack_registration=exact_p19_registration,
    source_registry=exact_single_release_p12_registry,
    benchmark_bundle=exact_p21b_bundle,
    p21b_execution_identity_fingerprint=independently_pinned_p21b_identity,
    wrapper_approvals=reviewed_wrapper_approvals,
    publisher_id=publisher_id,
    reviewer_id=reviewer_id,
    reviewed_at=reviewed_at,
    release_license=release_license,
    source_name=source_name,
    source_uri=credential_free_https_uri_or_none,
)
import_identity = compute_curated_import_fingerprint(release)
~~~

上例中的变量必须来自另行授权、独立认证的 exact inputs；不是占位授权。Builder 会重载所有 nested
contracts，重验 Pack/model/environment/adapter、protocol/run/result、P21B identity、positive evidence、
promoted policy、scope、OOD/abstain 和 dependency bindings。它不会认证 inputs，也不会创建 science 或
policy。

Wrapper approval 只记录 entrypoint、reviewed source hash、model card 和 reviewer binding。Registry 永不
调用 `importlib` 解析 entrypoint，也不下载、安装或执行 wrapper。Release license/source metadata 和
credential-free HTTPS URI syntax 会绑定 import identity，但 registry 不 fetch source，也不 live-verify
license、publisher 或 source truth。

## 4. Default deny 和 operator trust

无独立 trust 时必须保持：

~~~python
from praxis_virtualcell.model_zoo.curated_registry import CuratedRegistryTrustV1

trust = CuratedRegistryTrustV1.deny_all()
~~~

可信 consumer 必须从 registry/release 之外获得 operator-owned trust object：

~~~python
trust = CuratedRegistryTrustV1.from_dict(
    {
        "schema_version": "vc.curated-registry-trust.v1",
        "authority_id": independently_authenticated_authority_id,
        "authorized_import_fingerprints": sorted(exact_allowed_import_identities),
        "authorized_decision_fingerprints": sorted(exact_allowed_decision_fingerprints),
        "checkpoint": externally_persisted_checkpoint.to_dict(),
    }
)
~~~

不要从 candidate release、decision payload 或 registry entries 自行生成这些 allowlists。Import allowlist
subject 是 `compute_curated_import_fingerprint(release)`；decision allowlist subject 是 exact decision
fingerprint。Entry 内 authorization reference 稳定绑定 authority ID、kind 和 subject，但 fingerprint 本身
不是签名或 issuer authentication。

## 5. 创建、import 和 lifecycle

只有另行授权一个 exact absolute canonical、当时不存在的 local root 后，才能创建。用于
`create()` 的 trust checkpoint 必须是 exact empty head（`entry_count=0`、tail `null`）；非空
checkpoint 只用于 `open()` 已存在且包含该受信 prefix 的 registry：

~~~python
from pathlib import Path
from praxis_virtualcell.model_zoo.curated_registry import CuratedVirtualCellRegistry

registry = CuratedVirtualCellRegistry.create(
    Path(exact_write_new_root),
    trust=independently_supplied_trust,
)
stored = registry.import_release(release)
~~~

Import 总是 quarantine-first，默认 `query()` 不返回它。Catalog lifecycle 通过 strict
`CuratedRegistryDecisionV1` 追加：`approve_catalog`、`quarantine`、`revoke` 或 `supersede`。每个 decision
必须独立 allowlist，并固定：

~~~text
effect                   catalog_metadata_only
scientific_state_changed false
policy_state_changed     false
assets_installed         false
execution_performed      false
~~~

Revoke/supersede terminal；同 ID/version 不能换 bytes。Supersede 仅允许同一 Virtual Cell ID 的 active、
不同版本 release。所有 lifecycle 只改变派生 catalog state，永不改写历史 release、evidence 或 policy。

## 6. Python-only public projection

~~~python
catalog = registry.public_catalog()
inactive_audit_view = registry.public_catalog(include_inactive=True)
matches = registry.query(
    virtual_cell_id=virtual_cell_id,
    organism=organism,
    cell_type=cell_type,
)
graph = registry.dependency_graph(release_fingerprint)
~~~

这些是 Python read surfaces，不是 HTTP endpoint。Public catalog 固定：

- `write_api_enabled=false`；
- `executable=false`；
- `installed=null`；
- model/environment/adapter compatibility 均为 `null`；
- quarantined/revoked/superseded 默认隐藏；
- path、source URI、license detail、cache key、wrapper entrypoint、operator/reviewer 和 reason 脱敏。

其中 benchmark/science/promotion booleans 只复述 imported source registry 的 immutable truth。P22 不重算、
不提升它们。当前没有 HTTP/UI、Data Center/chat/job/runtime、installation 或 execution wiring。

## 7. Checkpoint、suffix authorization 与 rollback

~~~python
verified_head = registry.checkpoint()
~~~

`checkpoint()` 先 verify 再返回 `CuratedRegistryHeadV1`，但不把结果写入独立 trust domain，也不修改当前
trust。调用者必须另行安全持久化并在未来 open 时重新提供。给定外部 checkpoint 后：

1. registry 至少必须包含该 exact prefix；
2. prefix tail fingerprint 必须匹配；
3. checkpoint 后的每个 suffix entry 都必须由当前 authority 的 stable authorization reference 重验；
4. 不同 authority 追加的自洽 suffix 被拒绝。

Local head 能发现普通 truncation/unanchored tail。若攻击者把 entries 和 head 一起恢复到旧状态，只有已经
推进到较新 revocation 的外部 checkpoint 能发现。未推进 checkpoint 时，hash chain 不能防 whole-registry
rollback；hash 也不是 authentication。

Public `revocation_checkpointed=true` 只表示本次 supplied trust checkpoint 与当前 nonempty verified
tail 完全相同，不是全局发布或不可撤销证明；empty registry 固定为 false。

## 8. Storage 失败和恢复边界

Store 使用 absolute canonical write-new root、随机 sibling `0700` staging、held dirfd/inode、stable flock、
canonical content-addressed entries、exclusive link、predecessor chain、durable head 和 fsync。每次 read 都重验
layout 和 bytes。

Write-new 在 publication 前失败时 final target 不存在，但随机 `0700` staging 可能按设计保留；若
no-replace publication 已成功而随后 fsync/post-publish verification 失败，final target 也可能保留。
不要按 pathname 递归删除任一种残留。任何人工恢复/清理前必须：

1. quiesce 所有相关 writers；
2. 用 `lstat`/held descriptor 重验 exact inode、owner、`0700` mode 和随机 basename；
3. 只检查 expected marker/head/lock/entries，不跟随 symlink；
4. 在获准动作紧前再次重验全部 identity；
5. 任一变化立即停止，不触碰 replacement 或相邻目录。

Append 若已发布 exact entry 但 head 未更新，只允许通过重试同一个 trusted record、同一个 authorization
provenance 在 lock 内恢复；普通 `verify()` 不擅自恢复。

## 9. 本地 contract-only gates

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_curated_registry.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_curated_registry.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_pack_factory.py \
  praxis_virtualcell/tests/test_pack_product.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_virtual_experiment.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra tests \
  -m 'not (integration or llm or remote)'

python -m ruff check . --extend-exclude old --no-cache
python -m ruff format --check \
  praxis_virtualcell/model_zoo/curated_registry.py \
  praxis_virtualcell/tests/test_curated_registry.py
PYTHONDONTWRITEBYTECODE=1 python -m py_compile \
  praxis_virtualcell/model_zoo/curated_registry.py \
  praxis_virtualcell/tests/test_curated_registry.py
git diff --check
~~~

Frozen results：

~~~text
focused result       35 passed in 43.55s
affected matrix      289 passed, 1 skipped in 64.94s
safe result          1,680 passed, 49 skipped, 387 deselected in 334.23s
legacy result        1,147 passed, 58 skipped, 105 deselected in 60.48s
static checks        full Ruff excluding old / targeted format / py_compile / diff PASS
wheel evidence       1,217,155 bytes; SHA-256 3f978e9f3eb06ea17017c1838002762f28ae717ee08d987cfb8ea059162a2485;
                     372 entries / React 14 / tests 0 / AppleDouble 0;
                     byte-identical x2; ZIP PASS
~~~

Wheel 内 `praxis_virtualcell/model_zoo/curated_registry.py` 与 source SHA-256 均为
`9678b2460aff6738935a2728e12abf398985c4475d66be96d37a721a21bf62ff`。两次 build 从 completion
commit 的独立 `git archive` 开始，npm 使用 `--offline`，Python 使用本机已安装 build frontend、
`--no-isolation --skip-dependency-check`。工具链为 Python 3.13.12 / build 1.5.0 / setuptools 70.2.0 /
packaging 26.0、Node 25.8.2 / npm 11.11.1 / Vite 8.1.2。没有 network fallback。

该 packaging evidence 只支持 exact local source/toolchain reproducibility 和 content integrity；不支持
dependency closure、clean install、publication、release 或 deploy。

## 10. 停止条件与下一编号 gate

如果观察到真实 release/evidence/policy import、真实 catalog/revoke/supersede、外置 registry root、
HTTP/UI/runtime/installation/execution、data/asset/weight、training、GPU、remote/network、operator promotion、
push、release 或 deploy，立即停止；它们不属于本 P22 closure。

P21B/P21C 仍 `AUTHORIZATION_REQUIRED / NOT_RUN`。下一 eligible 本地 work unit 是 P23A
contract-only：只能实现 sender→receiver `interaction_evidence_score`，不得输出 receiver response 或
causal claim；真实 release/data/asset/execution 与可选 P23B 仍分别受 exact 授权门约束。

完整边界见 [ADR-0019](../ADR-0019-curated-virtual-cell-registry.md)、
[P22 completion report](../../reports/phase22/PHASE22_COMPLETION.md) 和
[Phase 12–30 execution plan](../PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)。
