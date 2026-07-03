# PRAXIS-VirtualCell

> 可信虚拟细胞扰动预测的**可靠性治理**软件系统。离线优先、可审计、可弃权。
> 卖点不是"更准",而是**适用性判断 / 拒绝 / 弃权 / 降级 / 溯源 / 不过度承诺**——不适用就诚实拒绝,而非硬报一个假数值。

用户选择物种 / 细胞场景 / 扰动任务,系统自动路由到合适的预测器或代理工具,输出带**治理裁决、证据边界、复现信息**的 Markdown 报告。**默认离线(零 LLM),无需任何 API key。**

---

## 安装

要求 Python ≥ 3.11(推荐 3.13)· Linux(Ubuntu 22.04/24.04)或 macOS。

```bash
git clone https://github.com/NHNQNHNQ/PRAXIS-Virtualcell.git
cd PRAXIS-Virtualcell
python3 -m venv venv && . venv/bin/activate
pip install ".[api]"          # 核心 + 本地 FastAPI 服务
```

安装后 `praxis-vc` 命令可用。运行时数据(cell catalog / brain 规则 / governance artifact)随包分发,离线即用。

自检:`bash deploy/vc/check_install.sh`(验 python + CLI + 一次 offline demo 产 report.md)。

Docker(可选):`docker build -f deploy/vc/Dockerfile -t praxis-virtualcell . && docker run -p 8000:8000 praxis-virtualcell`。

## 快速开始

```bash
# 本地网页(浏览器开 http://127.0.0.1:8000)
praxis-vc serve

# 命令行:结构化请求(离线确定性)
praxis-vc run --request examples/ahr_k562.json --mode offline --out runs/ahr

# 命令行:自然语言 →(--yes)执行
praxis-vc ask --text "在 human K562 里敲掉 AHR 会怎么样" --mode offline --yes --out runs/ahr
```

每次运行产出 `runs/<job>/report.md`——**确定性 9 段报告**(Question / Cell Context / Routing / Result / **Governance Verdict** / Evidence & Provenance / Biological Interpretation / **Limitations** / Reproducibility),offline 也有。

## 治理裁决(verdict)

| verdict | 含义 |
|---|---|
| **accept** | 适用且证据足,给预测 |
| **caution** | 带告警用(如跨物种 ortholog、药物签名噪声大) |
| **downgrade** | 引擎在但数据/证据不足,降级解读不可全信 |
| **abstain** | 无适用引擎 → 系统正确弃权,不产出预测 |

铁律:所有预测/治理决策由**后端确定性 runtime** 完成;LLM 只做自然语言解析、路由建议、critic 复核、报告润色,**绝不**碰 prediction / hard-rule / learned-reliability 终决 / provenance。`llm_assisted` 模式需 `DEEPSEEK_API_KEY`,失败自动回退离线。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/INSTALL.md](docs/INSTALL.md) | 安装(pip / Docker / tar.gz)+ 自检 |
| [docs/USER-GUIDE.md](docs/USER-GUIDE.md) | CLI / 本地网页 / 输出 / 模式与边界 |
| [docs/EXAMPLES.md](docs/EXAMPLES.md) | 三例(accept / caution / abstain,verdict 已实跑核实) |
| [docs/项目说明.md](docs/项目说明.md) · [PROVENANCE.md](PROVENANCE.md) | 系统现状 / 派生关系 |

## 开发

```bash
pip install -e ".[dev]"
PYTHONPATH=$PWD python -m pytest praxis_virtualcell/tests    # 后端测试(277 passed)
ruff check .                                                 # lint
cd praxis_vc_react && npm install && npm run build           # 前端(可选,serve 同源托管 dist)
```

声明式回归安全网:`praxis_virtualcell/tests/golden_cases/*.yaml`(路由/治理正向,KPI unsafe-accept=0)+ `negative_cases/*.yaml`(错输入拒绝,KPI 无静默 accept)。开发走 superpowers 流程(brainstorm → spec → plan → TDD),`main` 即生产线。

## 派生

基于 **PRAXIS-2**(commit `b124d66`)复制改造:继承 agent runtime / 长期大脑 / 规则系统 / 反幻觉地基,扩展虚拟细胞大脑、预测器注册表、生物 benchmark。python 包名保持 `praxis2`(继承 runtime);虚拟细胞代码在 `praxis_virtualcell/`,本地界面在 `praxis_vc_api/` + `praxis_vc_react/`。派生关系见 [PROVENANCE.md](PROVENANCE.md)。
