# 续接提示词 —— PRAXIS-VirtualCell v0.1.0 之后

> 新对话直接粘贴下面整段即可继续。

---

继续 PRAXIS-virtualcell。**Ultracode 模式**(每个 substantive task 用 Workflow 多智能体编排 + 两层对抗验证)。用简体中文,简洁。

**项目**:PRAXIS-virtualcell,位于 `/Volumes/T7/PRAXIS-virtualcell`(push 到 `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git`)。PRAXIS-2 派生的大脑引导可通讯虚拟细胞多智能体系统,方向 **iii-lite**(LLM-assisted but not -dependent)。

**已完成并 push(`v0.1.0` tag)**:GPT 计划 Week 1–7 全部完成。详见 `docs/RELEASE-v0.1.0.md`。
- W2 communicative runtime / W3 LLM-assisted(DeepSeek)/ W4a-b ML 迁移(**Coordinator Norman ΔPearson 0.7039**)/ W4c GEARS(pearson_de 0.8392)+scGPT(0.4407 frozen)/ W5 cross-species brain(§7)/ W6 reliability-critic(§8)/ W7 ablation(A↔D 两极, §9)。
- **Mac 71 passed + 23 skipped**(ml 测试标 `remote`,Mac 无 torch 自动 skip;远端全 ml pass)。

**架构速览**:
- `praxis_virtualcell/`:`core`(request/message/bus/agent/runtime)、`agents`(input_interpreter/object_normalizer/species_brain/model_applicability/ensemble/reliability/critic/provenance_agent/report)、`agents_llm`(4 LLM agent)、`predictors`(mock_* + `ml/`{donor_bridge,agent_adapter,coordinator_bridge,ml_predictor_agent})、`brains/virtualcell/`{generic,human,mouse,bacteria,yeast}、`workflows`(predict_delta_expression{,_ml})、`benchmarks`(coordinator_eval/norman_eval/gears_norman/scgpt_train_eval/ablation)。
- 数据流:`run_request` → InputInterpreter → ObjectNormalizer → SpeciesBrain(brain_context) → ModelApplicability(applicable/rejected + `routing`{cautions/rejection_reasons/rules_hit}) → fan-out predict(retrieve-before-predict 门) → Ensemble(算 disagreement) → Reliability(abstain/降级) → Critic(7 检查) → Provenance → Report{abstain,reliability,prediction,models_used/rejected/failed,abstain_reasons,downgrade_reasons,caution_flags,model_disagreement,provenance}。

**远端**:`zkyd@10.102.106.53`(6×A100;conda init `source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh`)。env:`virtualcell`(torch 2.6+donor+GEARS/PyG)、`vc-scgpt`(torch 2.3+torchtext+scgpt)、`vcell`(donor 原 env)。donor 只读 `/home/zkyd/data1/mzy/Virtual cell`(**含空格,SSH 务必引号**);ckpt `runs/full_bench_20260521_060815/checkpoints/norman_2019`。

**下一步选项(GPT §10–§11)**:
1. **Week 8 v0.1 finalize**:CLI(`praxis-vc run --request examples/x.json --mode offline --output out/`)、README(架构/offline+llm_assisted/Norman bench/cross-species)、examples(norman/bacteria/mouse mock request)、package(pyproject)、输出目录(report+trace+provenance.json via `runtime.export_outputs`)。
2. **backlog**(见各 finding):B/C ablation 档真实现;`data/manifests/norman_2019.yaml` + abstain_gain 数值(CLAUDE.md 不变量3);`agent_adapter` single-control→per-cell(解 W4.5 失配)让 C/D 出独立 Pearson;scGPT fine-tune;GEARS 同表可比;OOD/calibration;真 cross-species ML predictor。
3. **论文主线(§11)**:四问(理解输入/真多智能体/保持性能/提高可靠性)。

**约定(Ultracode)**:
- 每 substantive task 用 Workflow 编排 + **两层对抗验证**(design workflow 查 consistent + implement review 实跑 dry-run);据 verdict must-fix 修。Workflow 子代理会直接落盘文件,主代理须审查 + 补未实现的运行时接线。
- 诚实标注**声明式 vs 运行时**(对抗验证反复防 over-claim:"机制存在 ≠ 运行时可激活";凡声明式机制须标注 mock 不激活 + 留手搓测试证明可激活)。
- 每 task TDD + 单独 commit;commit 前 `find praxis_virtualcell docs -name '._*' -delete`;pytest 退出码别用 `|tail` 吞(用 `>file 2>&1; RC=$?`)。
- commit message 末尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- 偏好靠重写(迁移破坏旧测试→重写到新事实,不 skip/xfail);prototype-first;`core/` freeze 不改;远端改码 Mac commit+push → 远端 `git pull`。

**先复核**:`cd /Volumes/T7/PRAXIS-virtualcell && git log --oneline -5 && git tag | tail -3 && .venv/bin/python -m pytest praxis_virtualcell/tests -q`(应 **71 passed + 23 skipped**)。然后按选 1/2/3 推进。
