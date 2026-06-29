# PRAXIS-VirtualCell — 项目全景总结(供独立判断)

> 更新:2026-06-29 · git HEAD `a52d940`(已 push)· tag 见下 · 测试 Mac **93 passed + 25 skipped**
> 分层呈现:**真实见证 / 复现 donor / 声明式 / learned自研 / 诚实边界 / 未做**。刻意不替读者下结论。

## 0. 一句话定位
把"可信虚拟细胞扰动预测"重述为**控制流 / 治理问题**:别人有强 predictor 不重训、一律 agent 接入;
PRAXIS 自研**路由 / 可靠性 / 弃权 / 统一输出**。卖点不是更准,而是**拒绝 / 弃权 / 适用性 / 溯源 / 可审计 + 可学习治理**。
方向 iii-lite(LLM 可选增强,绝不进预测核心);主预测闭环离线可复现。

---

## 1. v0.1.0 — 通讯多智能体骨架(Week 1–7)
runtime / message bus / species brain / predictor-agent / abstain / critic / provenance + 可选 LLM agent。
核心数字(**远端见证为真**,见 §3):Coordinator Norman ΔPearson **0.7039** / 6 base 0.6716–0.6183 / scGPT frozen 0.4407 /
ablation A↔D 五指标 0→1 / cross-species 路由。

## 2. v0.2.0 — 论文 + 系统对比 + 诚信验证
- **论文 v0.2**(`docs/paper/v0.2/`):从头重写完整初稿,**22 引用全 CrossRef/官方核验**,四问四节,三表汇总。
- **三表**:A 准确性(+ mean-baseline 0.4615,scGPT 反垫底)· B 治理矩阵(5 系统全 ✗ vs PRAXIS 全 ✓)· C abstain_gain(manifest+risk-coverage 0.672→0.754,补 R9)。
- **诚信验证(关键)**:应"数据是否编造"之问,远端**当场重跑见证**全部准确性数字:linear 逐位 0.6638587、6 base diff 一致、Coordinator 0.703874、scGPT 逐位 0.4406901964584723、GEARS 重训 0.8461 同量级。**无任何编造**(`finding_w8_provenance_reverify`)。

## 3. v0.3 "Cell-OS"(进行中)——把治理从规则推进到可学习
路线图 `docs/ROADMAP-v0.3-cell-os.md`;M2 执行 `docs/PLAN-v0.3-M2-execution.md`。

### M1 — 给治理骨架"通电"
- **disagreement/abstain 在真 predictor 上自发激活**(解 v0.2 声明式局限):真 2000 维 delta → 分歧真值化(0.23–0.504,非 mock 伪 0.5)→ abstain 越线自发触发。
- **Eval Ledger**(`governance/ledger_features` 防泄漏审计);两强信号:**corr(disagreement, 准度)= −0.716**;**best predictor 因扰动而异**(gnn75/linear39/latent37)。

### M2 — 治理可学习(M2-lite,严守四坑:无泄漏/pert-level split/轻模型/多 baseline)
- **路由 oracle**:固定 ensemble 0.693 已近 oracle 0.7043 → 硬路由空间仅 +0.011 → **主力转 abstain/selective**(诚实发现,Router 降 backlog)。
- **Learned Reliability Model**(`governance/reliability_model`,纯 Python ridge):bad-pert **AUROC 0.907** > disagreement-only 0.774 > random;OOF dp 回归 corr 0.701。
- **Learned Abstain head**:risk-coverage **AUC 0.746** > disagreement-only 0.720(升级 v0.2 表 C 为 learned)。
- **特征增强 = 负结果**:加 magnitude/uncertainty 不升反微降 → 保持 base 3 特征(防过度工程)。
- **Step6 整合回 runtime(治理"运行时真的在用")**:
  - `ReliabilityAgent` 加 mode,默认 **learned_with_rule_fallback**;**硬规则(物种/空/全拒/core)恒 rule 权威**,learned 只接管 disagreement 软判定。
  - **冻结 artifact**(`governance/artifacts/`)+ **content_sha256 自校验**(篡改 weights/字段不全 → 主动 fallback)+ **artifact_sha256 写进 report**(每决策可追溯)+ fail-closed(缺失/schema 错 → rule)。
  - **rule vs learned 对照**:wrong_accept **0.974→0.211**、risk_coverage **0.026→0.789**、hard_rule_override **0**、provenance complete → 默认 learned **真改善软风险**且不破硬规则。
  - 7 gates 全过 + 篡改审计 + 对照,Mac 93 passed 零回归。

---

## 4. 诚实边界(持续,务必带进论文)
- **pert-level ≠ per-cell**:M2 全部数(~0.5–0.9 / AUROC / risk-cov)是**扰动级**,**不是**招牌 per-cell 0.67/0.70。
- **单 control(W4.5)**:disagreement 基于单一基线,非 per-cell 全量;解 W4.5 后下游可能整体升。
- **小样本**:ledger 151、单一确定性 5-fold、**无 bootstrap CI**(差距清晰但缺区间)。
- **learned 用 3 特征**;runtime `seen_in_train` 多为 None → 训练均值填(features_used 如实记),disagreement 主导。
- **阈值非端到端调优**(按训练分位);unnecessary_abstain 可随阈值调。
- **预测性能不赢 SOTA**(复现 donor + 套壳);强外部 baseline(GEARS 同 split/scGen/STATE)未做。
- mouse/bacteria/yeast 仅路由层原型(无真跨物种 predictor)。

## 5. 工程 / 状态
- Mac **93 passed + 25 skipped**;`origin/main = a52d940`,全部已 push。
- 远端 `zkyd@10.102.106.53`(8×A100;env virtualcell/vc-scgpt)复现准确性。
- 自研治理包 `praxis_virtualcell/governance/`(ledger_features / reliability_model / abstain_head / learned_reliability / freeze_artifacts / mode_compare + artifacts/)。

## 6. Backlog / 未做
- **v0.3 论文新 Result**(learned governance,PRAXIS 自己口径,**不碰 E9** code-gate 那条线)— **下一步**。
- Router(deferred:ensemble 近 oracle)· M2.4 Delta-Adapter(最后,易泄漏)· per-cell 解 W4.5 · 外部 predictor 进表 A · bootstrap CI · 真 cross-species predictor。
- 接更异构 predictor(STATE/GEARS/scGPT embedding)后重启 Router + 重测特征增强。

## 7. 供判断的问题
- 这篇论文的卖点完全押在**可信 / 可学习治理**(非预测 SOTA)——目标 venue 吃不吃?
- M2 是 pert-level 小样本结果,够不够强?(需 per-cell + CI 补强)
- "可学习治理 + 冻结 artifact + 可审计 provenance"是否构成足够新贡献?

## 8. 关键文件
- 论文:`docs/paper/v0.2/PRAXIS-VirtualCell-v0.2-manuscript.md` · `phase1_literature.md` · 图 `docs/paper/figures/`
- 路线/计划:`ROADMAP-v0.3-cell-os.md` · `PLAN-v0.3-M2-execution.md`
- findings:`finding_w8_*`(对比+诚信)· `finding_w9_m1_*`(通电+ledger)· `finding_w9_m2_*`(oracle/ensemble/reliability/abstain/特征/runtime整合/对照)
- 自研:`praxis_virtualcell/governance/*` + `artifacts/*.json`(冻结)· `data/manifests/norman_2019.yaml`
