# PRAXIS-VirtualCell 测试指南

> 本地观测：2026-07-18，分支 `codex/project-consolidation`
>
> 状态：`C4_COMPLETE_LOCAL`，固定实现证据 HEAD `8ce42fe`。当前分支尚未 push，不能据此声称 GitHub Actions 已绿。

## 当前质量口径

| 层 | 命令 | 本地结果 |
|---|---|---|
| 依赖 | Python 3.13 hash locks → editable `--no-build-isolation --no-deps` → `python -m pip check` | PASS，0 broken requirements |
| Python lint | Python 3.13 lock 环境内 `ruff check .` | PASS，0 diagnostics |
| VirtualCell 核心 | `python -m pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra` | `957 passed / 35 skipped / 9 deselected / 0 failed`；Python 3.13.12，无 C3 的 Starlette/httpx 弃用警告 |
| Legacy unit | `python -m pytest tests -m "not (integration or llm or remote)" -o addopts='' -q -ra` | `1136 passed / 59 skipped / 105 deselected / 0 failed` |
| Legacy broad non-LLM | `python -m pytest tests -m "not llm" -o addopts='' -q -ra` | `1136 passed / 158 skipped / 6 deselected / 0 failed`；广义本地口径，不替代 CI isolation |
| 前端 | `npm audit --audit-level=high` → typecheck → lint → build → `CI=1 npm run e2e` | 0 vulnerabilities；build/budget PASS；14 specs / 57 collected = `56 passed / 1 skipped / 0 failed` |
| C4 完整 wheel | 固定 HEAD 的两个 clean archive 分别构建、`cmp`、Python 3.13 locked clean install、console entry、站外 verifier | 922,334 bytes；SHA-256 `78e5287a5dd61478b041fd1a28783732cb75a250de02eec306d3803b3128fd4f`；全部 PASS |
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

CI 配置固定 Python `3.13.14` 和 Node `24.18.0`。C4 后端、wheel 与 clean install 已在本机 Python `3.13.12` 复现；浏览器门使用本机 Node `26.4.0` / npm `11.17.0`，并额外对显式启动的 Python 3.13.12 API 重跑为 `56 passed / 1 skipped`；Docker 门使用 digest-pinned Linux Node 24/Python 3.13 构建链。只有远端 CI 对候选 SHA 跑完后，才能声称 GitHub 的 Python 3.13.14 / Node 24.18.0 口径通过。

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

“已配置”不等于 branch protection 的 required/blocking check。只有 Phase D 获得授权并 push 候选分支后，才能观察对应 SHA 的 GitHub Actions、required-check 设置和 run URL/编号。没有可见远端 run 时，状态只能是本地复现通过。
