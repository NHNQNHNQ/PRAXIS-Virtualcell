# VirtualCellPack P8 Golden Norman/K562 runbook

## 1. 适用范围

本 runbook 只复现：

```text
公开 Norman source
→ hash-locked semantic Pack
→ 三个固定简单 baseline
→ 正式 Pack-aware runtime
→ condition-macro MSE + paired bootstrap artifact
```

它不运行 GEARS，不读取 GEARS checkpoint，不修改默认 model zoo，不部署服务，
不授予 `scientifically_validated=true`。所有输出目录必须是新目录；实现会拒绝
原地覆盖。

## 2. 真相源

Git 内小文件：

- `data/golden/norman_2019/contract.yaml`
- `data/golden/norman_2019/pack.manifest.yaml`
- `data/golden/norman_2019/model_cards/*.yaml`
- `data/golden/norman_2019/artifact-manifest.json`

`.53` 已验证资产根：

```text
/home/zkyd/data1/mzy/praxis-virtualcell-data/golden/norman-2019
├── source/
├── pack/
├── model_cache/
├── registries/
└── evaluation/evaluation.json
```

不要把该目录复制进 Git。

## 3. 环境

从仓库根使用 Python 3.13 strict dev lock；baseline 还需要 `omics` 中的
anndata/scipy stack：

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: \
  --require-hashes -r requirements/build-py313.lock
.venv/bin/python -m pip install \
  --require-hashes -r requirements/dev-py313.lock
.venv/bin/python -m pip install \
  --no-build-isolation --no-deps -e .
.venv/bin/python -m pip check
```

不得临时安装 GEARS、torch 或 checkpoint。

## 4. 获取并核对 source

在一个新建的外置工作目录执行：

```bash
mkdir /absolute/new/norman-source
cd /absolute/new/norman-source

curl --fail --location --retry 3 \
  --output Norman2019_simulation_cpa.h5ad.zip \
  https://dataverse.harvard.edu/api/access/datafile/6881912

printf '%s  %s\n' \
  64af382a6af9d129042577a651691d0bdbbdeef2ad973bef77f012b4b209c41f \
  Norman2019_simulation_cpa.h5ad.zip | sha256sum --check -

unzip Norman2019_simulation_cpa.h5ad.zip \
  Norman2019_simulation_cpa.h5ad

printf '%s  %s\n' \
  de50bb456ea344ae934878def8339e8b7050baf934a69bda2c7196bcb3a0e6cd \
  Norman2019_simulation_cpa.h5ad | sha256sum --check -
```

macOS 可用 `shasum -a 256` 或 `openssl dgst -sha256` 独立核对。任一 hash/size
不符就停止；不得修改 contract 迎合下载内容。

### 4.1 单条真实 held-out 预测

下载与 H5AD 校验完成后，可用一个项目内入口完成 Pack 派生、冻结 baseline 构建、
formal no-legacy runtime、单条件评分和 write-new receipt：

```bash
.venv/bin/python -m praxis_virtualcell.benchmarks.golden_norman_run \
  --source-h5ad /absolute/new/norman-source/Norman2019_simulation_cpa.h5ad \
  --output-dir /absolute/new/ahr-klf1-run \
  --condition-id AHR+KLF1
```

`--source-h5ad` 只接受本地文件；入口不联网、不下载模块、不发现远程模型。
`--output-dir` 必须是尚不存在的绝对路径，父目录必须已存在。默认条件
`AHR+KLF1` 是冻结 `test`/source `ood` 组合；训练条件 `AHR+ctrl` 和 validation
条件都会被拒绝，失败时不会发布最终目录。

输出 `prediction.json` 使用 `vc.golden-condition-run.v1`，保存完整 5,045-feature
预测、observed truth hash、单条件 full-feature MSE、Pack/model/runtime identities，且固定：

```text
legacy_predictors_registered=false
plan_legacy_adapter=false
benchmark_evidence_created=false
scientifically_validated=false
production_promoted=false
p16r_run=false
policy_changed=false
```

P8 v1 卡片只声明 `perturbation: gene`，所以组合在该冻结路径中仍编码为 `gene` 加
两个 ordered Ensembl target。receipt 会显式记录
`legacy_perturbation_encoding=gene_with_multiple_ordered_targets`；这不是严格 P16R
`gene_combination` binding，不能据此修改 P8 卡片或提升科学状态。

## 5. 派生 Pack

假设新输出根为 `/absolute/new/golden-run`：

```bash
.venv/bin/python -c \
  "from praxis_virtualcell.benchmarks.golden_norman import derive_pack; derive_pack('/absolute/source/Norman2019_simulation_cpa.h5ad', '/absolute/new/golden-run/pack')"
```

该步骤先验证 source file、obs/var 和 X/counts 的全部冻结 hash，再为每行增加
显式 semantic 字段。它复制 X/counts，不归一化、不补零、不去重、不随机 split。
成功前临时目录不会成为最终 Pack。

核对派生 matrix 仍与 source 合同一致：

```bash
.venv/bin/python -c \
  "from pathlib import Path; from praxis_virtualcell.benchmarks.golden_norman import _verify_matrix_storage, load_contract; _verify_matrix_storage(Path('/absolute/new/golden-run/pack/norman_k562_golden.h5ad'), load_contract()['source']['h5ad']); print('OK')"
```

## 6. 构建 baseline 与正式评估

```bash
.venv/bin/python -c \
  "from praxis_virtualcell.benchmarks.golden_norman import build_baseline_assets; build_baseline_assets('/absolute/new/golden-run/pack', '/absolute/new/golden-run/model_cache', '/absolute/new/golden-run/registries')"

.venv/bin/python -c \
  "from praxis_virtualcell.benchmarks.golden_norman import evaluate_baselines; evaluate_baselines('/absolute/new/golden-run/pack', '/absolute/new/golden-run/model_cache', '/absolute/new/golden-run/registries', '/absolute/new/golden-run/evaluation/evaluation.json')"
```

`evaluate_baselines` 对全部 30 个 validation 和 116 个 test condition，逐个使用
对应的一卡 registry 进入正式 broker/governance/report；没有 direct-to-score 的
mock shortcut。evaluation 记录每个 condition 的 prediction/report hash、loss、
路径无关的 report/compatibility contract hash 和三层状态，并以同一 condition
索引完成 paired bootstrap 比较。底层 runtime 保留绑定本机绝对 asset path 的原始
compatibility fingerprint；冻结 evaluation 只收录其路径无关合同投影。

预期 test MSE：

```text
no_change       0.006206092317116851
global_mean     0.0045820474227155905
additive_linear 0.0032570634320908554
```

数值或 artifact hash 不符时，先隔离整个新 run；不得调 split、metric、seed、
alpha 或 feature order。

## 7. 测试

```bash
.venv/bin/python -m pytest \
  praxis_virtualcell/tests/test_golden_norman.py \
  -o addopts='' -q -ra

.venv/bin/ruff check \
  praxis_virtualcell/benchmarks/golden_norman.py \
  praxis_virtualcell/model_zoo/wrappers/golden_baseline_wrapper.py \
  praxis_virtualcell/agents/ensemble.py \
  praxis_virtualcell/tests/test_golden_norman.py
```

阶段发布门仍需完整 core 和 legacy，不能只报定向测试。

## 8. `.53` 只读复核

```bash
cd /home/zkyd/data1/mzy/praxis-virtualcell-data/golden/norman-2019
find . -type f -print0 | sort -z | xargs -0 sha256sum
find . -type f -printf '%s %p\n' | sort -k2
```

结果必须逐项等于 Git 的 `artifact-manifest.json`。远端 Pack 不是部署；不要改
`/home/zkyd/data1/mzy/PRAXIS-virtualcell`、PRAXIS-2、systemd/nginx、main 或 tag。

## 9. 失败处理

- source/derived hash 不符：停止并隔离，不关闭验证。
- control guide 或 source split 未知：停止；不随机分配或 fallback。
- target 重复/未知：拒绝；不做 symbol/ortholog 转换。
- baseline asset 缺失/篡改：正式 runtime 应 abstain；不得转 mock。
- evaluation report 出现 `scientifically_validated=true`：视为合同破坏。
- 需要运行 GEARS：另行取得 `.53`、模型/checkpoint 精确 hash 与运行授权；本
  runbook 不提供该权限。
