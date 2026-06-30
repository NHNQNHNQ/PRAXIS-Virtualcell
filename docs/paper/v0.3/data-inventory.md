# PRAXIS-VirtualCell 全量数据盘点(v0.2 + v0.3）——投稿证据充分性自评

> 目的：把**所有已落地的结果与数字**一次铺开，标注每条的**口径 / 证据类型 / 样本量 / 来源 finding / 见证状态**，外加**缺口清单**与**分场景"够不够"自评**，方便判断论文数据是否充分。
> 本盘点不下最终结论替你拍板；数字一律抄自已记录 finding，无手工臆造。最后更新对应 git HEAD `c784c89`，测试 Mac **93 passed + 25 skipped**。

## 0. 阅读约定

**证据类型（强弱分级）**

| 标签 | 含义 | 强度 |
|---|---|---|
| `[远端见证·确定性]` | 远端 A100 当场重跑、逐位或容差复现 | 最硬 |
| `[远端实跑]` | 远端跑出、单次（确定性配方） | 硬 |
| `[Mac确定性]` | Mac 本地确定性可复跑 | 硬 |
| `[OOF泛化]` | 扰动级留出折交叉验证（泛化证据） | 中（小样本、无 CI） |
| `[in-sample回放]` | 全量拟合模型在同一批数据上回放（**非**泛化） | 仅作集成/行为证据 |
| `[能力矩阵]` | 能力有/无（presence-absence），**非**性能 | 定性 |
| `[声明式]` | 单测证明机制可激活；mock e2e 不触发 | 弱（机制存在性） |

**口径红线（全文务必不混）**

- **per-cell（n=18874）≠ pert-level（ledger n=60/151）**：v0.2 招牌准确性是 per-cell；v0.3 M1/M2 全部是 pert-level。
- **OOF 泛化 ≠ in-sample 回放**：0.907/0.746 是 OOF；rule-vs-learned 对照表是 in-sample。
- **learned 软治理 ≠ hard-rule 门控**：可学习层只动软判定，硬规则恒权威。

---

## 1. v0.2 — 准确性（表 A）

口径：donor Norman test split · **per-cell ΔPearson** · 同 EvalAgent · n=18874（scGPT 除外）。证据：`[远端见证·确定性]`。来源：`finding_w8_systems_comparison`（表A）+ `finding_w8_provenance_reverify`（逐位见证）。

| 系统 / 方法 | 类型 | ΔPearson | n | 见证 |
|---|---|---|---|---|
| **PRAXIS Coordinator (all-5)** | ensemble + 治理层 | **0.7039** | 18874 | 0.703874 ✓ |
| PRAXIS Coordinator (cpa+decoder+gnn) | ensemble | 0.7020 | 18874 | 0.701951 ✓ |
| PRAXIS Coordinator (latent+gnn) | ensemble | 0.6847 | 18874 | 0.684678 ✓ |
| cpa_style | 单 base | 0.6716 | 18874 | ✓ |
| decoder_only | 单 base | 0.6709 | 18874 | ✓ |
| gnn_pert | 单 base | 0.6675 | 18874 | ✓ |
| linear_additive | 单 base | 0.6639 | 18874 | **逐位** 0.6638587363779742 ✓ |
| latent_additive | 单 base | 0.6365 | 18874 | ✓ |
| pretrained-mock | 单 base | 0.6183 | 18874 | ✓ |
| **mean-perturbation** | naive 下界 | **0.4615** | 18874 | 远端实跑 ✓ |
| scGPT (frozen backbone + 轻 head) | foundation | **0.4407** | 7290 | **逐位** 0.4406901964584723 ✓ |

- **off-axis 不入表**：GEARS 原生 pearson_de 0.8392（重训复现 0.8461，同量级）——absolute-expression DE-gene pearson、不同 split，与 ΔPearson 不可比。
- **诚实卖点**：scGPT frozen 0.4407 **反低于** mean-baseline 0.4615 → "规模非解药"；PRAXIS **不声称赢 SOTA**。
- **缺口**：表 A 无**同协议外部专用 baseline**（GEARS 同 split / scGen / STATE 均未入表）。

## 2. v0.2 — 治理能力矩阵（表 B）

证据：`[能力矩阵]`（presence-absence，子代理逐项核查 5 系统论文+repo，每格附依据）。来源：`finding_w8_systems_comparison`（S1）。

| 治理能力 | GEARS | CPA | scGPT | scGen | STATE | **PRAXIS** |
|---|---|---|---|---|---|---|
| 1. OOD/跨物种输入拒绝 | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 2. applicability 检查 | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 3. abstain（主动弃权） | ✗ | ✗ | ✗ | ✗ | ✗ | **✓**¹ |
| 4. provenance + replayable trace | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 5. 多异构模型可审计通讯（bus） | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 6. retrieve-before-predict 门 + critic | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 7. 离线确定性可复现 | 部分 | 部分 | 部分 | 部分 | 部分 | **✓** |

¹ abstain 主路径（物种/空 targets/全拒）运行时激活；**子触发**（模型分歧/核心失败/细胞类型降级）在 v0.2 是 `[声明式]`，mock e2e 不触发、单测证明可激活——此局限已被 v0.3 M1 解除（见 §6）。

## 3. v0.2 — 弃权价值 / risk-coverage（表 C）

口径：真 donor predictor（cpa primary + 4 base aux）· Norman test split · **per-cell ΔPearson** · 按 disagreement 弃权 · 满覆盖参考 = cpa 0.6716。证据：`[远端实跑]`。来源：`finding_w8_systems_comparison`（表C）。

| tau | coverage | 保留集 ΔPearson | gain（vs 满覆盖 0.6716） |
|---|---|---|---|
| 1.0 | 1.00 | 0.6716 | —（参考） |
| 0.4 | 0.96 | 0.6830 | +0.011 |
| 0.3 | 0.88 | 0.7071 | +0.036 |
| 0.25 | 0.82 | 0.7320 | +0.060 |
| 0.2 | 0.74 | 0.7536 | **+0.082** |

- **真实 OOD split**：test 151 扰动中 **82 未见**（13056 cells）/ 69 已见（5818 cells）；manifest `data/manifests/norman_2019.yaml`（h5ad sha256 记录）。
- 趋势单调正向稳健；阈值附近因 GPU 浮点有 ±0.01 run 间抖动，**只报趋势不报单点精确值**。
- **缺口**：弃权在整个 test split 上做，"弃权扰动是否富集 OOD（82 未见）"未单独验证。
- **注意**：此表 per-cell 口径，与 §7 的 M2 pert-level risk-coverage **互补不替代、不可直接比绝对值**。

## 4. v0.2 — 运行时贡献（A↔D 消融，五轴）

口径：同一组 mock predictor，A=ML-only stub / D=完整 PRAXIS；offline 确定性。证据：`[能力矩阵]`（presence-absence，A 臂结构性缺失 → 四轴 0 by construction）。来源：v0.2 manuscript §3.4 / `finding_w7_ablation`。

| 轴 | Arm A（ML-only） | Arm D（完整 PRAXIS） |
|---|---|---|
| OOD 拒绝率 | 0.0 | 1.0 |
| 错误模型使用率 | 1.0 | 0.0 |
| 溯源完整性 | 0.0 | 1.0 |
| 弃权正确性 | 0.0 | 1.0 |
| 轨迹完整性 | 0.0 | 1.0 |

**缺口**：两极对照（A 是 stub，四轴 0 by construction）；缺真预测器/中间臂的分级消融。

## 5. v0.2 — 诚信验证（防编造）

证据：`[远端见证·确定性]` + `[Mac确定性]`。来源：`finding_w8_provenance_reverify`。

| 数字族 | 见证方式 | 结果 |
|---|---|---|
| 6 base（0.6716…0.6183） | 远端重 eval（确定性） | linear 逐位、其余 diff 与 finding 一致 ✓ |
| Coordinator 0.7039/0.7020/0.6847 | 远端重 eval | all-5=0.703874，n=18874 ✓ |
| scGPT 0.4407 | 存档 ckpt 重 eval | 逐位 0.4406901964584723 ✓ |
| GEARS pearson_de 0.8392 | 重训（随机） | 0.8461 同量级，确认真实（off-axis） |
| A↔D 五轴 + cross-species | Mac 本地重跑 | 一致（75 passed）✓ |

→ **论文全部量化结果当场见证为真，未发现任何编造或对不上的数字。**

---

## 6. v0.3 M1 — 治理通电 + Eval Ledger

### 6.1 disagreement/abstain 真激活（解 v0.2 §2 表 B 的 `[声明式]` 局限）

口径：60 Norman 真扰动 · 真 donor predictor（linear/latent/gnn，2000 维真 delta）。证据：`[远端实跑]`。来源：`finding_w9_m1_activation`。

| 指标 | 值 |
|---|---|
| 扰动数 | 60（test split） |
| disagreement.score 分布 | min 0.23 / median 0.375 / **max 0.504** / mean 0.359 |
| n_models | 3（真 donor base 全参与） |
| 越阈值（>0.5）→ 自发 abstain | **1 个**（counts `{high:59, low:1}`） |

→ disagreement 从 mock 伪 0.5 升级为**真值连续分布**，越线 `ReliabilityAgent` **自发 abstain**（非手搓）。激活率低（1/60）因 3 个 donor base 较一致；接更异构 predictor 分歧会更大。

### 6.2 disagreement ↔ 准度（abstain 依据的逐样本验证）

口径：**pert-level** per-pert ΔPearson（mean 聚合，≠ per-cell）。证据：`[远端实跑]`。来源：`finding_w9_m1_ledger_enriched`。

| 指标 | 值 |
|---|---|
| **corr(disagreement, per-pert ΔPearson)** | **−0.716**（n=60，强负相关） |
| 高分歧半 平均 dp | 0.571（n=30） |
| 低分歧半 平均 dp | 0.841（n=30） |

→ 高分歧 ⇒ 低准度（差 ~27 点）；弃权/降级依据真实。

### 6.3 best predictor 因扰动而异（路由有真实信号）

口径：pert-level。来源：`finding_w9_m1_ledger_enriched` / `finding_w9_m2_router_oracle`。

- 151 扰动最准 predictor 分布：**gnn 75 / linear 39 / latent 37**（无单一处处最优）。
- 60 样本：gnn 28 / latent 20 / linear 12。

### 6.4 Eval Ledger（阶段2 训练数据）

- 结构骨架 + Mac TDD（`benchmarks/eval_ledger.py`，纯 Python）。来源：`finding_w9_m1_eval_ledger`。
- 落盘：`docs/findings/m1_ledger_151.jsonl`（151 enriched，无泄漏审计过）。

---

## 7. v0.3 M2.1 — 可学习治理（核心新数据）

按你定的**证据分层**分三块呈现：泛化（OOF）/ 运行时集成（in-sample）/ 安全溯源。

### 7.0 路由 oracle 决定性对照（解释为何主力转 abstain）

口径：151 扰动 · **pert-level ΔPearson**。证据：`[远端实跑]`。来源：`finding_w9_m2_router_oracle` / `finding_w9_m2_ensemble_compare`。

| 策略 | pert-level dp | 相对 |
|---|---|---|
| 固定 latent | 0.6360 | — |
| 固定 linear | 0.6639 | — |
| 最强单模型 gnn | 0.6702 | 基准 |
| **固定 ensemble（均 3 预测）** | **0.693** | +0.023 vs 单模型 |
| oracle router（每扰动选最准，**上界**） | 0.7043 | **仅 +0.011 vs ensemble** |

→ ensemble 已吃掉大部分路由收益，硬路由空间仅 +0.011 → **主力转 abstain/selective**（Router deferred）。

### 7A. 泛化证据（OOF/CV）——`[OOF泛化]`

口径：151 扰动 · pert-level · 留扰动 5-fold · OOF 预测 · 无泄漏（仅 INFERENCE_FEATURES）。

**(a) Reliability Model**（来源：`finding_w9_m2_reliability_model`）

| 任务 | 指标 | 值 |
|---|---|---|
| 可靠性回归 | OOF corr(预测dp, 真dp) | **0.701** |
| bad-pert 检测（bad=底25%，thr 0.455，38bad/113good） | **learned AUROC** | **0.907** |
| | ood-only AUROC | 0.788 |
| | disagreement-only AUROC | 0.774 |
| | random AUROC | 0.479 |

**(b) Abstain head / risk-coverage**（来源：`finding_w9_m2_abstain_head`）

| 排序信号 | risk-coverage AUC |
|---|---|
| oracle（真dp，上界） | 0.7822 |
| **learned（reliability OOF）** | **0.7460** |
| ood-only | 0.7297 |
| disagreement-only（v0.2 用的） | 0.7196 |
| random | 0.6595 |

保留集 dp @ coverage 1.0 / 0.8 / 0.6：oracle 0.657/0.772/0.842 · **learned 0.657/0.733/0.796** · disagreement 0.657/0.713/0.749（learned 在 cov 0.6 比规则 +0.047）。

**(c) 特征增强 = 负结果**（来源：`finding_w9_m2_feature_enrich`）

| 特征集 | reg_corr | bad-pert AUROC | risk-cov AUC |
|---|---|---|---|
| **base（3）** | **0.701** | **0.907** | **0.7460** |
| base + 6 原始（norm/std×3） | 0.686 | 0.891 | 0.7378 |
| base + 2 派生 | 0.699 | 0.905 | 0.7450 |

→ 加幅度/不确定性特征不升反降（原始）或持平（派生）→ **保持 base 3 特征**，防过拟合。disagreement 主导。

**(d) 稳健性:bootstrap CI + 多 seed**（L1/B3,来源：`finding_w9_m2_bootstrap_ci.md`）

| 指标 | point | 95% CI / 跨 seed |
|---|---|---|
| AUROC 配对差(learned − disagreement) | +0.1325 | **[0.056, 0.191]**（不跨 0） |
| risk-cov AUC 配对差(learned − disagreement) | +0.0264 | **[0.014, 0.041]**（不跨 0） |
| learned AUROC 单点 | 0.907 | [0.846, 0.952]（宽,小样本） |
| learned AUROC 跨 5 seed | — | 0.900 ± 0.008 [0.885, 0.907] |
| learned risk-cov AUC 跨 5 seed | — | 0.744 ± 0.001 |

→ 配对优势统计显著（CI 不跨 0）、对 fold 划分稳健；单点区间宽是 151 的真实代价 → 论文强调**配对优势**而非单点绝对值。

**(e) OOD enrichment**（L2,来源：`finding_w9_m2_ood_enrichment.md`）

| 指标 | 值 |
|---|---|
| learned-flagged 中 OOD 占比 / base rate | 0.981(51/52) / 0.543 |
| OOD enrichment odds ratio | **74.7** |
| OOD-only / seen-only 子集 risk-cov AUC | 0.577 / 0.861 |
| learned AUROC vs ood-only(支撑"非 OOD 代理") | 0.907 vs 0.788 |

→ learned 强烈富集 OOD,但**超越 OOD 标签**(OOD-only 子集内仍有选择性 0.577>0.5)。

### 7B. 运行时集成证据（in-sample 回放）——`[in-sample回放]`

口径：151 ledger · 冻结**全量拟合**模型在**同一批 151** 回放 → **非独立泛化**，仅证"接回系统后真改决策 + 保硬规则 + 全溯源"。来源：`finding_w9_m2_mode_compare` / `finding_w9_m2_runtime_integration`。

**(a) rule_only vs learned 对照**（n=151，bad 底25% thr 0.455，38bad/113good）

| Mode | wrong_accept ↓ | unnec_abstain ↓ | risk_coverage ↑ | retained_util ↑ | n_flagged | hard_override | provenance |
|---|---|---|---|---|---|---|---|
| rule_only | **0.974** | 0.018 | **0.026** | 0.982 | 3 | 0 | — |
| **learned_with_rule_fallback** | **0.211** | 0.195 | **0.789** | 0.805 | 52 | **0** | **complete** |

→ learned 抓回 79% 被规则放过的 bad；hard_override=0；溯源完整。**（in-sample，不当泛化基准。）**

**(b) 冻结 artifact + runtime e2e**（来源：`finding_w9_m2_runtime_integration`）

- 冻结：`reliability_model_v0_3.json`（标准化 ridge 权重 disagreement **−0.118** / seen **+0.136** / n_zero **0**；带训练 ledger sha256 `548c444f…` + n_train 151）、`abstain_head_v0_3.json`（abstain<0.448 / downgrade<0.549；risk_cov_auc 0.746）、`feature_schema_v0_3.json`。
- runtime e2e：默认 `learned_with_rule_fallback`，report 实测 score **0.717**、ver `reliability_v0.3.0`。
- **硬规则恒 rule 权威**：物种/空/全拒/core 由规则决定，learned 只接管软判定；单测 `test_hard_abstain_not_overridden_by_learned` 独立证明。

### 7C. 安全 / 溯源证据 ——`[Mac确定性]`

来源：`finding_w9_m2_runtime_integration` / `finding_w9_m2_ledger_audit`。7 gates 全过：

1. Mac 全过 · 2. learned mode 可运行 · 3. 无 artifact→fallback rule · 4. schema 不匹配→fallback · 5. label 进 runtime 特征→断言失败（**无泄漏**）· 6. report 含 learned 决策 · 7. risk-cov AUC 0.746 可从 ledger 复现 · + 硬 abstain 不被 learned 覆盖。

- **fail-closed**：artifact 缺失/schema 错/字段不全/weights 篡改（content_sha256 自校验）→ 自动回退 rule。
- **可追溯**：每个 learned 决策带 `artifact_sha256` + `abstain_artifact_sha256` + model_version + feature_schema_version + features_used + fallback。
- **防泄漏**：ledger_features 编译期断言 特征∩标签=∅；pert-level split 无 cell 泄漏。

---

## 8. 工程状态

- Mac **93 passed + 25 skipped**（`praxis_virtualcell/tests` 范围；全仓库另含 praxis2 父项目测试，非本项目）。
- 自研治理包 `praxis_virtualcell/governance/`：ledger_features / reliability_model / abstain_head / learned_reliability / freeze_artifacts / mode_compare + artifacts/。
- 数据：`docs/findings/m1_ledger_151.jsonl`、`m1_per_pert_dp.json`、`m1_pred_features.json`。
- git `origin/main = c784c89`，全部已 push；tag `v0.3.0-alpha.1`。

---

## 9. 缺口清单（决定"够不够"的关键短板）

| 缺口 | 影响面 | 严重度 | 现状 / 补法 |
|---|---|---|---|
| ~~151 小样本无 bootstrap CI~~ → **已补(L1)** | 0.907 / 0.746 / 对照表 加了 95% CI | ~~高~~ → 已解 | ✅ 配对差值 CI 不跨 0(AUROC +0.13[0.056,0.191]、risk-cov +0.026[0.014,0.041];wrong-accept 降/risk-cov 增 [0.59,0.92])。`finding_w9_m2_bootstrap_ci.md` |
| **外部专用 baseline 未入表 A** | 完整 VirtualCell 论文竞争力 | **高** | GEARS 同 split / scGen / STATE 同协议（较重，需远端适配/训练） |
| **per-cell 解 W4.5 单 control** | M1/M2 全 pert-level，disagreement 单基线 | 中高 | 解 W4.5 后 disagreement 更准、可能整体升；较重 |
| **mode_compare 为 in-sample** | R7 非独立泛化 | 中 | 已用 OOF（7A）作泛化兜底 + 写法上明确定性，**不算硬伤但须写清** |
| **阈值非端到端调优** | unnecessary_abstain 随阈值动 | 中 | 训练分位设定；可后续按运营反馈调 |
| ~~单一确定性 5-fold（无多 seed）~~ → **已补(B3)** | OOF 稳健性 | ~~中~~ → 已解 | ✅ 5 seed learned AUROC 0.900±0.008、risk-cov 0.744±0.001,每 seed 均 > disagreement。`finding_w9_m2_bootstrap_ci.md` 补充节 |
| **Router / Delta-Adapter 未做** | — | 低 | Router deferred（ensemble 近 oracle）；Delta-Adapter 暂缓（易泄漏） |
| **跨物种仅路由层原型** | mouse/bacteria/yeast | 低（已声明 scope） | 无真跨物种 predictor，已诚实标 scope |

---

## 10. "够不够"——分场景自评

> 以下是供你决策的评估，不替你拍板。卖点押在**可信/可学习治理**（非预测 SOTA）。

**A. 作为「learned reliability governance」独立 Result / short paper（即 `learned-governance.md`）**
- **证据链完整**：规则挡硬错 → 软风险需学（−0.716）→ OOF 泛化（AUROC 0.907 / AUC 0.746）→ 负结果防过拟合 → 冻结接 runtime → fail-closed + 可追溯 → in-sample 对照（0.974→0.211）。逻辑闭环、每步有数、口径分层干净。
- **主要短板**：151 无 CI。**补 bootstrap CI 后**，这条线对 **workshop / methods-track / 系统类会议** 已相当稳。
- **结论倾向**：**基本够**（补 CI 更稳）。

**B. 作为完整 VirtualCell 主刊论文（v0.2 正文 + v0.3 增补）**
- **强项**：治理矩阵（5 系统全✗ vs PRAXIS✓）+ 准确性诚信见证 + 可学习治理新贡献，差异化清晰。
- **硬缺口**：① 表 A 无同协议外部强 baseline（GEARS同split/scGen/STATE）；② per-cell 解 W4.5；③ CI。这三项不补，审稿人易质疑"准确性侧无强对照 + 小样本无区间"。
- **结论倾向**：作为**治理/可信方向**的主刊投稿，**核心贡献够新**，但**竞争力补强需 ①②③**；若定位纯方法/系统贡献、明确不比 SOTA，则门槛低很多。

**最省力的下一步（性价比排序）**：~~① bootstrap CI~~ ✅**已完成**（L1 CI + B3 多 seed + L2 OOD enrichment,均纯 Mac）→ ② GEARS 同 split 入表 A（解 B①，较重，**远端**）→ ③ per-cell 解 W4.5（最重，解 B②，**远端**）。剩余两项均需远端,见 `docs/PLAN-v0.3-limitations-completion.md` 的 🛑 步骤。
