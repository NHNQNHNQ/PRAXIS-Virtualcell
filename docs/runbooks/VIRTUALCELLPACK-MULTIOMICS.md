# VirtualCellPack P5 多组学复现 runbook

本 runbook 只复现 tiny RNA+protein Pack、H5MU loader 和显式 feature alignment。
它不下载真实数据、不运行模型，也不构成科学验证。

## 环境

在仓库根目录使用 Python 3.13 的完整 hash lock：

```bash
python3.13 -m venv /tmp/praxis-p5-venv
/tmp/praxis-p5-venv/bin/python -m pip install \
  --require-hashes -r requirements/build-py313.lock
/tmp/praxis-p5-venv/bin/python -m pip install \
  --require-hashes -r requirements/dev-py313.lock
/tmp/praxis-p5-venv/bin/python -m pip install \
  --no-build-isolation --no-deps -e .
/tmp/praxis-p5-venv/bin/python -m pip check
```

MuData 是可选 `omics` 依赖。base/runtime-only 安装导入
`praxis_virtualcell.data_packs` 时不会导入或 fallback 到 MuData。

## tiny Pack 来源

- `praxis_virtualcell/tests/fixtures/mudata/rna_protein.yaml`：manifest source、
  四个全局 observation、部分配对 RNA/protein feature 表；
- `praxis_virtualcell/tests/fixtures/mudata/rna_mapping.json`：带 schema、ID、
  version、alias 和 aggregate 的显式 mapping asset；
- `praxis_virtualcell/tests/test_mudata_alignment.py::_write_pack`：只在 pytest
  临时目录生成 CSR H5MU，随后计算 bytes、size 和 SHA-256，并生成严格 manifest。

fixture source 中的 `fixture_*` 字段只是生成输入，不是合法 manifest 字段；生成器
在调用生产验证器前移除它们。不要把临时 H5MU 提交到 Git。

## 权威定向验证

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_mudata_alignment.py \
  -o addopts='' -p no:cacheprovider -q -ra
```

该模块覆盖：

- paired 与 partially-paired observation；
- backed/read-only H5MU、公开 API 和禁用 annotation pull；
- modality order、shape、media type、target modality 与 registry fail-closed；
- v0.1 frozen fingerprint；
- strict default；
- alias、aggregate、drop、fill、reorder 的显式授权、数值结果与 provenance；
- 无自动补零、无 ortholog/namespace fallback；
- mapping bytes/version 与 Pack/contract fingerprint；
- optional dependency 与 runtime-lock 边界；
- Ensembl/UniProt canonical ID 和超大 fill 整数异常边界。

## 使用生产 API 的最小形态

```python
from praxis_virtualcell.data_packs import (
    ModelFeatureContract,
    align_features,
    load_mudata_view,
)

contract = ModelFeatureContract.from_dict(contract_json)
with load_mudata_view(pack_root) as pack:
    aligned = align_features(
        pack.modality("rna"),
        contract,
        mapping_root=pack_root,
    )
    provenance = aligned.report.to_dict()
```

`align_features` 成功只表示该 modality 满足模型输入合同。调用方必须把
`AlignmentReport` 一并保存；不得据此声称模型已经运行或
`scientifically_validated`。

## 资产修改规则

1. mapping bytes 改变时重新计算其 SHA-256，并更新 Pack asset 和
   `ModelFeatureContract.mapping_asset`；
2. mapping 语义改变时同时递增 `mapping_version`；
3. H5MU bytes、shape 或 observation/feature identity 改变时更新 manifest
   size/hash/shape 和 Pack version；
4. 不在验证器前做归一、补零、去重、重排、随机 split 或 ortholog projection；
5. 真实大数据与权重保持在 Git 外，只提交 manifest、许可/provenance、hash、
   小型 fixture 和本 runbook。
