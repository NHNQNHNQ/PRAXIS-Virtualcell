# PRAXIS-VirtualCell 安装指南

> 离线优先：在源码 checkout 中无需任何 API key 即可跑完整 offline demo。`llm_assisted` 才需 `DEEPSEEK_API_KEY`。
> P30A 发布状态：`1.7.0` 仅是本地、未发布的 RC 候选版本；本文不表示正式 local RC 或 OCI 门已通过，也不授权 P30B push、tag、发布或部署。

## Python 支持矩阵

| Python | 支持层级 | P30A 含义 |
|---|---|---|
| 3.13 | exact-locked RC target | `requirements/*-py313.lock` 按版本和 hash 锁定；只有完整本地门通过后才能成为 RC 证据 |
| 3.11 / 3.12 | metadata-compatible only | 满足 `requires-python >=3.11`，但未经 exact-hash RC 矩阵资格化，不是 `1.7.0` release-qualified runtime |

Ubuntu 22.04/24.04 和 macOS 可用于源码开发；平台可安装不等于该平台已通过 RC 验收。

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

### `1.7.0` 候选 wheel（P30A 本地、未发布）

```bash
PYTHON_BIN=python3.13 \
  PRAXIS_RELEASE_OFFLINE=1 \
  scripts/build_release_wheel.sh /tmp/praxis-dist
PRAXIS_REPO_ROOT="$(pwd)"
PRAXIS_PIP_CACHE_ROOT="${PRAXIS_PIP_CACHE_ROOT:-$(python3.13 -m pip cache dir)}"
RC_WHEELHOUSE="$(mktemp -d /tmp/praxis-runtime-wheelhouse.XXXXXX)"

python3.13 "${PRAXIS_REPO_ROOT}/scripts/release_candidate.py" materialize-wheelhouse \
  --lock "${PRAXIS_REPO_ROOT}/requirements/runtime-py313.lock" \
  --cache-root "${PRAXIS_PIP_CACHE_ROOT}" \
  --output "${RC_WHEELHOUSE}" \
  --source-date-epoch "$(git -C "${PRAXIS_REPO_ROOT}" log -1 --format=%ct)" \
  --target-profile macos_arm64_cp313

python3.13 -m venv /tmp/praxis-release-venv
/tmp/praxis-release-venv/bin/python -m pip install \
  --no-index \
  --find-links "${RC_WHEELHOUSE}" \
  --only-binary=:all: \
  --require-hashes \
  -r "${PRAXIS_REPO_ROOT}/requirements/runtime-py313.lock"
/tmp/praxis-release-venv/bin/python -m pip install \
  --no-deps /tmp/praxis-dist/praxis_virtualcell-*.whl
(cd /tmp && /tmp/praxis-release-venv/bin/python \
  "${PRAXIS_REPO_ROOT}/scripts/verify_release_install.py")
```

该脚本拒绝任何 dirty state，从 `git archive HEAD` 建立全新临时源码树。P30A 本地流程使用 `PRAXIS_RELEASE_OFFLINE=1`：Python build wheel 必须从现有本地 pip cache 按 `requirements/build-py313.lock` 的 exact hash 物化，React 必须以 `npm ci --offline` 构建；缺任何精确依赖即 fail-closed。随后以 `--no-build-isolation` 构建完整 wheel，不复用 checkout 中旧的 `build/`、egg-info 或 hashed static asset。只有成功生成的 wheel 才内含 CLI/API、React 静态资源、`praxis_vc_web/app.py` 和默认 gene-set 数据，且不包含测试包。

发行 verifier 从源码仓库外运行，覆盖 CLI `run` 的四项产物、API health/job、同源首页与 hashed asset，以及 Streamlit app 内容存在。它没有运行 `praxis-vc ask` 或启动完整 Streamlit server，不能把这些能力写成已验证。

## 2. React 同源页面

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
praxis-vc serve
```

源码 editable 安装必须在 `dist/` 构建完成后启动 FastAPI，才会把 React 挂到 `/`；没有 `dist/` 时源码服务只提供 API。只有已成功构建的完整 release wheel 或 OCI artifact 才使用包内 `praxis_vc_api/static`，不依赖源码目录。

`praxis-vc web` 是旧 Streamlit 入口。完整 wheel 已包含入口文件并使用包内绝对路径，但仍需安装 `web` extra；当前发行门没有启动 Streamlit server。

## 3. OCI 候选构建合同（P30A 尚未验收）

候选 OCI 合同使用 digest-pinned Python 3.13.14 基础镜像和预先验证的 exact wheelhouse；`deploy/vc/Dockerfile.artifact` 在 `--network=none` 下安装，最终镜像只复制 `/opt/venv`。运行用户为 UID/GID 10001，持久化目录是 `/var/lib/praxis-vc/runs`。合同和 builder 存在不等于 OCI 已构建、双构建已等价或正式 P30A gate 已通过。

构建必须显式注入完整候选 SHA 与 commit epoch；缺少或格式非法时 Dockerfile 会拒绝构建：

```bash
scripts/build_release_oci.sh \
  /absolute/path/to/exact-wheelhouse \
  /tmp/praxis-virtualcell-1.7.0.oci.tar
```

脚本从当前 clean committed HEAD 取完整 SHA 与 epoch，拒绝复用输出、非本地 Docker endpoint、未命中 pinned digest 的基础镜像以及任何依赖下载。两次 OCI 只能在 manifest、config 和有序 layer 均一致后成为可候选证据；归档 tar 字节本身不是等价判据。

完整 Docker smoke 是显式双门，普通 core 测试只会 skip：

```bash
PRAXIS_RUN_DOCKER_SMOKE=1 .venv/bin/python -m pytest \
  praxis_virtualcell/tests/test_linux_docker_smoke.py \
  --run-integration -o addopts='' -q -ra
```

该 smoke 使用每次唯一的 image/container 名和 owner label，只清理本次创建的资源；验证 non-root、health/version/SHA、容器内 CLI、React hashed assets 与 offline API report。它仅在实际执行并保存 exact artifact evidence 时才是当次候选的证据；Docker Desktop 的 Linux-container 结果不等同于原生 Linux/amd64 或 `.53` 已验证，远端结果必须单列。

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
CURIE 离线校验；Cellosaurus 只接受正式 `CVCL_XXXX` accession，标准 ID 与 local
term 都绑定 identity/state/context 角色。canonical key 同时固定 modality、
feature namespace/version、local-term 定义、完整 condition/perturbation catalog
与 split/leakage 声明，不把 display symbol 或 matrix 数值冒充 metadata 身份。
v0.2 登记也必须完成该语义门并保存同一次语义加载实际验证的 manifest，缺少
`omics` extra 时 fail-closed。manifest symlink 不得逃出 Pack root。安装与运行
均不查询 ontology 服务，也不做 ortholog projection。
旧 `vc.pack.v0.1` 的 manifest 与 fingerprint 语义保持不变。
