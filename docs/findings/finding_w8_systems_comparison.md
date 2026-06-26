# Finding W8 — 与现有系统全面对比(计划见 docs/paper/v0.2/04_systems_comparison_plan.md)

> 三表:**A 准确性(same-protocol)/ B 治理能力矩阵 / C abstain_gain(risk-coverage)**。
> 本 finding 随 /loop 逐 S 项推进更新。**S1(治理能力矩阵)已完成**;S2–S5 待远端。

## 进度
- [x] **S1 治理能力矩阵(表 B)** — Mac+联网,据实核查 5 系统 repo+论文,每格附依据。
- [ ] S2 mean-perturbation baseline + 统一准确性表骨架(表 A) — 远端
- [ ] S4 manifest + OOD split + abstain_gain(表 C) — 远端
- [ ] S3 GEARS 适配 donor split+ΔPearson / scGen 接入 — 远端
- [ ] S5 STATE 接入 — 远端
- [ ] S6 汇总三表 → manuscript Results §3.3–3.4 + Related Work

---

## 表 B — 可信治理能力矩阵(S1 完成)

核查方法:3 个子代理并行读各系统**公开论文 + GitHub repo 实际内容**,逐项判定 ✓/✗/部分,
每格附论文章节或代码路径依据;**严格区分「主动治理机制」与「恰好失败/报错」、「uncertainty 输出」与「abstain 机制」**。

| 治理能力 | GEARS | CPA | scGPT | scGen | STATE | **PRAXIS** |
|---|---|---|---|---|---|---|
| 1. OOD/跨物种输入拒绝 | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 2. applicability 检查 | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 3. abstain(主动弃权) | ✗ | ✗ | ✗ | ✗ | ✗ | **✓**¹ |
| 4. provenance + replayable trace | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 5. 多异构模型可审计通讯(message bus) | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 6. retrieve-before-predict 门 + critic | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 7. 离线确定性可复现 | 部分 | 部分 | 部分 | 部分 | 部分 | **✓** |

### 各系统关键依据(✗ 也据实给出处)
**GEARS**(Roohani 2024;github snap-stanford/GEARS)
- 1/2:`pertdata.py::filter_pert_in_go()` 在**数据预处理阶段**静默过滤非 GO 扰动,非推理时拒绝;`get_pert_idx()` 对词表外基因引发索引错误而非优雅拒绝。
- 3:`model.py` uncertainty 分支输出 `(predictions, log_variance)`,弃权过滤在**用户侧**(tutorial 95th 百分位),模型本身无 abstain。
- 7:开源(`pip install cell-gears`)+ `prepare_split(seed=1)`,但 `model.py` 无 `torch.manual_seed`/确定性标志。

**CPA**(Lotfollahi 2023;github theislab/cpa, facebookresearch/CPA 已 2024-11 存档)
- 1:论文原话"CPA will fail if the test data are very different from the training data"——承认局限,非主动拒绝。
- 3:uncertainty = "到训练扰动集的最小距离"代理值,"cannot replace experimental validation";`_model.py` 无 abstain 逻辑。
- 7:开源 + GEO accession,但 `_model.py` 无全局 seed。

**scGPT**(Cui 2024;github bowang-lab/scGPT)
- 1/2:词表过滤把 OOV 基因静默 drop/映射 padding(教程"match 4399/5060 genes");预训练 `scGPT_human` 但代码不检查输入物种。
- 4:仅可选 wandb 实验日志,非预测级 provenance。6:scBank 向量检索是数据增强,非"预测前适用性门控"。
- 7:教程 `set_seed(42)`,但 tokenizer 过滤层无确定性文档。

**scGen**(Lotfollahi 2019;github theislab/scgen)
- 1:README 把"跨物种"当卖点,但 predict 完全不拒绝不支持物种。2:predict 仅校验"cell type 与 adata 参数互斥",无适用性检查。
- 3:仅返回 `predicted_cells`/`delta` 点估计,解码硬编码方差 `Normal(px,1)`,无弃权。
- 7:开源,但 predict 用无 seed 的 `np.random.choice()`,结果不保证逐次一致。

**STATE**(Adduri 2025 preprint;github ArcInstitute/state)
- 1/2:定位"跨情境泛化预测"(对任何情境都给预测,反而=无拒绝);基因词表自动 overlap 匹配,不匹配时"行为未定义而非显式拒绝";训练数据 167M **human** cells 但无物种拒绝。
- 3:GitHub 站内搜 `uncertainty OR abstain OR confidence OR seed` 返回 **0 files**;只输出预测表达量。
- 5/6:单体两模块(SE+ST)顺序 CLI 流水线,无 message bus/critic。
- 7:开源(CC BY-NC-SA)+ Singularity 容器,但 repo 无 seed/determinism 记录。
- Arc 自我定位:"帮助科学家探索更大组合可能性空间"的**实验前假设筛选辅助工具**,非可信部署治理系统。

### PRAXIS 列依据(v0.1.0 findings / 代码)
1. OOD/跨物种拒绝:[[finding_w5_cross_species]] bacteria/yeast 全拒→abstain(rule `mammalian_scrna_predictor_not_applicable`);`ModelApplicabilityAgent` + `generic.negative_transfer`。
2. applicability 检查:`ModelApplicabilityAgent` 读 `supported_species/modalities/tasks/reject_if/object_vocabulary.genes`(W5 字段语义,运行时)。
3. abstain:`ReliabilityAgent` — `species_not_supported`/`no_perturbation_specified`/`all_predictors_rejected`(W5/W6,运行时激活)。
4. provenance+trace:`ProvenanceAgent` + `MessageBus` 可重放 trace([[finding_w7_ablation]] 8/8 stage trace + 6/6 provenance 字段)。
5. 多异构模型可审计通讯:`MessageBus` 唯一通道(W2 runtime;W7 ablation A↔D trace_completeness 0→1)。
6. retrieve-before-predict 门 + critic:硬门 + `CriticAgent` 7 检查([[finding_w6_reliability_critic]])。
7. 离线确定性可复现:offline deterministic core;linear 逐位复现 diff 1.2e-8([[finding_w4a_norman_anchor]]);Mac 75 passed offline。

## 诚实边界(防 over-claim)
- **PRAXIS 的 ✓ 分两层**:第 1/2/4/5/6 项与 abstain 主路径(物种/空 targets/全拒)是**运行时激活**(W5 cross-species + W7 ablation 实测);abstain 的**子触发**(模型分歧/核心失败/细胞类型降级)是**声明式**,mock e2e 不激活、手搓测试证明可激活([[finding_w6_reliability_critic]])。¹ 标注于此。
- **第 7 项"部分" vs "✓"**:对手"部分"指开源+局部 seed 但无完整确定性保证;PRAXIS "✓"指预测核心 offline + linear 逐位复现 + 全套 offline 测试通过——这是不同层级,据实区分。
- 治理矩阵是**能力有/无**对比,不是性能对比;准确性对比见表 A(待 S2 起)。**PRAXIS 准确性不声称赢 SOTA**。
- 矩阵每格均有代码路径/论文出处依据,非印象;子代理核查 repo 实际内容,STATE 为 2025 新 preprint,信息以当前公开为准。

## 留待(表 A / 表 C)
S2 mean-perturbation baseline(满足 ≥3 baseline 不变量)→ 统一准确性表;S3 GEARS 同 split 适配解"不可比";
S4 `data/manifests/norman_2019.yaml` + OOD split → abstain_gain / risk-coverage 数值;S5 STATE 接入同协议;S6 汇总进 manuscript。
