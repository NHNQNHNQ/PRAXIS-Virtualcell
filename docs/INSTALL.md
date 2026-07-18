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

### 当前 wheel 验证边界

```bash
python -m pip install "./praxis_virtualcell-<版本>-py3-none-any.whl[api]"
```

C2 只在独立 Python 3.13 环境验证了 wheel metadata、`praxis_virtualcell`/`praxis2` import、`praxis-vc --version` 和 `praxis-vc --help`。完整依赖解析、offline run/ask、API、React/Streamlit 与同源 `dist` 的 wheel 复现仍归 C4；不能把上面的 smoke 扩写成完整 wheel 发布保证。

## 2. React 同源页面

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
praxis-vc serve
```

FastAPI 必须在 `dist/` 构建完成后启动，才会把 React 挂到 `/`。没有 `dist/` 时 `praxis-vc serve` 只提供 API。

`praxis-vc web` 是源码 checkout 中的旧 Streamlit 入口；当前 wheel 未包含 `praxis_vc_web`，因此 C2 的 wheel smoke 不声明该子命令可运行。该打包缺口归 C4。

## 3. Docker（待 C4 验证）

当前 Dockerfile 的依赖 stub 未复制 `README.md`，React `dist` 复制也尚未纳入镜像契约；历史 `.53` Docker smoke 仍是 pending。现阶段不能把 Docker 称为“最稳”或已通过的评审复现路径。

下面命令只供 C4 修复/验证使用，不构成当前发布保证：

```bash
docker build -f deploy/vc/Dockerfile -t praxis-virtualcell .
docker run -p 8000:8000 praxis-virtualcell
```

## 4. 便携源码目录（无 Docker 的 Linux）

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e ".[api]"
bash deploy/vc/start.sh            # 启动 API；已有 dist 时才同源提供 React
```

这些脚本依赖源码仓库相对路径，必须从仓库根目录运行。`start.sh` 本身不构建 React；需要网页时先按第 2 节生成 `dist/`。这不是独立 wheel 安装的证明。

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
