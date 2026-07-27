# PRAXIS-VirtualCell

可信虚拟细胞扰动预测的可靠性治理系统：离线优先、可审计、可弃权。它的重点不是笼统宣称“更准”，而是在适用范围不足时明确拒绝、降级或弃权，并为结果保留证据与溯源。

用户描述物种、细胞场景和扰动任务后，系统把请求路由到适用的预测器或规则模块，产出包含治理裁决、证据边界和复现信息的 Markdown 报告。默认 `offline`，不需要 API key。

当前安装包版本来自 `pyproject.toml`，可用 `praxis-vc --version` 查询。GitHub、当前本地候选和 `.53` 的发布状态并不由版本字符串推断，请以 [三端同步台账](docs/status/SYNC-STATE.md) 为准。

## 安装与本地页面

要求 Python 3.11+（项目 CI 使用 3.13）以及 Linux 或 macOS。以下命令在源码仓库根目录执行：

```bash
git clone https://github.com/NHNQNHNQ/PRAXIS-Virtualcell.git
cd PRAXIS-Virtualcell
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[api]"
praxis-vc --version
```

源码可编辑安装的 `praxis-vc serve` 可以启动 API；若要让源码 checkout 在 `/` 同源托管 React 页面，先构建前端：

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
praxis-vc serve
```

浏览器打开 `http://127.0.0.1:8000`。安装自检脚本 `bash deploy/vc/check_install.sh` 仍是源码 checkout 专用；独立 wheel 与容器路径见 [安装指南](docs/INSTALL.md)。

完整 release wheel 由 `scripts/build_release_wheel.sh` 构建，内含 React 静态资源、CLI/API 代码、`praxis_vc_web/app.py` 和经过许可审查的默认 gene-set 数据；从 wheel 启动 `praxis-vc serve` 不依赖源码 checkout 或外置 `dist/`。`praxis-vc web` 的入口文件已打包，但运行 Streamlit 仍需安装 `web` extra；当前发行门只验证其打包和绝对路径接线，不声称完整 Streamlit server smoke。

发布容器从同一完整 wheel 安装，不复制源码到最终镜像。构建时必须注入候选 commit 和 epoch：

```bash
scripts/build_release_container.sh praxis-virtualcell:local
docker run --rm -p 127.0.0.1:8000:8000 \
  -v praxis-vc-runs:/var/lib/praxis-vc/runs \
  praxis-virtualcell:local
```

构建脚本拒绝把未提交的 tracked 内容或未知 untracked 文件标成当前 HEAD；受保护且已被 Docker context 排除的 `.claude/` 与 `string.jpeg` 不影响候选身份。容器以 UID/GID 10001 非 root 运行，在 `/api/health` 暴露产品版本与注入的 Git SHA，并同源提供打包后的 React 页面。完整构建首次仍需网络取得 npm 与 hash-locked Python wheels；最终安装阶段和运行时不访问包索引。

## 快速开始

```bash
# 结构化请求：离线确定性执行
praxis-vc run \
  --request examples/ahr_k562.json \
  --mode offline \
  --out runs/ahr

# 自然语言解析后确认执行
praxis-vc ask \
  --text "在 human K562 里敲掉 AHR 会怎么样" \
  --mode offline \
  --yes \
  --out runs/ahr
```

每次运行会生成 `runs/<job>/report.md`，包含 Question、Cell Context、Routing、Result、Governance Verdict、Evidence & Provenance、Biological Interpretation、Limitations 和 Reproducibility 九个确定性章节。

## 治理裁决

| verdict | 含义 |
|---|---|
| `accept` | 请求适用且证据足够，可以给出预测 |
| `caution` | 可以使用，但必须携带明确告警 |
| `downgrade` | 引擎存在，但数据或证据不足，只能降级解读 |
| `abstain` | 没有适用引擎，系统拒绝伪造预测 |

所有预测和治理终决由后端确定性 runtime 完成。LLM 只可参与自然语言解析、路由建议、critic 复核和报告润色，不能修改 prediction、hard rule、learned reliability、provenance 或最终 verdict。`llm_assisted` 需要 `DEEPSEEK_API_KEY`；缺少凭证或调用失败时回退到离线路径。

## VirtualCellPack 与模型输入

可选 `omics` extra 提供严格、只读的数据合同：`vc.pack.v0.1/v0.2` 使用 H5AD，
`vc.pack.v0.3` 使用 H5MU，并显式区分完全配对和部分配对 observation。部分配对
不会为缺失 modality 造行或补零。

`vc.model-feature-contract.v1` 把模型要求的物种、assembly、modality、feature
namespace/version 和有序 feature ID 固定下来。默认必须逐字匹配；alias、
aggregate、drop、fill、reorder 只有被合同或 hash/version 绑定的 mapping asset
明确授权时才能执行，并写入 `vc.alignment-report.v1`。不存在自动 symbol
替换、Ensembl version 剥离、ortholog/同源转换或 mock fallback。

这三层不能混用：Pack 完整验证只得到 `pack_valid`；成功显式对齐才得到指定模型
的 `model_compatible`；两者都不能推出 `scientifically_validated`。

Pack-aware runtime 由严格 `vc.model-card.v1`、`CapabilityRegistry` 和
`ModelBrokerAgent` 生成 `vc.compatibility-report.v1` 与确定性
`vc.execution-plan.v1`。只有完整提供已注册的 `pack_id + pack_version` 才走该
路径；无 Pack 调用保留显式 legacy adapter。缺资产、坏 hash、缺依赖/资源、
越 scope 或缺 runtime task/output adapter 都会弃权，不会 fallback 到 mock。
当前 plugin execution adapter 只实现 `predict_delta_expression →
delta_expression`，模型卡可发现不等于可执行或科学有效。

架构和复现边界见 [ADR-0003](docs/ADR-0003-virtualcellpack-p5-multiomics-alignment.md)、
[ADR-0004](docs/ADR-0004-virtualcellpack-p6-capability-runtime.md)、
[多组学 runbook](docs/runbooks/VIRTUALCELLPACK-MULTIOMICS.md) 与
[能力 runtime runbook](docs/runbooks/VIRTUALCELLPACK-CAPABILITY-RUNTIME.md)。

## 能力边界

PRAXIS-VirtualCell 是带可靠性治理的操作层，不是通用或 SOTA 预测模型。当前可复现证据只支持以下克制表述：

- 真实引擎级覆盖为四类：M2（真实 donor 证据来自 `.53` 历史亲验）、M3、M4 和 M7。
- M1、M5、M8 属于 rule-based advisory；M6 以及 EMT、fate、spatial、communication 等路径存在明确 limitation。
- 本地 offline 流程会使用 mock 或当前可用 predictor 验证完整治理链，不能把它描述成所有远端模型都已运行。
- 多模块结果表示路由计划中的多个 entry 与 advisory，不表示多个预测器已经完成证据融合。
- 更完整的 met / narrowed / unsupported / pending 边界以 [Phase 10 Gate](reports/phase10/PHASE10_GATE.md) 为准。

## 开发与测试

```bash
python -m pip install -e ".[dev,api,mechanistic,omics]"
python -m pip check
ruff check .

# VirtualCell 核心权威口径；真实 LLM 不在普通门中
pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra

# 继承测试口径；排除容器、真实 LLM、GPU/checkpoint 和私网服务
pytest tests -m "not (integration or llm or remote)" -o addopts='' -q -ra

cd praxis_vc_react
npm ci
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

当前精确结果、skip/deselect 含义、显式外部门和 GitHub CI 状态见 [测试指南](docs/TESTING.md)。普通测试默认不访问固定私网服务；`integration`、`llm`、`remote` 分别需要 `--run-integration`、`--run-llm`、`--run-remote`，一个测试拥有多个 marker 时必须同时满足对应门。

## 文档入口

| 文档 | 内容 |
|---|---|
| [文档地图](docs/INDEX.md) | 当前权威、历史材料和计划的边界 |
| [项目状态](docs/status/PROJECT-STATE-2026-07-18.md) | 当前阶段、验证结果、受保护资产和下一步 |
| [三端同步台账](docs/status/SYNC-STATE.md) | 本地、GitHub、`.53` 的 SHA 与授权边界 |
| [安装指南](docs/INSTALL.md) | pip、前端、Docker 现状和可选依赖 |
| [用户指南](docs/USER-GUIDE.md) | CLI、五阶段界面、输出与模式 |
| [版本契约](docs/VERSIONING.md) | 产品、协议、schema、artifact 和模型版本边界 |
| [Phase 10 Gate](reports/phase10/PHASE10_GATE.md) | 科学能力与远端证据边界 |

## 版本与同步流程

唯一允许的流向是：本地 feature branch → GitHub branch/CI → 审批合入 GitHub `main` → 本地 `main` fast-forward → `.53` 从同一 GitHub SHA fast-forward → 三端 SHA 核对。不要在 `.53` 直接开发，也不要把本地 tag 当成已发布 tag。

整理分支已按两次精确 D1a 授权把 GitHub `codex/project-consolidation` 快进到 `ee36d7948047f346f55a02d62ccaac84391e3c20`。对应的 [GitHub Actions run 29971566980](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29971566980) 为 `4/5`：Python core、frontend/Playwright、reproducible wheel 和 Linux release container 通过，legacy 唯一失败是 Linux shell 子进程未随直接 shell 终止。修复提交 `6a8198771581d0897a13457e93e50cfec172d59a` 已把输出截断、timeout、pipe 异常和上层取消统一为进程组清理，并在 macOS/Python 3.13.12 与 Linux/Python 3.13.14 严格锁环境得到 legacy `1139 passed / 0 failed`。包含本段的最终文档提交必须由交接中的 post-commit release artifact 重新绑定，之后才能申请新的 exact-SHA D1a retry；GitHub `main`/tag、本地 `main` 和 `.53` 均未改变。

## 派生关系

本项目由 PRAXIS-2 commit `b124d66` 复制改造，继承 agent runtime、长期大脑、规则系统与反幻觉基础，并扩展 VirtualCell 大脑、预测器注册表和生物 benchmark。兼容运行时代码位于 `praxis2/`，产品代码位于 `praxis_virtualcell/`，本地 API/React 界面位于 `praxis_vc_api/` 与 `praxis_vc_react/`。详见 [PROVENANCE.md](PROVENANCE.md)。
