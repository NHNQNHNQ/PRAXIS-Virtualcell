# 续接提示词 —— 把 PRAXIS-VirtualCell v0.1.0 写成论文 + Nature 风格图

> 新对话直接粘贴下面整段即可开始写论文。用简体中文沟通,论文正文英文。

---

把 PRAXIS-VirtualCell **v0.1.0** 写成一篇 systems/methods 论文(方法/系统型),并用 Python 出 Nature 风格图。

**写论文用 `academic-research-skills`**(已装,repo `github.com/Imbad0202/academic-research-skills`):先 `/ars-plan`(Socratic 章节规划)→ `/ars-outline`(详细提纲+证据图)→ `/ars-full`(完整管线:研究→写→审→修→定稿),或直接 `academic-paper` skill full mode。**做图用 `nature-figure` skill(Python/matplotlib 后端)**,出版级 SVG/PDF/TIFF。

**项目**:`/Volumes/T7/PRAXIS-virtualcell`(已 push `v0.1.0` tag)。成果来源(**先读这些**):`docs/RELEASE-v0.1.0.md`(版本说明)、`docs/findings/finding_w4{a,b,c}_*.md`、`finding_w5_cross_species.md`、`finding_w6_reliability_critic.md`、`finding_w7_ablation.md`;代码 `praxis_virtualcell/`。

## 论文定位(一句话)
PRAXIS-VirtualCell is a brain-guided communicative agent operating system for virtual cell prediction: it parses virtual-cell tasks into structured biological requests, retrieves species-aware model-applicability and negative-transfer rules, coordinates heterogeneous predictor-agents through auditable message passing, and produces calibrated predictions with abstention and provenance — fully reproducible offline, with optional LLM agents for input interpretation / routing review / critique / reporting that never replace the predictive models.

## 论文主线(GPT §11 四问 = 四个 Results 小节)
1. **能理解虚拟细胞输入吗** — VirtualCellRequest schema / deterministic + LLM-assisted parser / object normalization / 不支持输入拒绝。
2. **是真多智能体吗** — MessageBus 唯一通讯通道 / 全量 trace 可 replay / predictor-agent 独立 rejection / retrieve-before-predict 门(critic 可检) / 无 Coordinator 直调捷径。
3. **保持预测性能吗** — Norman ΔPearson;communicative 包装**不损害**性能(等价性 atol 1e-6,见诚实边界)。
4. **提高可靠性吗** — ablation A↔D 两极:OOD rejection / wrong-model-use / negative-transfer / provenance / abstain / offline reproducibility。

## 关键结果数字(self-contained,可直接入表/图)
**Norman benchmark(donor ML predictor,远端 EvalAgent,per-cell ΔPearson)**:
- 单 base ΔPearson:cpa 0.6716 / decoder 0.6709 / gnn 0.6675 / linear 0.6639 / latent 0.6365 / pretrained(mock backbone) 0.6183。
- **Coordinator 复现 ~0.70**:all-5 **0.7039**;cpa+decoder+gnn 0.7020;latent+gnn 0.6847。
- scGPT(frozen backbone + 轻 head)0.4407 < base(foundation 非银弹,诚实记)。
- GEARS 原生 pearson_de 0.8392(**与 base 不可比**:指标=DE 基因 absolute pearson、split 不同)。

**cross-species 路由(§7,Mac offline 确定性)**:human=3 predictor applicable 无 caution / mouse=applicable+ortholog caution(真投影,未映射基因加 unmapped flag)/ bacteria=yeast=全拒→abstain(negative-transfer rule `mammalian_scrna_predictor_not_applicable`)/ martian=abstain 无假证据。

**ablation A(ML-only Coordinator)↔ D(Full PRAXIS)(§9,Mac offline 确定性,全复现)**:
| 指标 | A | D |
|---|---|---|
| OOD_rejection_rate | 0.0 | 1.0 |
| wrong_model_use_rate | 1.0 | 0.0 |
| provenance_completeness | 0.0 | 1.0 |
| abstain_correctness | 0.0 | 1.0 |
| trace_completeness | 0.0 | 1.0 |

**reliability/critic(§8)**:model disagreement(pairwise cosine)/ Critic 7 检查(retrieve-before-predict / rejected-in-ensemble / missing_provenance / missing_uncertainty / unsupported_species / abstain_inconsistent 等)/ report 拆 abstain_reasons vs downgrade_reasons。

**测试规模**:Mac 75 passed + 23 skipped(ml 测试标 remote,Mac 无 torch skip);远端全 ml pass。

## 诚实边界(必须写进 Limitations,**严禁 over-claim** —— 这是 PRAXIS 核心 + 全程对抗验证的精神)
- **性能维度 communicative 层不参与张量计算**:D 的 Pearson 由共享 predictor 经同一 EvalAgent 给出;ablation 性能 claim 仅"Full **不损害**性能",**非"更准"**。不可暗示 message-passing 架构跑出 0.70。
- **ablation 实为 2 档**:B(brain-guided 无 bus)纸面无实现、C(communicative 无 reliability)≈D(同 agent 栈),故只发 A↔D 两极。
- **声明式机制在 mock e2e 不激活**:model disagreement / core_predictor_failed / cell_type 降级 / 真 ortholog 投影在当前 mock 流不触发(已手搓测试证明可激活,真实激活待真 predictor)。
- **abstain_gain 数值未做**:需 `data/manifests/norman_2019.yaml` 声明 held-out OOD-pert split(CLAUDE.md manifest 制度),未声明前不报数值。
- scGPT frozen 局限 / GEARS 与 base 不可比 / cross-species 暂只 routing+rejection(无真高性能 mouse/bacteria/yeast predictor)。
- **最小可发表口径**(GPT §15):validates its first implementation on human single-cell perturbation prediction;mouse/bacteria/yeast 是 brain routing 原型,不声称全物种预测完成。

## 图清单(`nature-figure`,Python,出版级)
1. **Fig 1 系统架构/数据流**:10-agent 编排(request→InputInterpreter→Normalizer→SpeciesBrain→ModelApplicability→predictor-agents→Ensemble→Reliability→Critic→Provenance→Report),标注 MessageBus 通讯 + retrieve-before-predict 门 + abstain 分支。schematic(matplotlib 手绘框图或 SVG)。
2. **Fig 2 Norman 性能**:各 base ΔPearson + Coordinator 组合(latent+gnn / cpa+decoder+gnn / all-5)横向 bar,标 0.70 线。
3. **Fig 3 ablation A↔D 两极**:5 指标 grouped bar(A vs D),全 0↔1 对比(论文核心可靠性证据)。
4. **Fig 4 cross-species 路由矩阵**:4 species(行)× 3 predictor(列)heatmap,色=applicable/caution/reject;旁注 ortholog caution / negative-transfer rule。
5. **Fig 5 可靠性机制**(可选):model disagreement(pairwise cosine 示意)或 abstain 触发条件树 / provenance-trace completeness 对比。

## 论文结构建议
Title / Abstract(双语)/ Intro(虚拟细胞预测的可信缺口:ML-only 无拒绝/无溯源)/ Results(四问四节,Fig 1-4)/ Discussion(communicative 架构价值 + foundation model 不是银弹 + 对抗验证方法论)/ Methods(agent 契约 / brain schema / Norman bench / ablation 设计 / 等价性论证)/ Limitations(上面诚实边界)/ Data&Code availability(GitHub v0.1.0)。

## 工作约定
- 先 `/ars-plan` 或读 findings 厘清证据→`/ars-outline`→分节写;图与正文证据对齐(每图引对应 finding 数字)。
- 数字一律引 finding/RELEASE,不臆造;诚实边界逐条进 Limitations。
- 图:先问 "Python or R?"——本项目定 **Python**(nature-figure matplotlib);出 SVG+PDF,600dpi TIFF 备投稿。
- 论文与图产物放 `docs/paper/`;用简体中文与我沟通,论文正文英文。
