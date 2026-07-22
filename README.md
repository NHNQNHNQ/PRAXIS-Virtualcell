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

## 能力边界

PRAXIS-VirtualCell 是带可靠性治理的操作层，不是通用或 SOTA 预测模型。当前可复现证据只支持以下克制表述：

- 真实引擎级覆盖为四类：M2（真实 donor 证据来自 `.53` 历史亲验）、M3、M4 和 M7。
- M1、M5、M8 属于 rule-based advisory；M6 以及 EMT、fate、spatial、communication 等路径存在明确 limitation。
- 本地 offline 流程会使用 mock 或当前可用 predictor 验证完整治理链，不能把它描述成所有远端模型都已运行。
- 多模块结果表示路由计划中的多个 entry 与 advisory，不表示多个预测器已经完成证据融合。
- 更完整的 met / narrowed / unsupported / pending 边界以 [Phase 10 Gate](reports/phase10/PHASE10_GATE.md) 为准。

## 开发与测试

```bash
python -m pip install -e ".[dev,api,mechanistic]"
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

整理分支已按首次 D1a 授权把精确 SHA `6086e6995b1c3c01ec31075ce1164a0165cb8d43` 发布到 GitHub `codex/project-consolidation`。对应的 [GitHub Actions run 29894971142](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29894971142) 未全绿：五项 job 中只有 reproducible release wheel 通过。修复提交 `d6011d82d297bbfe14d940f9cb09cb4988715f53` 已完成原生 macOS 分层验证；Linux/amd64 QEMU 的依赖、Ruff、packaging 和核心门通过，但 legacy 如实保留一个 `/dev/zero` 超时失败。最终文档提交、release artifact 绑定和新的 exact-SHA D1a retry 授权仍待完成；旧 SHA 的单项 CI 通过不能继承给新候选。GitHub `main`/tag、本地 `main` 和 `.53` 均未改变。

## 派生关系

本项目由 PRAXIS-2 commit `b124d66` 复制改造，继承 agent runtime、长期大脑、规则系统与反幻觉基础，并扩展 VirtualCell 大脑、预测器注册表和生物 benchmark。兼容运行时代码位于 `praxis2/`，产品代码位于 `praxis_virtualcell/`，本地 API/React 界面位于 `praxis_vc_api/` 与 `praxis_vc_react/`。详见 [PROVENANCE.md](PROVENANCE.md)。
