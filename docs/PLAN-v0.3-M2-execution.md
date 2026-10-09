# PRAXIS-VirtualCell v0.3 — M2 执行计划(Learned Reliability Model 之后)

> 生成 2026-06-28。承接 M2.1 Step1-2(已完成)。本文是 M2 剩余的细化、逐步闸门执行计划。
> 母路线图 docs/ROADMAP-v0.3-cell-os.md;M2 顺序由用户定:reliability/abstain → router → soft MoE → delta-adapter。

## 现状

| 已完成 | 结果 |
|---|---|
| M2.1 Step1 Ledger 审计 | `governance/ledger_features.py`:INFERENCE_FEATURES vs LABELS 编译期防泄漏 + pert-level split |
| M2.1 Step2 Learned Reliability Model | `governance/reliability_model.py`(纯 Python ridge):OOF corr 0.701;bad-pert AUROC **learned 0.907** > disagreement-only 0.774 > random 0.48 |
| 数据 | `docs/findings/m1_ledger_151.jsonl`(151 enriched:disagreement + per-predictor dp + OOD 标签) |

**核心已证**:PRAXIS 治理"可学习"且强于单信号规则。下面把它兑现成弃权/路由/整合能力。

## 执行顺序(逐步闸门,每模块出结果即暂停审)

### Step 3 — Learned Abstain head【下一个,最高价值】
- **目标**:把 reliability 预测变成 accept/abstain 决策 → risk-coverage,**把 v0.2 表 C 从规则升级为 learned**。
- **做法**:按 reliability model OOF 预测 dp 排序,弃权预测最差的 X% → 保留集 dp 随 coverage 的曲线 + AUC。
- **对照(必含)**:learned-reliability / disagreement-only(v0.2 用的)/ OOD-only / random / **oracle**(按真 dp 排,上界)。
- **验收**:learned risk-coverage AUC **> disagreement-only**(预期成立,因 bad-pert AUROC 0.907 > 0.774);全 OOF、pert-level、无泄漏。
- **环境**:Mac(用已有 OOF 预测,纯 Python)。产物 `governance/abstain_head.py` + finding。
- **诚实**:这是 **pert-level** risk-coverage(≠ v0.2 的 per-cell 表 C),互补不替代;标清。

### Step 3.5 — 特征增强【并行小步,提升杠杆】
- 远端 re-run activation,记录每 predictor 的 **prediction magnitude / uncertainty(std)** → 扩 INFERENCE_FEATURES。
- 重训 reliability/abstain,看 AUROC/risk-coverage 是否再升。**诚实**:加特征 ≠ 必升,据实报(可能持平)。

### Step 4 — Learned Router(predictor selection)
- **目标**:预测每扰动该用哪个 predictor(label = per_predictor dp 的 argmax)。
- **对照**:always-gnn / 固定 ensemble / disagreement-heuristic / learned / oracle。
- **指标**:**regret**(oracle_best_dp − chosen_dp)为主(非 top-1 acc)+ chosen-predictor mean dp。
- **验收**:learned regret < always-gnn。**诚实关键**:固定 ensemble 0.693 已近 oracle 0.7043(硬路由空间仅 +0.011),据实报 router 边际可能很小——若如此,router 主职归并到 abstain/加权,不强推。

### Step 5 — Soft MoE(weighted ensemble)
- prediction = Σ softmax(router logits)·predictor;对照 uniform / best-single / 固定 ensemble / hard-router / oracle-weighted。
- **验收**:≥ uniform/固定 ensemble 即有用;> 0.693 是好结果,> donor Coordinator(per-cell 0.7039,不可比)需另算。诚实标 pert-level。

### Step 6 — 整合回 runtime【分析 → 系统能力,关键】
- `ReliabilityAgent`:规则 → **可选** learned reliability/abstain(开关,默认规则保向后兼容);learned 路径 e2e 通讯流跑通 + 测试。
- **诚实**:标清声明式 vs 运行时;learned 模型作为 agent 的一个可插拔可靠性源。

### M2.4 — Delta-Adapter【最后,谨慎】
- 校准异构 predictor 输出 → 标准 delta。**易泄漏/过拟合**,等 ledger/split 更稳、特征更全再做。

## 诚实纪律(贯穿)
- 四坑:无泄漏(真 dp 只当 label)/ pert-level split / 轻模型 / 多 baseline 对照。
- **pert-level ≠ per-cell**(招牌 0.67/0.70 是 per-cell;ledger dp 是 pert-level);disagreement 仍**单 control(W4.5)**(可选支线:解 per-cell 后 disagreement 更准、下游可能整体升)。
- 小样本(151)单一确定性 5-fold(可加 bootstrap CI 增强说服力)。
- oracle/learned 分清;router 必 vs ensemble 不只 vs 单模型;数字实跑不臆造、先远端见证再入表/论文。

## 里程碑闸门
Reliability ✓ → **Abstain** → Router → soft MoE → Runtime 整合 → Delta-Adapter。每出可验证结果暂停让用户审,再过闸。

## 与论文(v0.3 新章雏形)
每个 learned 模块把 v0.2 的"规则治理"claim 升级为"**可学习治理,实证强于规则**":reliability AUROC 0.907 > 0.774、learned abstain risk-coverage > 规则。最终成 v0.3 论文新贡献(learned selective prediction / governance over heterogeneous predictors)——现有系统全无。
