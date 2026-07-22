# PRAXIS-VirtualCell 测试指南

> 本地观测：2026-07-22，分支 `codex/project-consolidation`，CI 修复提交 `d6011d82d297bbfe14d940f9cb09cb4988715f53`
>
> 状态：`D1A_ATTEMPT_1_RECORDED — CI_FAILED — LOCAL_FIX_VERIFIED — RETRY_APPROVAL_PENDING`。固定 C5 实现证据 HEAD `038e747`、C4 发行证据 `8ce42fe` 仍是历史冻结快照；首次发布 SHA `6086e6995b1c3c01ec31075ce1164a0165cb8d43` 的 CI 不是全绿，最终文档提交和 artifact binding 尚未形成新的 exact candidate。

## 当前质量口径

| 层 | 命令 | 本地结果 |
|---|---|---|
| 依赖 | Python 3.13 hash locks → editable `--no-build-isolation --no-deps` → `python -m pip check` | macOS/arm64 Python 3.13.12 fresh hash install PASS；Linux/amd64 Python 3.13.14 QEMU strict hash install、`pip check` 和 import PASS |
| Python lint | Python 3.13 lock 环境内 `ruff check .` | macOS/arm64 与 Linux/amd64 QEMU 均 PASS，0 diagnostics |
| FBA + packaging 定向回归 | 两条真实 FBA 正例，加 dev extra/lock 与 CI lock 角色测试 | macOS/arm64 `13 passed / 0 failed`；其中 packaging 单模块 `11 passed`，Linux/amd64 QEMU 同一 packaging 单模块 `11 passed / 0 failed` |
| VirtualCell 核心 | `python -m pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra` | macOS/arm64 与 Linux/amd64 QEMU 均为 `965 passed / 35 skipped / 9 deselected / 0 failed` |
| Legacy unit | `python -m pytest tests -m "not (integration or llm or remote)" -o addopts='' -q -ra` | 原生 macOS `1136 passed / 59 skipped / 105 deselected / 0 failed`；Linux/amd64 QEMU `1135 passed / 59 skipped / 105 deselected / 1 failed`，唯一失败为既有 `test_huge_output_capped_not_ooming`，QEMU 下 `/dev/zero` 未在 10 秒内早停，不能写成 Linux legacy 全绿 |
| Legacy broad non-LLM（C5 冻结） | `python -m pytest tests -m "not llm" -o addopts='' -q -ra` | C5 历史证据为 `1136 passed / 158 skipped / 6 deselected / 0 failed`；本轮未将其冒充为新候选 CI isolation |
| C5 Gate A 本地 seam | provenance gate 定向测试 + W4B remote test module 在普通本地 marker gate 下被收集并跳过 | `38 passed / 2 remote skipped / 0 failed`；三 adapter success/no-gate 与缺版本 fail-closed 已证明，非真 donor 推理 |
| C5 W4B remote | `test_ml_workflow_e2e.py --run-remote -m remote` | 本机无 torch：`2 skipped / 0 failed`，明确为 `REMOTE_VALIDATION_PENDING`；只有批准候选 SHA、clean donor SHA/remote 和可信六文件 digest 集上 `2 passed / 0 skipped / 0 failed` 可关闭 |
| 前端 | `npm ci` → typecheck → lint → build → 对显式启动的 fresh dev-lock API 执行 `npm run e2e` | 本地 PASS；14 specs / 57 collected = `56 passed / 1 skipped / 0 failed`；测试 API 使用包含 mechanistic/Cobra 的 dev lock；另有 `CI=1` 目标失败用例窄回归 `1 passed` |
| C4 完整 wheel（冻结） | 固定 `8ce42fe` 的两个 clean archive 分别构建、`cmp`、Python 3.13 locked clean install、console entry、站外 verifier | 922,334 bytes；SHA-256 `78e5287a5dd61478b041fd1a28783732cb75a250de02eec306d3803b3128fd4f`；全部 PASS；仅是 C4 历史证据，不能继承为尚未形成的新候选 artifact |
| C4 Linux container | Docker Desktop Linux/arm64，显式 Docker 双门，容器 `--network none` | `5 passed / 0 failed`；结束后无本次资源残留 |
| C2 历史干净 wheel | 从提交 `73f3324` 的 `git archive` 构建；独立 Python 3.13 venv `--no-deps` 安装后验证 import、version、CLI | `praxis_virtualcell-1.5.1-py3-none-any.whl`，714,871 bytes，SHA-256 `b571ee71a42d028774221b068a5d0b5a613bcebb456ba655c1a3b4e1d1690580`；不是当前 `1.6.0` wheel 证据 |

核心结果与根 `tests/` 不能相加成一个“总通过数”。前者是 VirtualCell 发布权威口径；后者是继承的 PRAXIS-2 unit 范围。Phase 10 的 `912/40/9` 是新增产品版本契约测试之前的冻结证据，不应在原报告中回写成新数字。

## 本地复现

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: \
  --require-hashes -r requirements/build-py313.lock
.venv/bin/python -m pip install \
  --require-hashes -r requirements/dev-py313.lock
.venv/bin/python -m pip install \
  --no-build-isolation --no-deps -e .
.venv/bin/python -m pip check
.venv/bin/ruff check .

.venv/bin/pytest praxis_virtualcell/tests \
  -m "not llm" -o addopts='' -q -ra

.venv/bin/pytest tests \
  -m "not (integration or llm or remote)" \
  -o addopts='' -q -ra

# 可选的广义 legacy 本地盘点；与上面的 CI isolation 分开记数
.venv/bin/pytest tests \
  -m "not llm" -o addopts='' -q -ra

cd praxis_vc_react
npm ci
npm audit --audit-level=high
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

CI 配置固定 Python `3.13.14` 和 Node `24.18.0`。完整本地/CI 测试环境使用 `requirements/dev-py313.lock`；frontend Playwright 的 API 也使用该 lock，确保真实 FBA 正例具备 mechanistic/Cobra。`requirements/runtime-py313.lock` 继续服务于精简发行安装和 clean-wheel verifier，不能替代完整测试环境。

修复提交 `d6011d8` 已在本机 Python 3.13.12/macOS arm64 和 Python 3.13.14/Linux amd64 QEMU 上复现严格 hash install、Ruff、packaging 与核心测试；前端本地为 `56 passed / 1 skipped`。QEMU legacy 的单个超时失败不能被降格、skip 或描述成 Linux 全绿；同一用例在原生 macOS 的完整 legacy isolation 中通过，最终平台结论必须由新候选的 GitHub native runner retry 给出。C4 wheel/clean install 和 Docker 证据仍按各自固定 commit 冻结；最终文档提交完成后还必须重新绑定 exact candidate 的 release artifact。

## C4 发布复现

完整 wheel 从 committed HEAD 的临时 archive 构建，不复用 checkout 的 `dist/` 或 Python build 目录：

```bash
PYTHON_BIN=python3.13 scripts/build_release_wheel.sh /tmp/release-one
PYTHON_BIN=python3.13 scripts/build_release_wheel.sh /tmp/release-two
cmp /tmp/release-one/praxis_virtualcell-*.whl \
    /tmp/release-two/praxis_virtualcell-*.whl
```

随后在全新 Python 3.13 venv hash-install `requirements/runtime-py313.lock`，以 `--no-deps` 安装 wheel，运行 `pip check`，并从 checkout 外执行安装生成的 `praxis-vc --version` / `praxis-vc run` 与 `scripts/verify_release_install.py`。console entry 和 installed-package verifier 都覆盖 offline run 的四项产物；verifier 还覆盖 API health/job、同源 root/hashed asset、包内 web 入口和测试树排除。不包括完整 Streamlit server 或 `praxis-vc ask`。

Docker smoke 必须同时打开环境变量和 pytest integration 门；缺少任一项时只能得到 skip：

```bash
PRAXIS_RUN_DOCKER_SMOKE=1 .venv/bin/python -m pytest \
  praxis_virtualcell/tests/test_linux_docker_smoke.py \
  --run-integration -o addopts='' -q -ra
```

它从 committed HEAD 构建唯一标记镜像，以 `--network none` 启动，并在容器 loopback 验证 non-root、health/version/SHA、installed CLI、React assets 和 offline API report。本地结果只代表 Docker Desktop 的 Linux/arm64 container，不代表原生 Linux、amd64 或 `.53`。

## Marker 与外部门

pytest 启用 strict markers，并静态注册：

- `integration`：容器、数据库、Redis 或发行环境依赖；需 `--run-integration`。兼容旧流程的 `PRAXIS_INTEGRATION=1` 仍可开启该门。
- `llm`：真实外部 LLM 请求；需 `--run-llm`，测试还会单独检查凭证。
- `remote`：GPU、checkpoint、donor 或私网服务；需 `--run-remote`，测试还会单独检查本地依赖。
- `operational`：活部署健康探针，而非隔离测试依赖。

一个测试拥有多个 marker 时，必须满足全部相关 opt-in。只打开 integration 不会运行同时标记为 `integration + llm + remote` 的真实 LLM 模块。

固定 `.53:7788` 健康不变量标记为 `remote + operational`，普通 legacy 命令不会建立 socket 或 HTTP 连接。只有在授权网络与明确运维窗口中才运行：

```bash
.venv/bin/pytest \
  tests/test_m9_invariants.py::test_inv5_v1_backend_still_healthy \
  --run-remote -m "remote and operational" \
  -o addopts='' -q -ra
```

退出码 0 但全部为 skip 只表示前置条件缺失，不能写成 LLM、integration 或 remote 能力通过。

W4B/Gate A 真 ML 验证必须在用户批准的同一候选 SHA、独立批准的 clean donor Git SHA/remote 和可信六文件 digest 集上，按 [Remote Science Validation](runbooks/REMOTE-SCIENCE-VALIDATION.md) 执行：

```bash
# 非独立入口：必须先在 linked runbook 的同一会话通过 donor 与 digest 信任门。
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  praxis_virtualcell/tests/test_ml_workflow_e2e.py \
  --run-remote -m remote -p no:cacheprovider -o addopts='' -q -ra
```

该门要求先只读发现 donor/code 与 checkpoint 元数据，再由可信负责人批准 donor Git 身份和三组 `.json/.pt` digest；当前 `weights_only=False` PT 在批准前禁止反序列化。批准后仍须满足正确 sidecar class、manifest-matching Norman 数据和可用 torch/donor 环境，且结果为 `2 passed / 0 skipped / 0 failed`。CUDA 只作现场环境盘点；当前实现以 `map_location="cpu"` 加载且未迁移 tensor 到 GPU，所以该门不证明 GPU 推理。普通 `run_query()` 不装载 W4B runtime；测试覆盖的是 `build_runtime_ml(...).run_workflow(...)`。

## 前端覆盖边界

14 个 Playwright spec 共收集 57 个 case，覆盖本地 S1–S9 与 S11–S13：五阶段/返回/重置、abstain、敌对输入、扰动矩阵、高级字段、预设、六个结果 tab 与审计产物、主题/历史、离线重复性、响应式语义可达和稳定性，以及两个 Results lazy-loading 路径。S10 是真实 LLM 外部门的 1 条显式 skip；没有运行，不能写成通过。

视觉/几何边界：C3 已完成人工浅色/深色验收并自动验证实际 `data-theme`。Results 工具栏在 1280×720 使用 `.card-actions` 与 `getBoundingClientRect()` 做一条窄几何回归，因为它保护已复现的标题/按钮挤压 bug；mobile/tablet 只证明语义可达，不声称逐像素等价。

C4 的 build budget 实测 initial JavaScript aggregate 为 226,046 bytes（gzip 70,320），延迟加载的 Results chunk 为 410,889 bytes（gzip 114,914），八个本地 font assets 合计 214,292 bytes。旧 C3 单主包 `635.51 kB` 已由 lazy boundary 取代；预算脚本会在初始 aggregate、任一 JavaScript chunk 或 font 范围超标时使 build 失败。

## GitHub Actions

`.github/workflows/ci.yml` 配置五个 job：

1. Python lint + VirtualCell core
2. frontend build + Playwright
3. reproducible full release wheel
4. Linux release container smoke
5. legacy unit（外部套件 gated）

首次 D1a 已把 `codex/project-consolidation=6086e6995b1c3c01ec31075ce1164a0165cb8d43` 发布到 GitHub。对应 [run 29894971142](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29894971142) 的实际结果为：

| GitHub job | 结果 | 失败边界 |
|---|---|---|
| Python lint and VirtualCell core | FAIL | dev lock 的严格 hash 安装阶段失败，未进入 Ruff/pytest |
| Frontend build and Playwright | FAIL | typecheck、lint、build 通过；Playwright `55 passed / 1 skipped / 1 failed` |
| Reproducible full release wheel | PASS | 只绑定旧 SHA `6086e6995b1c3c01ec31075ce1164a0165cb8d43`，不能继承给新候选 |
| Linux release container smoke | FAIL | hash 依赖安装阶段失败，未进入 smoke |
| Legacy unit tests (external suites gated) | FAIL | dev lock 的严格 hash 安装阶段失败，未进入 pytest |

三个 Python/Linux 失败首先暴露 macOS/arm64 编译的 dev lock 漏掉 Linux marker 依赖 `greenlet`，修复后 Linux 迭代又暴露 `watchdog`；hash mode 因此在环境创建阶段 fail-closed。frontend 使用 lean runtime lock 时没有 Cobra，真实 FBA 正例按设计返回 abstain，从而使旧断言失败。提交 `d6011d8` 通过显式 union `greenlet==3.5.3`、`watchdog==6.0.0`、重生成 dev lock、让 frontend CI 使用 dev lock 并增加 packaging 回归修复这两个环境问题，没有弱化科学断言。

“存在 run”不等于 CI 全绿，也不证明这些 job 是 branch-protection required checks。GitHub `main`/tag、本地 `main` 和 `.53` 未改变。最终文档提交和 post-commit artifact binding 完成后，必须以远端 candidate 的 expected old SHA `6086e6995b1c3c01ec31075ce1164a0165cb8d43` 申请新的 exact-SHA D1a retry 授权；在新 SHA 的五项 CI 全部完成前不得进入 D1b。
