# PRAXIS-VirtualCell 安装指南

> 离线优先:**无需任何 API key 即可跑完整 offline demo**。llm_assisted 才需 `DEEPSEEK_API_KEY`。
> 要求:Python ≥ 3.11(推荐 3.13)· Ubuntu 22.04/24.04 或 macOS。

## 1. pip 安装(开发者 / 集成)

```bash
# 从源码
pip install ".[api]"          # 核心 + FastAPI 本地服务(praxis-vc serve)
# 或从构建好的 wheel
pip install "praxis_virtualcell-<版本>-py3-none-any.whl[api]"
```

安装后 `praxis-vc` 命令可用(entry point → `praxis_virtualcell.cli:main`)。运行时数据(cell catalog / brain 规则 / governance artifact)随包分发,离线即用。

自检:
```bash
bash deploy/vc/check_install.sh    # 验 python + CLI + 一次 offline demo 产 report.md
```

## 2. Docker(最稳,适合服务器/评审复现)

```bash
docker build -f deploy/vc/Dockerfile -t praxis-virtualcell .
docker run -p 8000:8000 praxis-virtualcell
# 浏览器开 http://127.0.0.1:8000
```
镜像默认 `PRAXIS_VIRTUALCELL_MODE=offline`、non-root、无 DB、无需 key。

> 前端网页:若要 serve 同源托管 React 页面,先 `cd praxis_vc_react && npm run build` 再构建镜像(Dockerfile 里放开 `COPY praxis_vc_react/dist` 那行);否则仅 API 可用,前端可单独 `npm run dev`。

## 3. 便携 tar.gz(无 Docker 的 Linux)

```bash
python3 -m venv venv && . venv/bin/activate
pip install ".[api]"
bash deploy/vc/start.sh            # 起本地网站(offline)
```

## 4. 可选:LLM 辅助模式

仅用于自然语言解析 / 报告润色,**永不参与预测/治理决策**。
```bash
export DEEPSEEK_API_KEY=<你的key>
export PRAXIS_VIRTUALCELL_MODE=llm_assisted
```
无 key 或调用失败自动回退 offline 确定性。

## 5. 可选:机制模型(GEM/FBA 真数值)

bacteria/yeast 生长的真机制预测需 `cobra`(单独 extra;缺失时相关 case 降级/跳过):
```bash
pip install ".[mechanistic]"
```
