# CI 转绿:ruff lint 清理 — 设计文档

> 日期 2026-07-02 · 归属 v0.6 工程化前置(为「每步 push + CI 绿」扫清障碍) · 状态:已定方案,直接执行。

## 1. 背景

CI(`.github/workflows/ci.yml`)跑 `ruff check .` → 全仓 **563 个 lint 错误**,ruff 步骤在 origin/main 上一直失败(既存债,非本次功能引入)。这使「每步 push 保持 CI 绿」无法达成。目标:让 `ruff check .` 干净退出 0,且**零行为回归**。

## 2. 错误分布(ruff --statistics)

| 规则 | 数量 | 可自动修 |
|---|---|---|
| E501 line-too-long | 408 | 否 |
| I001 unsorted-imports | 64 | ✓ |
| E702 semicolon | 23 | 否 |
| F401 unused-import | 14 | ✓ |
| B905 zip-without-strict | 12 | 否 |
| E402 import-not-at-top | 8 | 否 |
| UP037/UP017/UP035/UP009/F541/E401 等 | ~22 | 多数 ✓ |
| E701/F841/B017/UP028/UP031/UP042 | ~14 | 否 |

E501 占 72%,是主要噪声。

## 3. 方案(行为保持,不改逻辑)

1. **`[tool.ruff] line-length` 100 → 120**。理由:本仓中英混排、注释密集,100 过紧;408 个 E501 中 372 个在 100–120 之间,属风格噪声。**这不是把 ruff 设为 advisory**——ruff 仍强制 120,且下面第 4 步会修掉所有 >120 的残留(36 个)。config bump 是把 linter 宽度设到贴合现实,不是忽略失败。
2. **自动修安全项**:`ruff check . --fix`(I001 排序、F401 删无用 import、UP037/UP017/UP035/UP009、F541、E401 等,约 100 个)。全为行为保持。
3. **手工修其余非 E501**(逐个行为保持):E702/E701 拆分号/冒号多语句;B905 给 `zip(...)` 加 `strict=False`(保持旧行为);E402 对**有意的**晚 import(sys.path 注入后)加 `# noqa: E402`,否则上移;F841 删/`_` 前缀无用变量;B017 收窄异常或 noqa;UP028/031/042 就地现代化或 noqa。
4. **残留 E501(120 后 36 个)**:能拆则拆;确不可拆的长数据行/长串(最长 337 字符)加 `# noqa: E501`。
5. **不碰任何逻辑**:仅 import/格式/语法糖/换行/noqa。核心 governance/predictors/reliability 的**行为不变**。

## 4. 验收(既是"测试")

- `ruff check .` 退出 0(0 errors)。
- `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests` 仍 ≥233 passed / 25 skipped(证明零行为回归)。
- 全部本地 commit → push origin main → GitHub CI 首次转绿(ruff + pytest 均过)。

## 5. 边界

- 只做 lint。不重构、不改功能、不动测试断言逻辑(除非 lint 要求,如 B017 收窄异常类型——若涉及则最小改并保持测试意图)。
- 若某处 lint 修复会改变行为(如 F401 删的 import 有副作用),则改用 `# noqa` 保留并注明,不冒险。
