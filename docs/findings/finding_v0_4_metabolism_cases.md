# finding v0.4 W2 — 机制模型(GEM/FBA)代谢 case:E. coli + Yeast KO growth(真跑)

> 目标:证明 PRAXIS 能接入**非神经网络的机制模型**(基因组尺度代谢模型 GEM / FBA),处理微生物 KO→growth 任务,并由 route_table 正确路由(microbe growth → gem_fba,不走哺乳类 predictor)。两个代表物种真跑:**E. coli(§1,textbook)+ S. cerevisiae(§4,iMM904)**。证据类型:`[Mac确定性]`(确定性可复跑;E. coli 无联网,yeast 用授权下载的 iMM904)。
> 对应 `docs/PLAN-v0.4-species-applications.md` 步骤 W2.1(E. coli)+ W2.2(yeast)。

## 1. C4 — E. coli KO growth case(7 部分,真实数值)

- **工具**:`cobrapy` 自带 `e_coli_core`(textbook)GEM;`praxis_virtualcell/predictors/mechanistic/ecoli_gem.py`。
- **路由**:route_table `(bacteria, gene, growth) → gem_fba`(accept),**未**走 donor_predictor(applicability 铁律)。
- **WT growth(FBA biomass)= 0.87392**(textbook 已知值,验证模型正确)。

**KO essentiality(实跑)**:

| gene | growth | ratio(vs WT) | essential |
|---|---|---|---|
| b0720(gltA,柠檬酸合酶) | 0.00000 | 0.000 | **✓ ESSENTIAL** |
| b1136(icd,异柠檬酸脱氢酶) | 0.00000 | 0.000 | **✓ ESSENTIAL** |
| b2276(nuoA,NADH脱氢酶) | 0.21166 | 0.242 | ✗(严重降低) |
| b0114(aceE,丙酮酸脱氢酶) | 0.79670 | 0.912 | ✗(轻微) |
| b0356(frmA) | 0.87392 | 1.000 | ✗(无影响) |

→ gltA/icd(TCA 循环核心)KO 致死,与已知 E. coli 必需性一致 → **真实机制预测,非 mock**。

## 2. 治理点(reliability decision)

- **基因不在 GEM → 不虚构生长**:全部 target 不在模型 → `abstain`;部分不在 → `caution`(降级),`caution_flags` 记 `targets_not_in_gem:[...]`;全在模型 → `accept`。测试 `test_ecoli_gem_case.py`(7 passed,无 cobra 自动 skip)覆盖三种 disposition。
- **大小写解析**:schema 归一把基因大写(B0720),GEM b-number 小写(b0720)→ `EcoliGEM._resolve` 大小写不敏感解析(TDD 抓出并修)。

## 3. 诚实边界

- FBA growth 是**约束型可行性/最优通量的相对量**(steady-state 假设),**非**绝对生长速率。
- **in-silico essentiality**,需湿实验证实;`e_coli_core` 是**核心代谢子集**(137 genes / 95 rxns),非全基因组模型(iML1515 未接入)。
- 本 case 证明的是**"agent 能路由到机制模型并产出受治理的真实预测"**(能力 + 治理),非 E. coli 代谢的完备刻画。

## 4. C5 — Yeast(S. cerevisiae)deletion growth case(iMM904,真跑)

- **工具**:iMM904(BiGG,905 genes / 1577 rxns;`data/gems/iMM904.xml.gz`,用户授权下载)。`praxis_virtualcell/predictors/mechanistic/yeast_gem.py`,**复用通用 `gem_model.GemModel` + `run_growth_case`**(与 E. coli 同一 FBA/KO/case 管线,仅换 SBML)。
- **路由**:`(yeast, gene, growth) → gem_fba`(同 applicability 铁律)。
- **WT growth(FBA)= 0.28787**(iMM904 已知值)。

**KO essentiality(实跑)**:

| gene | growth | ratio | essential / in_model |
|---|---|---|---|
| YGR175C(ERG1,角鲨烯环氧酶) | 0.00000 | 0.000 | **✓ ESSENTIAL** |
| YOR375C(GDH1) | 0.28787 | 1.000 | ✗ |
| YIL125W(KGD1) | 0.28725 | 0.998 | ✗ |
| ZZ_MISSING(伪基因) | — | — | 不在 GEM |

→ ERG1 KO 致死(与酵母必需性一致);缺失基因 → 整体 **caution**(`targets_not_in_gem`),**不虚构缺失基因生长**。测试 `test_yeast_gem_case.py`(6 passed,无 cobra/SBML 自动 skip)。

## 5. 架构复用点(代表物种可扩展性)

- `gem_model.GemModel`(基座:SBML→WT→大小写不敏感 KO)+ `run_growth_case`(7 部分 case)被 **E. coli(textbook)与 yeast(iMM904)共用** → 证明框架对不同物种机制模型**可扩展**:换 SBML 即换物种,治理/case 管线不变。
- 现有真跑代谢 case:**bacteria(E. coli)+ yeast(S. cerevisiae)** 两个真核/原核代表,均由 route_table 正确路由到 gem_fba。

## 6b. Phase II — E. coli 培养基/碳源切换 → growth(环境扰动,W5.1,真跑)

激活 schema 的 `medium` 扰动对象(gene 以外的**环境扰动**);route_table 扩 `(microbe, medium, growth)→gem_fba`。同一 e_coli_core,把 glucose 换成其它单一碳源(上限 -10、有氧),FBA 算 growth。`medium_shift.py`。

| carbon | growth | ratio vs glucose |
|---|---|---|
| glucose / fructose | 0.87392 | 1.000 |
| succinate | 0.39756 | 0.455 |
| lactate | 0.35031 | 0.401 |
| **acetate** | 0.17334 | **0.198** |
| unobtainium(伪) | — | 不在模型 |

→ acetate 远弱于 glucose(乙醛酸支路,教科书一致);碳源不在模型 exchange → **abstain**(全缺)/ **caution**(部分缺),不虚构。测试 `test_medium_shift_case.py`(6 passed)。**证明 agent 能处理环境/化学扰动(非 gene)并受治理**。

## 6. 诚实边界(通用)

- FBA growth 是**约束型可行性/最优通量的相对量**(steady-state),**非**绝对生长速率;in-silico essentiality 随培养基/目标函数变,需湿实验证实。
- e_coli_core(137 genes)/ iMM904(905 genes)均为**有限覆盖**重建,非完备代谢刻画。
- 本组 case 证明的是**"agent 能路由到机制模型并产出受治理的真实预测"**(能力 + 治理 + 可扩展),非 E. coli/yeast 代谢的完备刻画。
