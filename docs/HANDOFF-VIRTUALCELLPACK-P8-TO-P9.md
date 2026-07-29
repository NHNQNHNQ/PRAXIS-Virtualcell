# VirtualCellPack Phase 8 → Phase 9 交接

- 收口日期：2026-07-29（Asia/Shanghai）
- Golden Phase 8 起始基线：`09fb1bb3d02adfceed504cbccd7cf36c54a61b69`
- Phase 8 产品化收口唯一起始基线：`b6cf226382cb841fb50e70875c82d1804ae5681e`
- 分支：`codex/p8-product-closure`
- 状态：`P8_PRODUCT_CLOSURE_COMPLETE_LOCAL_CANDIDATE — PHASE9_AUTHORIZATION_PENDING`
- 完成提交：由提交后的阶段报告给出；Git commit 不能可靠地自嵌其 SHA

## 1. 结论

Phase 8 现在同时完成两层且不混淆：

1. Golden Norman/K562：冻结公开真实数据、split、metric/bootstrap、三个简单
   baseline、正式 Pack-aware runtime 证据与外置 artifact hash；
2. 产品化收口：提供 human、mouse、bacteria 三个小型内置 Pack，六个 Pack CLI、
   只读 discovery/validation/compatibility API、React 后端 capability 展示，以及
   历史 job Pack/model fingerprint 不可覆盖锁定。

没有新增生产模型，没有转换或复制 P7 大数据，没有改核心科学路由。无模型、错误
modality、错误 cell domain、跨物种 taxon 和篡改 Pack 都诚实弃权，不 fallback
到 mock。

## 2. 三个内置 Pack

| Pack | Taxon | Feature namespace | H5AD SHA-256 |
|---|---|---|---|
| `p8-human-tiny:1.0.0` | `NCBITaxon:9606` | `EnsemblGene / GRCh38` | `0fb1a353d0d6f106ce0e42fc91234589143d678b7571c5de38f338def0f5fe6e` |
| `p8-mouse-tiny:1.0.0` | `NCBITaxon:10090` | `EnsemblGene / GRCm39` | `73078395a3d3ce3335ffbefb0c7e84edaed458bffdac1ce3bf96fc9d490177f6` |
| `p8-bacteria-tiny:1.0.0` | `NCBITaxon:562` | `NCBIGene / GCF_000005845.2` | `87cfb06ae398b17ffdbb1d18bdc8202a27f87deb85fa65dfe30ed96fed7c6065` |

每个 fixture 是 `4 × 2` 合成 H5AD，约 44 KB，包含显式语义和预定义 split。
生成器连续运行两次后 bytes/hash 不变。三个 Pack 都由现有 v0.2
`PackRegistry` 完整校验；没有为物种新增 core runtime 分支。

## 3. 产品接口

CLI：

```text
praxis-vc pack inspect
praxis-vc pack validate
praxis-vc pack register
praxis-vc pack list
praxis-vc pack compatibility
praxis-vc pack run
```

API：

```text
GET  /api/packs
GET  /api/packs/{pack_id}/{pack_version}
GET  /api/packs/{pack_id}/{pack_version}/validate
POST /api/packs/compatibility
POST /api/jobs
```

HTTP 不提供 register；注册本地路径必须由部署者显式运行 CLI。API payload 不暴露
Pack root 或 model cache/asset path。React 数据资源页只 GET `/api/packs`，
展示后端 `pack_valid`、尚未绑定请求时的 `model_compatible=null`、model card
capability 和 `scientifically_validated=false`，不在浏览器复制 compatibility
checks。

## 4. 三层状态与历史锁定

三层状态保持独立：

```text
pack_valid
model_compatible
scientifically_validated
```

Pack catalog 中前者来自当前 bytes 的完整重验；第二层必须绑定具体
request×Pack×model×environment；第三层不会因 Pack 有效、模型可执行或一次预测
成功自动提升。

Pack-aware job 保存 `vc.job-execution-identity.v1`，固定：

- Pack ID/version/fingerprint；
- execution plan 中 model name/version/card fingerprint；
- compatibility-report fingerprint 与 executable 状态；
- 整体 identity SHA-256。

同名 job 目录只能创建一次，再保存会失败，不能覆盖历史身份。旧无 Pack job
显式标为 legacy，不补造 Pack/model。

## 5. Fail-closed 验收矩阵

| 场景 | 结果 |
|---|---|
| 匹配的测试 model/card/cache + human Pack | 正式 plugin 执行；prediction 与 Pack/model identity 落盘 |
| model registry 为空 | `steps=[]`、`abstain=true`、prediction `null` |
| 请求 modality 为 protein | reason `request.modality`，弃权 |
| 请求 cell 为 HeLa、card 只允许 K562 | reason `request.cell_domain`，弃权 |
| mouse 请求绑定 human Pack/card | reason `request.taxon`，弃权 |
| H5AD bytes 被附加篡改 | size/hash 重验失败，不规划、不执行 |
| 只提交 Pack ID 或 version 之一 | API 422 |
| Pack API envelope 拼错或带未知字段 | API 422；不静默忽略后走 legacy |
| HTTP Pack register | 404/405；服务器保持只读注册边界 |
| 同一 job ID 再保存 | `FileExistsError`；旧 identity 不变 |

正向 model 仅存在于 pytest，不进入生产 model zoo。所有负例均断言无 Mock
fallback。

## 6. 测试先行与最终证据

红阶段：

```text
产品模块缺失：collection error / ModuleNotFoundError
React capability region 缺失：1 failed
产品模块误入 data_packs 基础层：1 failed / 189 passed
```

架构守卫促使产品编排上移到 `praxis_virtualcell.pack_product`；
`data_packs` 基础层继续无 model-zoo/runtime 反向依赖。

最终：

```text
P8 product：13 passed / 0 failed
Pack/API/P6 capability 合并定向：191 passed / 0 failed
pip check：No broken requirements found
ruff check . --no-cache：All checks passed
VirtualCell core：1258 passed / 35 skipped / 9 deselected / 0 failed
legacy：1146 passed / 59 skipped / 105 deselected / 0 failed
frontend typecheck/lint/build/bundle：PASS
Playwright：59 passed / 1 skipped / 0 failed（60 collected）
临时无 AppleDouble wheel content smoke：三个 Pack manifest/H5AD 在 wheel，
tests 不在 wheel
```

唯一 Playwright skip 是真实 LLM 显式门。core skip 仍是 remote/Docker 外部门。
本阶段未运行真实 LLM、GEARS、GPU/checkpoint、Docker、远端科学模型或 `.53`
服务。

## 7. 文件范围

实现：

- `praxis_virtualcell/pack_product.py`
- `praxis_virtualcell/cli.py`
- `praxis_virtualcell/workflows/run_virtualcell_query.py`
- `praxis_virtualcell/io/job_store.py`
- `praxis_vc_api/main.py`
- `praxis_vc_api/models/api_schema.py`
- `praxis_vc_api/services/runtime_service.py`
- `praxis_vc_react/src/api.ts`
- `praxis_vc_react/src/components/data/DataLibrary.tsx`
- `praxis_vc_react/src/styles/components.css`

小型 fixture/打包：

- `praxis_virtualcell/example_packs/{human,mouse,bacteria}/`
- `scripts/build_p8_example_packs.py`
- `MANIFEST.in`
- `pyproject.toml`

测试：

- `praxis_virtualcell/tests/test_pack_product.py`
- `praxis_virtualcell/tests/test_packaging.py`
- `praxis_vc_react/e2e/data-library.spec.ts`

文档：

- `README.md`
- `docs/ADR-0007-virtualcellpack-p8-product-surfaces.md`
- `docs/runbooks/VIRTUALCELLPACK-PRODUCT-SURFACES.md`
- `docs/VIRTUALCELLPACK-CAPABILITY-MATRIX.md`
- `docs/VERSIONING.md`
- `docs/TESTING.md`
- `docs/INDEX.md`
- 本交接文件

## 8. Golden Phase 8 保留状态

Golden Norman 的 source/derived Pack、三 baseline artifact 和完整 evaluation
仍只位于授权的 `.53` 外置根；15 个文件、总计 `4,693,649,813` bytes 的 hash
证据保持冻结。GEARS 仍为 `run=false`、`assets_accessed=false`。

冻结 test MSE 保持：

| Baseline | test MSE |
|---|---:|
| no-change | 0.0062060923 |
| global mean | 0.0045820474 |
| additive ridge | 0.0032570634 |

产品化收口没有读取、改写或重新评分这些资产。

## 9. 已知限制

- 三个微型 Pack 证明插件和 schema/namespace 可替换，不具科学代表性；
- 没有 production-ready 通用模型；默认 model card 可发现不等于本机可执行；
- `model_compatible` 是每个请求的关系，catalog 不能预先给全局 true；
- 本地 index 是单机文件合同，不是签名、多主或远端分发 registry；
- 完整 H5AD 校验需要 omics extra，缺依赖时不降级；
- API 不提供 register/unregister，React 也不上传或注册 Pack；
- list/API 每次同步重验全部已登记 Pack；大 Pack 目前没有后台缓存或分页；
- job identity 防止应用层覆盖，不替代只读文件系统、签名或外部审计存储；
- 未提交源码的临时 wheel 只做 package-data smoke，不是 release artifact；
- 本地 Git 仍有既存 AppleDouble pack-index warning，未修改 `.git`。

## 10. 三端与授权边界

产品化收口开始前只读核对：

- 本地隔离工作树：`codex/p8-golden-norman`，HEAD
  `b6cf226382cb841fb50e70875c82d1804ae5681e`，clean；
- GitHub `main`：
  `8e0d06348ebdf22e076037e6d661094ae877c5d1`；
- `.53` 代码仓库：`codex/deploy-v1.6.0`，HEAD
  `8e0d06348ebdf22e076037e6d661094ae877c5d1`，既存 `?? vc_api.log`。

本阶段没有 push，没有修改 main/tag、`.53`、PRAXIS-2 或旧 dirty
`/Volumes/T7/PRAXIS-virtualcell`。没有同步、部署或重启服务。

## 11. Phase 9 授权模板

提交后的阶段报告会把占位符替换为精确 SHA：

```text
授权以 <P8 产品化收口完成 SHA> 作为 Phase 9 唯一起始基线，开始实施 Phase 9。
```

精确迁移关系：

```text
expected_old_sha=b6cf226382cb841fb50e70875c82d1804ae5681e
→ new_sha=<P8 产品化收口完成提交 SHA>
```
