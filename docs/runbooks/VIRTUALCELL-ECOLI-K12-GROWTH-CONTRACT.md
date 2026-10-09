# E. coli K-12 knockout→growth contract 本地只读运行手册

本 runbook 只检查 P14E 的 strict scope、identity bindings、prepared input、
growth-ratio envelope、deterministic conformance 和 fail-closed 边界。它不访问网络或
外置资产，不读取 GEM/SBML/growth data，不调用 Cobra 或 solver，不生成 scientific
evidence/policy，也不执行 release、deploy 或 promotion。

## 1. 身份与边界

从仓库根执行：

~~~bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git branch --show-current
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git status --short
~~~

P14E 完成代码身份为：

~~~text
starting SHA          0b193310009d6e4d2ebc0fc8abf95da20a56acdb
SDK prerequisite      c3401450fd79f7829c438d6b55c1902ea2f4cf5f
completion code SHA   8778e93c31c2dfe1ef0f77f06e7a80a425633736
completion tree       fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78
branch                codex/p14e-ecoli-growth-contract
~~~

后续文档或 P15E commit 会改变 HEAD/tree；P14E 验收结果和 fingerprints 绑定上述
completion code SHA。不要为了匹配旧 SHA 回退工作树。

状态必须解释为：

~~~text
P14E engineering   COMPLETE
P14R science       AUTHORIZATION_REQUIRED / NOT_RUN
P14B policy        NOT_RUN
default registry   delta-expression only
~~~

不能写成 Phase 14 scientific complete、real E. coli Virtual Cell、GEM execution、
scientifically validated 或 production promoted。

## 2. 检查默认 registry 与 adapter identity

以下纯内存检查不读取资产：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterRegistry,
    DEFAULT_ADAPTER_REGISTRY,
)
from praxis_virtualcell.model_zoo.ecoli_growth_contract import (
    EcoliK12KnockoutGrowthAdapter,
)

assert DEFAULT_ADAPTER_REGISTRY.keys() == (
    ("predict_delta_expression", "delta_expression"),
)

adapter = EcoliK12KnockoutGrowthAdapter()
local = AdapterRegistry()
local.register(adapter)

assert local.keys() == (("predict_knockout_growth", "growth_ratio"),)
assert DEFAULT_ADAPTER_REGISTRY.keys() == (
    ("predict_delta_expression", "delta_expression"),
)

print("adapter", adapter.fingerprint())
print("input", adapter.input_contract.fingerprint())
print("output", adapter.output_contract.fingerprint())
PY
~~~

预期值：

~~~text
adapter  0b26d81c99f3ed216f5dcc6c86814379b6997633c0a6c071109d3ed45918b1a9
input    6995a1c262367bbd510a488b80b2c01a15e18cd6c32169f3036045869218edfa
output   bfda36704cfd82006ec0a3bd1c772d62209eb8c860b7baffae982f150955f13f
~~~

如果 growth adapter 出现在 DEFAULT_ADAPTER_REGISTRY、registry.yaml 或自动发现结果中，
立即停止：P14E 只提供 local/conformance contract，不提供生产执行授权。

## 3. 冻结 scope 的解释

| 维度 | 唯一允许值或要求 |
|---|---|
| taxonomy | NCBITaxon:562 / Escherichia coli |
| strain | NCBITaxon:511145 / E. coli K-12 MG1655 |
| assembly | GCF_000005845.2 |
| task/output | predict_knockout_growth / growth_ratio |
| target | exactly one canonical NCBIGene CURIE |
| output shape/unit | (1,) / dimensionless |
| reference | wild_type_same_gem_medium_condition |
| model inputs | exact release, GEM artifact, environment and adapter fingerprints |
| data inputs | exact growth-condition Pack/data fingerprint |
| gene mapping | exact hash-bound NCBIGene→GEM mapping asset |
| execution | exact medium, condition, objective, objective unit and solver configuration |
| compatibility | assets_verified=false, executable=false, reason=p14r_not_authorized |

所有 identity 必须交叉相等。名称相似、legacy card available、文件存在、Python import
成功或 solver package 存在都不能补足 fingerprint。p8-bacteria-tiny 是 synthetic scRNA
contract fixture，不是 growth-condition Pack。

## 4. 审计 prepared input

EcoliK12KnockoutGrowthAdapter.prepare_input 必须消费调用方显式传入的 request、
scope、protocol、artifact、environment、release、data binding、mapping、
execution binding 和 negative compatibility。审计重点：

- task/output/unit、species、strain、assembly、medium 和 condition exact；
- perturbation 只有一个 gene target，identifier 是 canonical NCBIGene CURIE；
- release 引用 exact artifact/environment/adapter/Pack；
- artifact 是声明为 data_only 的 GEM/SBML identity，但本阶段不打开其 URI；
- environment 引用 exact adapter，execution binding 标记 deterministic；
- data binding、mapping asset、compatibility 和 scope fingerprints 相互一致；
- validation protocol 绑定同一 scope 和 Pack，并固定 held-out gene/condition 分组、
  baseline、primary metric、paired CI、independent cohort、zero adaptation 与 OOD axes；
- prepared model_input 在每次消费时重新 strict validation，不能用 model_copy extra、
  subtype、exclude/computed field 或跨请求 provenance 绕过。

缺绑定时必须抛出 AdapterContractError；不得扫描目录、读取 asset、选择 textbook
model、从 symbol 猜 gene、从 Pack 猜 medium，或返回 mock input。

## 5. 审计 output、OOD 与 abstain

成功 raw output 只允许：

~~~text
prediction:
  knockout_objective
  wild_type_objective
  objective_unit
solver_status
scope_fingerprint
uncertainty
ood
abstain
abstain_reasons
~~~

成功路径必须是 optimal、finite、knockout objective 非负、wild-type objective 正数，
并把两者相除得到一个非负 growth_ratio。公开 projection 只能是：

~~~json
{"growth_ratio": [0.25]}
~~~

deterministic_fba uncertainty 必须保持 unavailable、uncalibrated、无 value/sigma。
deterministic 不等于正确或已验证。

以下情况必须拒绝或 value-free abstain：

| 现象 | 必须行为 |
|---|---|
| scope/request/Pack/provenance fingerprint 漂移 | 拒绝 |
| wrong strain/assembly/medium/condition/namespace/target | 拒绝或 exact-axis OOD abstain |
| NaN、Infinity、bool、unsafe integer、负 ratio、错 shape/unit | 拒绝 |
| infeasible、unbounded、target_not_found、error | value-free abstain，包含 reason |
| OOD detected | value-free abstain，列出 canonical OOD dimension |
| abstain 仍有 prediction，或没有 reason | 拒绝 |
| unknown raw/projection/nested field | 拒绝 |
| flux、essentiality、evidence、policy、promotion field | 拒绝 |
| standalone validate/project/aggregate | 拒绝；必须提供 exact prepared binding |

Flux 只能保存于未来独立 solver trace，不能进入 adapter envelope、metadata 或 projection。

## 6. Canonical synthetic conformance

冻结 fixture fingerprints：

~~~text
artifact              435f2868ed5e86a7ea1cf5ff47463896213b4cef8f515acd731f30c34d50c283
environment           b572089b347346becb09a2915046b8cd6e55c3ba681124e5275d2250c87fa065
model release         03db9b219ea47e954a2b89cdd0fa28c6395235cd28a4b938e6aa63ec0de405ba
mapping               c355339c2450214384300aa966de130f42e64d68fa50138d9fae3d6e3fef1886
execution             832eb94872fc2ed09fbbc97368287538ca6673424f5e3928c61fc5f0699dc5ac
Pack identity         5555555555555555555555555555555555555555555555555555555555555555
data binding          93faa211ed040d378d67c82055c00f96c5af5399cf677ca986692b5c323d74a6
compatibility         b61c7d6bacf2a2ca2de76d0ced740acef4a548155c9f4e09b7e5fa891ba81878
scope                 bd7bc1cf60877ee8abfeb2e8769cf1cfd6e99e34305487da09fb18e810fc996e
protocol              a4b0bcc46aed1586cc5a466d06422753f944043ca526a2c88ceeeef79f3a88dc
prepared              f6b1e7f263fc0b4608fedda71475b66fa0a20e9754dbe27a27d7714730e1f344
envelope              c7ea3e0d8d966bed09008425adc81c018be4643566e0fbe3db7fafbe7b1d6cae
conformance report    608e931a8a2b5199410b15428587ef03b9c5b6bd6b7b8fdf89ab753b1f1a752e
~~~

这些 identity 都是 synthetic conformance evidence。它们不表示对应外置 asset 存在，
不允许作为 P14R benchmark/result 或 P14B policy 输入。

## 7. 安全定向回归

P14E 合同文件：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_ecoli_growth_contract.py \
  -o addopts='' -p no:cacheprovider -q -ra
~~~

相邻 SDK 门：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_ecoli_growth_contract.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_model_adapter_output_flow.py \
  -o addopts='' -p no:cacheprovider -q -ra
~~~

安全 directed gate：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_ecoli_growth_contract.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_model_adapter_output_flow.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_model_registry_v2.py \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/baseline/test_baseline_offline_report.py \
  praxis_virtualcell/tests/baseline/test_baseline_routing_snapshot.py \
  -o addopts='' -p no:cacheprovider -q -ra
~~~

Completion code SHA 的结果：

| Gate | 结果 |
|---|---|
| P14E contract | 71 passed |
| P14E + adjacent SDK/output flow | 148 passed |
| safe nine-file directed | 360 passed |
| safe legacy | 1147 passed, 58 skipped, 105 deselected |
| full active-tree Ruff | PASS |
| git diff --check | PASS |

不得用本 runbook 运行 test_ecoli_gem_case.py、test_gem_wrapper.py、
test_medium_shift_case.py、test_antibiotic_case.py、test_yeast_gem_case.py 或任何
真实 GEM/textbook/Cobra science path。

## 8. Packaging 解释

从 exact completion commit 的两个 clean Git archives、在 OS 层禁止网络后，完整
release wheel 的前端 offline build 与 Python build byte-identical：

~~~text
size       1,086,768 bytes
SHA-256    462b89376a5134906e98ea4b1ec573bc24e5f2e53266d5a7104be8d625eb88b3
contents   14 deterministic React static files + P14 module
metadata   no AppleDouble or __MACOSX entries
~~~

这只证明 exact code commit 的本地构建可重复，不代表 artifact 已发布。隔离 runtime
smoke、dependency compatibility、default-registry 和 no-Cobra checks 通过；但四个
runtime dependency 的原始 wheel bytes 不在本地 uv cache，因而本窗口不能重新证明
one-shot --require-hashes offline install。四个 cache 内容重打包后只用于受限的版本/
兼容性 smoke，不能冒充 lockfile hash integrity evidence。依赖没有在 P14E 改动，P13
保留的 hash-locked install 证据也不能被回写为本 commit 的新证明。

## 9. P14R/P14B 停止条件

没有逐项 exact path、size、SHA-256、license、source、只读 source root、write-new
output root 和 run window 授权时，不得进入 P14R。没有正 P14R evidence 与具名
operator 时，不得进入 P14B。

P14E 完成后可继续不依赖正科学结果的 P15E contract-only 工程；这不改变 P14R/P14B
状态。
