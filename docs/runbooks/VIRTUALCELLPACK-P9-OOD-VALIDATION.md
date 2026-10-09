# VirtualCellPack P9 OOD / abstention / external validation runbook

本 runbook 只重放已冻结的 P9 结果。它不下载到 Git、不访问 `.53`、不运行
GEARS、不修改 model zoo/runtime/API/UI，也不把失败模型升级为可用模型。

## 1. 合同与小型 artifact

```text
data/benchmarks/p9/ood-manifest.json
data/benchmarks/p9/group-fixture.json
data/benchmarks/p9/external-validation.json
data/benchmarks/p9/SHA256SUMS
```

`group-fixture.json` 是八轴分组与泄漏审计的合同 fixture，不是科学 performance
dataset。`external-validation.json` 只含 condition-level 结果和 hash，不含原始
count matrix 或 4,484 维参数。

校验 Git 内文件：

```bash
cd data/benchmarks/p9
sha256sum -c SHA256SUMS
```

macOS 没有 `sha256sum` 时逐项使用 `openssl dgst -sha256`，并与
`SHA256SUMS` 比较。

## 2. 获取四个公开输入

在 Git 外创建临时目录：

```bash
work_dir="$(mktemp -d)"
cd "$work_dir"

curl --fail --location --output GSE67402_counts.csv.gz \
  'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE67nnn/GSE67402/suppl/GSE67402_counts.csv.gz'
curl --fail --location --output GSE67402_family.soft.gz \
  'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE67nnn/GSE67402/soft/GSE67402_family.soft.gz'
curl --fail --location --output GSE94117_RAW.tar \
  'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE94nnn/GSE94117/suppl/GSE94117_RAW.tar'
curl --fail --location --output GSE94117_family.soft.gz \
  'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE94nnn/GSE94117/soft/GSE94117_family.soft.gz'
```

必须先核对：

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `GSE67402_counts.csv.gz` | 168,809 | `4d8e8e4bee7cf08dea4247f319403c1399af6c9e4069f40f65f54911b748a688` |
| `GSE67402_family.soft.gz` | 5,055 | `2b150e6b48a0d7fc48aa1a5b8de4e7c3a6b569206d054ca3e22fcd33154ff881` |
| `GSE94117_RAW.tar` | 2,560,000 | `3433f1d37d90fd24fa59b19b04e52cb68fc6201d5e49408efcb610fe47d18483` |
| `GSE94117_family.soft.gz` | 11,234 | `7b99331077d6aaa392c65a5070baf279bcfc5174d6daff512120c0a2f5f179a4` |

任何 filename、size 或 hash 不一致都必须停止。脚本不会接受镜像替代、解压后的
bytes、缺文件或 mock。

## 3. 重放

从仓库根运行；需要测试/omics 环境中的 NumPy，但不需要 GPU：

```bash
python scripts/build_p9_external_validation.py \
  --manifest data/benchmarks/p9/ood-manifest.json \
  --source-counts "$work_dir/GSE67402_counts.csv.gz" \
  --source-soft "$work_dir/GSE67402_family.soft.gz" \
  --external-raw "$work_dir/GSE94117_RAW.tar" \
  --external-soft "$work_dir/GSE94117_family.soft.gz" \
  > "$work_dir/external-validation.json"

cmp data/benchmarks/p9/external-validation.json \
  "$work_dir/external-validation.json"
```

`cmp` 必须无输出且返回 0。脚本只向 stdout 写结果；不会修改仓库或输入目录。

## 4. 冻结结果

| 指标 | candidate | no-change baseline |
|---|---:|---:|
| condition-macro MSE（主） | 1.0603835779 | 1.0533347059 |
| condition-macro MAE | 0.6632488091 | 0.6671449858 |
| condition-macro Pearson | 0.5749060334 | undefined / `null` |

paired MSE difference 是 `+0.0070488720`，95% CI
`[-0.9076414928, 0.9749711895]`。冻结阈值是
`-0.4150374993`，external coverage `0.625`，wrong accept `0.75`，
unnecessary abstain `0.5`。

结论必须保持：

```text
available=false
scientifically_validated=false
reason_codes=[
  "primary_not_better_than_baseline",
  "primary_ci_not_below_zero"
]
```

不能因为 MAE 略好、Pearson 有限、某些 time point 胜出或代码执行成功而改写该
结论。

## 5. 测试

```bash
python -m pytest -q praxis_virtualcell/tests/test_ood_validation.py
ruff check praxis_virtualcell/benchmarks/ood_validation.py \
  praxis_virtualcell/benchmarks/p9_external.py \
  praxis_virtualcell/tests/test_ood_validation.py
```

测试覆盖 duplicate/unknown field、八轴 partition、biological-unit/replicate
泄漏、feature-label 泄漏、validation-only threshold、选择性指标、baseline/CI
门禁、外部来源 hash、adaptation steps 和结果篡改。

## 6. 允许的更新

任何 source bytes、cohort、split、feature policy、transform、candidate、
baseline、阈值目标、metric、bootstrap 或 promotion gate 改动，都必须：

1. 新建 schema/benchmark identity；
2. 重新进行泄漏审计；
3. 重新生成 result 与 hash；
4. 单独审查科学结论；
5. 不覆盖本 P9 artifact。
