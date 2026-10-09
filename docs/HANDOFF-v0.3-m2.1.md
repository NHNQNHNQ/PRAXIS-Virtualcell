# 续接提示词 —— PRAXIS-VirtualCell v0.3 M2.1 之后(写 learned-governance 论文 Result)

> 新对话直接粘贴下面整段。用简体中文沟通,论文正文英文。

---

继续 PRAXIS-virtualcell。项目 `/Volumes/T7/PRAXIS-virtualcell`(remote `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git`,`origin/main` 同步)。PRAXIS-2 派生的大脑引导可通讯虚拟细胞多智能体系统,方向 iii-lite。**先读 `docs/PROJECT-SUMMARY.md` 和 `docs/PLAN-v0.3-M2-execution.md` 摸清现状。**

## 已完成(本阶段)
- **v0.2.0**:论文 v0.2(22 引用全核验)+ 系统对比三表 + **全部准确性数字远端见证为真**(无编造,finding_w8_provenance_reverify)。
- **v0.3 M1**:disagreement/abstain 在真 predictor 自发激活(解 v0.2 声明式局限);Eval Ledger;corr(disagreement,准度)=**−0.716**;best predictor 因扰动而异。
- **v0.3 M2.1(治理可学习,已收口)**:Learned Reliability Model bad-pert **AUROC 0.907** > 规则 0.774;Learned Abstain risk-coverage **AUC 0.746** > 规则 0.720;特征增强=负结果(保持 base 3 特征);**Step6 整合回 runtime**(默认 learned_with_rule_fallback,硬规则恒 rule 权威,content_sha256 篡改→fallback,artifact_sha256 可追溯,fail-closed);**rule vs learned 对照** wrong_accept 0.974→0.211 / risk_cov 0.026→0.789 / hard_override 0 / provenance complete。Mac **93 passed + 25 skipped**。
- 自研治理包 `praxis_virtualcell/governance/`(ledger_features/reliability_model/abstain_head/learned_reliability/freeze_artifacts/mode_compare + artifacts/);数据 `docs/findings/m1_ledger_151.jsonl`。

## 下一步(主线):写 v0.3 论文新 Result —— learned reliability governance
**用 PRAXIS-VirtualCell 自己的口径,不碰 E9**(E9 / code-gate vs prompt-gate 是另一条 LLM-agent 治理线,不属本项目;最多在 Discussion 轻提一句"可推广但本研究未评估")。落点建议 **B:单独 `docs/paper/v0.3/learned-governance.md` 独立成章**(不动已核验的 v0.2;A=追加进 v0.2 manuscript 亦可,听用户)。逻辑 8 步:
1. 规则治理挡硬错误(物种不适用/空结果/全拒/core)。2. 但软风险(predictor disagreement / 扰动级不确定性 / 该不该 downgrade/abstain)不能只靠规则。
3. 训练 reliability model 学软风险:**AUROC 0.907 / 回归 corr 0.701**。4. **abstain risk-coverage AUC 0.746 > 规则 0.720**。5. Step3.5 特征增强**负结果**(不并入,防泄漏/过拟合)。
6. 冻结 artifact 接入 runtime,默认 learned_with_rule_fallback。7. 缺失/schema 错/字段不全/weights 篡改 → fallback;report 带 **artifact_sha256** 可追溯。8. **rule vs learned 对照**(wrong_accept 0.974→0.211 等)证明默认模式真有价值、不破硬规则。
**诚实边界必带**:pert-level≠per-cell、单 control(W4.5)、151 小样本无 CI、learned 用 3 特征、runtime seen_in_train 多 None 用均值填、阈值非端到端调优。数字一律引 finding,不臆造。

## Backlog(主线之后或并行,低优先)
- per-cell 解 W4.5(单 control→全量)让 disagreement 更准 · bootstrap CI 补强 · 外部 predictor(GEARS 同 split/scGen/STATE)进表 A(解 R8)· Router(deferred,接更异构 predictor 后再启)· M2.4 Delta-Adapter(最后,易泄漏,暂不做)。

## 约定
- 远端 `zkyd@10.102.106.53`(conda virtualcell/vc-scgpt;先 git pull;donor 只读 `/home/zkyd/data1/mzy/'Virtual cell'` 含空格须引号)。Mac commit+push→远端 pull。
- 铁律:数字实跑不臆造、先远端见证再入表/论文;无泄漏(真 dp 只当 label,过 governance/ledger_features);pert-level≠per-cell 不混;oracle/learned 分清;硬规则不被 learned 覆盖;诚实标声明式 vs 运行时。
- 每 task TDD + 单独 commit(末尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`);commit 前 `find docs praxis_virtualcell -name '._*' -delete`;每个自研模块/章节出可验证结果即暂停让用户审。
- **不重训 foundation model、不重写成熟工具、不先做跨物种 predictor、暂不做 Delta-Adapter、不把 E9 写进本论文。**

## 先复核
`cd /Volumes/T7/PRAXIS-virtualcell && git log --oneline -5 && .venv/bin/python -m pytest praxis_virtualcell/tests -q`(应 93 passed + 25 skipped)。然后按主线写论文 Result,或按 backlog 推进。
