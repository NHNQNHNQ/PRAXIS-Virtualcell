# VirtualCellPack Phase 9 → Phase 10 交接

## 1. 状态与边界

- P9 implementation anchor：
  `6de2ec1543aada7f4e7b265280a784ce0528c9dc`
- P9 release-closure branch：`codex/p9-release-closure`
- final closure SHA：由阶段结束报告在提交后精确绑定
- 产品版本：`1.6.0` local candidate，未发布、未打 tag、未部署
- GitHub `main` 与 `.53` 代码：
  `8e0d06348ebdf22e076037e6d661094ae877c5d1`

本交接不实施 Phase 10，不授权 push、main/tag、PRAXIS-2 或 `.53` 受保护代码仓库
变更。用户单独要求的 `.53` 网站只允许使用隔离 preview 目录和独立端口，不代表
部署或发布。

## 2. P0–P9 已冻结能力

| Phase | 冻结结果 |
|---|---|
| P0 | 基座科学边界、三层状态、Report request 与 ActiveLearning 兼容修复 |
| P1 | strict versioned request domain |
| P2 | manifest、资产路径和 hash 的严格 Pack 验证 |
| P3 | AnnData adapter 与确定性输入合同 |
| P4 | 标准数据语义、legacy/MCP startup-timeout 收口 |
| P5 | H5MU、多组学和显式 feature alignment |
| P6 | capability-driven runtime 与 fail-closed 模型裁决 |
| P7 | 四物种数据目录、受控下载与 byte-preserving quarantine 上传 |
| P8 | human/mouse/bacteria 小型 Pack、Pack CLI/只读 API/UI 与 immutable execution identity |
| P9 | 八轴 OOD 合同、泄漏审计、选择性预测和无适配外部验证 |

P8 的三个内置 Pack 覆盖 `EnsemblGene` 与 `NCBIGene`。Yeast 是 P7 数据资源，不是
P8 内置 Pack；不得把二者静默等同。

## 3. P9 科学结论

真实外部验证只覆盖 E. coli 的 dataset/platform、carbon-source condition 和 time
extrapolation。其余 OOD 轴只有 `contract_fixture`，没有科学性能证据。

```text
candidate condition-macro MSE  1.0603835779
no-change condition-macro MSE  1.0533347059
paired difference 95% CI       [-0.9076414928, 0.9749711895]
available                       false
scientifically_validated        false
```

该负结果是门禁成功，不是执行失败。不得用 MAE、Pearson、单个 time point 或 LLM
解释覆盖主指标与 CI 裁决。

## 4. 已绑定验证

P9 implementation anchor：

```text
Phase 定向                         342 passed
VirtualCell core                  1270 passed / 35 skipped / 9 deselected
legacy                            1146 passed / 59 skipped / 105 deselected
ruff / pip check                  PASS
frontend typecheck/lint/build     PASS
Playwright                        59 passed / 1 skipped
Docker exact-HEAD smoke           5 passed
wheel SHA-256                     97a71283005ec462cd3b91f60efe2bcd95a8d5b2f63b44bd7c7160b5d34149ad
```

Release-closure 新增 `PRAXIS_VC_TEST_PYTHON`，允许 Playwright 使用 checkout 外的严格
Python 环境；默认仍为 `.venv/bin/python`。Bundle budget 同时忽略外置盘产生的
AppleDouble `._*` 旁车，避免把它们误算成 JavaScript/font 资产。最终 closure 回归
和 artifact 由阶段结束报告绑定。

## 5. 数据与网页

`.53` 的 P7 public inventory 有 5 个已校验文件，共 `27,823,623` bytes；P8 Golden
Norman 有 15 个已校验文件，约 4.69 GB。数据不进入 Git。

正式页面仍未部署。隔离 preview 固定使用：

```text
directory /home/zkyd/data1/mzy/praxis-virtualcell-preview/p9
port      18080
data root /home/zkyd/data1/mzy/praxis-virtualcell-data
```

Preview 必须从 committed wheel 启动，绑定准确 `GIT_SHA`，使用独立 runs/upload
配置，不修改 `/home/zkyd/data1/mzy/PRAXIS-virtualcell` 或现有 PRAXIS-2 进程。

## 6. 已知限制

- P9 尚无 exact-SHA GitHub 五项 CI；没有 push 授权时不得伪称远端全绿。
- P9 没有通用、跨物种或临床科学有效性。
- human 的 GEARS/scGPT/Norman 模型仍为 planned；缺资产时必须 abstain。
- P7 upload 是共享部署 token 保护的 quarantine，不是用户账户、对象存储或 Pack
  注册服务。
- Preview 是临时验收入口，不是 production、TLS、反向代理、systemd 或 SLA。
- 后续阶段不得修改既有 P0–P9 artifact 来“改善”历史结论；需要新 identity。
