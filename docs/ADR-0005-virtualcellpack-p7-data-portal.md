# ADR-0005：VirtualCellPack P7 物种数据资源库与受控交换

- 状态：Accepted（P7 本地候选）
- 日期：2026-07-28
- 唯一起始基线：`bcc812eed8a9b1cd162361f8c12fb9e325cdb17c`
- 前置：ADR-0001、ADR-0002、ADR-0003、ADR-0004

## 背景

P0–P6 已冻结 request、Pack、feature alignment、model card 和 capability runtime
边界，但网页没有独立的数据资源入口，服务器也没有一个与代码仓库分离、可校验的
公开组学数据根目录。直接把来源文件放进 Git、把任意上传当作 Pack，或让页面自行
推断文件是否可用于模型，都会破坏现有的身份、确定性和 fail-closed 合同。

P7 只解决资源交换：

```text
strict catalog → hash-verified public download
operator-authenticated upload → byte-preserving quarantine
```

它不实现 Pack loader，不把上传注册为 Pack，也不改变任何模型或预测路径。

## 决策

### 1. Git 只保存严格清单，大文件保存在外部数据根

`praxis_virtualcell/catalogs/data_catalog.yaml` 使用
`vc.data-catalog.v1`。每个 dataset 必须显式声明：

- 唯一 dataset/file ID、版本和标题；
- runtime species、NCBI Taxonomy CURIE 和学名；
- modality、数值语义、observation/feature 数；
- 来源落地页、citation、使用条款；
- 文件相对路径、文件名、media type、精确字节数、SHA-256 和 HTTPS 来源。

清单采用 strict Pydantic 合同，拒绝未知字段、重复 YAML key、重复 ID/路径、
非 canonical 相对路径、错误类型、坏 hash/CURIE 和空数组。原始数据、上传内容和
模型权重不进入 Git。

### 2. 公开下载是 allowlist，不是任意文件服务

`GET /api/data-catalog` 只返回公开元数据、物种选项、文件可用状态和受控 URL，
不暴露服务器根路径或上传令牌。`species` 过滤逐字匹配；大小写错误或未知物种直接
返回 `unsupported_species`，不做 fallback。

`GET /api/data-catalog/{dataset_id}/files/{file_id}/download` 只解析清单中的
dataset/file 组合。每次下载前都重新验证：

- 数据根为显式绝对路径；
- resolved path 仍在 `public/` 内；
- 目标是普通文件；
- 字节数和 SHA-256 与清单完全一致。

缺文件返回 unavailable；路径逃逸、篡改或无法读取 hash 均 fail-closed。下载由
Starlette `FileResponse` 提供原生 Range 响应，但 Range 支持不跳过完整文件校验。

### 3. 上传只进入隔离区

`POST /api/data-uploads` 需要至少 32 字符的共享操作员 bearer token。鉴权和声明
body 上限在 multipart 解析前执行；无 `Content-Length` 的 chunked 请求也由 ASGI
receive 边界限制。应用随后执行：

- 物种逐字匹配清单中的 runtime species；
- 文件名安全检查和显式扩展名 allowlist；
- 单文件精确字节上限和全局 quarantine 配额；
- 进程间 `flock` 串行计费；
- upload/lock 目录符号链接逃逸检查；
- 原字节流 SHA-256 计算、原子 rename 和权限收紧。

成功结果写入独立 UUID 目录：

```text
uploads/quarantine/<upload_id>/payload
uploads/quarantine/<upload_id>/receipt.json
```

receipt 使用 `vc.upload-receipt.v1`，记录用户声明的文件名、物种、content type、
精确字节数、SHA-256 和 UTC 时间。相同内容不会静默去重。系统不解包、不检查组学
内部 schema、不归一化、不补零、不转换 identifier、不随机划分，也不自动把它
加入公开目录或模型输入。

### 4. 网页只是受控通道

React 侧栏新增“数据资源”入口：

- 可按四个 runtime species 精确筛选公开数据；
- 只有后端确认 `available=true` 的文件才显示下载链接；
- 未落盘文件保持禁用，不跳转到来源 URL 伪装成本地下载；
- 上传令牌只保存在当前组件内存，不写 local storage、URL 或 receipt；
- 成功提示明确写出“不会自动参与预测”。

网页不计算 hash、不判断 Pack/model 状态，也不参与任何科学裁决。

### 5. 数据资源状态不提升三层科学状态

| 事实 | 可以说明 | 不能说明 |
|---|---|---|
| catalog schema 有效 | 元数据满足 P7 清单合同 | 来源文件已落盘、内容科学正确 |
| 文件 `available=true` | 当前字节数和 SHA-256 匹配 | `pack_valid` |
| 上传 receipt 有效 | 某次原字节写入隔离区且有 hash | 文件内部 schema、质量或安全已审查 |
| 下载/上传成功 | 资源交换完成 | `model_compatible`、可执行或 `scientifically_validated` |

只有后续显式 Pack 构建与 `PackRegistry` 完整验证才能授予 `pack_valid`；只有
P6 compatibility contract 才能授予特定模型关系的 `model_compatible`。P7 不会
把 `scientifically_validated` 设为 true。

### 6. 首批数据冻结

首批清单覆盖四个现有 runtime species：

- human：10x PBMC 1k v3 filtered feature-barcode matrix；
- mouse：10x E18 brain 1k v3 filtered feature-barcode matrix；
- yeast：GEO GSE122392 两个 submitter-normalized expression 文件；
- bacteria：GEO GSE67402 gene-count 文件。

共 5 个文件、`27,823,623` bytes。10x 条目按其公开条款记录；GEO 条目显式引用
NCBI GEO disclaimer。Yeast 文件保持来源的 normalized semantics，系统没有重新
归一化。完整 URL、大小和 hash 见清单与数据 portal runbook。

### 7. LLM 不参与

清单解析、路径/大小/hash 验证、上传鉴权、限额、receipt 和 UI 可用状态均由
确定性代码完成。LLM 不能增加条目、修改 hash、推断物种、批准上传、授予 Pack/
model/scientific 状态或决定下载结果。

## 后果与限制

- P7 新增一个小型清单、一组 API 和一个 React 页面，没有新增模型或 Pack loader。
- 上传 token 是部署级共享操作员凭证，不是用户账户、租户隔离或细粒度 RBAC。
- 扩展名和 declared content type 不是文件内容验证；上传必须由后续人工/隔离
  工具审查。
- quota 是单数据根、基于当前 `quarantine/*/payload` 的字节计数；没有数据库、
  自动过期、审计用户身份或恶意文件扫描。
- 进程崩溃可能留下无 receipt 的 `.part`/payload，需要操作员按 runbook 审查，
  不能自动认定可删除。
- catalog 每次列出可用文件时都会读 hash；当前 27.8 MB 基线可接受，大规模目录
  需要另行设计不可伪造的缓存/索引。
- P7 没有部署或重启 `.53` VirtualCell 服务；只按授权创建独立数据根并下载文件。
- 资源来源许可与后续再分发责任仍需部署者复核；hash 只证明字节身份，不证明许可、
  生物学质量或 benchmark 有效性。
