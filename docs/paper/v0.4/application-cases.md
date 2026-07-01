# PRAXIS-VirtualCell v0.4 — 代表物种 × 代表应用 case 矩阵 + Results outline

> 目的:把 v0.4 补强(代表物种 × 代表应用)汇总为**能力矩阵 + case 清单 + 论文 Results 结构**。
> 状态图例:✅ 真跑完成(有 finding)· ⏸ 接口就绪·停在数据门 · 🛑 待数据/远端 · ⬜ 未启动。
> 最后更新:2026-07-01。测试:Mac **144 passed + 25 skipped**。

## 1. 代表物种 × 应用 能力矩阵(roadmap;主文不填满,标状态)

| 应用 \ 物种 | Human | Mouse | Yeast | Bacteria |
|---|---|---|---|---|
| Gene perturbation | ✅ Norman CRISPR(C1,0.7039)+ OOD(C2) | ✅ ortholog caution(C3) | ✅ deletion growth(C5) | ✅ KO growth(C4) |
| Drug/chemical | ✅ drug MOA(C6)+ dose-response(R2) | — | — | ✅ 碳源切换(S1)+ antibiotic(R3) |
| State/fate | ✅ IFN 激活(S2)+ EMT(R4) | ✅ 分化 fate(R1,paul15) | — | — |
| Metabolism/flux | ✅ 通路 tendency(S3,治理对照) | — | ✅ yeast GEM(C5) | ✅ E. coli GEM(C4) |
| Communication/env | ✅ L-R 共表达(S4)+ 空间 niche(R5)+ co-culture(R6) | — | — | — |

> 5 应用 × 4 物种全覆盖;**16 个真跑 case + L4 baseline**;strict 15/15 达成(见 §2/§3)。

## 2. Phase I — 主文 6 核心 case(状态)

| Case | 应用 | 物种 | 状态 | 结果 / finding |
|---|---|---|---|---|
| C1 | Gene perturbation | Human | ✅ 已有 | Coordinator 0.7039(表 A);`finding_w8_systems_comparison` |
| C2 | Unseen/OOD perturbation | Human | ✅ 已有 | learned abstain AUROC 0.907 / OOD OR 74.7;`finding_w9_m2_ood_enrichment` |
| C3 | Mouse ortholog routing | Mouse | ✅ 完成 | donor_predictor + ortholog caution(降级);`finding_v0_4_species_routing` |
| C4 | E. coli KO growth | Bacteria | ✅ 完成 | WT 0.874;gltA/icd essential;`finding_v0_4_metabolism_cases` §1 |
| C5 | Yeast growth/flux | Yeast | ✅ 完成 | WT 0.288;ERG1(YGR175C)essential;`finding_v0_4_metabolism_cases` §4 |
| C6 | Drug response | Human | ✅ 完成 | HSP90 富集 2.6-3.5×→accept;HDAC 弱→downgrade;`finding_v0_4_drug_case` |

**外部同协议 baseline(表 A 增补)**:✅ L4 GEARS same-split ΔPearson **0.4877**(`finding_w9_l4_gears_same_split`)。

## 3. Phase II — supplement(自主用公开数据完成 10 个 case)

| Case | 应用 | 状态 | 结果 / finding |
|---|---|---|---|
| S1 E. coli 碳源切换 growth | Metabolism(环境) | ✅ | glucose 0.874→acetate 0.173;`finding_v0_4_metabolism_cases` §6b |
| S2 免疫激活 cell-state | State/fate | ✅ | IFN-β→ISG d=2.49 accept;髓系>淋巴>巨核;`finding_v0_4_cellstate_case` |
| S3 代谢通路 tendency | Metabolism | ✅ | 治理对照:ISG accept vs 代谢 downgrade;`finding_v0_4_metabolic_tendency` |
| S4 L-R 通讯 | Communication | ✅ | CXCL10→CXCR3 Mono→CD8T 51× accept;→CD4T downgrade;`finding_v0_4_communication` |
| R1 分化 fate | State/fate(3A) | ✅ | 红系 vs 髓系 d=4.32 accept(paul15);`finding_v0_5_fate_case` |
| R2 drug dose-response | Drug(dose) | ✅ | geldanamycin Spearman 0.90 accept;sirolimus downgrade;`finding_v0_4_drug_case` §6 |
| R3 antibiotic → growth | Drug(2C) | ✅ | trimethoprim/sulfa 靶抑制致死 accept;非代谢靶 abstain;`finding_v0_4_metabolism_cases` §7 |
| R4 cancer EMT state | State/fate(3C) | ✅ | 肉瘤 vs 上皮癌 d=1.72 accept(mcfarland);`finding_v0_5_emt_case` |
| R5 spatial niche | Communication(5B) | ✅ | 间质邻接肿瘤 EMT d=0.74 caution(imc);`finding_v0_5_spatial_case` |
| R6 co-culture 两步链 | Communication(5C) | ✅ | Mono→CD8T accept;→巨核 downgrade;`finding_v0_5_coculture_case` |

→ **strict 15/15 达成**:5 应用 × 3 例全部有真跑 case(共 16 case + L4 baseline)。物种:human/mouse/bacteria/yeast。

## 4. 论文 Results 结构(6 节;现有证据可支撑度)

| Result | 内容 | 证据状态 |
|---|---|---|
| R1 architecture | agent runtime / bus / 治理管线 | ✅ v0.1 |
| R2 human perturbation benchmark | 表 A 0.7039 / mean 0.4615 / scGPT 0.4407 / **GEARS same-split 0.4877** | ✅ 见证 |
| R3 learned reliability governance | −0.716 / AUROC 0.907 / risk-cov 0.746 / CI / OOD / runtime | ✅ v0.3 |
| R4 representative species routing | human/mouse/yeast/bacteria 路由 + applicability + reject/downgrade | ✅ C3/C4/C5 真跑(human/mouse/bacteria/yeast 全覆盖) |
| R5 representative application cases | 5 应用 × 3 例;主文展开 core case | ✅ **5 应用全落地**(gene/drug/state-fate/metabolism/communication);Phase I 6 core + Phase II 4 真跑 |
| R6 reliability-governed reporting prevents overclaiming | 各应用 accept/downgrade/abstain 总表 | ✅ 硬证据(下表:同扰动 accept vs downgrade) |

## 5. R6 收束总表(治理防过度承诺;已完成 case)

| Case | Raw model output | Baseline | Reliability decision | Boundary statement |
|---|---|---|---|---|
| C1 human gene | Coordinator ΔPearson 0.7039 | mean 0.4615 | accept | per-cell;donor 复现 |
| C2 human OOD | learned reliability score | disagreement-only | abstain 富集 OOD(OR 74.7) | pert-level;小样本 CI |
| C3 mouse gene | donor_predictor(ortholog 投影) | ungoverned=直接用 human predictor | **caution/downgrade**(ortholog_required) | 跨物种迁移不可当母种精度 |
| C4 E. coli KO | WT 0.874;gltA/icd essential | WT growth | accept(全基因在 GEM);缺失→abstain | FBA 相对量非绝对速率;核心代谢子集 |
| C5 yeast del | WT 0.288;ERG1 essential | WT growth | accept;缺失→caution | FBA 相对量;iMM904 有限覆盖 |
| C6 drug MOA | HSP90 富集 2.6-3.5×;HDAC 0.10 | 跨 MOA 均值 | HSP90 **accept**;HDAC/单例 **downgrade**;未知 **abstain** | LINCS bulk 方向级,非 per-cell;阈值默认 |
| S2 cell-state | IFN-β→ISG d=2.49 | ctrl 激活评分 | **accept**;巨核弱效应暴露 | marker 代理,非绝对通路活性 |
| S3 metabolic | 糖酵解/OXPHOS d=0.10/0.28 | ctrl 通路评分 | **downgrade**(对照 S2 accept) | 表达代理非真通量 |
| S4 communication | CXCL10→CXCR3 fold 51× | ctrl comm score | Mono→CD8T/NK **accept**;→CD4T **downgrade** | 共表达代理,非实测信号转导 |
| R1 分化 fate | 红系−髓系 d=4.32 | 两谱系对比 | **accept**;缺 marker→downgrade | lineage 相对量,非命运概率 |
| R2 drug dose | Spearman(dose,recall) | 剂量单调性 | geldanamycin **accept**;sirolimus **downgrade** | 签名层,非绝对剂量效应 |
| R3 antibiotic | 靶反应抑制 growth 0 | WT growth | **accept**(代谢靶);非代谢靶 **abstain** | 理想化抑制;仅代谢靶适用 |
| R4 cancer EMT | 肉瘤−上皮 d=1.72 | 癌类对比 | **accept** | 状态刻画,非诱导转变 |
| R5 spatial niche | 间质邻接 EMT d=0.74 | niche 对比 | **caution**(中等 niche 效应) | 空间共定位,非因果 |
| R6 co-culture | 两步链(通讯+receiver) | ctrl 链 | Mono→CD8T **accept**;→巨核 **downgrade** | 多步代理,非真 co-culture |
| L4 GEARS | same-split ΔPearson 0.4877 | Coordinator 0.7039 | — | condition→cell broadcast caveat |

## 6. 最稳口径(全文守住)

> PRAXIS-VirtualCell is **first quantitatively validated on human perturbation prediction**(表 A + 同协议 GEARS baseline),then **demonstrated across representative species and applications through reliability-governed agent workflows**——每个非 human case 的价值是**识别适用性 / 路由 / 降级 / 弃权**(治理有效),而非高性能预测。

## 7. 下一步(硬门,待用户)

- **strict 15/15 达成**:Phase I 6 core + Phase II 10 case(S1-S4 + R1-R6)全部真跑;**5 应用 × 3 例 × 4 物种全覆盖**;16 case + L4 baseline。
- **需远端 zkyd(硬门#5,仅剩)**:scGen/STATE 同协议入表 A(G1)· B2 per-cell 解 W4.5(G2)。
- 论文数据侧已充分:主 benchmark + 同协议外部 baseline + 可学习治理 + 5 应用 × 4 物种受治理 case。
