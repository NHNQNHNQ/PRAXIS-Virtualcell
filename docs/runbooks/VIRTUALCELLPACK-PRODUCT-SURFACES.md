# VirtualCellPack 产品面运行手册

本手册覆盖 Phase 8 的微型 Pack、CLI、只读 API、React 能力展示和历史 job
identity。它不授权部署、远端写入、模型下载或科学状态提升。

## 1. 安装与本地路径

完整 Pack 校验需要 omics 依赖：

```bash
python -m pip install -e ".[api,omics]"
export PRAXIS_VC_PACK_INDEX=/absolute/path/pack-index.json
export PRAXIS_VC_RUNS=/absolute/path/runs
```

自定义 model card/cache 可显式配置：

```bash
export PRAXIS_VC_MODEL_REGISTRY=/absolute/path/models.yaml
export PRAXIS_VC_MODEL_CACHE=/absolute/path/model-cache
```

未配置时使用现有默认 model zoo/cache。不要把权重或大数据放进 Git。

## 2. CLI

```bash
# 只解析 manifest；不会声称 Pack 已通过资产/数据验证
praxis-vc pack inspect /absolute/path/to/pack

# 完整验证 manifest、asset bytes 和 H5AD/H5MU 语义
praxis-vc pack validate /absolute/path/to/pack

# 完整验证后写入本地索引
praxis-vc pack register /absolute/path/to/pack

# 列出内置/已注册 Pack；每次重新验证
praxis-vc pack list

# 只规划 compatibility，不执行
praxis-vc pack compatibility \
  --request /absolute/path/request.json \
  --pack-id p8-human-tiny \
  --pack-version 1.0.0

# 正式 Pack-aware runtime；没有可执行模型时诚实弃权
praxis-vc pack run \
  --request /absolute/path/request.json \
  --pack-id p8-human-tiny \
  --pack-version 1.0.0 \
  --mode offline \
  --out /absolute/path/runs/job-id
```

`inspect` 的 `pack_valid=null` 是有意状态，不得解释为通过。`validate/register/list`
均不计算某个请求的 model compatibility。

## 3. API

启动：

```bash
praxis-vc serve --host 127.0.0.1 --port 8000
```

只读 discovery/validation：

```bash
curl -s http://127.0.0.1:8000/api/packs
curl -s \
  http://127.0.0.1:8000/api/packs/p8-human-tiny/1.0.0
curl -s \
  http://127.0.0.1:8000/api/packs/p8-human-tiny/1.0.0/validate
```

只读 compatibility planning 使用 POST 传入 request body：

```bash
curl -s -X POST http://127.0.0.1:8000/api/packs/compatibility \
  -H 'Content-Type: application/json' \
  --data @- <<'JSON'
{
  "request": {
    "request_id": "p8-example",
    "species": "human",
    "cell_type": "K562",
    "perturbation_type": "gene",
    "perturbation_targets": ["AHR"],
    "input_modality": "scRNA",
    "output_modality": "delta_expression",
    "task_type": "predict_delta_expression"
  },
  "pack_id": "p8-human-tiny",
  "pack_version": "1.0.0"
}
JSON
```

API 没有 `/api/packs/register`。执行继续使用 `POST /api/jobs`，在原 body 中同时
提供 `pack_id` 和 `pack_version`。历史身份可从
`GET /api/reports/{job_id}/provenance` 的 `execution_identity` 读取。

## 4. 状态解释

| 字段 | 只表示 | 不表示 |
|---|---|---|
| `pack_valid` | 当前 manifest、asset 和 schema/数据语义通过完整验证 | 任何模型可运行 |
| `model_compatible` | 指定 request×Pack×model×environment 通过 compatibility | 模型准确或科学有效 |
| `scientifically_validated` | 独立、可复现的科学验证状态 | 可由前两者或一次成功执行推导 |

Pack catalog 中 `model_compatible=null` 表示还没有绑定具体 request 做判断。React
只展示这些后端字段，不在浏览器重算。

## 5. 故障检查

- `pack_index_invalid`：检查索引 JSON schema、重复字段、canonical path 和冲突；
- `pack_not_found`：核对完整 ID/version，禁止只按 ID 猜版本；
- HTTP 422：核对 Pack ID/version 是否成对提供以及 envelope 是否有拼错/未知字段；
  服务不会忽略这些字段后降级到 legacy；
- `pack_unavailable`：重跑 `pack validate`，按首个 size/hash/semantic 错误修复源
  Pack；不得改 manifest hash 迎合未知文件；
- `execution_plan.executable=false`：阅读每个 compatibility report 的 reasons；
  缺模型、asset、dependency、modality、cell domain 或 taxon 都应保持弃权；
- `job_already_exists`：换一个新 job ID；不得覆盖旧目录。

## 6. 验收命令

```bash
python -m pytest praxis_virtualcell/tests/test_pack_product.py \
  -p no:cacheprovider -o addopts='' -q
python -m pytest praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_data_packs.py \
  praxis_virtualcell/tests/test_pack_semantics.py \
  praxis_virtualcell/tests/test_anndata_adapter.py \
  praxis_virtualcell/tests/test_api.py \
  praxis_virtualcell/tests/test_pack_product.py \
  -p no:cacheprovider -o addopts='' -q
```

前端：

```bash
cd praxis_vc_react
npm run typecheck
npm run lint
npm run build
npm run e2e
```

普通验收不访问 `.53`、不运行 GEARS、GPU、真实 LLM、Docker 或远端服务。
