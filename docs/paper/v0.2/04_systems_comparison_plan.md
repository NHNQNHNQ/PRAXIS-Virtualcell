# 04 · PRAXIS-VirtualCell 与现有系统「全面对比」计划

> 动机:这是论文当前**最大的硬缺口**,也是审稿对抗暴露的两条 MAJOR(02_review R8 无外部 same-protocol
> baseline / R9 无 manifest+abstain_gain),同时违反项目自身的「≥3 baseline」不变量。把 PRAXIS 与现有
> 虚拟细胞扰动预测系统在**统一协议**下对比,既补这个缺口,又把 PRAXIS 的真正差异化(可信治理层)用
> 一张能力矩阵讲清楚。**诚实主线**:PRAXIS 卖点不是「更准」(通讯层不算张量),而是「在不损害准确性的
> 前提下,提供现有系统普遍缺失的拒绝/弃权/适用性/溯源/审计」。对比要据实,准确性上不声称赢 SOTA。

## 1. 对比对象

| 系统 | 类型 | 当前状态 | 准确性可比性 |
|---|---|---|---|
| **PRAXIS Coordinator**(all-5 / cpa+decoder+gnn) | ensemble + 治理层 | 已有 0.7039 / 0.7020 | 基准(donor norman split, ΔPearson, n=18874) |
| donor 6 base(cpa/decoder/gnn/linear/latent/pretrained-mock) | 单模型 | 已有 0.6716–0.6183 | 同协议可比 |
| **scGPT**(frozen backbone + head) | foundation model | 已有 0.4407 | **同协议可比**(同 split 同 metric) |
| **GEARS** | task-specific GNN | 原生 0.8392 **不可比** | 需适配 donor split + ΔPearson 才可比 |
| **CPA** | 生成模型 | donor 版已在 6 base(0.6716) | 可比;原版 CPA 另算 |
| **scGen** | 生成模型 | 未接入 | 需接入 |
| **STATE**(Arc Institute, 2025 SOTA) | perturbation foundation model | **未接入**(最新最强对比) | 需接入,工作量大 |
| **mean-perturbation** | naive baseline | 未实现 | 必做(满足 ≥3 baseline 不变量) |

## 2. 三类对比维度

### A. 预测准确性 —— 统一协议(same-protocol,补 R8)
**唯一可比口径**:donor `load_vcbench_split("norman_2019","test",max_cells_per_pert=200,rng_seed=1)` +
per-cell ΔPearson + 同一 EvalAgent。**只有同 split 同 metric 才进此表**(GEARS 原生 0.8392 是 DE 基因
absolute pearson、不同 split,绝不混入)。
- 把 GEARS / scGen / STATE / 原版 CPA 适配到该 split+metric;
- 加 mean-perturbation naive baseline;
- 产出统一准确性表。**诚实**:PRAXIS Coordinator 0.7039 是 ensemble 复现,不声称 > STATE/GEARS。

### B. 可信治理能力矩阵 —— PRAXIS 的真正差异化(现有系统普遍缺失)
逐系统**用代码/论文证据**核查(不需 GPU,Mac + 联网即可):
| 能力 | GEARS | CPA | scGPT | scGen | STATE | **PRAXIS** |
|---|---|---|---|---|---|---|
| OOD / 跨物种拒绝 | ? | ? | ? | ? | ? | ✓(W5) |
| applicability 检查(物种/模态/扰动类型/词表) | ? | ? | ? | ? | ? | ✓ |
| abstain(可靠性不足主动弃权) | ? | ? | ? | ? | ? | ✓ |
| provenance + replayable trace | ? | ? | ? | ? | ? | ✓ |
| 多异构模型可审计通讯(message bus) | ? | ? | ? | ? | ? | ✓ |
| retrieve-before-predict 门 + critic | ? | ? | ? | ? | ? | ✓ |
| 离线确定性可复现 | 部分 | 部分 | 部分 | ? | ? | ✓ |
> `?` 需逐个核实:读各系统论文 + 公开 repo,据实填 ✓/✗/部分,**每格附依据**(论文章节或代码路径)。
> 这张表是 PRAXIS 最有力、最诚实的卖点 —— 预测模型们各自缺这一层。

### C. abstain_gain / risk–coverage —— 治理价值的定量证据(补 R9)
- 建 `data/manifests/norman_2019.yaml`:声明 in-distribution test + **held-out OOD-perturbation split**
  (DOI+sha256,遵 CLAUDE.md manifest 制度);
- 在 OOD split 上跑 risk–coverage:PRAXIS abstain(覆盖率<100%)的 error vs 强行全预测(coverage=100%)的 error;
- 产出 abstain_gain 数值 + risk–coverage 曲线。**这是论文目前唯一「PLANNED 未做」的定量项**。

## 3. 执行阶段(标注 Mac / 远端 + 优先级)

| # | 阶段 | 环境 | 依赖 | 优先级 |
|---|---|---|---|---|
| S1 | 治理能力矩阵(B):逐系统读论文+repo 据实填,每格附依据 | Mac+联网 | 无 | **高**(零 GPU,直接出强结果) |
| S2 | mean-perturbation baseline + 统一准确性表骨架(A) | 远端 | donor split | **高**(满足 ≥3 baseline) |
| S3 | GEARS 适配 donor split+ΔPearson(解「不可比」)+ scGen 接入 | 远端 | S2 协议 | 中 |
| S4 | manifest + OOD split + abstain_gain / risk–coverage(C) | 远端 | manifest | **高**(补 R9,治理定量证据) |
| S5 | STATE 接入(最新 SOTA,跨 env 适配) | 远端 | S2 协议 | 中(工作量最大) |
| S6 | 汇总三表 → 进 manuscript(Results §3.3 + Related Work + 新 finding) | Mac | S1–S5 | 收口 |

> S1 优先:不依赖 GPU、直接产出 PRAXIS 最有力的差异化证据。S2/S4 次之(补两条 MAJOR 缺口)。
> S5(STATE)价值高但工程量大,可最后做或单独立项。

## 4. 诚实边界(写进计划,严防 over-claim)
- **准确性不声称赢**:PRAXIS Coordinator 是 ensemble 复现 + wrapper,通讯层不算张量;STATE/GEARS 同协议下可能更准,据实报。
- **same-protocol 铁律**:跨 metric/split 的数字(如 GEARS 原生 0.8392)永不与 ΔPearson 同表。
- **治理矩阵每格要有依据**:✓/✗ 必须指向论文章节或代码,不靠印象。
- **abstain_gain 需真 OOD split**:无 manifest 前不报数值(沿用 W7 诚实标注)。
- **STATE 是 preprint**:对比时标注 preprint 状态 + 复现条件。

## 5. 产出
- `docs/findings/finding_w8_systems_comparison.md`(三表 + 依据 + 诚实边界);
- 统一准确性表 → manuscript Results §3.3「保持性能」;
- 治理能力矩阵 → manuscript Related Work / Results §3.4 + 新增对比图(Fig 6 候选);
- abstain_gain 数值 → 补 Limitations 里「PLANNED」那条,升级为实测;
- `data/manifests/norman_2019.yaml`(顺带解决 R9 + manifest 不变量)。

## 6. 风险
| 风险 | 对策 |
|---|---|
| STATE 接入跨 env/工程量大 | 设为 S5 可选;先用 S1 治理矩阵 + S2/S4 拿主要价值 |
| GEARS 适配 donor split 仍踩老包坑(W4c 6 轮) | 复用 W4c 已破解的 monkey-patch + donor h5ad 路径 |
| 准确性表显示 PRAXIS 非最强 | 这是诚实预期;用治理矩阵承载差异化,不在准确性轴上硬比 |
| 远端 GPU 排队/掉线 | /loop 自我调速等待;每阶段独立 commit 防丢 |
