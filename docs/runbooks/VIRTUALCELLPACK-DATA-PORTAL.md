# VirtualCellPack P7 数据资源库 runbook

## 1. 适用范围

本 runbook 只管理：

- `vc.data-catalog.v1` 公开数据清单；
- 外置 `public/` 文件；
- bearer 保护的 byte-preserving quarantine 上传；
- `vc.upload-receipt.v1` receipt。

它不构建/加载 Pack，不注册模型，不运行预测，不授予
`pack_valid`、`model_compatible` 或 `scientifically_validated`。

## 2. 配置

服务至少需要一个绝对数据根：

```bash
export PRAXIS_VC_DATA_ROOT=/absolute/path/praxis-virtualcell-data
```

未配置时，目录 API 仍可返回清单，但所有文件显示 unavailable，上传保持
fail-closed。启用上传还需设置部署 secret：

```bash
export PRAXIS_VC_UPLOAD_TOKEN='<at-least-32-random-characters>'
export PRAXIS_VC_UPLOAD_MAX_BYTES=5368709120
export PRAXIS_VC_UPLOAD_TOTAL_BYTES=21474836480
```

不要把 token 写进 Git、前端构建参数、URL、日志或 receipt。两个限额必须是正
十进制整数，且总配额不得小于单文件上限；否则上传能力关闭。默认单文件 5 GiB、
总 quarantine 20 GiB。应用额外允许最多 1 MiB multipart envelope，并同时限制
有/无 `Content-Length` 的请求；反向代理仍应配置相同或更小的显式 body 门。

可用绝对路径覆盖打包清单：

```bash
export PRAXIS_VC_DATA_CATALOG=/absolute/path/data_catalog.yaml
```

覆盖文件使用相同 strict schema；错误清单使目录返回 503，不回退到打包清单。

## 3. 目录布局

```text
${PRAXIS_VC_DATA_ROOT}/
├── public/
│   ├── human/...
│   ├── mouse/...
│   ├── yeast/...
│   └── bacteria/...
└── uploads/
    ├── .upload.lock
    └── quarantine/
        └── <uuid>/
            ├── payload
            └── receipt.json
```

`public/` 下路径必须逐字对应 Git 清单。不要用符号链接绕过数据根。上传成功前使用
`.part`，完成后原子改名；不得让 Web server 直接暴露 `uploads/`。

## 4. P7 首批远端库存

2026-07-28 已按授权在
`/home/zkyd/data1/mzy/praxis-virtualcell-data/public` 下载并验证：

| Species | 相对路径 | Bytes | SHA-256 |
|---|---|---:|---|
| human | `human/10x-pbmc-1k-v3/pbmc_1k_v3_filtered_feature_bc_matrix.tar.gz` | 9,610,650 | `9beae9e7852b2514b4449ecdc5d5a762445289dcfbe5ddb70a44866380b673ce` |
| mouse | `mouse/10x-e18-mouse-brain-1k-v3/neuron_1k_v3_filtered_feature_bc_matrix.tar.gz` | 15,614,242 | `483f7bae81020de70928f6eec71a373b47454e4fb6c39d54900232d98719dec3` |
| yeast | `yeast/geo-gse122392-yeast-scrna/GSE122392_normExpression_YJM_NatMicro.tab.gz` | 577,889 | `f7c16697210358abf14d18ee25edd66ff9e0ab39b9e977fc001d90ac28a7b00a` |
| yeast | `yeast/geo-gse122392-yeast-scrna/GSE122392_normExpression_YPD_NatMicro.tab.gz` | 1,852,033 | `2d64664d20c027bb5659d4caeed76f3470254aeb5ab84c78a775efba0c90a61c` |
| bacteria | `bacteria/geo-gse67402-ecoli-starvation/GSE67402_counts.csv.gz` | 168,809 | `4d8e8e4bee7cf08dea4247f319403c1399af6c9e4069f40f65f54911b748a688` |

总计：5 文件，`27,823,623` bytes。来源 URL 是
`praxis_virtualcell/catalogs/data_catalog.yaml` 的事实源；不要在 runbook 另建
可漂移 URL 列表。

此次操作没有修改
`/home/zkyd/data1/mzy/PRAXIS-virtualcell`、现有 PRAXIS-2 配置/进程、main 或 tag，
也没有启动 VirtualCell 服务。数据已落盘不等于页面已部署。

## 5. 校验

从仓库根运行合同测试：

```bash
python -m pytest praxis_virtualcell/tests/test_data_portal.py \
  -o addopts='' -q -ra
```

对已配置服务：

```bash
curl --fail --silent http://127.0.0.1:8000/api/data-catalog
curl --fail --range 0-31 \
  http://127.0.0.1:8000/api/data-catalog/10x-pbmc-1k-v3/files/filtered-feature-barcode-matrix/download
```

目录响应不得含 `PRAXIS_VC_DATA_ROOT` 或 token。下载出现 `409
dataset_integrity_failed` 时先隔离目标并重验来源，不得关闭 hash 检查或修改清单
迎合现有文件。

远端库存只读复核：

```bash
find /home/zkyd/data1/mzy/praxis-virtualcell-data/public \
  -type f -exec sha256sum {} +
```

## 6. 上传与审查

示例上传：

```bash
curl --fail \
  -H "Authorization: Bearer ${PRAXIS_VC_UPLOAD_TOKEN}" \
  -F species=human \
  -F file=@/absolute/path/cells.h5ad \
  http://127.0.0.1:8000/api/data-uploads
```

允许扩展名由目录 API 返回。扩展名和 declared content type 都不是内容真相。收到
receipt 后，操作员至少应独立完成：

1. 核对 receipt 与 payload 的 size/hash；
2. 在无执行权限、无网络的隔离环境做恶意文件/压缩炸弹检查；
3. 确认来源、许可、consent/隐私和物种；
4. 使用独立的 Pack 构建流程显式声明 modality、feature/observation 语义；
5. 让 `PackRegistry` 重新验证全部资产。

在上述步骤完成前，不得移动到 `public/`、不得载入模型、不得声称 Pack 或科学有效。
相同 hash 的两个上传仍是两个独立 receipt，不得静默去重。

## 7. 配额与故障处理

- quota 只统计 `quarantine/*/payload` 普通文件；
- 超限、空文件、非法物种/类型和写入错误不会留下成功 receipt；
- lock/上传目录是符号链接或无法加锁时返回 503；
- 进程崩溃可能留下 `.part` 或只有 payload 的 UUID 目录。

故障残留必须先记录路径、owner、mtime、size 和 SHA-256，再由操作员人工判定。不要
写自动清理 cron，也不要把“无 receipt”直接等同于“可删除”。任何删除、迁移到
公开区或配额变更都应有独立审批与审计记录。

## 8. 更新公开目录

增加或替换数据时：

1. 先核对来源主页、再分发条款、citation、物种和数值语义；
2. 下载到目标旁的唯一临时文件；
3. 计算精确 bytes/SHA-256；
4. 先写失败测试，再更新 strict manifest；
5. 仅在 hash/size 匹配时原子移入 `public/`；
6. 跑 P7 定向、完整 core、legacy、前端 lint/build/E2E；
7. 报告新 manifest/文件身份和三层状态边界。

不要把大文件提交到 Git，不要原地覆盖 hash 不同的既有目标，不要自动解包、归一化、
补零、去重、随机划分、symbol/ortholog 转换，也不要 fallback 到 mock。
