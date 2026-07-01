# PRAXIS-VirtualCell 现有结果深度总结(v0.1→v0.3,投稿前证据盘点)

> 目的:把**当前已落地、已见证的全部结果**一次性深度汇总,并**明确指出"用来写完整 VirtualCell 主刊论文还缺什么"**——为 v0.4「代表物种 × 代表应用」补强计划提供依据(见 `docs/PLAN-v0.4-species-applications.md`)。
> 数字一律抄自已记录 finding,无手工臆造。口径红线严格分层。最后更新:2026-07-01,测试 Mac **105 passed + 25 skipped**,本地 HEAD 见 `git log -1`。
> 详版逐条盘点见 `docs/paper/v0.3/data-inventory.md`;本文件是**面向论文叙事的深度综合 + 缺口判断**。

---

## 0. 一句话定位与当前证据强度

PRAXIS-VirtualCell 把"可信虚拟细胞扰动预测"重述为**控制流 / 治理问题**:不重训 foundation model、强 predictor 一律 agent 接入;自研**路由 / 可靠性 / 弃权 / 统一输出 / 可审计溯源 + 可学习治理**。卖点不是更准,而是**拒绝 / 弃权 / 适用性判断 / 溯源 / 可审计 + 可学习治理**。

**当前证据可支撑的论断(强)**:
> PRAXIS 的治理层在 human Norman 扰动上被**定量验证有效**——可学习可靠性模型在留扰动泛化下 bad-pert AUROC 0.907、risk-coverage AUC 0.746,均显著优于规则基线,且配对优势的 95% CI 不跨 0、对 fold 划分稳健。

**当前证据尚**不能**支撑的论断(缺口,motivates v0.4)**:
> PRAXIS 是一个能跨代表物种、跨代表应用协调不同虚拟细胞任务的**通用智能体框架**。
> ——因为主结果仍集中在 human Norman single-cell perturbation;跨物种目前只有**路由层原型**(无真跨物种 predictor);应用维度只有 gene perturbation 一类。

---

## 1. 证据分层总览(强弱分级,全文务必不混)

| 标签 | 含义 | 强度 |
|---|---|---|
| `[远端见证·确定性]` | 远端 A100 当场重跑、逐位/容差复现 | 最硬 |
| `[远端实跑]` | 远端跑出、单次(确定性配方) | 硬 |
| `[Mac确定性]` | Mac 本地确定性可复跑 | 硬 |
| `[OOF泛化]` | 扰动级留出折交叉验证(泛化证据) | 中(小样本) |
| `[in-sample回放]` | 全量拟合模型在同批数据回放(**非**泛化) | 仅作行为/集成证据 |
| `[能力矩阵]` | 能力有/无(presence-absence),**非**性能 | 定性 |
| `[声明式]` | 单测证明机制可激活;mock e2e 不触发 | 弱(机制存在性) |

**三条口径红线**:
1. **per-cell(n=18874)≠ pert-level(ledger n=60/151)**:v0.2 招牌准确性是 per-cell;v0.3 M1/M2 全部 pert-level。
2. **OOF 泛化 ≠ in-sample 回放**:0.907/0.746 是 OOF;rule-vs-learned 对照表是 in-sample。
3. **learned 软治理 ≠ hard-rule 门控**:可学习层只动软判定,硬规则恒权威。

---

## 2. 主结果簇(按论文 Result 章节组织)

### R1 — 系统架构 / agent runtime(v0.1)
runtime / message bus / species brain / predictor-agent / abstain / critic / provenance + 可选 LLM agent。离线确定性可复现。证据:`[能力矩阵]` + `[Mac确定性]`。

### R2 — Human perturbation benchmark(表 A,v0.2 招牌)
口径:donor Norman test split · **per-cell ΔPearson** · 同 EvalAgent · n=18874。证据:`[远端见证·确定性]`。来源:`finding_w8_systems_comparison` + `finding_w8_provenance_reverify`。

| 系统 / 方法 | 类型 | ΔPearson | n |
|---|---|---|---|
| **PRAXIS Coordinator (all-5)** | ensemble + 治理 | **0.7039** | 18874 |
| 6 base predictor | 单 base | 0.6716–0.6183 | 18874 |
| **mean-perturbation** | naive 下界 | **0.4615** | 18874 |
| scGPT (frozen + 轻 head) | foundation | **0.4407** | 7290 |

- **诚实卖点**:scGPT frozen 0.4407 **反低于** mean-baseline 0.4615 →"规模非解药";PRAXIS **不声称赢 SOTA**。
- **off-axis 不入表**:GEARS 原生 `pearson_de` 0.8392(重训 0.8461 同量级)——不同指标/split,与 ΔPearson 不可比。
- **缺口**:表 A **无同协议外部专用 baseline**。→ **L4(GEARS 同 split donor-eval)正在补**(见 §5)。

### R3 — Learned reliability governance(v0.3 M1/M2.1,**最强新贡献**)
证据链完整闭环,每步有数、口径分层干净:

**(通电,M1)** 60 真扰动,disagreement 从 mock 伪 0.5 升级为真值连续分布(0.23–0.504),越阈值自发 abstain;**corr(disagreement, per-pert ΔPearson) = −0.716**(高分歧⇒低准度差~27点);best predictor 因扰动而异(gnn75/linear39/latent37,无单一处处最优)。证据:`[远端实跑]`。

**(泛化,M2.1 OOF)** 151 扰动 · pert-level · 留扰动 5-fold · 无泄漏:

| 指标 | learned | 规则基线 | random |
|---|---|---|---|
| bad-pert AUROC | **0.907** | disagreement 0.774 / ood 0.788 | 0.479 |
| risk-coverage AUC | **0.746** | disagreement 0.720 / ood 0.730 | 0.660 |
| 可靠性回归 OOF corr | **0.701** | — | — |

**(稳健,L1/B3)** 配对差 95% CI 不跨 0(AUROC +0.13 [0.056,0.191]、risk-cov +0.026 [0.014,0.041]);跨 5 seed learned AUROC 0.900±0.008、risk-cov 0.744±0.001。

**(负结果防过拟合)** 加 magnitude/uncertainty 特征不升反降 → 保持 base 3 特征。

**(OOD enrichment,L2)** learned-flagged 98% 是 OOD(odds ratio **74.7**),但**超越 OOD 标签**(OOD-only 子集 risk-cov 0.577>0.5、AUROC 0.907>ood-only 0.788)→ learned 不只是 OOD 代理。

**(接回 runtime,in-sample)** 默认 `learned_with_rule_fallback`;rule vs learned 对照:wrong_accept **0.974→0.211**、risk_coverage **0.026→0.789**、**hard_override=0**、provenance complete;冻结 artifact + content_sha256 自校验 + fail-closed + 逐决策可追溯。7 gates 全过 + 防泄漏审计。

### R(治理矩阵,表 B,v0.2)
7 项治理能力,GEARS/CPA/scGPT/scGen/STATE **全 ✗** vs PRAXIS **全 ✓**(presence-absence,逐项核查论文+repo)。证据:`[能力矩阵]`。

---

## 3. 诚信验证(防编造,已当场见证)
应"数据是否编造"之问,远端 A100 **当场重跑见证**全部准确性数字:linear 逐位 0.6638587、Coordinator 0.703874、scGPT 逐位 0.4406901964584723、GEARS 重训 0.8461 同量级。**无任何编造**(`finding_w8_provenance_reverify`)。

---

## 4. 诚实边界(务必带进论文)
- **pert-level ≠ per-cell**:M2 全部数(AUROC/risk-cov)是扰动级,**不是**招牌 per-cell 0.70。
- **单 control(W4.5)**:disagreement 基于单一基线,非 per-cell 全量。
- **小样本**:ledger 151;bootstrap CI/多 seed 已补,但单点 AUC 区间仍宽(AUROC 0.907 [0.846,0.952])→ 论文强调**配对优势**而非单点绝对值。
- **预测性能不赢 SOTA**:复现 donor + 套壳;强外部 baseline 同协议未做(L4 补 GEARS)。
- **跨物种仅路由层原型**:mouse/bacteria/yeast 无真跨物种 predictor。
- **应用维度单一**:目前只有 gene perturbation 一类。

---

## 5. 进行中 / 待补(直接决定论文竞争力)

### 🔄 L4 — GEARS 同 split donor-eval 入表 A(远端,进行中)
- **状态**:2026-07-01 远端 `zkyd@10.102.106.53` 已跑通 pipeline。防泄漏 custom split(train 137 / test 151 互斥),用 donor `EvalAgent` 算 **per-cell ΔPearson**(同表 A 口径,n=18874)。smoke(1 epoch)ΔPearson=0.424 验证端到端通;正式 **5 epoch**(对齐参考基线 hidden=64/5ep→pearson_de 0.8392)后台运行中。
- **待回填**:`GEARS 同协议 ΔPearson + n` → 入表 A(PRAXIS Coordinator 0.7039 旁)、写 finding、解"无同协议外部 baseline"。
- 脚本:`praxis_virtualcell/benchmarks/gears_donor_eval.py`(远端);runbook `docs/L4-gears-remote-runbook.md`。

### 缺口清单(v0.4 要解决的核心)
| 缺口 | 影响面 | 现状 |
|---|---|---|
| 外部专用 baseline 未入表 A | 高 | L4 进行中(GEARS);scGen/STATE 未做 |
| per-cell 解 W4.5 单 control | 中高 | 远端重跑,B2 待启 |
| **跨物种仅路由原型** | 中(scope 已声明) | **v0.4 补代表物种 case** |
| **应用维度单一(只 gene pert)** | **高(VirtualCell 广度)** | **v0.4 补代表应用 case** |

---

## 6. 结论:为什么"现在写论文还不够"

**够的部分**:作为「learned reliability governance」独立 Result / methods-track / 系统类会议,证据链完整、逻辑闭环——**基本够**。

**不够的部分(投完整 VirtualCell 主刊)**:
1. 准确性侧无同协议强外部对照(L4 补 GEARS 后缓解);
2. 主结果单物种(human)、单应用(gene perturbation)→ 审稿人易判定"只是 Norman benchmark + governance analysis";
3. "虚拟细胞"广度未体现(无 drug / state-fate / metabolism / communication;无 mouse/yeast/bacteria 真 case)。

**v0.4 补强目标**(详见 `docs/PLAN-v0.4-species-applications.md`):把论文从
`Norman prediction → governance → learned abstain`
升级为
`Core human benchmark → learned reliability governance → representative applications → cross-species agent routing prototype`

**最稳口径**(不过度承诺):
> PRAXIS-VirtualCell is first quantitatively validated on human perturbation prediction, then demonstrated across representative species and applications through **reliability-governed agent workflows**.
