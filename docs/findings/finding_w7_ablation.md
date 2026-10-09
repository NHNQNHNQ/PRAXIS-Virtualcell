# Finding W7 — Norman benchmark + ablation(GPT §9, Workflow 对抗验证)

> Week 7:4 组 ablation。**design workflow 对抗验证(consistent=false)挡掉方法论站不住的 4 档**,采纳最小可发表方案:A(ML-only)↔D(Full)两极 × 4 个 Mac 确定性指标。`test_ablation_system` 4 PASS,全套零回归。

## A↔D 两极 ablation(Mac offline, 确定性, 实跑)
| arm | OOD_rejection | wrong_model_use | provenance_completeness | abstain_correctness | trace_completeness |
|---|---|---|---|---|---|
| A ML-only Coordinator | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| **D Full PRAXIS** | **1.0** | **0.0** | **1.0** | **1.0** | **1.0** |

→ §9.3 验收成立:Full 在 OOD rejection / wrong-model-use / provenance / abstain / trace 上**明显优于 ML-only**;Mac offline 全复现(§9.4)。

## design verdict 挡掉的方法论陷阱(consistent=false)
1. **B 纯纸面**(brain-guided 无 bus 无现成实现, 全指标推断)→ 砍, backlog。
2. **C≈D**(同 agent 栈, OOD/WMU/abstain 主指标相同, 仅 trace/critic 有别)→ 实为 2.5 档, 砍 C。
3. **§9.2 性能不损害是同义反复**(证"D 的 nn.Module 集合==A 的", message bus 零参与)+ **predictor 集合错配**(D 仅 3-predictor, A 招牌 0.7039 是 all-5, 不可比)→ 措辞改"communicative 包装对 predictor 前向零代价", 不声称 D 跑出更高 Pearson。
4. **abstain_gain 数值违反 manifest 制度**(CLAUDE.md 不变量 3, 仓库无 data/manifests)→ 标 PLANNED, 建 manifest 前不发表。
5. `retrieve_before_predict`(B/C/D 全 1)/`offline_reproducibility`(全 1)无 ablation 意义 → 移出对比表。

## 诚实边界
- A 用 Mac stub(无 bus/brain/species 检查)**忠实**模拟"无这些组件"(确实没有, 非假装)。
- 性能维度 communicative 层不参与张量计算;Pearson 由共享 predictor 经 EvalAgent 给出(A/D 3-set 对齐, 见 Week4b `coordinator_eval`)。
- `critic_violation_detection` 是 Critic 单元注入检出能力(D 独有 Critic), 非 e2e 自发。

## 留 backlog(verdict fixes)
- B(`build_runtime_brain_only`)/C(`_run_communicative`)真实现(若 reviewer 坚持 4 档)。
- `data/manifests/norman_2019.yaml` 声明 in-dist test + held-out OOD-pert split → abstain_gain 数值。
- `agent_adapter` single-control(ds[0].control)→ per-cell 全量(解 W4.5 失配)让 C/D 出独立 Pearson。
- 远端补一次"A 真硬预测"存在性验证(把 bacteria 喂 build_coordinator 观察不拒), 把 A 行为契约从读码推断升级为实测锚定。
