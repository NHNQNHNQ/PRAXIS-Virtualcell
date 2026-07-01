# PLAN v0.4 — 代表物种 × 代表应用 系统验证(把"治理机制验证"升级为"通用虚拟细胞智能体")

> 目的:在不重训任何 foundation model 的前提下,补一组 **代表物种 × 代表应用 × 每类 3 例** 的系统验证,把论文从"单 benchmark + governance"升级为"reliability-governed agent framework across representative systems"。
> **进度以本文件勾选框为准**(loop 每次重读本文件找第一个未勾选 `- [ ]` 步骤);每步完成把 `- [ ]` 改 `- [x]` 并回填 finding 路径。
> 现状依据:`docs/paper/v0.4/RESULTS-CONSOLIDATED.md`(现有结果 + 缺口)。测试基线:Mac **105 passed + 25 skipped**。

## 核心定位(不过度承诺)

最稳口径,全文守住:
> PRAXIS-VirtualCell is **first quantitatively validated on human perturbation prediction**, then **demonstrated across representative species and applications through reliability-governed agent workflows**.

论文结构升级:
`Core human benchmark → learned reliability governance → representative applications → cross-species agent routing prototype`

**不声称**"从细菌到哺乳动物全能力预测";每个非 human case 的价值是**证明 agent 能识别适用性 / 路由 / 降级 / 弃权**,而非高性能预测。

---

## 总原则(铁律,每步必守)

- **诚实优先于炫技**:每个 case 必须有**真实分析输出**(真跑工具/模型,非流程演示 mock);拿不到真数据/工具就**如实停下标注**,不臆造结果。
- **不过度解释**:非 human case 若预测不可靠,正确输出是 **downgrade / abstain + boundary statement**,这本身就是卖点(治理有效),**不是失败**。
- **无泄漏**;**per-cell ≠ pert-level 不混**;**OOF/泛化 与 in-sample 回放 分清**;**硬规则不被 learned 覆盖**。
- **不训练新模型**:不做 new foundation model / Delta-Adapter / cross-species predictor / Router(用户明确)。只**接入现成工具/模型 + 形成 case analysis + 让 ReliabilityAgent 管住结论**。
- 每步 **TDD**(先写失败测试)+ **本地单独 commit**(末尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`);commit 前 `find docs praxis_virtualcell -name '._*' -delete`。
- 自研模块/case 出可验证结果 → 在本文件勾选 + 简短汇报。

## 四类步骤处理方针(按工具/数据可得性分级)

| 类 | 定义 | loop 处理 |
|---|---|---|
| **M 类(Mac 可做)** | 纯 Python schema / routing table / applicability rules / mock-to-real 单测 | **现在自驱做**(loop 主战场) |
| **T 类(需装工具)** | 需 pip 装现成工具(cobrapy 等),模型/数据随包自带或轻量下载 | **loop 先尝试装+跑最小可行例**;装不上/需大数据→停下汇报 |
| **D 类(需数据)** | 需外部数据集(CPA/LINCS drug、mouse perturbation、真实 GEM 大模型) | **准备好接口+schema+验收清单,停下等用户提供数据/路径** |
| **R 类(需远端)** | 需 `zkyd@10.102.106.53` GPU / donor 私有数据 | **准备 runbook,停下等用户远端跑** |

---

## 每个 case 必须输出的 7 部分(质量铁律,validator 强制)

每个 case 的 finding 必须含且仅当 7 项齐全才算完成:

```
1. Structured input        — 物种/细胞类型/扰动对象规范化后的结构化输入
2. Object normalization    — 输入对象如何被归一(gene/drug/medium/ligand…)
3. Models/tools selected   — 路由选了什么模型/工具,为什么(applicability)
4. Raw prediction/analysis — 真实跑出的原始输出(数值/结构,非"系统调用了模型")
5. Baseline comparison     — 与什么 baseline 比,差异
6. Reliability decision    — accept / downgrade / abstain,依据(disagreement/OOD/applicability)
7. Provenance + boundary   — 溯源 + 哪些结论不能过度解释
```

**M 类新增 validator**:`tests/test_v04_case_schema.py`——断言 case report 对象含全 7 字段且非空;缺任一字段测试失败。这是所有 case 的公共门。

---

## 代表物种 × 应用 能力矩阵(roadmap,主文不填满)

| 应用 | Human | Mouse | Yeast | Bacteria |
|---|---|---|---|---|
| Gene perturbation | Norman CRISPR(已有) | ortholog caution | gene deletion | KO growth |
| Drug/chemical | cancer/immune drug | optional | antifungal/medium | antibiotic/carbon |
| State/fate | stem/immune/cancer | dev cell state | stress response | growth state |
| Metabolism/flux | scFEA/Compass | optional | yeast GEM | E. coli GEM |
| Communication/env | tumor-immune/spatial | tissue niche | co-culture | cross-feeding |

**Phase I(主文 6 核心 case)**:
| Case | 应用 | 物种 | 类 | 目的 |
|---|---|---|---|---|
| C1 | Gene perturbation | Human | 已有 | 主 benchmark(Norman,复用) |
| C2 | Unseen/OOD perturbation | Human | M | learned abstain 最强展示(复用 ledger) |
| C3 | Mouse ortholog routing | Mouse | M(+D 可选) | 跨物种 routing prototype 写实 |
| C4 | E. coli KO growth | Bacteria | T(cobrapy) | 机制模型/GEM,最像"虚拟细菌细胞" |
| C5 | Yeast growth/flux | Yeast | T(GEM) | 真核微生物桥梁 |
| C6 | Drug response | Human | D(CPA/LINCS) | 药物扰动应用 |

**Phase II(supplement 9 case)**:stem/fate · immune activation · cancer EMT · human flux(scFEA/Compass) · tumor-immune communication · spatial niche · co-culture receiver · bacteria antibiotic · drug dose/time。

---

## 执行步骤(loop 按顺序找第一个未勾选项)

### Week 1 — 代表物种 schema + routing(M 类,纯 Mac,loop 主战场)

#### - [x] W1.1 — species-aware request schema(M)【已完成】
- **产出**:`praxis_virtualcell/agents/species_schema.py`(SPECIES/PERTURBATION_OBJECTS/TARGET_OUTPUTS 词汇 + `normalize_request` + `SchemaError`)。
- **验收**:`tests/test_species_schema.py`(11 passed)——human gene / mouse gene / ecoli KO growth / yeast deletion growth / human drug 五输入归一(gene→大写、drug→小写);未知 species/object/output、缺字段、空 targets 全报错。
- **诚实**:仅 schema/归一层,不含预测;非法输入不静默补默认。finding 汇总到 W1.3。

#### - [x] W1.2 — human/mouse/yeast/bacteria route table + applicability rules(M)【已完成】
- **产出**:`praxis_virtualcell/agents/route_table.py`(`route(req)→RouteDecision{engine,disposition,reason,caution_flags,data_gated}`,引擎 donor_predictor/gem_fba/embedding/reject)。
- **验收**:`tests/test_route_table.py`(9 passed)——bacteria/yeast growth→gem_fba(**不**路由哺乳类 predictor);bacteria expression→abstain(mammalian_not_applicable);mouse gene→ortholog caution;drug→embedding+data_gated downgrade;human flux→data_gated downgrade;决策可 to_dict 进 provenance。
- **诚实**:route table 是**声明式能力图** `[能力矩阵]`,非性能;data-gated 引擎真跑前恒 downgrade/abstain,不假装 accept。

#### - [x] W1.3 — 3 个 mock-to-real routing 单测 + case validator(M)【已完成】
- **产出**:`praxis_virtualcell/agents/case_report.py`(`CaseReport` 7 字段 + `validate_case_report` + `routing_case`)+ `tests/test_v04_case_schema.py`(12 passed)。
- **验收**:validator 拒绝 7 部分任一缺失;3 routing case 方向正确(C3 mouse→donor+ortholog caution、C4 ecoli→gem_fba、C5 yeast→gem_fba)且 7 部分齐全;C4/C5 生长数值 boundary 标 pending W2。
- **产出 finding**:`docs/findings/finding_v0_4_species_routing.md`(schema + route table 覆盖矩阵 + 3 routing 决策 + 诚实标注)。
- **Week 1(M 类)全部完成** → 继续 Week 2(T 类 cobrapy,可能停)。

### Week 2 — E. coli / yeast metabolism cases(T 类,先试装 cobrapy)

#### - [x] 🔧 W2.1 — E. coli KO growth case(C4,T:cobrapy)【已完成】
- **落地**:`pip install cobra` 成功;用 cobrapy **自带 e_coli_core(textbook)**(无联网)。`praxis_virtualcell/predictors/mechanistic/ecoli_gem.py`(WT FBA + 大小写不敏感单基因 KO,避 macOS 多进程卡)。
- **真跑数字**:WT growth **0.87392**;b0720(gltA)/b1136(icd)KO→growth 0 **ESSENTIAL**;b2276 0.212、b0114 0.912、b0356 1.0。route `(bacteria,gene,growth)→gem_fba` accept。
- **治理**:基因不在 GEM → abstain(全缺)/caution(部分缺),不虚构生长。`test_ecoli_gem_case.py`(7 passed,无 cobra skip)。
- **finding**:`docs/findings/finding_v0_4_metabolism_cases.md`(§1-3)。pyproject 加 `[mechanistic]` extra。

#### - [x] W2.2 — Yeast growth/flux case(C5,T:yeast GEM)【已完成 — 用户授权下载 iMM904】
- **落地**:用户授权 → 下载 iMM904(BiGG,`data/gems/iMM904.xml.gz`,905 genes)。泛化出 `gem_model.GemModel` + `run_growth_case` 基座,`yeast_gem.py` 复用(与 E. coli 同管线,仅换 SBML)。
- **真跑数字**:WT growth **0.28787**;YGR175C(ERG1)KO→growth 0 **ESSENTIAL**;YOR375C/YIL125W 非必需;缺失基因→**caution**(不虚构)。route `(yeast,gene,growth)→gem_fba`。
- **架构复用点**:E. coli + yeast 共用 GemModel/run_growth_case → 框架对不同物种机制模型可扩展(换 SBML 即换物种)。`test_yeast_gem_case.py`(6 passed,无 cobra/SBML skip)。finding §4-6。
- **产出(若数据可得)**:yeast GEM 接入 + carbon source change / gene deletion → growth/flux;并入 `finding_v0_4_metabolism_cases.md`。
- **验收**:flux shift / growth prediction / medium sensitivity;7 部分 validator 过。
- **停止条件**:yeast GEM SBML 本地无 → 停,标 D 类等用户提供 SBML 路径。

### Week 3 — human drug response case(D 类,先自主找公开数据)

#### - [x] W3.1 — Human drug response case(C6,drug perturbation)【已完成 — 自主取公开数据】
- **落地**:自主下载 Enrichr LINCS L1000 Chem Pert 签名(公开无凭证;原始 ~30MB gitignore,provenance `data/drug_signatures/PROVENANCE.json`,curated 子集 `curated_subset.json` committed)。`predictors/embedding/drug_signature.py`(`DrugSignatureDB` + `run_drug_response_case`)。
- **真跑 + 治理**:drug→签名→同 MOA vs 跨 MOA 富集。HSP90(geldanamycin/tanespimycin)富集 **2.6-3.5×→accept**;HDAC(vorinostat)弱 0.10**→downgrade**;单例(sirolimus)无参考**→downgrade**;未知药**→abstain**。**R6 防过度承诺硬证据**(信号弱主动降级不硬说)。
- route_table `drug→embedding` 改为**非 data-gated**(caution);`test_drug_signature_case.py`(7 passed)+ route test 更新。**不训练模型**。finding `finding_v0_4_drug_case.md`。

### Week 4 — 整理 application matrix + 论文 outline(M 类,纯 Mac)

#### - [x] W4.1 — application matrix + v0.4 paper outline(M)【已完成】
- **产出**:`docs/paper/v0.4/application-cases.md`——能力矩阵(状态标注)+ 6 core / 9 supplement 分类 + Results 6 节结构 + R6 收束总表(治理防过度承诺)+ 最稳口径。
- **落地状态**:C1/C2 已有、C3/C4 真跑完成、L4 GEARS baseline 入表;C5(yeast)⏸ 数据门、C6(drug)🛑 数据门,均如实标注不虚填。
- **诚实**:主文只展开真跑 core case;未跑进 roadmap 标 ⏸/🛑;非 human case 价值定位为治理(识别/路由/降级/弃权),不夸大预测。

### Week 5 — Phase II supplement(自主可做子集:公开数据/工具)

#### - [x] W5.1 — 微生物 培养基/碳源切换 → growth(环境扰动,T:cobra 复用)【已完成】
- **落地**:route_table 扩 `(microbe, medium, growth)→gem_fba`;`medium_shift.py`(碳源名→exchange + FBA 切换)。激活 schema 的 `medium` 扰动对象。
- **真跑**:glucose 0.874 → succinate 0.398 → lactate 0.350 → **acetate 0.173**(教科书梯度);碳源不在模型→abstain/caution。`test_medium_shift_case.py`(6 passed)。finding §6b。**新增 State 之外的应用维度:环境/化学扰动**。

#### - [ ] W5.2 — Human 免疫激活 cell-state(填补 State/fate 空白应用,D:公开 scRNA)
- **自主动作**:自主取公开刺激-响应 scRNA(如 Kang 2018 IFN-β PBMC via pertpy/scanpy 或 GEO)→ 计算激活 marker state score(control vs stimulated)→ 过 route_table(state 输出)→ 7 部分 case + 治理(marker 覆盖不足→downgrade)。
- **验收**:activation state score(control vs stim 可分)+ marker panel + reliability;7 部分 validator 过。data 记 provenance。
- **只有当**公开数据需注册/无可定位子集 → 硬门#4 停。产出 `finding_v0_4_cellstate_case.md`。

#### - [ ] W5.3 — Human metabolic flux(scFEA/Compass,4C,T/D:重)
- **自主动作**:试装 scFEA/Compass;若模型/数据轻量可得 → 跑 human 表达→pathway flux tendency + 治理;否则备接口停(硬门#4)。

#### - [ ] W5.4 — Cell-cell communication(NicheNet/CellChat,应用 5,重/多为 R)
- 多为 R 工具 + 先验数据 → 大概率硬门;先自主评估 Python 侧(如 `liana-py`)可行性,不可行则备接口 + roadmap 停。

---

## 自主执行协议(autonomous;尽量不打断)

**每次 fire**:读本文件 → 找**第一个未勾选 `- [ ]` 步骤** → 按其"产出/验收/铁律"**做到底** → 跑 `.venv/bin/python -m pytest praxis_virtualcell/tests` 无回归 → 写/更新 finding → 本地单独 commit → 勾上回填 → **直接继续下一个未勾选步骤**,循环到所有步骤完成或撞硬门。

**自主授权(不必问,直接做 + 在 finding 记 provenance)**:
- **标准 pip 工具直接装**(cobra 等);
- **有明确权威公开来源的数据/模型直接下载**(BiGG GEM 如 iMM904/iML1515、cobrapy 自带 textbook、小型公开扰动数据集如 sciPlex/LINCS 公开子集),在 finding 记 **URL + sha256/大小**;
- **需要的科学默认选择自己定合理值**(培养基、目标函数、阈值分位、gene 归一约定等),在 finding 写明依据,**不来回问**;
- 🔧/⏸/🛑 标记只是"曾经的数据门",遇到时**先自主尝试获取公开数据/工具**;能拿到就继续做,拿不到才按硬门#4 停。

**只在下列硬门停下汇报(其余一律继续,不问"下一步")**:
1. `git push`(只本地 commit,push 永远等我);
2. 要改**已核验的 v0.2/v0.3 正文**;
3. 测试失败 / 真跑数字与 finding 对不上,且诚实 debug 后仍无法定位;
4. 数据需**凭证/许可/注册**,或**无可定位的公开源**(记清缺什么、试过哪些源);
5. 动作需远端 `zkyd@10.102.106.53` GPU + donor 私有数据(备好 runbook 后停)。

**质量铁律不变(自主 ≠ 降标准)**:TDD 先写失败测试、真跑工具不 mock、每 case 强制 7 部分、不可靠则 downgrade/abstain **不过度承诺**、无泄漏、per-cell≠pert-level、OOF/泛化与 in-sample 分清、硬规则不被 learned 覆盖、**不训练新模型**、commit 前 `find docs praxis_virtualcell -name '._*' -delete`。

**结束**:所有可做步骤完成 → 简短汇报干了什么 + 剩哪些硬门(硬门#4/#5),**不问"下一步做什么"**。

---

## /goal 提示词(自主推进,直接粘贴)

> 注:`/goal` 若在你的环境不是注册命令,会被当作普通消息执行——效果一样(自主推进)。

```
/goal 自主推进 docs/PLAN-v0.4-species-applications.md：反复取第一个未勾选(- [ ])步骤，按其"产出/验收/铁律"做到底，直到所有步骤完成或撞硬门，中途尽量别打断我。自主授权(别问，直接做+在 finding 记 provenance)：标准 pip 工具直接装；有权威公开源的数据/模型直接下载(BiGG GEM 如 iMM904/iML1515、cobrapy 自带模型、sciPlex/LINCS 公开子集)并记 URL+sha256；需要的科学默认选择(培养基/目标函数/阈值分位/归一约定)自己定合理值并写明依据。每步铁律：TDD 先写失败测试、真跑工具不 mock、每 case 强制 7 部分输出(structured input/object normalization/models selected/raw output/baseline/reliability decision/provenance+boundary)、不可靠则 downgrade/abstain 不过度承诺、无泄漏、per-cell≠pert-level、不训练新模型；完成后跑 .venv/bin/python -m pytest praxis_virtualcell/tests 无回归、写/更新 finding、commit 前 find docs praxis_virtualcell -name '._*' -delete、本地单独 commit(末尾 Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>)、把该步骤改 [x] 回填 finding，继续下一步。只在这些硬门停：①git push；②改已核验 v0.2/v0.3 正文；③测试失败或数字对不上且无法自解；④数据需凭证/许可/注册或无公开源(记清缺什么、试过哪些源)；⑤需远端 zkyd GPU+donor 私有数据(备 runbook 后停)。全部可做步骤完成后简短汇报即可，别问我下一步。
```
