# K562 Golden Norman perturbation→delta-expression contract 本地只读运行手册

本 runbook 只检查 P16E strict K562 scope、P8 identity references、single/combination
bindings、prepared input、5,045-feature delta-expression envelope、deterministic synthetic
conformance 与 fail-closed 边界。它不访问网络或外置资产，不打开 H5AD、
`golden_contract.json`、NPY、checkpoint 或 model cache，不导入或运行 Golden benchmark、
GEARS/scGPT，不产生 scientific evidence/policy，也不执行 release、deploy 或 promotion。

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

P16E 完成代码身份：

~~~text
starting SHA          d1e2e37b69784bd2f440cba34f51cfb56dcc00b2
completion code SHA   9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2
completion tree       098cd563e3d865e080a0d121727b987e2d40ed18
branch                codex/p16e-k562-perturbation-contract
~~~

后续 docs-closure 或 P17 commit 会改变 HEAD/tree；P16E fingerprints 与验收结果绑定
上述 completion code SHA，不要为了匹配旧 SHA 回退工作树。

状态只能解释为：

~~~text
P16E engineering     COMPLETE
P16R science         AUTHORIZATION_REQUIRED / NOT_RUN
P16B policy          NOT_RUN
real assets/model    NOT_RUN
default registry     generic delta-expression reference only
release/version      NO CHANGE / NOT RUN
~~~

不能写成 Phase 16 scientific complete、real K562 predictor、candidate superior、
scientifically validated、promotion eligible 或 production promoted。

## 2. 默认 registry 与 adapter identity

以下纯内存检查不读取资产：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterRegistry,
    DEFAULT_ADAPTER_REGISTRY,
    DeltaExpressionReferenceAdapter,
)
from praxis_virtualcell.model_zoo.k562_golden_delta_contract import (
    K562GoldenPerturbationAdapter,
)

key = ("predict_delta_expression", "delta_expression")
assert DEFAULT_ADAPTER_REGISTRY.keys() == (key,)
default = DEFAULT_ADAPTER_REGISTRY.resolve(*key)
assert isinstance(default, DeltaExpressionReferenceAdapter)

adapter = K562GoldenPerturbationAdapter()
local = AdapterRegistry([adapter])
assert local.keys() == (key,)
assert local.resolve(*key) is adapter
assert DEFAULT_ADAPTER_REGISTRY.resolve(*key) is default

print("adapter", adapter.fingerprint())
print("input", adapter.input_contract.fingerprint())
print("output", adapter.output_contract.fingerprint())
PY
~~~

预期：

~~~text
adapter  873c4e441619da1eeeac8da3522b5c919dac0ab49b3a16cc36a74e020f55997e
input    46dc96360506b7ec7b25609c619960e97ae613e9d05277c26fc09a21d96d1fe3
output   10a211d99f2a2b8170e2fc9b0fb7030009849ff5e7d2968510e49c9375b21854
~~~

P16E adapter 与默认 adapter 共享 task/output，但 identity、scope 与 prepared bindings
不同。相同 task/output 或 import 成功不能把默认 generic reference adapter解释为 P16
capability。若 K562 adapter 出现在 `DEFAULT_ADAPTER_REGISTRY`、registry.yaml、wrapper、
routing、case dispatch 或自动发现的生产路径，立即停止。

## 3. Checked-in P8 identity 审计

只允许读取以下三个小型 checked-in manifests：

~~~bash
wc -c \
  data/golden/norman_2019/contract.yaml \
  data/golden/norman_2019/pack.manifest.yaml \
  data/golden/norman_2019/artifact-manifest.json

openssl dgst -sha256 \
  data/golden/norman_2019/contract.yaml \
  data/golden/norman_2019/pack.manifest.yaml \
  data/golden/norman_2019/artifact-manifest.json
~~~

预期 byte identities：

| File | Size | SHA-256 |
|---|---:|---|
| contract.yaml | 4,749 | 6bfc46e23e55e05a2c87dcdac9bd48da6c1f6bd2240742dc18f73ec963cf0d76 |
| pack.manifest.yaml | 30,074 | 704b81da74fd96907b7e6012757b2c12104fcf3a2a3ae56af52c76d7f2c163a6 |
| artifact-manifest.json | 3,864 | 724b701beda574ad344b764de09dafb86648e49c9a327df717212aaf25cc71ac |

Canonical/reference identities：

| Identity | Value |
|---|---|
| canonical Golden contract | f34afa761239abc97033c78bb9d0c29a1c36a4c7d1a106a9cbbaa805a5196ff5 |
| Pack fingerprint | 42165e430bab3474cdc9e607770ff5e204608c4243f84e492c08e2c6442c55ee |
| H5AD reference | `norman_k562_golden.h5ad`; 2,285,816,806 bytes; 43da7aeeaca2a3ceb00ec6e9ee983b9b708b01f85922cc7afee229225a66792a |
| Golden contract reference | `golden_contract.json`; 4,663 bytes; 456242651b50a87f507c6e9787999d4fd325beec82106363c7261cbdaa744521 |
| feature IDs | ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7 |
| feature records | 1cc8b612bef0a0d7daac01bb8cc509346a4a32850f93298f29865bb2328d9747 |
| split | c501e8a05514b914b216ddb2dbe0a94e709fa7a1e2214d727b831102503f956e |
| condition IDs | 6f41dd46159a926ad476152d20c2f82e5def422f16a8213b0918af48594cabb3 |
| matched control | 2fc6ba835e3a9353345651b9369abdd189c6017a854932c038b157faa4b378ae |
| perturbation IDs | e69d8b83e3f69a628c545b3c44f6ad694d8406619451f1db1b6489be33fc9e21 |
| condition values | 7f3e175c495bc9499d852965869bafc23249948e0be5c87eb89e5d01befc44c9 |
| perturbation records | 0a43f9c57560f7192c0a848cb1ec044a9bf2bfdbc20d6405f98d73b3ca04d1e9 |
| target IDs | 4f58ed5c3ad7355ccba64eed0dd95e02cbcbf75a977d6aec2a1cfd5357abd64c |
| control assignment | 8f09650026e297ce0e010120814230bc7de306364ab49316b7c102e836c6e3d5 |
| unseen train target IDs | 3bec2a15f4c5965dd32112c3508e4b70ead1724f308d597ab61e9b6210587de3 |

不要在本 runbook 中打开 H5AD 或 external `golden_contract.json`。Manifest reference 的
size/hash 不证明文件当前存在、可访问、获许可用于当前用途或可执行。

## 4. 冻结 exact scope、split 与 condition records

| 维度 | 唯一允许值或要求 |
|---|---|
| taxonomy | NCBITaxon:9606 / Homo sapiens |
| cell | K562 / CVCL_0004 |
| request cell encoding | `cell_type_name=K562`; `cell_type_id=None`; attributes 中 `cell_identity_id=CVCL_0004` |
| source metadata | A549 / upstream_metadata_error_preserved；永不作为 canonical request cell |
| assembly | GRCh38 / GCA_000001405.15 |
| assay/modality | scRNA / EFO:0008913 |
| feature identity | EnsemblGene / Ensembl 84 / ensembl_gene；exact ordered 5,045 features |
| task/output | predict_delta_expression / delta_expression |
| output shape/unit | (5045,) / null |
| semantics/reference | condition_mean_X_minus_matched_split_control_mean_X / matched_split_control_mean_X |
| perturbation | CRISPR activation；dose 1.0 unit `1`；time 5d |
| scopes | single_gene 与 combination 独立 |
| compatibility | assets_verified=false, executable=false, reason=p16r_not_authorized |

Split 固定为：

~~~text
source train -> train       137 non-control conditions
source test  -> validation   30 non-control conditions
source ood   -> test        116 non-control conditions
leakage guard              condition_id
~~~

Source control 是 `ctrl`。Exact derived controls：

~~~text
train       norman.control.train       NegCtrl0_NegCtrl0__NegCtrl0_NegCtrl0
validation  norman.control.validation  NegCtrl10_NegCtrl0__NegCtrl10_NegCtrl0
test        norman.control.test        NegCtrl11_NegCtrl0__NegCtrl11_NegCtrl0
~~~

Canonical condition fixtures：

| Scope | condition | ordered targets | record SHA-256 |
|---|---|---|---|
| single_gene | AHR+ctrl | ENSG00000106546 | e04567ee8d8fb3273d600b3dc8956c3f0dd35d4e4bab1d1a5ba1fb83f483b9c1 |
| combination | AHR+FEV | ENSG00000106546, ENSG00000163497 | 7b77f2c32cde91604fe8182fa38af90a991c1c10f27fdc116d6f94aa6eff2a85 |

Checked-in Pack text包含 284 个 perturbation records 与 286 个 conditions：`ctrl` 是
record-only，三个 `norman.control.*` 是 condition-only。该有意结构不是缺失记录。
P16E 的 condition binding 可验证 proposal 自身 canonical record hash，但固定
`record_membership_verified=false`；aggregate hash 不能替代 P16R 对 external bytes 的
membership verification。

## 5. Prepared input 审计

`K562GoldenPerturbationAdapter.prepare_input` 必须消费调用方显式传入的 request、scope、
protocol、model artifact、environment、release、data binding、perturbation binding、
execution binding 与 negative compatibility。重点检查：

- human/K562/GRCh38、task/output/unit、scRNA/Ensembl 84 与 dose/time exact；
- core request 的 `cell_type_id=None`，CVCL identity 只在 strict attributes；
- condition、scope、kind 与 ordered Ensembl targets 全部相等；
- baseline_context 绑定 source `ctrl`、matched-control hash、control-assignment hash 与
  exact scope；
- request constraints 绑定 condition、value semantics、perturbation/protocol fingerprints
  与 `record_membership_verified=false`；
- release 引用 exact artifact/environment/adapter/Pack，且不含 evidence/policy；
- artifact 是 `application/json`、`safe_load_policy=data_only` 的 identity-only fixture；
- Pack/data、execution、compatibility、scope 和 protocol fingerprints 交叉一致；
- execution 保持 feature order，并显式禁止 absolute-to-delta conversion、normalization、
  reorder、fill、imputation 与 deduplication；
- prepared model input 每次消费时重新 strict validation，不能用 hidden field、subtype 或
  `model_copy` extra 绕过。

缺绑定必须抛出 `AdapterContractError`。不得扫描目录、打开 URI、加载 H5AD/model、从
A549、gene symbol、versioned ID、ortholog、legacy card 或 model name 猜 fallback。

## 6. Validation protocol 审计

未来 P16R protocol 必须保持：

~~~text
split_name                       norman-condition-holdout-v1
leakage_guard                    condition_id
primary_metric                   condition_macro_full_feature_delta_mse
metric_direction                 lower_is_better
primary_comparator               condition_level_additive_ridge
historical_comparator_role       checked_in_historical_reference_only
same_runtime_required            true
contamination_audit_required     true
paired_difference                candidate_mse_minus_additive_ridge_mse
bootstrap_unit                   held_out_perturbation_condition
bootstrap_method                 paired_percentile
bootstrap_rng                    numpy.PCG64
bootstrap_seed                   0
bootstrap_replicates             2000
bootstrap_interval               0.025, 0.975
candidate superiority            paired_difference_ci_upper_below_zero
stochastic_seeds                 11, 23, 37
validation_only_tuning           true
external requirement             independent_semantically_compatible_k562_dataset_platform
external_adaptation_steps        0
separate_scope_evaluation        true
record_role                      preregistration_not_evidence
~~~

Historical additive result是
`b82dc7ab26c6f6fdef4414f6b05c51edb32b2a35e4c00f45824cc839ab9cf1a9`，
P8 test MSE 是 `0.0032570634320908554`。这是 checked-in historical reference，不是
P16 candidate result。没有真实 candidate outcome、paired CI、contamination audit、
independent K562 external 与 OOD result 时，不能创建 validation evidence。

Canonical OOD order：

~~~text
iid
perturbation
combination
cell_type
donor
dataset_platform
species
dose_time
~~~

Donor 或非 K562 external 只能作为 OOD，不能替代独立 K562 dataset/platform gate。
Single-gene 与 combination 的 protocol、结果和晋级必须分开。

## 7. Output、uncertainty、OOD 与 abstain

成功 raw output 只允许：

~~~text
prediction:
  delta_expression
  feature_ids_sha256
  feature_records_sha256
  n_features
  value_semantics
  reference
  condition_id
  evaluation_scope
  unit
prediction_status
scope_fingerprint
uncertainty
ood
abstain
abstain_reasons
~~~

`delta_expression` 必须是 exact 5,045-value finite JSON-safe vector。Adapter 原样透传，
不 normalize、reorder、fill、impute、deduplicate、clip 或执行 absolute→delta conversion。
公开 projection 只能含 `delta_expression` 一个 key，其 value 必须是 5,045 个 exact
finite values；不得加入 metadata、evidence、policy 或其他 prediction。

Uncertainty 必须精确为 unavailable/uncalibrated neutral state：

~~~text
available   false
calibrated  false
value       null
sigma       null
method      not_available
reason      no_calibrated_uncertainty_declared
~~~

授权状态不得放进 uncertainty；`p16r_not_authorized` 只属于 compatibility。

| 现象 | 必须行为 |
|---|---|
| request/scope/Pack/provenance fingerprint 漂移 | 拒绝 |
| wrong cell/assembly/assay/namespace/condition/scope/target order/dose/time | 拒绝或 exact-axis OOD abstain |
| A549 被用作 request cell | 拒绝 |
| NaN、Infinity、bool、unsafe integer、错 shape/unit/semantics/reference | 拒绝 |
| target_not_found 或 error | value-free abstain，包含 reason |
| unsupported_scope | detected OOD + canonical dimension/reason + value-free abstain |
| 任意 OOD detected | value-free abstain |
| abstain 仍含 prediction 或缺 reason | 拒绝 |
| unknown/reserved science/policy/promotion field | 拒绝 |
| standalone validate/project/aggregate | 拒绝；必须提供 exact prepared binding |

## 8. Canonical synthetic fingerprints

Adapter-global 与 shared identities：

~~~text
adapter             873c4e441619da1eeeac8da3522b5c919dac0ab49b3a16cc36a74e020f55997e
input contract      46dc96360506b7ec7b25609c619960e97ae613e9d05277c26fc09a21d96d1fe3
output contract     10a211d99f2a2b8170e2fc9b0fb7030009849ff5e7d2968510e49c9375b21854
artifact            38f21e38edcd2876095c29a342c8dc4f04c52f8afcb914079a69721211a30714
environment         e4764936dabfdc36bb011190a8d4b3846fa5cc73bc5d58978dffef7f4ffe0572
model release       a2b61b216dae1547429435b1bcc7351c7d63b4a0ec61f28338a5342bb249bb9b
data binding        080f140a48eed4b2a8a072b262132c64cd376d5418cf1edca0a4c3ed58a7c167
execution binding   c11517270bc132ca6581019cc6449fa94e69298aae6fc0f4b9f706967c090ecb
~~~

Scope-specific identities：

| Identity | single_gene | combination |
|---|---|---|
| perturbation | 454a851530484b4993e9a1a07ccef6f724684e65b21171d32c37545c8959b6b2 | 01eb25c45e844e22a15f85b5fe4c1fc9b55c4350532450a700d86a1cc0f8f573 |
| compatibility | 5ccdeffe1cfb2188cf8dc4232aba8bc02e97be45b2bb742ec71baecd246c0f6f | 414d64b93a398080fd3172f51d76513250349f39b71ef0fe478d27f2a2f7c170 |
| scope | 14393395712f70d4e05bfa220933548695d3d619162d9a8e23f082f96b3a7f24 | 579b2eee8fd32a410443086983c224ad83ea18226c6d696332c5a8b01da0926f |
| protocol | 5322aa8261d786482c4d24a92e7f40bbf55fef8cecfd3819ca9bb778b274d73b | a6700ae44273cb3f788724be10239b40c89217c378c9bd2f0aedd14a6776f229 |
| prepared | d54d10582bd5abe3a16848d1fa3fb2ad48dd16fab6b0cfb4756c4bffcb985322 | 94b541ee7a4500a33ff862d6f531ebd5a4cc6e7633c2f7db64c48057d268290a |
| envelope | 69f948b0282a0cc1be59d8c6a5a3efa2f32848b3d4ab0bc21223e9993769b73b | add96cc86478db890a594512afe92a97c0380d79893992de01596ecef51bd1eb |
| conformance report | e3083e73df38a045e707d2117309ddf5f0fef824fc26f521f97fa4f1aba0f4c5 | 42f9612a6eb5e433a826c5b21e6a20c622df2a7dba2369c347cb01c9192ce203 |

这些都是 synthetic conformance identities，不表示外置 asset/candidate 存在、许可已
审查、模型可执行、MSE 达标、科学有效或产品获批。

## 9. 安全本地验证

P16E contract suite：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_k562_golden_delta_contract.py \
  -o addopts='' -p no:cacheprovider -q -ra
~~~

安全 eleven-file directed gate：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_k562_golden_delta_contract.py \
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
| P16E contract | 231 passed |
| safe eleven-file directed | 689 passed |
| safe legacy | 1147 passed, 58 skipped, 105 deselected |
| authoritative Ruff | PASS |
| format check | PASS |
| git diff --check | PASS |
| final adversarial review | no remaining P1/P2 findings |

不要用本 runbook 运行 Golden benchmark/science、GEARS/scGPT、remote、GPU、真实 model
wrapper 或外置 asset paths。Skip/deselect 不能写成这些能力通过。

## 10. Packaging 证据与边界

Exact completion code commit 的 build epoch 已冻结为：

~~~text
SOURCE_DATE_EPOCH       1786011676
wheel size              1,108,165 bytes
wheel SHA-256           d333180996a4ed91161d364275589e992d0be634582cc83a57e9758b86c03c66
archive entries         365
React static entries    14
test entries            0
AppleDouble/__MACOSX    0
Python / Node / npm     3.13.12 / 24.14.0 / 11.11.1
build toolchain         build 1.5.0 / setuptools 83.0.0 / wheel 0.47.0 / packaging 26.2
~~~

两个独立 exact `9f6b14e…` clean-archive build 在 sandbox network denial、npm offline
边界内产生上述 byte-identical wheel，且包含 P16E module。该证据只证明 exact 本地
source/toolchain 的 wheel reproducibility；不证明 strict offline dependency closure、
科学执行或发布。official strict script 因本地 hash cache 缺 `packaging==26.2` 而 fail
closed，未生成 wheel；全局 `pip check` 受已有 invalid distributions/dependency conflicts
污染，不能作为 P16E 证据。

Python 3.13 临时 system-site venv 以 offline `--no-deps` 安装该 wheel 后，从 checkout
外确认 installed package 来自 venv、P16E adapter import/fingerprint 通过、默认 generic
registry 不变且 `praxis-vc --version` 返回 `1.6.0`。这只是有限 installed-wheel smoke；
继承的受污染 system packages 使它不能作为 clean hash-locked install 或 dependency-
integrity 证据。所有结果均不能从 P15E 历史构建继承。

无论包装结果如何，P16E 都没有 product/API/runtime version bump、tag、push、PR、
publication、release 或 deployment。

## 11. P16R/P16B 停止条件与 P17

没有逐项 exact absolute path、size、SHA-256、license、source、只读 source root、
write-new output root、run window、network/GPU policy 和 candidate/environment identity
授权时，不得进入 P16R。P16R 至少还需运行同 runtime baseline/candidate、contamination
audit、三 seeds、scope-separated paired CI、independent K562 external 和 OOD gates。

没有正 P16R evidence 与具名 operator 时，不得进入 P16B。P16E completion 不改变
`real_assets_verified=false`、`executable=false`、`scientifically_validated=false` 或
`production_promoted=false`。

下一 eligible 本地 work unit 是 P17 Virtual Cell Brain contract-only engineering。
实际 P17 starting SHA 必须在 P16E docs-closure 后从 Git history 读取，不能在本文件中
预测。当前少于两个 P14–P16 production-promoted capabilities，因此 P17 可完成合同/DAG
工程，但不得声称真实多模型执行已通过。P16R/P16B 保持独立授权窗口。
