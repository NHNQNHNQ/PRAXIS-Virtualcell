# PRAXIS-VirtualCell 分析结果总结(截至 2026-07-02)

> 本文件汇总本轮全部分析结果:核心 benchmark + 可学习治理 + 代表物种×应用 16 case(strict 15/15)+ 外部 baseline(GEARS/scGen/STATE)+ per-cell W4.5 + LLM 通讯架构。作为下一步**工程化计划**的单一参考。
> 状态:测试 Mac **203 passed + 25 skipped**;git `origin/main` 已含 v0.4+v0.5(3 个 G1/G2 commit 待 push);数字一律来自已记录 finding,无臆造。

---

## 0. 一句话定位

把"可信虚拟细胞扰动预测"重述为**控制流/治理问题**:不重训 foundation model,强 predictor 一律 agent 接入;自研**路由/可靠性/弃权/统一输出/可审计溯源 + 可学习治理**。卖点不是更准,而是**适用性判断 / 拒绝 / 弃权 / 降级 / 溯源 / 不过度承诺**。
最稳口径:
> first quantitatively validated on human perturbation prediction, then demonstrated across representative species and applications through **reliability-governed agent workflows**.

---

## 1. 核心 benchmark(表 A,human Norman,per-cell ΔPearson,n=18874)

| 系统 | ΔPearson | 证据 |
|---|---|---|
| **PRAXIS Coordinator (all-5)** | **0.7039** | 远端见证·逐位 |
| 6 donor base | 0.6716–0.6183 | 远端见证 |
| **GEARS (same-split, 5ep)** | **0.4877** | 远端实跑(L4) |
| mean-perturbation | 0.4615 | 远端 |
| scGPT (frozen) | 0.4407 | 逐位 |

- **同协议外部 baseline = GEARS 0.4877**(L4 本轮完成):GEARS 原生 `pearson_de 0.8392` 是 off-axis;拉到同协议 per-cell ΔPearson 只有 0.4877(低于所有 donor base)。**读法:指标/协议决定结论,PRAXIS ensemble+治理具竞争力**;非"赢 SOTA"标题。caveat:GEARS condition→cell broadcast。finding `finding_w9_l4_gears_same_split`。

## 2. 可学习治理(v0.3,最强新贡献)

- disagreement 通电:corr(disagreement, per-pert dp) = **−0.716**(60 扰动);越阈值自发 abstain。
- OOF 泛化(151 扰动,留扰动 5-fold,无泄漏):bad-pert **learned AUROC 0.907**、risk-coverage **AUC 0.746**(均 >> disagreement-only/random);reg corr 0.701。
- 稳健:配对差 95% CI 不跨 0;跨 5 seed AUROC 0.900±0.008。
- OOD enrichment:learned-flagged 98% OOD(OR 74.7)但超越 OOD 标签。
- 接回 runtime(in-sample):wrong_accept 0.974→0.211、risk_cov 0.026→0.789、hard_override=0、冻结 artifact + sha256 自校验 + fail-closed。
- 治理矩阵表 B:7 能力,GEARS/CPA/scGPT/scGen/STATE 全 ✗ vs PRAXIS 全 ✓。

## 3. 代表物种 × 应用:strict 15/15(16 case + L4)

**5 应用 × 4 物种全覆盖**;每个 case 真跑公开数据/工具 + 7 部分输出 + 受治理裁决(accept/caution/downgrade/abstain)。

| 应用 \ 物种 | Human | Mouse | Yeast | Bacteria |
|---|---|---|---|---|
| Gene perturbation | Norman 0.7039(C1)+OOD(C2) | ortholog caution(C3) | deletion growth(C5) | KO growth(C4) |
| Drug/chemical | drug MOA(C6)+dose(R2) | — | — | 碳源(S1)+antibiotic(R3) |
| State/fate | IFN 激活(S2)+EMT(R4) | 分化 fate(R1) | — | — |
| Metabolism/flux | 通路 tendency(S3) | — | yeast GEM(C5) | E.coli GEM(C4) |
| Communication/env | L-R(S4)+spatial(R5)+co-culture(R6) | — | — | — |

**各 case 关键实测数字 + 裁决:**

| case | 数据/工具 | 结果 | 裁决 |
|---|---|---|---|
| C1 human gene | donor Coordinator | ΔPearson 0.7039 | accept |
| C2 human OOD | learned reliability | AUROC 0.907 / OOD OR 74.7 | abstain 富集 OOD |
| C3 mouse ortholog | route_table | ortholog 投影 | caution/downgrade |
| C4 E.coli KO | cobra e_coli_core | WT 0.874;gltA/icd essential | accept;缺失→abstain |
| C5 yeast KO | cobra iMM904 | WT 0.288;ERG1 essential | accept |
| C6 drug MOA | LINCS L1000 签名 | HSP90 富集 2.6-3.5× | HSP90 accept;HDAC 弱 downgrade |
| S1 碳源切换 | cobra e_coli_core | glucose 0.874→acetate 0.173 | accept;未知碳源 caution |
| S2 免疫激活 | Kang 2018 IFN | ISG d=2.49;髓系>淋巴>巨核 | accept;巨核弱 |
| S3 代谢 tendency | Kang 2018 | 糖酵解/OXPHOS d=0.10/0.28 | **downgrade**(对照 S2 治理) |
| S4 L-R 通讯 | Kang 2018 | CXCL10→CXCR3 Mono→CD8T 51× | CD8T/NK accept;CD4T(CXCR3^low)downgrade |
| R1 分化 fate | scanpy paul15 | 红系 vs 髓系 d=4.32 | accept |
| R2 drug dose | LINCS 剂量 | geldanamycin Spearman 0.90 | accept;sirolimus 近零 downgrade |
| R3 antibiotic | cobra iML1515 | trimethoprim/sulfa 靶抑制致死 | accept;非代谢靶 abstain |
| R4 cancer EMT | pertpy mcfarland | 肉瘤 vs 上皮癌 d=1.72 | accept(状态刻画非诱导) |
| R5 spatial niche | squidpy imc | 间质邻接肿瘤 EMT d=0.74 | caution(中等 niche) |
| R6 co-culture | Kang 两步链 | Mono→CD8T 链完整 | accept;→巨核链断 downgrade |

**贯穿主线 = R6 治理防过度承诺(硬证据)**:同一 IFN 扰动 ISG accept 但代谢 downgrade;同一 CXCL10 对 CXCR3⁺ accept、CXCR3^low downgrade;抗生素代谢靶 accept、非代谢靶 abstain。**从不为"跑通"硬报**。

**架构可扩展性**:`GemModel`/`scoring.py`/`CaseReport`/route_table 引擎多 case 复用(换 SBML 即换物种;换 panel 即换程序);route 引擎:donor_predictor/gem_fba/embedding/state_scoring/pathway_scoring/communication/spatial_niche/reject。**全程不训练新模型**。

## 4. 外部 baseline + per-cell(本轮远端)

- **G2 per-cell 解 W4.5 ✅ 真跑完成**:disagreement 从单 control(`ds[0].control`)升级 per-cell(每 cell 自身 control,18874 cells)。坐实 per-cell control 确改变 delta。Mac 复算:learned AUROC 0.907→**0.869**、risk-cov 0.746→**0.736**、reg corr 0.701→0.646。**诚实发现:per-cell 让指标略降(单 control 略乐观),但治理结论稳健**(learned 仍 >> disagreement >> random;ood/oracle 对照不变验证正确)。finding `finding_g2_percell_w45`。
- **G1 scGen/STATE ⚠️ 诚实阻塞(未强跑)**:① scgen 2.1.0 ✗ scvi-tools 1.4.2(`scvi._compat` 移除),pin 旧 scvi 会降级 torch 破坏 donor;② scGen 是条件迁移模型,对 Norman 未见扰动 test 无法 leak-free 预测(不同于 GEARS pert-emb 泛化)→ 不是合适对照。STATE 更合适但重/新,建议独立 env 交互式设置。**GEARS 0.4877 已填同协议 baseline 缺口**;不产出泄漏/无意义数字。finding `finding_g1_scgen_state`;runbook `docs/G1-/G2-*-remote-runbook.md`。

## 5. LLM 通讯架构(回答"是否用大模型 token")

- **智能体通讯不用 LLM token**:agent 间是**确定性 message bus**(结构化 `AgentMessage`)。默认 `mode=OFFLINE`、`llm_enabled=False`。**全部 case/预测/治理/远端跑零 LLM token**。
- **LLM 仅可选增强层** `agents_llm/`(input_interpreter/router/critic/report),仅当 `mode=LLM_ASSISTED` + 有 key 才激活;模型 **`deepseek-chat`**(DeepSeek,OpenAI 兼容 `/chat/completions`,temp 0,max 1024,失败回退确定性)。定位:iii-lite,绝不进预测核心。
- **安全**:`.env` 有真实 DeepSeek key(已 gitignore、未 push);若曾外泄建议 rotate。

## 6. 诚实边界(务必带进论文)

- **pert-level ≠ per-cell**:治理指标(AUROC/risk-cov)是扰动级,非招牌 per-cell 0.70。
- **预测不赢 SOTA**:复现 donor + 套壳;GEARS 同协议 0.4877 已入表,scGen/STATE 未入(G1 阻塞)。
- **非 human/非 gene case 是"受治理演示"**:证明 agent 能识别适用性/路由/降级/弃权,**非**各领域完备预测;多为 marker/共表达/FBA **代理**,非实测通量/信号转导。
- **cell-state/EMT/niche 部分是状态刻画**(非扰动诱导转变,如 R4/R5 已标注)。
- 各 case 用公开数据**演示子集** + 设定默认阈值(写明依据,非调优)。

## 7. 工程状态

- 测试 **203 passed + 25 skipped**;所有新模块 TDD + ruff 干净(E501 中文长行按仓库惯例保留);**不训练任何模型**。
- 自研包:`governance/`(reliability/abstain/ledger/artifacts…)· `predictors/`(mechanistic GEM · embedding drug · state · spatial · communication · ml donor-bridge)· `agents/`(schema/route/case_report + bus 通讯)· `agents_llm/`(可选 DeepSeek)。
- 大数据全 gitignore,只提交 curated 子集 + provenance(URL+sha256):LINCS/iMM904/iML1515/Kang/paul15/mcfarland/imc。
- 远端 `zkyd@10.102.106.53`(A100,env virtualcell,torch 2.6+cu124)复现准确性 + 跑 L4/G2;免密 ssh 可直连。
- **待办**:3 个 G1/G2 commit 待 push;G1 scGen/STATE 若要补需独立 env(STATE 优先);Phase II 仍可扩(但 5×4 已全覆盖)。

## 8. 关键文件索引

- 主参考:本文件 · `docs/paper/v0.4/RESULTS-CONSOLIDATED.md` · `application-cases.md` · `docs/paper/v0.3/data-inventory.md`
- 计划:`docs/PLAN-v0.5-complete-remaining.md`(A 类 R1-R7 全勾 + B 类 G1/G2)
- 远端 runbook:`docs/L4-` / `G1-` / `G2-*-remote-runbook.md`
- findings:`finding_w9_l4_gears_same_split`(L4)· `finding_g2_percell_w45`(G2)· `finding_g1_scgen_state`(G1)· `finding_v0_4_*` / `finding_v0_5_*`(16 case)
- 治理核心:`praxis_virtualcell/governance/*` · route/schema/case `praxis_virtualcell/agents/{species_schema,route_table,case_report}.py`
