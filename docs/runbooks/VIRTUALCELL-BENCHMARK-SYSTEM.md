# Virtual Cell Benchmark System 本地合同运行手册

本 runbook 只用于 P21A repository-local contract verification 和 pytest `tmp_path` synthetic fixtures。
它不授权真实 candidate run、raw/test/external read、任何 asset/weight/output root、training、GPU、
remote、network、operator decision、promotion、release 或 deploy。

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

P21A frozen identity：

~~~text
starting SHA          5f3fc2d88c20e8083fb66a4c3399c5fe148241be
completion code SHA   20ecc12542e5df40c90d1fc367dbe86b563478b8
completion tree       ffcd261dd7d506d0ad852023afcba0f5c97a2d72
source date epoch     1786050825
branch                codex/p21-benchmark-system
engineering status    COMPLETE — SYSTEM_ONLY
science               NOT_RUN
policy                NO_NEW_DECISION
P21B / P21C           AUTHORIZATION_REQUIRED / NOT_RUN
~~~

这些 identity 只证明 completion code 上的 system contract。测试中的 synthetic positive state、
pytest 临时目录、中间 worktree 和自报 authorization 都不是 completion 或 scientific evidence。

## 2. 唯一允许的合同链

~~~text
pre-result frozen vc.benchmark-protocol.v1
→ exact P20 candidate provenance + adapter/Broker/runtime receipt bindings
→ full vc.benchmark-run-authorization.v1 content binding
→ pre-evaluation biological leakage audit
→ validation-only threshold receipt
→ embedded group×seed/test/calibration/OOD/external records
→ deterministic reproduction and layered evidence derivation
→ untrusted self-contained bundle (negative by default)
→ optional negative-only write-new ledger
~~~

P21A 库不提供真实 runner 或 operator policy 入口。Formal adapter/Broker/runtime fields 只记录冻结
receipt identity，不证明 P21A 已执行 model integration。

## 3. 冻结 protocol 和 leakage boundary

Protocol authoring 只能从完整 strict object 构造：

~~~python
from praxis_virtualcell.benchmarks.system import BenchmarkProtocolV1

protocol = BenchmarkProtocolV1.from_dict(frozen_protocol_object)
protocol_fingerprint = protocol.fingerprint()
~~~

`frozen_protocol_object` 只表示 API 形状，不是可执行占位值。Protocol 必须在观察 candidate
result 前冻结，并完整绑定：

1. scope、Pack、internal/external dataset 和 platform；
2. feature/output contracts 与 biological-group split；
3. validation/test/external exact group IDs、counts 和 set fingerprints；
4. train/validation/test/external donor、condition、replicate、batch records identity；
5. simple train-only baseline、primary metric direction、seeds 和 P8-compatible paired CI policy；
6. validation-only threshold、test calibration/selective/OOD、zero-adaptation external policy 和 promotion gates；
7. `candidate_result_observed=false`、`frozen=true`、`composite_score=null`。

使用 `audit_group_leakage()` 时必须提供全部 partition 的 exact `GroupIdentityV1` records：

~~~python
from praxis_virtualcell.benchmarks.system import audit_group_leakage

audit = audit_group_leakage(
    frozen_group_records,
    split_fingerprint=protocol.split.split_fingerprint,
    dataset_fingerprints=(
        protocol.dataset.dataset_fingerprint,
        protocol.external_policy.dataset_fingerprint,
    ),
)
~~~

Audit 必须在任何 test/external evaluation 前完成。它的 records/count/fingerprint 必须与 protocol
双向一致；跨 partition 的 group/donor/condition/replicate/batch overlap 立即 fail closed。

## 4. Threshold 和 deterministic result reproduction

Threshold 只能由 canonical validation rows 选择：

~~~python
from praxis_virtualcell.benchmarks.system import select_validation_threshold

threshold_receipt = select_validation_threshold(
    validation_rows,
    policy=protocol.threshold_policy,
)
~~~

Test/external rows 不能进入 threshold selection。P21A 重用已冻结的 P9 `select_threshold` /
`selective_metrics`，不创建第二套决策规则。Completed `BenchmarkResultV1` 必须嵌入：

- exact group×seed primary measurement rows 和 biological-group paired differences；
- validation selection rows 与 test selective rows；
- calibration bins 与 OOD group values；
- independent external primary result、leakage audit 和 content-bound receipt。

Canonical aggregation 使用 `math.fsum`，paired CI 使用冻结 P8 settings 和 helper 重放。任何
summary-only 改写、浮点容差伪造、group/seed 缺失、threshold drift、calibration/OOD 不可重算或
runtime/dataset/split/model identity 不符都必须拒绝。

## 5. Authorization 与 out-of-band P21B trust

Authorization 和 run 要求全内容 hash 和 bidirectional bindings，但这只是 identity/content integrity，
不是 issuer authentication。不要把 `authorization_record_sha256` 或调用者传入的 fingerprint
写成已受信授权。

P21B consumer 只能在一个 independently trusted source 已同时 pin authorization、完整 run 和 final
result 后，计算并比对 composite identity：

~~~python
from praxis_virtualcell.benchmarks.system import compute_p21b_execution_fingerprint

execution_identity = compute_p21b_execution_fingerprint(run, result)
evidence = bundle.derive_with_p21b_execution(
    trusted_p21b_execution_fingerprint=independently_pinned_execution_identity,
)
~~~

上述代码只描述 consumer verification 形状，不为当前 P21A 授权 P21B。这个 composite 是
authorization + full run + result 的 identity；它不得由待验证 bundle 自身当作受信来源。

`BenchmarkEvidenceBundleV1.from_components()` 不接受也不序列化 trust。它每次构造/加载都以
untrusted default 重算 evidence；authorized candidate 没有 out-of-band composite 时 reason 为
`p21b_execution_not_verified`，不可通过 benchmark/science/promotion gates。

## 6. Evidence 状态分离

`derive_evidence()` 只产生分层 engineering evidence：

~~~text
benchmark_passed
→ scientifically_validated (requires independent external result)
→ promotion_eligible (requires calibration/selective/OOD gates)
~~~

上述任何状态都不是 `production_promoted`。P21A 没有 operator identity、rationale、revocation 或
promotion write path，policy 固定为 `NO_NEW_DECISION`。Protocol/result/profile 的 `composite_score` 固定为
null；不要在下游自行合成一个未冻结分数。

## 7. P8/P9 compatibility replay

只运行检入身份的本地重放：

~~~python
from pathlib import Path
from praxis_virtualcell.benchmarks.system import replay_checked_in_benchmarks

receipts = replay_checked_in_benchmarks(Path("/absolute/canonical/repository/root"))
~~~

Path 必须是 exact absolute canonical repository root。重放只使用已检入文件的 exact size/SHA，
不访问 network。P8 继续是 null/unbound historical inventory；P9 继续是 exact
negative/unbound receipt 和原 reason codes。这不是 published replay，不重新运行 science，也不补齐
不存在的 historical output-root authorization。

## 8. Negative-only ledger

Library surface 为 `BenchmarkEvidenceLedger.create()`、`open()`、`append()` 和 `verify()`。只有在另行
授权一个 exact absolute canonical、当时不存在的 local root 后，才能调用 `create()`；
P21A completion 本身不授权手工 ledger path。测试只使用 pytest `tmp_path`。

Ledger 只允许：

- authorized-candidate 的 negative evidence bundle；
- exact P9 legacy negative receipt。

它拒绝 synthetic/contract fixture、promotion-eligible bundle、P8 null receipt、冲突 protocol/run/auth ID、
重复 result/run 和 authorization reuse。Entry 是 canonical content-addressed write-new file，使用稳定 lock、
predecessor hash chain 和 durable head。`verify()` 可发现 entry/head tamper 和 truncation；`append()` 可在
lock 内恢复恰好一个已发布但未锚到 head 的 crash tail。

Hash chain + durable head 不能防止攻击者同时回滚或删除整个 ledger 与 head；如需该保证，
必须增加仓库外或签名 anchor。

### 失败初始化恢复

Write-new 初始化失败会保持 final target 不存在，但可能留下 parent 内随机命名的
`0700` staging directory。不要在 library 里按 path 递归删除它。人工恢复前必须：

1. quiesce 所有相关 writers；
2. 通过 `lstat`/held descriptor 确认 exact inode 且仍为 directory；
3. 核对 owner、`0700` mode 和随机 basename；
4. 仅检查 expected marker/head/lock/entries content，不跟随 symlink；
5. 在任何经另行批准的恢复/清理动作紧前重验 inode、owner、mode 和 content。

任一 identity 变化时停止，不得触碰 replacement 或其他目录。

## 9. 本地 system-only gates

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_benchmark_system.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_ood_validation.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_training_pipeline.py \
  praxis_virtualcell/tests/test_capability_runtime.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra tests \
  -m 'not (integration or llm or remote)'

python -m ruff check . --extend-exclude old --no-cache
python -m ruff format --check \
  praxis_virtualcell/benchmarks/system.py \
  praxis_virtualcell/tests/test_benchmark_system.py
python -m py_compile \
  praxis_virtualcell/benchmarks/system.py \
  praxis_virtualcell/tests/test_benchmark_system.py
git diff --check
~~~

Frozen results：

~~~text
focused result       35 passed
affected matrix      238 passed
safe result          1,645 passed, 49 skipped, 387 deselected in 285.21s
legacy result        1,147 passed, 58 skipped, 105 deselected in 61.52s
static checks        full Ruff / targeted format / py_compile / git diff --check PASS
wheel evidence       1,202,180 bytes; SHA-256 ee98d4b3c6895bb6a91be1c439a0f927050cb813e9f7e5c61a37552a15c326f1;
                     371 entries / React 14 / tests 0 / AppleDouble 0; byte-identical x2; ZIP PASS
~~~

Wheel 内 `praxis_virtualcell/benchmarks/system.py` 与 source SHA-256 均为
`583d14434216c26ddffa170e2c35f24963f03461d4e9f10c3fe105073624c4d0`。两次 build 从 completion
commit 的独立 `git archive` 开始，npm 使用 explicit offline mode，Python 使用本机已安装
frontend/backend 且显式 no-isolation/skip-dependency-check。没有 network fallback。

Global `pip check` 因 pre-existing host pollution、缺失 `python-magic` 和 `vcbench` conflicts 失败；
它不是 P21A gate，也不构成新 dependency compatibility evidence。

## 10. 停止条件与 P22

如果观察到真实 candidate execution、raw/test/external read、asset/weight 读取、training、GPU、
remote/network、人工 output path 推断、positive evidence 写入 ledger、operator decision、
`production_promoted=true`、push、release 或 deploy，立即停止并保持 false/NOT_RUN。

P21B real execution 与 P21C operator policy 仍需独立 exact authorization。P21A 之后下一个 eligible
local gate 是 P22 contract-only curated model registry；它不得导入 executable release 或推导
promotion。

完整边界见 [ADR-0018](../ADR-0018-virtual-cell-benchmark-system.md)、
[P21A completion report](../../reports/phase21a/PHASE21A_COMPLETION.md) 和
[Phase 12–30 execution plan](../PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)。
