# Virtual Cell Model Adapter SDK 本地只读运行手册

本 runbook 只检查 Phase 13 的 strict adapter contracts、显式 registry、feature/alignment
绑定、output envelope、deterministic conformance 和 Pack-aware runtime 接线。它不访问
网络或外置资产，不加载、下载或训练模型，不运行科学实验，不创建 evidence/policy，
也不执行 release、deploy 或 promotion。

## 1. 边界与代码身份

从仓库根运行，并先核对 Git identity：

```bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git branch --show-current
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git status --short
```

Phase 13 完成身份为：

```text
starting SHA         f83c13db386cb552b3ce7a5643e5ffbead0ff573
branch               codex/p13-model-adapter-sdk
completion code SHA  744d0a28d2cfc13d1b10e85b133b6c13b9426174
completion tree      198e623120688d3704b9312990ddaa93c9a7b0e6
```

文档提交或后续本地提交会改变 `HEAD`/tree；验收数字和冻结 fingerprints 绑定上面的
completion code SHA。不要为匹配旧 SHA 回退用户的工作树。

允许的默认生产能力只有：

```text
adapter id/version  delta-expression-reference / 1.0.0
task/output         predict_delta_expression / delta_expression
```

growth 和 fitness adapters 只存在于测试；若它们出现在
`DEFAULT_ADAPTER_REGISTRY`，立即视为边界破坏。

## 2. 检查默认 registry 和冻结 fingerprints

运行以下纯内存检查；它不加载模型或 Pack data：

```bash
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
from praxis_virtualcell.model_zoo.adapter_sdk import DEFAULT_ADAPTER_REGISTRY

expected_key = ("predict_delta_expression", "delta_expression")
assert DEFAULT_ADAPTER_REGISTRY.keys() == (expected_key,)
adapter = DEFAULT_ADAPTER_REGISTRY.resolve(*expected_key)

print("adapter", adapter.adapter_id, adapter.version)
print("task/output", *expected_key)
print("adapter fingerprint", adapter.fingerprint())
print("input fingerprint", adapter.input_contract.fingerprint())
print("output fingerprint", adapter.output_contract.fingerprint())
PY
```

预期输出中的 fingerprints 必须逐字符为：

```text
adapter fingerprint 17afc27e56dba13567001ff1982cbf1660e2948fadf2147301a1d0dcf61aeb3d
input fingerprint   d10cf437291dc1ebb1689c3f4c5eea4d82af3842491c224172215faddca93078
output fingerprint  d863783786504ebf768cfd7e2fbad66cfd03a029deb1dee3543a9872712e363d
```

还应检查 P12 `AdapterIdentity` 的 implementation 为
`praxis_virtualcell.model_zoo.adapter_sdk.DeltaExpressionReferenceAdapter`，并包含同一
task、唯一 output 及两端合同 fingerprints。`resolve_identity()` 必须按完整 identity
bytes 解析；只对上 adapter id/version、model name 或 task 不足以通过。

Registry 只接受显式 `register()`；没有 entry-point discovery、目录扫描、远端发现或按
名字 fallback。v1 拒绝任何 multi-output request；未来 composite adapter 需要新的 schema
与 registry 语义，不能只注册一个当前单 output adapter 来绕过。

## 3. 合同如何解释

Phase 13 公开 versioned schemas 固定为：

```text
vc.adapter-input-contract.v1
vc.prepared-adapter-input.v1
vc.adapter-output-contract.v1
vc.adapter-output-envelope.v1
vc.adapter-execution-provenance.v1
vc.adapter-conformance-report.v1
```

`AdapterUncertainty` 和 `AdapterOOD` 只是 envelope 的严格嵌套对象，没有独立
`schema_version`。不要为它们编造额外 schema identity。

| 层 | 审计重点 | 不证明 |
|---|---|---|
| Input contract | task/output、float、shape、unit、data/alignment requirements | Pack 中存在所需矩阵 |
| Prepared input | exact adapter/contract/request 及可选 Pack/compatibility/alignment bindings | 模型科学有效 |
| Output contract | shape/unit、uncertainty/OOD/abstain requirements | uncertainty 已校准 |
| Output envelope | finite values 或明确 abstain、exact provenance | evidence 或 promotion |
| Conformance report | 同一输入/output 两次执行 byte-identical | benchmark 通过 |
| P12 adapter identity | exact implementation 与合同 fingerprints | artifact/environment 可执行 |

Delta reference input contract 是 float `(None, None)`、unit `None`，并明确
`pack_data_required=false`、`alignment_required=false`。这只允许既有 request-only
reference 路径，不允许未来 data-required adapter 省略 Pack matrix。其 output contract
是 float `(None,)`、unit `None`，且 uncertainty/OOD 必填、abstain 可用。

## 4. 审计 prepared input 和 feature alignment

优先通过定向测试检查 input preparation，不要手工修补 serialized input。必须覆盖：

- adapter、input contract、request、Pack 和 compatibility fingerprints 无漂移；
- values 非空、矩形、shape 相符，且拒绝 bool、NaN/Infinity、unsafe integer 和 ragged
  tensor；
- unit 与 input contract exact 相等；
- `pack_data_required=true` 时 values 与 Pack fingerprint 同时存在；
- `alignment_required=true` 时 P5 `ModelFeatureContract` 与 `AlignmentReport` 同时存在；
- feature contract fingerprint、target feature order、target shape、mapping asset identity/
  hash 全部精确相等。

SDK 复用 P5 feature/alignment 合同，不维护第二套 identifier mapping。它也不自动选择
row、control、split 或 matrix，不猜 gene identifier、shape、unit 或 transform。若 native
data-required adapter 只有 target compatibility、没有明确 values/matrix binding，Broker
必须返回空计划，而不是制造 prepared input。

`pack_data_required=false` 的 delta reference 可以带可选、已 fingerprint 的 Pack/
compatibility binding；可选不等于可以传入漂移或非 canonical identity。

## 5. 审计 output envelope 和 conformance

每个 strict output 必须满足：

1. task/output、adapter fingerprint 和 input/output contract fingerprints 精确匹配；
2. 非 abstain 时 values、shape、unit 完整且一致，所有数值 finite；
3. 合同要求的 uncertainty 和 OOD 状态存在；
4. `ood.detected=true` 时必须 abstain；
5. abstain 时 values/shape 为空，且 `abstain_reasons` 非空；
6. provenance 绑定 exact prepared input、request、Pack 和 compatibility fingerprints；
7. projection metadata 为 JSON-safe，且不含 science/policy reserved keys。

Wrapper raw output 的 `evidence` 或 `policy` 字段不能进入 envelope，也不能被 adapter
改写为科学或产品结论。至少拒绝
`scientifically_validated`、`promotion_eligible`、`operator_policy` 和
`production_promoted` 等 projection keys。

`run_adapter_conformance()` 对同一 prepared input/raw output 执行两次完整 adapt/validate，
再比较 envelope、fingerprint 和非 abstain projection。任何 nondeterminism 都拒绝；
`deterministic=true` 只证明 adapter 合同实现可重复。

Ensemble 只可聚合同一已注册 adapter fingerprint 的 strict envelopes。混合 strict/
legacy、fingerprint/task/output/shape/unit 不同或任一 envelope abstain 时必须 fail closed。
Delta reference 的 ensemble mean 明确返回 unavailable uncertainty；不要把它展示为
calibrated。Learned reliability 只可用于 delta task/output，其他 output 保持 unsupported。

## 6. Pack-aware runtime 与 legacy 边界

严格路径应按以下顺序审计：

```text
P12 AdapterIdentity exact resolve
  -> CapabilityRegistry compatibility/empty-plan gate
  -> Broker prepares exact adapter input
  -> wrapper consumes prepared model_input
  -> adapter validates and normalizes output envelope
  -> critic/provenance/report/governance gates
```

缺失或未注册 adapter、identity drift、data-required input 缺 matrix、wrapper output 不合
同、OOD 或 adapter abstain 都不能产生成功 prediction。Adapter abstain 应成为 rejected
result，并保留 adapter provenance。Governance abstain 清除公开 adapter output，但不得
删除审计 provenance。

现有 route table/case dispatch 不应出现 P13 新增的 model/species 特判。无 Pack legacy
执行仍是独立兼容路径；它不是 P12/P13 fully governed，也不能与 strict envelope 混合
聚合。禁止 mock fallback 或用 legacy dict 绕过 strict adapter gate。

## 7. Fail-closed 故障处理

| 现象 | 处理 |
|---|---|
| 默认 registry 不只一个 delta adapter | 停止；移除 growth/fitness 或自动发现注册 |
| P12 adapter identity 无法 exact resolve | 空计划/abstain；不得按名称猜实现 |
| adapter/input/output fingerprint 改变 | 停止；确认是否为有意新 schema/implementation identity |
| data-required adapter 缺 values 或 Pack fingerprint | 空计划；不得从 Pack 自动猜 matrix |
| alignment fingerprint/order/shape/mapping hash 漂移 | 拒绝 prepared input；修复上游 exact binding |
| output 含 NaN/Infinity、ragged values 或 unit/shape drift | 拒绝 envelope；不得清洗后继续 |
| OOD detected 但仍返回 values | 强制拒绝；OOD 必须 abstain |
| abstain 同时含 values 或没有 reason | 拒绝 envelope |
| projection 含 evidence/policy/promotion 字段 | 拒绝 projection；adapter 不作 science/policy |
| strict 与 legacy output 被一起聚合 | 拒绝 ensemble；保持两条路径隔离 |
| governance abstain 后公开 payload 仍有 adapter output | 清除公开 output，同时保留 audit provenance |
| P9 状态变为 available/positive science/promotion | 立即停止；恢复原负结果，不更新 fixture 掩盖变化 |

错误消息和报告不应回显 secret、credential、外置绝对路径或模型 cache 内容。

## 8. 回归与静态检查

Phase 13 三组合同测试可分别运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  -o addopts='' -p no:cacheprovider -q -ra

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_model_adapter_output_flow.py \
  -o addopts='' -p no:cacheprovider -q -ra

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_capability_runtime.py \
  -o addopts='' -p no:cacheprovider -q -ra
```

在 completion code SHA 上的精确结果为：

| Gate | 结果 |
|---|---|
| Adapter SDK | `48 passed` |
| Adapter output flow | `22 passed` |
| Capability runtime | `75 passed` |
| P13 directed gate（含相邻 runtime 回归） | `265 passed` |
| Core | `1462 passed, 35 skipped, 9 deselected`；2 known MuData deprecation warnings |
| Legacy | `1146 passed, 59 skipped, 105 deselected` |
| Packaging | `13 passed` |
| Ruff | pass |
| `python -m pip check` | pass |
| Frontend typecheck/lint/build/bundle budget | pass |

Core、legacy 和 packaging 使用仓库 `docs/TESTING.md` 中的冻结选择规则；不要把 skip/
deselect 写成 remote、GPU、外置模型或科学验证通过。静态与包装检查：

```bash
python -m ruff check praxis_virtualcell praxis_vc_api praxis_vc_web praxis2 tests --no-cache
python -m pip check

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_packaging.py \
  -o addopts='' -p no:cacheprovider -q -ra

git diff --check

cd praxis_vc_react
npm run typecheck
npm run lint
npm run build
```

`npm run build` 已包含 bundle-size check。上述测试不得触发 network、external assets、
model weights、training、GPU、remote、`.53` 或真实科学运行。

## 9. 允许的更新与下一阶段

修改 adapter schema、canonicalization、registry resolution、input/output contract 或
runtime projection 时必须：

1. 对不兼容语义使用新 schema/adapter identity；
2. 保留 strict unknown-field、bad-number、shape/unit、wrong-binding、OOD、abstain 和
   science/policy reserved-key 负例；
3. 保持默认生产 registry delta-only，除非新的工程阶段明确授权注册其他 adapter；
4. 不自动读取 Pack matrix、下载/运行模型或创建 scientific evidence/operator policy；
5. 不改写 P9 negative result；
6. 不把工程 conformance 描述成 scientific validation 或 production promotion。

P13 engineering 已 COMPLETE。下一阶段是 P14E；P14R 真实科学运行和 P14B operator
policy/promotion 均需单独授权。
