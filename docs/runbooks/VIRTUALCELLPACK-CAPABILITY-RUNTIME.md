# VirtualCellPack P6 Capability Runtime Runbook

本 runbook 复现 P6 的本地、确定性、Pack-aware 模型计划。它不下载权重、不运行
GPU/remote/LLM，也不授予科学验证状态。

## 1. 前置条件

- 使用已安装 `omics`/dev 依赖的 Python 3.13 环境；
- Pack 必须先由 `PackRegistry.register()` 完整验证；
- 模型资产只放在本地 cache，不能提交到 Git；
- model card 中每个 asset 的 filename、SHA-256 和 media type 必须与实际文件一致。

默认 cache 布局：

```text
~/.cache/praxis_virtualcell/model_zoo/
└── <model_name>/
    └── <declared asset filename>
```

P6 不联网取权重，也不会在缺文件时改用 mock。

## 2. 组装 Pack-aware runtime

```python
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import EnvironmentSnapshot
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

zoo = ModelZooRegistry("/absolute/path/to/registry.yaml")
packs = PackRegistry()
packs.register("/absolute/path/to/validated-pack")
cache = ModelCache("/absolute/path/to/model-cache")
cards = tuple(zoo.card(name) for name in zoo.capability_names())
environment = EnvironmentSnapshot.detect(cards)

runtime = build_runtime(
    model_registry=zoo,
    model_cache=cache,
    pack_registry=packs,
    environment=environment,
)
request = VirtualCellRequest.from_dict({...})
report = runtime.run_workflow(
    request,
    pack_id="declared-pack-id",
    pack_version="declared-pack-version",
)
```

`pack_id` 与 `pack_version` 必须成对出现。无两者时走显式 legacy adapter；只给
一个会在任何 predictor 执行前抛出 `ValueError`。

## 3. 审计产物

Pack-aware report 的 provenance 必须包含：

```text
execution_plan.schema_version == vc.execution-plan.v1
execution_plan.request_fingerprint
execution_plan.pack_fingerprint
execution_plan.environment_fingerprint
execution_plan.steps
compatibility_reports[*].schema_version == vc.compatibility-report.v1
compatibility_reports[*].pack_valid
compatibility_reports[*].model_compatible
compatibility_reports[*].environment_compatible
compatibility_reports[*].scientifically_validated == false
compatibility_reports[*].checks
compatibility_reports[*].reasons
```

`steps` 为空是合法的 fail-closed 结果，不是 planner 错误。此时 runtime 必须
abstain，且 `models_used=[]`，不能出现 Mock predictor fallback。

## 4. 新增 plugin 的最小合同

新增 plugin 只需：

1. 在 registry 增加完整 `vc.model-card.v1`；
2. 提供一个 `ModelWrapper` 子类；
3. 把小型测试资产放入测试临时 cache，真实大资产放在 Git 外 cache；
4. 运行契约测试。

不应修改：

```text
workflows/predict_delta_expression.py 的模型专用分支
agents/route_table.py
predictors/case_dispatch.py
```

当前 runtime plugin 只支持模型卡声明
`task=predict_delta_expression`、`output` 包含 `delta_expression`，并要求：

```python
{
    "prediction": {"delta": [0.25, ...]},  # 非空、有限数字；bool/NaN/Inf/超大不可表示整数拒绝
    "uncertainty": {"method": "<card-declared method>"},
    "evidence": [...],                     # 可选 list
    "provenance": {...},                   # 可选 object
}
```

整个返回对象必须递归满足 JSON 类型合同；tuple、自定义对象和非有限浮点不会被
字符串化或静默归一。Broker 在生成计划时检查资产，并在实例化前重新核对 hash。

其他 task/output 需要新的显式 execution adapter 和测试，不能通过改
Environment 声明绕过实际 coordinator 能力。

## 5. 常见拒因

| reason | 操作 |
|---|---|
| `pack.unregistered` | 注册并完整验证精确 Pack ID/version；不要直接传 manifest |
| `request_pack.modality` | 检查请求 modality 是否确实存在于 Pack |
| `request_pack.feature_namespace` | 显式 namespace 必须属于请求 modality 的 Pack 合同 |
| `asset.missing:<file>` | 把精确资产放入对应模型 cache；不要 fallback |
| `asset.sha256:<file>` | 重新核对文件来源；只有确认的新版本才更新 card hash |
| `environment.dependency:<module>` | 在批准环境安装声明依赖；不要伪造 snapshot |
| `environment.resource:<resource>` | 使用真实具备该资源的环境 |
| `environment.runtime_task:*` / `runtime_output:*` | 当前 runtime 没有该 adapter；另立阶段实现 |
| `model.wrapper` / `model.wrapper_initialization` | 修复 class path/constructor；不要绕过 Broker |

## 6. 本地验证

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_capability_runtime.py \
  -o addopts='' -p no:cacheprovider -q -ra

python -m pytest praxis_virtualcell/tests \
  -m "not llm" -o addopts='' -q -ra

python -m pytest tests \
  -m "not (integration or llm or remote)" \
  -o addopts='' -q -ra

ruff check . --no-cache
```

普通本地 skip 不等于 remote/GPU/LLM 通过。P6 不运行 `.53` 真模型，也不修改
GitHub、main/tag 或远端 checkout。
