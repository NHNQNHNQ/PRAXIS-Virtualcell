# ADR-0007：VirtualCellPack 产品面、只读能力展示与历史执行身份

- 状态：Accepted（Phase 8 product-closure local candidate）
- 日期：2026-07-29
- 唯一起始基线：`b6cf226382cb841fb50e70875c82d1804ae5681e`
- 决策范围：微型 Pack、CLI/API/UI 产品面、fail-closed 验收、历史 job 身份

## 背景

P2–P6 已有严格 Pack schema、语义 adapter、feature alignment、model card 和
capability-driven runtime；Golden Norman 又证明了真实外置数据可以走正式执行
链路。但产品仍缺少以下闭环：

- 可随发行物安装、无需复制 P7 大数据的 human、mouse、bacteria 示例 Pack；
- inspect、validate、register、list、compatibility、run 的稳定 CLI；
- 只读 HTTP 能力面和 React 展示；
- 历史 job 对 Pack/model fingerprint 的不可覆盖锁定。

这些产品面不能复制科学路由，不能把资源存在、Pack 有效、模型兼容或一次执行成功
升级为科学验证。

## 决策

### 1. 三个小型内置 Pack

发行物包含三个独立的 `vc.pack.v0.2` H5AD Pack：

| Pack | Taxon | Feature namespace | 形状 | Pack fingerprint |
|---|---|---|---:|---|
| `p8-human-tiny:1.0.0` | `NCBITaxon:9606` | `EnsemblGene / GRCh38` | `4 × 2` | `8c75475dda70f52963e6e742f5e7aa48a7aff057a6f752a7146b1d38ea0202ed` |
| `p8-mouse-tiny:1.0.0` | `NCBITaxon:10090` | `EnsemblGene / GRCm39` | `4 × 2` | `530faa57c7680869c54b455a73ee6f87b82681d41189dea09aaa1623fc701694` |
| `p8-bacteria-tiny:1.0.0` | `NCBITaxon:562` | `NCBIGene / GCF_000005845.2` | `4 × 2` | `8600261ad68302432186e7107f053a7a0fdf0e3dbc61dc9754a502b20a95b1fe` |

每个 Pack 都有显式 observation/feature identity、cell
identity/state/context、condition、perturbation、matched control、dose/time 和
预定义 train/test split。fixture 是合成的可审计数据，不是 P7 文件的抽样、转换
或副本。生成器重复运行得到相同 H5AD SHA-256；Git 只新增三个约 44 KB 的 H5AD
和 manifest。

### 2. 产品编排不进入 Pack 基础层

`praxis_virtualcell.data_packs` 保持无 model-zoo/runtime 依赖。产品编排位于
`praxis_virtualcell.pack_product`，复用现有 `PackRegistry`、
`CapabilityRegistry`、`ModelZooRegistry`、`ModelCache` 和
`run_workflow()`；没有给核心 runtime 新增物种、模型或科学路由分支。

### 3. inspect、validate 与 register 分离

- `inspect` 只解析严格 manifest，返回
  `validation_status=unchecked`、`pack_valid=null`；
- `validate` 必须读取并验证 manifest、path、size、SHA-256、H5AD 和全部 v0.2
  科学语义；
- `register` 只接受完整验证通过的本地 Pack，把 canonical absolute root、
  Pack identity 和 fingerprint 写入本地 `vc.pack-index.v1`；
- 索引使用进程锁和原子替换，拒绝重复 JSON key、未知字段、非 canonical path、
  identity/root 冲突；
- list/get/compatibility/run 每次重新验证 Pack bytes，不把旧索引记录当成当前
  数据真相。

### 4. CLI 与 API

CLI 固定为：

```text
praxis-vc pack inspect
praxis-vc pack validate
praxis-vc pack register
praxis-vc pack list
praxis-vc pack compatibility
praxis-vc pack run
```

HTTP 提供：

```text
GET  /api/packs
GET  /api/packs/{pack_id}/{pack_version}
GET  /api/packs/{pack_id}/{pack_version}/validate
POST /api/packs/compatibility
POST /api/jobs
```

前三个 GET 和 compatibility planning 都不改变服务器状态。HTTP 不暴露 register
端点；路径注册仍是部署者本地 CLI 操作。`POST /api/jobs` 是既有执行/落盘端点，
现在可选接受完整的 `pack_id + pack_version`；只给一个字段在 Pydantic 边界返回
422。API payload 不返回 Pack root、model cache path 或 wrapper asset path。

### 5. React 只展示后端事实

“数据资源”页只调用 `GET /api/packs`，显示：

- 后端重验得到的 Pack 状态、taxon、modality、feature namespace 和 fingerprint；
- `model_compatible` 未按具体请求评估时的明确空状态；
- 后端 model card 声明的 capability 与 fingerprint；
- 始终独立显示 `scientifically_validated=false`。

浏览器不调用 compatibility 端点来预判、不复制 capability checks，也不产生最终
裁决。

### 6. 历史 job 不可覆盖

每次 Pack-aware job 保存 `vc.job-execution-identity.v1`：

- Pack ID、version、fingerprint；
- execution plan 中每个 model card 的 name、version、fingerprint、
  compatibility fingerprint 和 executable 状态；
- 上述 canonical identity 的 SHA-256。

`JobStore.save()` 只能创建新目录；同名 job 已存在时拒绝覆盖。旧的无 Pack job
保留显式 `legacy_adapter=true` 和空 Pack/model identity，不伪造历史信息。

### 7. Fail-closed 验收矩阵

| 场景 | 预期 |
|---|---|
| Pack、model card、asset、环境与请求全匹配 | 正式 plugin 执行并锁定 Pack/model fingerprint |
| 没有模型 | 空 execution steps，`abstain=true`，prediction 为 `null` |
| modality 错误 | compatibility reason 含 `request.modality`，弃权 |
| cell domain 错误 | compatibility reason 含 `request.cell_domain`，弃权 |
| 请求 taxon 与 Pack/model 不同 | compatibility reason 含 `request.taxon`，弃权 |
| Pack asset 被修改 | 每次重验失败；不规划、不执行 |
| Pack API envelope 含未知/拼错字段 | 422；不得静默丢字段后走 legacy |
| 同名历史 job 再保存 | `FileExistsError`；原 execution identity 不变 |

所有弃权路径都禁止 fallback 到 Mock predictor。LLM 不参与 compatibility、
数值预测、Pack/model identity 或最终 verdict。

## 后果与限制

- 三个 Pack 证明同一核心 registry 可加载不同 taxon 与至少两个 feature
  namespace，不证明这些微型矩阵有科学代表性。
- 内置 Pack 的 `scientifically_validated` 固定为 false；没有新增生产模型。
- model capability catalog 是声明面，不证明本机 asset/dependency 可用；具体请求
  必须调用 compatibility 或 run。
- 本地索引是单机文件合同，不是多主数据库、签名仓库或远端 Pack 分发协议。
- list/API 当前同步重验全部登记 Pack；大 Pack 没有缓存、后台扫描或分页。
- 完整 H5AD 语义验证需要 `omics` extra；缺依赖时不能降级为仅 manifest 有效。
- 本阶段不转换 P7 大数据、不修改 Golden Norman、GEARS、main/tag、`.53`、
  PRAXIS-2 或旧 dirty T7。
