# Linux 发行版(离线可跑)— 设计文档

> 日期 2026-07-03 · 归属 v0.8(计划 §5) · 状态:已 brainstorm(自主定薄方案),待写实现计划。

## 1. 目标与约束

让科学家能下载/安装/离线运行 PRAXIS-VirtualCell(本地网页 + CLI + offline 确定性、无需 API key)。三种形态:pip wheel / Docker image / portable tar.gz(计划 §5.2)。

**约束**:开发机是 Mac,**无 Docker/无 Linux**——`docker build` 与 clean-Ubuntu smoke 我跑不了(硬门⑤,那步请用户在 Linux 侧验)。本切片交付**本地可验的核心 + 可 lint 的脚手架/文档**。

## 2. 现状对齐(已读 + 实证)

- `pyproject.toml` 有 `[project.scripts] praxis-vc = praxis_virtualcell.cli:main` + extras(api/web/mechanistic/prod)。
- **真实 gap(实证确认)**:`[tool.setuptools.packages.find] include = ["praxis2*"]` **只打包 praxis2**,不含 `praxis_virtualcell`/`praxis_vc_api`——故构建的 wheel 里 `praxis-vc` CLI 会 ImportError。`find_packages(include=["praxis2*"])` 不含 praxis_virtualcell(已验)。
- **package-data gap**:多处从包路径读运行时资源——`catalogs/*.yaml`(/api/options)、`governance/artifacts/*.json`(learned_reliability)、`brains/virtualcell/**/*.yaml`(治理配置)、`examples/*.json`。当前无 package-data 配置 → 这些不会进 wheel。
- `deploy/Dockerfile` 是**母项目 PRAXIS-2 后端**镜像(gunicorn + praxis2.server.app + postgres/redis),**不是**虚拟细胞离线发行。
- 离线 demo 不需 `data/gems/*`(cobra-gated,mechanistic extra)。

## 3. 方案(薄发行,先保证 wheel + offline demo 可跑)

### 3.1 打包修复(核心,本地可验)
- `[tool.setuptools.packages.find] include` 增补 `"praxis_virtualcell*"`、`"praxis_vc_api*"`(保留 praxis2*)。
- 包内运行时数据打进 wheel:`[tool.setuptools] include-package-data = true` + `MANIFEST.in`:
  ```
  recursive-include praxis_virtualcell *.yaml *.json
  ```
  (覆盖 catalogs/brains/governance-artifacts/examples;wheel smoke 实证完整性,缺则补 glob。)
- **验证(本地可跑)**:`pip wheel . --no-deps -w dist/` 构建 wheel → 全新 venv `pip install <wheel>[api]` → `praxis-vc run --request examples/ahr_k562.json --mode offline --out /tmp/vc_smoke` → 断言 `report.md` 生成、9 段、offline。这是「无 API key 可跑 offline demo」的硬证据。

### 3.2 离线发行脚手架(可 lint,docker build 用户侧)
- `deploy/vc/Dockerfile`:`python:3.13-slim` + `pip install .[api]` + COPY praxis_virtualcell/praxis_vc_api/examples(+ 可选 React dist)+ non-root + `EXPOSE 8000` + `CMD ["praxis-vc","serve","--host","0.0.0.0","--port","8000"]`。无 DB/无 API key。
- `deploy/vc/start.sh`:起 `praxis-vc serve`,打印本地网址 + Mode: OFFLINE。
- `deploy/vc/check_install.sh`:验 python≥3.11 + `praxis-vc --help` + 跑一次 offline demo 断言 report.md。
- 三脚本过 `shellcheck`(有则)/`bash -n` 语法检查。

### 3.3 文档
- `docs/INSTALL.md`:pip / Docker / tar.gz 三法;强调无 key 可 offline。
- `docs/USER-GUIDE.md`:CLI(run/ask/serve)+ 本地网页 + 输出(report.md 等)+ offline vs llm_assisted。
- `docs/EXAMPLES.md`:examples/*.json 跑法(human/mouse/bacteria)。

## 4. 测试
- 后端 pytest:新增 `praxis_virtualcell/tests/test_packaging.py`——解析 `pyproject.toml`,断言 `packages.find.include` 含 `praxis_virtualcell*` 与 `praxis_vc_api*`(防回退);断言 MANIFEST.in 存在且含 `recursive-include praxis_virtualcell`。
- 本地 wheel smoke(手动,plan 里给命令):build→fresh venv→offline demo 产 report.md。
- shellcheck/`bash -n` 脚本;全量 `pytest praxis_virtualcell/tests` 0 failed。

## 5. 验收
- `pip wheel .` 构建成功;全新 venv 装 wheel 后 `praxis-vc run --mode offline` 无 API key 产出 report.md(9 段)。
- `test_packaging.py` 绿(防打包配置回退)。
- Dockerfile/start.sh/check_install.sh 语法过;INSTALL/USER-GUIDE/EXAMPLES 齐。
- 全量 pytest 无回归;每 task push。

## 6. 边界(不做 / 用户侧)
- `docker build` + clean-Ubuntu smoke:Mac 无法,硬门⑤——交付 Dockerfile/脚本后请用户在 Linux 侧验。
- 不打包 GEM SBML(cobra-gated,mechanistic 单独装);离线 demo 用 mock predictor 已足。
- 不做复杂 GUI installer;不引入新重依赖(复用现有 extras)。
- tar.gz 真打包(bin/app/data 目录树)可作后续;本切片先给 Dockerfile+脚本+wheel+docs 的薄核心。
