# PRAXIS-VirtualCell 路线图 —— v0.3+ "Cell-OS"

> 生成:2026-06-27 · 上游里程碑:v0.2.0(W8:系统对比三表 + 论文 v0.2 + 全部数字诚信验证)
> 本文是 v0.3 → v1.0 的工程路线图。**采纳的核心判断**(用户提出、我赞同):
> **别人已有强 predictor 的部分不要重复训练;PRAXIS 的核心价值是把它们接成一个真正能工作的虚拟细胞智能体,
> 只在"现有模型缺位"的地方训练自己的模型——路由 / 可靠性 / 统一输出 / 缺口预测。**

---

## 0. 定位:从"治理骨架"到"细胞科研操作系统"

v0.2 已有:agent runtime / message bus / species brain / predictor-agent 接口 / abstain / critic / provenance /
可选 LLM agent,主闭环离线可复现。v0.3 要补的是 **功能栈(接入现成模型)+ 模型栈(自研治理/缺口模型)**。

目标形态(五段式):
```
输入  → 物种 / 细胞类型 / 基因·药物·环境扰动 / 剂量 / 时间 / 数据模态
理解  → 这是什么任务?对象是否真实?当前哪些模型能做?
预测  → 扰动后表达 / 状态 / 通路 / 代谢 / 命运 / 通讯 / 空间变化
判断  → 哪些预测可靠?哪些应 abstain?
输出  → 预测 + 机制解释 + 不确定性 + provenance + 下一步实验建议
```

---

## 1. 三条设计原则(贯穿全程)

1. **接入优先**:foundation model / 成熟分析工具 一律作为 predictor-agent / analysis-agent 接入,**不重造**。
2. **只自训练四类**:① 路由(MoE Router)② 可靠性(OOD / abstain / calibration)③ 统一输出(Delta Adapter)④ 缺口预测(small reliable predictor + 多细胞/空间/通讯)。这些是别人没系统做好、也最可能超过别人的地方。
3. **守住 PRAXIS DNA**:每个新接入/新模型都按 v0.2 的诚实标准——same-protocol 才同表、不可比标 off-axis、声明式 vs 运行时分清、实跑不臆造、provenance 可追溯。**大愿景配里程碑闸门,先证小闭环再扩,不摊大饼。**

---

## 2. 三个关键工程洞察(决定路线的先后)

### 洞察 A:接入真 predictor = 给现有治理骨架"通电"(一举三得)
v0.2 的两个最大局限,**接入真 perturbation predictor(GEARS/CPA/scGen)即可同时解掉**:
- R8(无强外部 same-protocol baseline)→ 真模型同协议进表 A。
- 声明式机制 mock 不激活(disagreement / core-predictor-failed / cell-type 降级)→ 真模型有真分歧、真失败、多维输出,机制**自发触发**。
- abstain / router 的训练数据 → 真模型在真任务上的逐样本表现。
→ **所以阶段 1 不是"加新功能",而是把已建好的治理层接上真电源。** 这是性价比最高的第一步。

### 洞察 B:数据依赖链 —— 自研治理模型需要"评测账本"先行
MoE Router / OOD classifier / Abstain head 是**学习型**模型,训练数据 = 模型库在 benchmark 上的
**逐样本(per-cell / per-perturbation)表现 + 模型间分歧 + 与 ground-truth 的误差**。
→ 因此阶段 1 的隐藏关键产物是 **PRAXIS Eval Ledger**:统一记录每个 predictor-agent 在每个样本上的
预测 / 不确定性 / 误差 / 分歧 / 是否 OOD。没有它,阶段 2 的自研模型无数据可训。

### 洞察 C:env 隔离是现实,不是缺陷
scVI / CellOracle / NicheNet / COBRApy / scFEA 各有依赖地狱。沿用 v0.2 已验证的模式:
**per-agent 独立 conda env + 远端跑 + 桥接**(已有 `vc-scgpt` 单独 env 先例)。predictor-agent 通过
message / 轻 RPC 跨 env 通讯,**不强求单一 env**。这把"环境复杂度"关进每个 agent 内部,不污染 core。

---

## 3. 10 功能层 → 现有架构映射

| 功能层 | 接入(别人) | 自研接线点(PRAXIS 现有组件的升级) |
|---|---|---|
| 1 输入理解 | 规则 + 可选 LLM(已有) | 后续可训任务分类器(InputInterpreter 升级) |
| 2 对象标准化 | gene/drug/celltype/ontology 数据库 | ObjectNormalizer 扩库(已有骨架) |
| 3 细胞状态识别 | CellTypist / scVI / foundation embedding | **cell-state confidence/OOD classifier(自研)** |
| 4 基因扰动预测 | GEARS / CPA / scGen / STATE | **MoE Router + Abstain(自研)**;predictor-agent 接口已有 |
| 5 药物扰动预测 | CPA / STATE / LINCS / DeepPurpose | drug-cell adapter(自研) |
| 6 命运/动态 | CellRank / CellOracle | state-transition adapter(自研) |
| 7 调控/机制 | CellOracle / LINGER / SCENIC+ | GRN→expression correction head(自研) |
| 8 代谢/通量 | COBRApy / scFEA / MICOM | expression→flux calibrator(自研) |
| 9 通讯/空间 | NicheNet / CellChat / Tangram / cell2location / Squidpy | **sender–receiver / niche-aware response(自研)** |
| 10 可靠性治理 | 几乎无现成 | **PRAXIS 核心自研:OOD / calibration / abstain / critic / router** |

→ 现有 `ModelApplicabilityAgent`(规则路由)是 **MoE Router 的前身**;`ReliabilityAgent`(后处理 abstain)是
**Abstain Head 的前身**;`predictors/base.py` 接口是所有外部模型接入的契约。**升级而非重写。**

---

## 4. 模型栈总表:用别人的 vs 自研

| 模块 | 直接用别人 | 自研 | 优先级 |
|---|---|---|---|
| 单细胞 foundation | scGPT / Geneformer / scFoundation / CellFM / UCE | 仅 embedding adapter,不训 foundation | 高 |
| 细胞注释 | CellTypist / scVI / scANVI | confidence/OOD classifier | 高 |
| 基因扰动 | GEARS / CPA / scGen / STATE | **MoE router + abstain + 缺口 predictor V1** | **最高** |
| 药物扰动 | CPA / STATE / LINCS / DeepPurpose / ChemBERTa | drug-cell adapter | 中高 |
| GRN/TF | CellOracle / LINGER / SCENIC+ | GRN→expr correction | 中高 |
| 命运动态 | CellRank / RNA velocity | state-transition adapter | 中 |
| 代谢 | COBRApy / scFEA / MICOM | expr→flux calibrator | 中 |
| 通讯 | NicheNet / CellChat | sender–receiver model | 高(阶段 2) |
| 空间 | Tangram / cell2location / Squidpy | niche-aware response | 中高 |
| 跨物种 | UCE / SATURN / ortholog | applicability/abstain,不急训 predictor | 中 |
| 可靠性 | 几乎无 | **OOD/calibration/abstain(必自研)** | **最高** |
| agent 治理 | 无现成 virtual-cell agent OS | **PRAXIS Agent OS(必自研)** | **最高** |

---

## 5. 六个自研模块(优先级 + 契约 + 数据来源)

| # | 模块 | 输入 | 输出 | 训练数据来源 | 依赖 |
|---|---|---|---|---|---|
| 1 | **MoE Router** | species/celltype/pert 类型·target/seen-unseen/cell-state emb/foundation emb/brain rules/各 predictor 历史表现·不确定性·OOD 分数 | 各 predictor 权重 / abstain / 需更多输入 | Eval Ledger(各模型逐样本表现) | 阶段1 模型库 + Ledger |
| 2 | **OOD / Applicability Classifier** | 物种/celltype/pert 对象/训练集覆盖/gene-graph 覆盖/embedding 距离/模型分歧/历史失败 | in-domain / weakly-supported / OOD / must-abstain | Ledger + seen/unseen 标注(已有 OOD split) | 阶段1 |
| 3 | **Abstain Head** | 同 #2 + 预测置信 | accept / downgrade / abstain(给定 coverage 下最大化保留集性能) | Ledger(把 v0.2 的 risk-coverage 从后处理变训练目标) | #2 |
| 4 | **Delta Adapter** | model-specific 输出(GEARS/CPA/scGen latent shift/STATE/LINCS signature/CellOracle GRN/scFEA flux)+ cell context | 标准化 delta expression / pathway score / uncertainty / provenance | 各模型输出 + 同 ground-truth 校准 | 阶段1 模型库 |
| 5 | **Perturbation Predictor V1** | cell-state emb / pert emb / gene graph / pathway prior / foundation emb / brain features | delta expr / uncertainty / DE 置信 / pathway response | Norman + 后续数据(**先在 unseen-gene / low-data / 高 OOD / cross-celltype 局部赢,不求全面 SOTA**) | #1-#4 |
| 6 | **Sender–Receiver Propagation** | sender 细胞扰动 → ligand 改变 → receiver 状态 | receiver 表达/状态变化 | 通讯数据集 + NicheNet/CellChat 先验 | 阶段2 模型库(通讯) |

---

## 6. 四阶段路线图 + 里程碑闸门

> 每阶段一个**可验证里程碑(M)**,过闸才进下一阶段。每步落 finding + 单独 commit + 诚实标注。

### 阶段 1 —— 模型库 + Eval Ledger(给治理骨架"通电")
- 接入 **真 perturbation predictor**:`GEARSAgent` / `CPAAgent` / `scGenAgent`(套现有 `predictors/base.py` 接口,各自 env 桥接)。
- 建 **PRAXIS Eval Ledger**:统一记录每个 predictor-agent 逐样本 预测/不确定性/误差/分歧/OOD。
- 让 disagreement / core-predictor-failed / cell-type 降级 在**真模型上自发激活**(解 v0.2 声明式局限)。
- 真模型同协议进 **表 A**(解 R8)。
- **里程碑 M1**(也是最小可发表增量):真 predictor 库(≥3)+ Eval Ledger 跑通;在 Norman 上证明
  **现有规则 router + abstain 在真模型上端到端生效**(risk-coverage 在多真模型上的增益,而非单 cpa+aux)。

### 阶段 2 —— 自研治理模型(PRAXIS 的核心差异化)
- 用阶段 1 的 Ledger 训练:**OOD Classifier → Abstain Head → MoE Router → Delta Adapter**。
- **里程碑 M2**:learned router + trained abstain 在 Norman(+ 第二数据集)上**显著优于任何单模型、也优于固定 ensemble**(用 risk-coverage / selective-accuracy 指标);Delta Adapter 把异构输出统一。这是论文从"治理骨架"升级到"治理带来可测量端到端增益"的关键证据。

### 阶段 3 —— 缺口 Predictor V1
- 训练 **PRAXIS-Perturbation-Predictor V1**:不求全面打赢 STATE,**在 unseen-gene / low-data / 高 OOD / cross-celltype transfer 局部赢**。
- **里程碑 M3**:V1 在指定缺口区间 > 现有最佳;router 学会"在缺口区间选 V1、其余选现成"。

### 阶段 4 —— 多细胞 / 空间 / 通讯(虚拟组织)
- 接入 NicheNet/CellChat/Tangram/cell2location/Squidpy(analysis-agent);训练 **Sender–Receiver** + **Niche-aware** adapter。
- **里程碑 M4**:从"单细胞扰动预测"升级到"多细胞虚拟组织/微环境响应"的可演示闭环。

---

## 7. 最小可行里程碑 M1(建议从这里开刀)

**做什么**:把 GEARS / CPA / scGen 接成真 predictor-agent + Eval Ledger,让现有 router/abstain/critic 在真模型上跑通。
**为什么是它**:① 性价比最高(复用已建治理层)② 一举解掉 v0.2 两个最大局限(R8 + 声明式不激活)③ 是阶段 2 自研模型的数据前提 ④ 直接、干净、可验证、强化论文。
**验收**:≥3 真 predictor 同协议进表 A;Eval Ledger 落盘逐样本表现;disagreement/abstain 在真模型自发触发(非手搓);risk-coverage 在多真模型上复现正向增益。**全部实跑、诚实标注。**

---

## 8. 工程风险与对策

| 风险 | 对策 |
|---|---|
| 外部工具 env 地狱 | per-agent 独立 conda env + 远端 + 桥接(沿用 vc-scgpt 模式);跨 env 走 message/RPC |
| 摊大饼(10 层一起上) | 里程碑闸门:M1→M2→M3→M4 逐过;先证小闭环 |
| 自研模型无训练数据 | Eval Ledger 先行(阶段 1 隐藏关键产物) |
| 接入即声称"做了该功能" | 守 DNA:接入 ≠ 验证;每模型标 same-protocol/不可比、声明式/运行时、实跑/未做 |
| router/abstain 过拟合到 Norman | M2 要求第二数据集 + selective-accuracy 指标,跨数据验证 |
| 跨物种/代谢过早开坑 | 明确"先把 human 扰动 + 治理做强",跨物种维持 routing/abstain 原型(不训 predictor) |

---

## 9. 与论文的关系(每阶段如何升级 claim)

- **M1** → 论文从"治理骨架(mock 不激活)"升级为"治理层在真异构模型上运行,abstain/disagreement 真触发,R8 外部 baseline 补齐"。
- **M2** → 新增核心 claim:"learned routing + abstain 在真模型上带来可测量的 selective-prediction 增益,优于单模型与固定 ensemble"——这是从"系统论文"走向"有方法贡献"的关键。
- **M3/M4** → 扩展为"缺口 predictor + 虚拟组织",对应更大的 venue 野心。
- 全程:v0.2 的诚实/可复现/provenance 标准不降级。

---

## 10. 不做清单(明确边界)

1. **不自训大型单细胞 foundation model**(scGPT/Geneformer/scFoundation/CellFM/UCE)——只训 embedding adapter / OOD head。
2. **不重写成熟分析工具**(scVI/CellTypist/Tangram/cell2location/Squidpy/NicheNet/CellChat/COBRApy/MICOM/scFEA)——一律 agent 接入。
3. **不先做跨物种全能力 predictor**——跨物种维持 applicability/abstain 原型,先把 human 做强。

---

## 11. 版本与产物约定

- 当前 tag:**v0.2.0**(W8 里程碑)。本路线图覆盖 v0.3(M1–M2)→ v0.4(M3)→ v0.5+(M4)→ v1.0(完整 Cell-OS)。
- 新 agent 产物:`praxis_virtualcell/predictors/external/{gears,cpa,scgen}_agent.py`(阶段 1)、`praxis_virtualcell/governance/{router,ood,abstain,delta_adapter}.py`(阶段 2)。
- 评测账本:`praxis_virtualcell/benchmarks/eval_ledger.py` + 落盘 `docs/findings/finding_w9_*`。
- 每模块:TDD + 单独 commit + finding 诚实记录;外部模型接入标 env / 来源 / 同协议性。
