# Linux 发行版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。Steps 用 checkbox 跟踪。

**Goal:** 让 PRAXIS-VirtualCell 可 pip wheel 安装、无 API key 离线跑 demo,并给 Docker/脚本/文档脚手架(真机 docker/Ubuntu 验证用户侧)。

**Architecture:** 修 pyproject 打包(含 praxis_virtualcell/praxis_vc_api + package-data)→ wheel smoke(fresh venv offline demo 产 report.md)→ Dockerfile/start.sh/check_install.sh 脚手架 + INSTALL/USER-GUIDE/EXAMPLES 文档。

**Tech Stack:** setuptools/pip wheel · Docker(用户侧)· bash · Markdown。

**铁律:** 不碰科学核心;发行必须无 key 可 offline;不引入新重依赖(复用 extras);Mac 无法 docker build/Ubuntu smoke → 那步撞硬门⑤停下请用户验。每 task 后端全量 pytest 0 failed 才 push。commit 前删 `._*`,末尾 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

---

## Task 1: 打包修复 + wheel offline smoke(核心,本地可验)

**Files:**
- Modify: `pyproject.toml`(packages.find include + include-package-data)
- Create: `MANIFEST.in`
- Create: `praxis_virtualcell/tests/test_packaging.py`

- [ ] **Step 1: 写打包守卫测试(先失败)**

写 `praxis_virtualcell/tests/test_packaging.py`:

```python
"""打包配置守卫:wheel 必须含 praxis_virtualcell/praxis_vc_api + 运行时数据。
防 packages.find 回退到只打 praxis2(否则 praxis-vc CLI ImportError)。"""
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def test_packages_find_includes_virtualcell():
    cfg = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    include = cfg["tool"]["setuptools"]["packages"]["find"]["include"]
    assert any(p.startswith("praxis_virtualcell") for p in include), include
    assert any(p.startswith("praxis_vc_api") for p in include), include


def test_include_package_data_and_manifest():
    cfg = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert cfg["tool"]["setuptools"].get("include-package-data") is True
    manifest = (_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include praxis_virtualcell" in manifest
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_packaging.py -q`
Expected: FAIL(include 只含 praxis2* / 无 MANIFEST.in)

- [ ] **Step 3: 修 pyproject.toml 打包**

`pyproject.toml`:把 `[tool.setuptools.packages.find]` 段改为:

```toml
[tool.setuptools]
include-package-data = true

[tool.setuptools.packages.find]
include = ["praxis2*", "praxis_virtualcell*", "praxis_vc_api*"]
```

(注:原文件是 `[tool.setuptools.packages.find]\ninclude = ["praxis2*"]`,在其上方加 `[tool.setuptools]\ninclude-package-data = true`,并把 include 扩为三项。)

- [ ] **Step 4: 写 MANIFEST.in**

写 `MANIFEST.in`:

```
recursive-include praxis_virtualcell *.yaml *.json
```

- [ ] **Step 5: 跑守卫测试通过 + 全量**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_packaging.py -q`
Expected: PASS(2 passed)

Run(后台): `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -o console_output_style=classic 2>&1 | tail -1`
Expected: `277 passed, 25 skipped`(275 + 2),0 failed

- [ ] **Step 6: wheel offline smoke(本地硬证据)**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell
rm -rf /tmp/vc_wheel /tmp/vc_smoke && mkdir -p /tmp/vc_wheel
.venv/bin/pip wheel . --no-deps -w /tmp/vc_wheel 2>&1 | tail -3
python3 -m venv /tmp/vc_venv
/tmp/vc_venv/bin/pip install -q "$(ls /tmp/vc_wheel/praxis_virtualcell-*.whl)[api]" 2>&1 | tail -2
/tmp/vc_venv/bin/praxis-vc run --request examples/ahr_k562.json --mode offline --out /tmp/vc_smoke 2>&1 | tail -3
ls /tmp/vc_smoke/report.md && grep -c '^## ' /tmp/vc_smoke/report.md
```
Expected: wheel 构建成功;fresh venv 装后 `praxis-vc run` 无 ImportError/FileNotFound,`/tmp/vc_smoke/report.md` 存在、9 段。
**若报 FileNotFound(缺某运行时 yaml/json)**:把该资源 glob 补进 MANIFEST.in(如 `recursive-include praxis_virtualcell *.xml.gz`),重跑 smoke,直至绿。清理:`rm -rf /tmp/vc_wheel /tmp/vc_venv /tmp/vc_smoke`。

- [ ] **Step 7: commit + push**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add pyproject.toml MANIFEST.in praxis_virtualcell/tests/test_packaging.py
git commit -m "fix(v0.8): 打包含 praxis_virtualcell/praxis_vc_api + package-data → wheel 可 offline 跑

修 packages.find(原只打 praxis2 致 praxis-vc CLI ImportError)+ MANIFEST.in 纳运行时 yaml/json。
本地 wheel smoke:fresh venv 装后无 key 跑 offline demo 产 report.md 9 段。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin main
```

---

## Task 2: 离线发行脚手架(Dockerfile + 脚本,可 lint)

**Files:**
- Create: `deploy/vc/Dockerfile`
- Create: `deploy/vc/start.sh`
- Create: `deploy/vc/check_install.sh`

> 注:`deploy` 目录在 ruff exclude 内(CI 转绿切片设的),但这些是 Dockerfile/bash 非 py,不受 ruff 影响。

- [ ] **Step 1: 写 deploy/vc/Dockerfile**

```dockerfile
# PRAXIS-VirtualCell 离线发行镜像(本地网页 + CLI,offline 确定性,无需 API key/DB)。
# 真机构建:docker build -f deploy/vc/Dockerfile -t praxis-virtualcell .
# 跑:docker run -p 8000:8000 praxis-virtualcell  → 浏览器开 http://127.0.0.1:8000
FROM python:3.13-slim
WORKDIR /app

# 先装依赖(cache 友好):只拷 pyproject + 最小包 stub
COPY pyproject.toml MANIFEST.in ./
COPY praxis_virtualcell ./praxis_virtualcell
COPY praxis_vc_api ./praxis_vc_api
COPY examples ./examples
RUN pip install --no-cache-dir ".[api]" && rm -rf /root/.cache

# 可选:若已构建 React dist,拷入让 serve 同源托管(dist 不在 git,构建时挂载或先 npm build)
# COPY praxis_vc_react/dist ./praxis_vc_react/dist

# non-root
RUN useradd -r -u 1000 -m -s /sbin/nologin praxisvc && chown -R praxisvc /app
USER praxisvc

ENV PRAXIS_VIRTUALCELL_MODE=offline
EXPOSE 8000
CMD ["praxis-vc", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 写 deploy/vc/start.sh**

```bash
#!/usr/bin/env bash
# 本地起 PRAXIS-VirtualCell(offline)。需先 pip install '.[api]'。
set -euo pipefail
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
export PRAXIS_VIRTUALCELL_MODE=offline
echo "PRAXIS-VirtualCell is running."
echo "Local website: http://${HOST}:${PORT}"
echo "Mode: OFFLINE · LLM: disabled · Demo data: examples/"
exec praxis-vc serve --host "${HOST}" --port "${PORT}"
```

- [ ] **Step 3: 写 deploy/vc/check_install.sh**

```bash
#!/usr/bin/env bash
# 安装自检:python 版本 + CLI 可用 + 一次 offline demo 产 report.md。
set -euo pipefail
python3 -c 'import sys; assert sys.version_info>=(3,11), "需 Python>=3.11"' && echo "[ok] python>=3.11"
praxis-vc --help >/dev/null && echo "[ok] praxis-vc CLI"
OUT="$(mktemp -d)/demo"
praxis-vc run --request examples/ahr_k562.json --mode offline --out "$OUT" >/dev/null
test -f "$OUT/report.md" && echo "[ok] offline demo → report.md" || { echo "[FAIL] 无 report.md"; exit 1; }
echo "check_install: ALL OK"
```

- [ ] **Step 4: 语法 lint**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell
chmod +x deploy/vc/*.sh
bash -n deploy/vc/start.sh && bash -n deploy/vc/check_install.sh && echo "bash 语法 OK"
command -v shellcheck >/dev/null && shellcheck deploy/vc/*.sh || echo "(无 shellcheck,跳过)"
```
Expected: bash -n 通过。

- [ ] **Step 5: commit + push**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react deploy -name '._*' -delete
git add deploy/vc/
git commit -m "feat(v0.8): 离线发行脚手架 Dockerfile + start.sh + check_install.sh(offline,无DB/无key)

真机 docker build + Ubuntu smoke 需用户在 Linux 侧验(Mac 无 Docker)。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin main
```

---

## Task 3: 安装/使用文档

**Files:**
- Create: `docs/INSTALL.md`
- Create: `docs/USER-GUIDE.md`
- Create: `docs/EXAMPLES.md`

- [ ] **Step 1: 写 docs/INSTALL.md**

内容涵盖:①pip(`pip install '.[api]'` 或 wheel)②Docker(`docker build -f deploy/vc/Dockerfile -t praxis-virtualcell . && docker run -p 8000:8000 …`)③自检(`deploy/vc/check_install.sh`)。强调**无 API key 即可 offline 全功能**;llm_assisted 才需 `DEEPSEEK_API_KEY`。要求 Python≥3.11 / Ubuntu 22.04+。

- [ ] **Step 2: 写 docs/USER-GUIDE.md**

内容:CLI(`praxis-vc run/ask/serve/web`)+ 本地网页流程(Ask→Confirm(下拉+cell 预设)→Report/Trace/Provenance)+ 输出(`runs/<job>/report.md` 9 段 + report.json/trace/provenance)+ offline vs llm_assisted 边界(LLM 不碰预测/治理)。

- [ ] **Step 3: 写 docs/EXAMPLES.md**

内容:`examples/*.json` 三例跑法(human ahr_k562 / mouse / bacteria);每例给命令 + 预期 verdict(accept/caution/abstain)。数值精度口径:offline 用 mock predictor,真数值在远端 A100。

- [ ] **Step 4: commit + push**

```bash
find docs -name '._*' -delete
git add docs/INSTALL.md docs/USER-GUIDE.md docs/EXAMPLES.md
git commit -m "docs(v0.8): INSTALL / USER-GUIDE / EXAMPLES(离线发行使用文档)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin main
```

---

## 验收(全部完成后)
- `pip wheel .` + fresh venv 无 key 跑 offline demo 产 report.md(Task 1 已验)。
- `test_packaging.py` 绿;全量 pytest 0 failed。
- Dockerfile/start.sh/check_install.sh 语法过;INSTALL/USER-GUIDE/EXAMPLES 齐。
- 每 task push。

## 停止条件(硬门)
1. 需改核心科学逻辑;2. wheel smoke 缺数据无法自解;3. pytest 回归;4. push 失败/CI 红;
5. **docker build / clean-Ubuntu smoke 需真机而 Mac 无法** → 交付 Dockerfile/脚本/文档后停下,请用户在 Linux 侧 `docker build` + 跑 check_install.sh 验;6. Task 1–3 完成→切片 4 收尾汇报。
