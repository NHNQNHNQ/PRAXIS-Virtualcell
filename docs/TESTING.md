# PRAXIS-VirtualCell 测试指南

> 本地观测：2026-07-18，分支 `codex/project-consolidation`
>
> 状态：`LOCAL_REPRODUCTION_ONLY`。当前分支尚未 push，不能据此声称 GitHub Actions 已绿。

## 当前质量口径

| 层 | 命令 | 本地结果 |
|---|---|---|
| 依赖 | `.venv/bin/python -m pip check` | PASS，0 broken requirements |
| Python lint | `.venv/bin/ruff check .` | PASS，0 diagnostics |
| VirtualCell 核心 | `.venv/bin/pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra` | `917 passed / 40 skipped / 9 deselected / 0 failed`；1 个既有 Starlette/httpx 弃用警告 |
| Legacy unit | `.venv/bin/pytest tests -m "not (integration or llm or remote)" -o addopts='' -q -ra` | `1136 passed / 59 skipped / 105 deselected / 0 failed` |
| 前端 | `npm ci` → typecheck → lint → build → `CI=1 npm run e2e` | 0 vulnerabilities；build PASS；`4 passed` |
| 干净 wheel | 从提交 `73f3324` 的 `git archive` 构建；独立 Python 3.13 venv `--no-deps` 安装后验证 import、version、CLI | `praxis_virtualcell-1.5.1-py3-none-any.whl`，714,871 bytes，SHA-256 `b571ee71a42d028774221b068a5d0b5a613bcebb456ba655c1a3b4e1d1690580` |

核心结果与根 `tests/` 不能相加成一个“总通过数”。前者是 VirtualCell 发布权威口径；后者是继承的 PRAXIS-2 unit 范围。Phase 10 的 `912/40/9` 是新增产品版本契约测试之前的冻结证据，不应在原报告中回写成新数字。

## 本地复现

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,api,mechanistic]"
.venv/bin/python -m pip check
.venv/bin/ruff check .

.venv/bin/pytest praxis_virtualcell/tests \
  -m "not llm" -o addopts='' -q -ra

.venv/bin/pytest tests \
  -m "not (integration or llm or remote)" \
  -o addopts='' -q -ra

cd praxis_vc_react
npm ci
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

CI 配置使用 Python 3.13 和 Node 24。C1 在这些版本下复现的是当时的 `912` 条核心测试和 3 条 E2E；C2 当前的 `917` 条核心测试、legacy 与 4 条 E2E 是在 Python `3.12.13` / Node `26.4.0` 下复现。C2 另在独立 Python 3.13 venv 安装干净 wheel，并验证两个包名、`--version` 和 `--help`。只有远端 CI 对候选 SHA 跑完后，才能把当前完整口径记为 Python 3.13 / Node 24 通过。

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

四条 Playwright 测试覆盖：五阶段 happy path、六个结果 tab、首屏结构，以及 UI 从后端 health 消费产品版本/build SHA。它们不覆盖 CSS/像素视觉验收、深层 abstain/failed 数值、真实 LLM 或远端模型。

Vite 仍报告主 JavaScript chunk 超过 500 kB；这是 C4 的测量驱动优化项，不是当前 build 失败。

## GitHub Actions

`.github/workflows/ci.yml` 有三个 blocking job：

1. Python lint + VirtualCell core
2. frontend build + Playwright
3. legacy unit（外部套件 gated）

只有 Phase D 获得授权并 push 候选分支后，才能观察对应 SHA 的 GitHub Actions 并记录 run URL/编号。没有可见远端 run 时，状态只能是本地复现通过。
