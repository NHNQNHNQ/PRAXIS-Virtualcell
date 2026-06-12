# Week 4b 设计 — donor predictor 全迁移 + Coordinator 复现 + predictor agent 化

> 对齐用户提供的 GPT 战略计划 §6(Week 4 验收:同时要「复现 ~0.70」+「predictor-as-agent + trace/provenance」)。用户决策:**完整 Week 4b(M1 复现 + M2 agent 化)+ 含外部 GEARS/scGPT**。延续 Week 4a 的 donor_bridge 模式。

## 0. 目标
1. **M1(纯 ML 复现)**:迁 donor latent/gnn/decoder/cpa/**scGPT**(pretrained_backbone)+ 集成 donor Coordinator,复现 Norman ΔPearson **~0.70**。
2. **M2(predictor agent 化)**:把真 ML predictor 接入 Week 2 communicative 骨架(PredictorAgent + MessageBus + retrieve-before-predict + reliability/abstain + provenance/trace),端到端跑通。
3. **外部 GEARS**:audit-first 风险隔离,可迁则迁、否则诚实降级。

## 1. 现状(recon 实测)
- donor norman ckpt(8):latent_additive / gnn_pert / decoder_only / cpa_style / linear_additive / pretrained_backbone / tabular_transformer / mechanistic。
- 4 base(latent/gnn/decoder/cpa)+ pretrained_backbone 的 `predict(ctx, pert)` 接口与 linear **完全相同**(`ctx.control` + `pert.meta['pert_emb']` → `forward` → `Prediction.mean`)→ Week 4a `donor_bridge` 可直接泛化。
- 各 base anchor ΔPearson(Norman test, max_cells=200 / seed=1,**Task1 实测权威值**):**cpa 0.6716 / decoder 0.6709 / gnn 0.6675 / linear 0.6639 / latent 0.6365 / pretrained_backbone(mock backbone,非真 scGPT) 0.6183 / mechanistic 0.0**。(⚠ 早期 recon 的 latent 0.6922 / cpa 0.5673 等串行有误,见 finding_w4b_multi_anchor)
- Coordinator 组合:run_full_bench 用 latent+gnn,但实测 latent 偏弱 → **Task 3 实测 donor Coordinator 真值为准**,不预设 0.70。
- Coordinator API:`from agents.subagent import SubAgent, SubAgentSpec`;`SubAgentSpec(name, bench_id, predictor_name)` + `SubAgent(spec, predictor)`;`Coordinator(subagents, *, router, ensembler, in_features, calibrators, experience_query, default_bench_id)`,是 `Predictor` 子类(`predict` 接口),`EvalAgent.evaluate(coord, ds)`。
- **scGPT** 已集成在 donor `pretrained_backbone`(`BackboneAdapter`→`SCGPTAdapter`,ckpt `data/raw/pretrained/scgpt/`,norman anchor 0.6750)→ 走 donor_bridge,低风险。
- **GEARS**:donor norman **无 GEARS ckpt**;`vcell` 环境有 `cell-gears 0.0.2` + `scgpt 0.2.4` 包 + `gears_aux.yaml` manifest → 包可用但需 ckpt/训练 → audit-first(见 [[p2b_external_models_blocked]])。
- Week 2 communicative 骨架(`predictors/base.py::PredictorAgent`):`assess_applicability`(查 brain `model_applicability`)→ `prepare_input` → `run_prediction`(抽象)→ emit `PredictorResultMessage`(success/rejected/failed),带 retrieve-before-predict 门。`workflows/predict_delta_expression.py` 注册 mock predictor + ensemble/reliability/critic/provenance/report。
- **粒度 gap**:communicative 骨架是 schema 层(dict request),真 predictor 需 tensor(control + pert_emb)。M2 须在 `prepare_input` 做 schema→tensor 适配(只远端跑)。

## 2. 决策(ADR)
- **ADR-W4b-1 两线分工**:M1(`EvalAgent` per-cell 路线)管 benchmark 数值复现(0.70);M2(communicative per-request 路线)管「真多智能体 + 真模型」端到端可审计。**不强求 M2 复现 benchmark 数值**(粒度不同,见 [[w45_abstain_granularity]])。
- **ADR-W4b-2 donor_bridge 泛化**:不为每 predictor 写 bridge;`_cls` 注册多类,`build_predictor_from_ckpt`/`load_norman` 已通用;`MLPredictorAgent` 通用 `predict_tensor`(接口对所有 base 相同)。
- **ADR-W4b-3 外部分级**:scGPT 走 `pretrained_backbone` donor_bridge(已有 ckpt,低风险,并入 M1);GEARS audit-first 风险隔离(独立 task,可降级为携带项,不阻塞 M1/M2)。
- **ADR-W4b-4 复用 donor Coordinator**:M1 sys.path 注入复用 donor `SubAgent`/`Coordinator`,不在 praxis 重写 MoE/Ensembler(prototype-first)。
- **ADR-W4b-5 prototype-first**:本期迁 5 predictor + Coordinator + agent 化;mechanistic(0 分,drug 模型不适 gene pert)/tabular(可选)/cross-species/GEARS 训练留 Week 4c+。

## 3. 不变量 / 风险
- 只读复用 donor(不写 `Virtual cell/runs`);torch 只远端;Mac 零回归(remote skip)。
- 外部模型 audit-first,不硬凑(p2b 教训)。
- M2 粒度适配若受阻,如实记录;M1 数值结果独立成立。

## 4. 留后续(Week 4c+)
GEARS 训练(若 audit 降级)、mechanistic、tabular_transformer、cross-species brain(Week 5)、abstain/critic 强化(Week 6)、4 组 ablation(Week 7,GPT §9)。
