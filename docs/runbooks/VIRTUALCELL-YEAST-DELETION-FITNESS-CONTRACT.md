# S. cerevisiae deletion→fitness contract 本地只读运行手册

本 runbook 只检查 P15E strict scope、identity bindings、prepared input、finite scalar
fitness envelope、deterministic synthetic conformance 与 fail-closed 边界。它不访问网络
或外置资产，不读取 deletion screen、H5AD、真实模型或 GEM，不调用 Cobra，不产生
scientific evidence/policy，也不执行 release、deploy 或 promotion。

## 1. 身份与状态

从仓库根只读检查：

~~~bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git branch --show-current
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git status --short
~~~

P15E 完成代码身份：

~~~text
starting SHA          0ff6870a70a04d71098a16875e633f909e31cc5a
completion code SHA   62480a3951173a2aa7b006403af9b169521db138
completion tree       64906691c4c989a843df4da97f0a93f32cd65ad2
branch                codex/p15e-yeast-fitness-contract
~~~

后续 docs-closure 或 P16E commit 会改变 HEAD/tree；P15E fingerprints 与验收结果绑定
上述 completion code SHA，不要为了匹配旧 SHA 回退工作树。

状态只能解释为：

~~~text
P15E engineering   COMPLETE
P15R science       AUTHORIZATION_REQUIRED / NOT_RUN
P15B policy        NOT_RUN
real assets/GEM    NOT_RUN
default registry   delta-expression only
release            NOT RUN
~~~

不能写成 Phase 15 scientific complete、real yeast fitness predictor、scientifically
validated、promotion eligible 或 production promoted。

## 2. 默认 registry 与 adapter identity

以下纯内存检查不读取资产：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterRegistry,
    DEFAULT_ADAPTER_REGISTRY,
)
from praxis_virtualcell.model_zoo.yeast_deletion_fitness_contract import (
    YeastDeletionFitnessAdapter,
)

assert DEFAULT_ADAPTER_REGISTRY.keys() == (
    ("predict_delta_expression", "delta_expression"),
)

adapter = YeastDeletionFitnessAdapter()
local = AdapterRegistry([adapter])

assert local.keys() == (("predict_deletion_fitness", "fitness"),)
assert DEFAULT_ADAPTER_REGISTRY.keys() == (
    ("predict_delta_expression", "delta_expression"),
)

print("adapter", adapter.fingerprint())
print("input", adapter.input_contract.fingerprint())
print("output", adapter.output_contract.fingerprint())
PY
~~~

预期：

~~~text
adapter  b1aa00416fd851b3b340bf54fcfc702bb3406e6b7007d5f80c3e46616a5e357f
input    f17599d4c40142d5b07628e1d14142d05535eab23deccb8d61f40ed040262597
output   adbf56f663b072483680fdce3bb7faa4109639b3663d35332db1e8f7ad9303ea
~~~

若 yeast adapter 出现在 DEFAULT_ADAPTER_REGISTRY、registry.yaml、wrapper/routing 或
自动发现的生产路径，立即停止。P15E 只提供 local/conformance contract；legacy
yeast_deletion_fitness card 仍为 planned。

## 3. 冻结 exact scope

| 维度 | 唯一允许值或要求 |
|---|---|
| taxonomy | NCBITaxon:4932 / Saccharomyces cerevisiae |
| strain | NCBITaxon:559292 / Saccharomyces cerevisiae S288C |
| assembly | R64 / GCF_000146045.2 |
| task/output | predict_deletion_fitness / fitness |
| target | exactly one canonical SGD systematic ID |
| target grammar | `^Y[A-P][LR][0-9]{3}[CW](?:-[A-Z])?$` |
| perturbation | complete_gene_deletion |
| output shape/unit | (1,) / dimensionless |
| reference | matched_non_deletion_control_same_condition_platform |
| value semantics | prepared_scope_assay_defined_scalar |
| biological bindings | exact condition, control, assay, platform, fitness-semantics and target-universe IDs/fingerprints |
| model bindings | exact release, application/json data-only artifact, environment and adapter fingerprints |
| data/mapping | exact deletion-fitness Pack/data and SGD→model target-universe mapping fingerprints |
| execution | exact runner and inference-configuration fingerprint |
| compatibility | assets_verified=false, executable=false, reason=p15r_not_authorized |

所有 identities 必须交叉相等。文件名相似、import 成功、legacy card 存在或 Pack 可读
均不能补足 fingerprint。P10 yeast tiny Pack 是 scRNA/NCBIGene synthetic fixture，
不是 deletion-fitness screen。

## 4. Prepared input 审计

YeastDeletionFitnessAdapter.prepare_input 必须消费调用方显式传入的 request、scope、
protocol、model artifact、environment、release、data binding、mapping、execution
binding 与 negative compatibility。重点检查：

- species/strain/R64、task/output/unit 与 complete deletion exact；
- 一个 target 且严格匹配 canonical SGD systematic grammar；
- request attributes 同时绑定 namespace version、condition、control、assay、platform、
  fitness semantics 与 target universe；
- baseline_context 绑定 matched non-deletion control 和 exact scope；
- release 引用 exact artifact/environment/adapter/Pack，且不含 evidence/policy；
- artifact 是 application/json、safe_load_policy=data_only 的 identity-only fixture；
- mapping 同时绑定 SGD namespace version/fingerprint 与 model target universe；
- Pack/data、execution、compatibility、scope 和 protocol fingerprints 交叉一致；
- prepared model_input 每次消费时重新 strict validation，不能用 hidden field、subtype、
  dataclass/MappingAssetRef drift 或 model_copy extra 绕过。

缺绑定必须抛出 AdapterContractError。不得扫描目录、打开 URI、加载真实 screen/model、
调用 GEM/Cobra、从 symbol/NCBIGene 猜 target，或从 P10 fixture 猜 condition/platform。

## 5. Validation protocol 审计

未来 P15R protocol 必须保持：

~~~text
split_unit                     held_out_biological_group
biological_group_keys          target_gene_id, condition_id, replicate_group_id
baseline                       training_mean_fitness_same_condition
primary_metric                 mean_squared_error_fitness
metric_direction               lower_is_better
paired_ci_required             true
independent_condition_required true
independent_platform_required  true
external_adaptation_steps      0
validation_only_tuning         true
stochastic_seeds               11, 23, 37
record_role                    preregistration_not_evidence
~~~

任一 protocol record 的 stochastic_seeds 至少三个、不重复、非负且为 JSON-safe
integer。Canonical OOD order 是：

~~~text
strain
assembly
assay
condition
control
platform
gene_namespace
target_universe
target
~~~

Output reference 与 evaluation baseline 不可互换。Protocol 只有预登记身份；没有真实
outcome、MSE、paired CI 或 external result 时，不能创建 validation evidence。

## 6. Output、uncertainty、OOD 与 abstain

成功 raw output 只允许：

~~~text
prediction:
  fitness
  fitness_semantics_id
  reference
  unit
prediction_status
scope_fingerprint
uncertainty
ood
abstain
abstain_reasons
~~~

成功 fitness 必须是 finite JSON-safe scalar，并原样进入：

~~~json
{"fitness": [-0.25]}
~~~

Adapter 不计算 ratio、不 normalize、不 clip，也不施加非负或其他 range cap。
Uncertainty 必须精确为 unavailable/uncalibrated neutral state：

~~~text
available   false
calibrated  false
value       null
sigma       null
method      not_available
reason      no_calibrated_uncertainty_declared
~~~

授权状态不得放进 uncertainty；p15r_not_authorized 只属于 compatibility。

| 现象 | 必须行为 |
|---|---|
| request/scope/Pack/provenance fingerprint 漂移 | 拒绝 |
| wrong strain/assembly/condition/control/assay/platform/namespace/target universe | 拒绝或 exact-axis OOD abstain |
| NaN、Infinity、bool、unsafe integer、错 shape/unit/semantics/reference | 拒绝 |
| target_not_found 或 error | value-free abstain，包含 reason |
| unsupported_scope | detected OOD + canonical dimension/reason + value-free abstain |
| 任意 OOD detected | value-free abstain |
| abstain 仍含 prediction 或缺 reason | 拒绝 |
| unknown/reserved science/policy/promotion field | 拒绝 |
| standalone validate/project/aggregate | 拒绝；必须提供 exact prepared binding |

## 7. Canonical synthetic fingerprints

~~~text
artifact              5ae9b7ae69ba01c34cd7ddeb307dfbf69458fd369290e97ac286a24e1e755dcf
environment           34a38273d839f1a2eddabc5ba3cbbc5e00fa8521198e403a60f8e013a019f291
model release         c0f476559c7d586b254e0a15126e29a684a549a2a855b64d6e5e57d85fb6e5d7
mapping               71375cb49f543f9d5600b983738c87b1ef9d27489bc9f80779838ea7fb00cd83
execution             5a1e7dafaa619b1a15b95029aa26b2a1ebcf4bfd8b8dcb56096f0c443cdc4e29
Pack/data binding     f3dfbfe59d6f9277ba6d6b6255e45f4f45ab915d55d27a565535e94233535097
compatibility         b63327a28621ed05de6884fa4d9b701f7540570b9fed97e40346aa73c7a9f574
scope                 b0260216a68850faad4d45469d2e649f2e0fb61ec326bf60279309af08e07e1b
protocol              279c5aa53f58b55d0bc62e23eaafb08ecf6263ed20a405a426eb9738928645ea
prepared              1fc11d4129c7df92d1e5f5caba9c0934161b3b747398410ebd1ec485e88dd90d
envelope              03f83e286066530e9daa38b0428f3283c8bc2f05cbd23dd2f8d70adf774812ee
conformance report    80b43f37340f3c073a0fd479ca071718fce53dc99c2a7d69cd7c39aeebed75c3
~~~

这些都是 synthetic conformance identities，不表示外置 asset 存在、许可已审查、模型
可执行、MSE 达标、科学有效或产品获批。

## 8. 安全本地验证

P15E contract suite：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_yeast_deletion_fitness_contract.py \
  -o addopts='' -p no:cacheprovider -q -ra
~~~

安全 directed gate：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_yeast_deletion_fitness_contract.py \
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

Authoritative lint：

~~~bash
ruff check . --extend-exclude old --no-cache
~~~

Completion code SHA 的记录：

| Gate | 结果 |
|---|---|
| P15E contract | 98 passed |
| safe ten-file directed | 458 passed |
| safe legacy | 1147 passed, 58 skipped, 105 deselected |
| authoritative Ruff | PASS |
| format check | PASS |
| git diff --check | PASS |

不要用本 runbook 运行 test_yeast_gem_case.py、test_gem_wrapper.py、Phase 10 real GEM
cases 或任何真实 deletion-screen/model/GEM/Cobra science path。

## 9. Packaging 证据与限制

Exact completion commit 的两个 clean Git archives 在以下边界内完成完整 wheel build：

~~~text
sandbox network        denied
npm                    offline
Python                  3.13 local build toolchain
SOURCE_DATE_EPOCH       1786006797
wheel size              1,096,472 bytes
wheel SHA-256           7758c13bd5a53c74618d556b14c6e27e0492381162a9ab3364aee7dde5d2bb8d
archive entries         364
React static files      14
test entries            0
AppleDouble entries     0
~~~

两次 wheel bytes 相同。这只证明 exact code commit 在上述本地工具链与 sandbox 下的
构建可重复，不表示 wheel 已发布。

严格官方离线脚本因本地 cache 缺 packaging==26.2 且网络明确拒绝而 fail closed。
全局 pip check 受预存 base environment 污染，不能作为 P15E dependency 证据。
Python 3.13 system-site 的有限 wheel install/import smoke 成功；Python 3.12 smoke 因
环境缺 PyYAML 而失败。这些有限 smoke 不能冒充 clean isolated、hash-locked dependency
installation proof。没有 version bump、tag、push、publication、release 或 deployment。

## 10. P15R/P15B 停止条件

没有逐项 exact path、size、SHA-256、license、source、只读 source root、write-new
output root 与 run window 授权时，不得进入 P15R。没有正 P15R evidence 与具名
operator 时，不得进入 P15B。

P15E completion 不改变 real_assets_verified=false、executable=false、
scientifically_validated=false 或 production_promoted=false。持续本地工程若进入
P16E，必须从 actual P15E docs-closure SHA 开始，并保持 P15R/P15B 为独立窗口。
