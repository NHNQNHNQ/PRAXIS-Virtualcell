# PRAXIS-VirtualCell 安装指南

> 离线优先：在源码 checkout 中无需任何 API key 即可跑完整 offline demo。`llm_assisted` 才需 `DEEPSEEK_API_KEY`。
> 要求:Python ≥ 3.11(推荐 3.13)· Ubuntu 22.04/24.04 或 macOS。

## 1. 源码 pip 安装（开发者 / 集成）

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e ".[api]"  # 核心 + FastAPI 本地服务
praxis-vc --version
```

源码安装后 `praxis-vc` 命令可用（entry point → `praxis_virtualcell.cli:main`），cell catalog、brain 规则和 governance artifact 可供离线流程使用。

自检:
```bash
bash deploy/vc/check_install.sh    # 验 python + CLI + 一次 offline demo 产 report.md
```

### 完整 release wheel

```bash
PYTHON_BIN=python3.13 \
  scripts/build_release_wheel.sh /tmp/praxis-dist
PRAXIS_REPO_ROOT="$(pwd)"

python3.13 -m venv /tmp/praxis-release-venv
/tmp/praxis-release-venv/bin/python -m pip install \
  --require-hashes -r requirements/runtime-py313.lock
/tmp/praxis-release-venv/bin/python -m pip install \
  --no-deps /tmp/praxis-dist/praxis_virtualcell-*.whl
(cd /tmp && /tmp/praxis-release-venv/bin/python \
  "${PRAXIS_REPO_ROOT}/scripts/verify_release_install.py")
```

该脚本拒绝 tracked dirty state，从 `git archive HEAD` 建立全新临时源码树，在其中用 `npm ci && npm run build` 生成 React 产物；随后在临时 Python 3.13 环境按 `requirements/build-py313.lock` 安装 hash-locked build backend，并以 `--no-build-isolation` 构建完整 wheel。这样不会复用 checkout 中旧的 `build/`、egg-info 或 hashed static asset。wheel 内含 CLI/API、React 静态资源、`praxis_vc_web/app.py` 和默认 gene-set 数据，不包含测试包。

发行 verifier 从源码仓库外运行，覆盖 CLI `run` 的四项产物、API health/job、同源首页与 hashed asset，以及 Streamlit app 内容存在。它没有运行 `praxis-vc ask` 或启动完整 Streamlit server，不能把这些能力写成已验证。

## 2. React 同源页面

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
praxis-vc serve
```

源码 editable 安装必须在 `dist/` 构建完成后启动 FastAPI，才会把 React 挂到 `/`；没有 `dist/` 时源码服务只提供 API。完整 release wheel 与发布容器使用包内 `praxis_vc_api/static`，不依赖源码目录。

`praxis-vc web` 是旧 Streamlit 入口。完整 wheel 已包含入口文件并使用包内绝对路径，但仍需安装 `web` extra；当前发行门没有启动 Streamlit server。

## 3. Docker 发布容器

容器使用固定 multi-platform digest 的 Node 24 与 Python 3.13.14 基础镜像。四阶段构建先生成 React、构建同一完整 wheel、在 `--network=none` 的 installer 中从 hash-verified wheelhouse 安装，最终镜像只复制 `/opt/venv`。运行用户为 UID/GID 10001，持久化目录是 `/var/lib/praxis-vc/runs`。

构建必须显式注入完整候选 SHA 与 commit epoch；缺少或格式非法时 Dockerfile 会拒绝构建：

```bash
scripts/build_release_container.sh praxis-virtualcell:local
docker run --rm -p 127.0.0.1:8000:8000 \
  -v praxis-vc-runs:/var/lib/praxis-vc/runs \
  praxis-virtualcell:local
```

脚本从当前 committed HEAD 取完整 SHA 与 epoch，并拒绝 tracked dirty state 或不在保护清单中的 untracked 文件，防止镜像内容与 OCI/health 身份错配。若直接调用 Dockerfile，同样必须显式提供两项 build arg。

完整 Docker smoke 是显式双门，普通 core 测试只会 skip：

```bash
PRAXIS_RUN_DOCKER_SMOKE=1 .venv/bin/python -m pytest \
  praxis_virtualcell/tests/test_linux_docker_smoke.py \
  --run-integration -o addopts='' -q -ra
```

该 smoke 使用每次唯一的 image/container 名和 owner label，只清理本次创建的资源；验证 non-root、health/version/SHA、容器内 CLI、React hashed assets 与 offline API report。Docker Desktop 的 Linux-container 结果不等同于原生 Linux/amd64 或 `.53` 已验证；远端结果必须单列。

## 4. 便携源码目录（无 Docker 的 Linux）

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e ".[api]"
bash deploy/vc/start.sh            # 启动 API；已有 dist 时才同源提供 React
```

这些脚本依赖源码仓库相对路径，必须从仓库根目录运行。`start.sh` 本身不构建 React；需要网页时先按第 2 节生成 `dist/`。`check_install.sh` 也读取根 `examples/ahr_k562.json`，不能在只含已安装 wheel 的最终容器中直接使用。这些脚本不是独立 wheel 安装的证明。

## 5. 可选:LLM 辅助模式

仅用于自然语言解析 / 报告润色,**永不参与预测/治理决策**。
```bash
export DEEPSEEK_API_KEY=<你的key>
export PRAXIS_VIRTUALCELL_MODE=llm_assisted
```
无 key 或调用失败自动回退 offline 确定性。

## 6. 可选:机制模型(GEM/FBA 真数值)

bacteria/yeast 生长的真机制预测需 `cobra`(单独 extra;缺失时相关 case 降级/跳过):
```bash
pip install ".[mechanistic]"
```

## 7. 可选:AnnData/H5AD

VirtualCellPack 的 backed、只读 H5AD 适配器需要独立 `omics` extra；核心 runtime
不安装或导入 AnnData：

```bash
pip install ".[omics]"
```

适配器只按 manifest 映射加载和选择，校验声明资产的流式 SHA-256、shape、obs/var
名称及映射 ID 唯一性、condition 与预定义 split。`matrix` 可从旧 manifest 中省略，
但 H5AD manifest 必须提供非 null 的 `matrix.location: X`；layer 会在 manifest 边界
fail-closed。

`X` 在访问前保持只读 backed，CSR/CSC 选择后保持原稀疏格式；canonical metadata
会物化为不可变 tuple。selection 必须按源 obs/feature 顺序给出，乱序、未知或重复
ID 均拒绝，不会静默重排、归一化矩阵、修改 ID 或生成 split。

`vc.pack.v0.2` 在同一 adapter 上增加标准语义门：versioned NCBI assembly、
`var_names` canonical feature ID、独立的 cell identity/state/context、
condition/perturbation/target 外键、control matching、显式 dose/time unit，以及
named split leakage guard。Ontology 只按 manifest 中的标准 ID 或有定义 local
CURIE 离线校验；安装与运行均不查询 ontology 服务，也不做 ortholog projection。
旧 `vc.pack.v0.1` 的 manifest 与 fingerprint 语义保持不变。
