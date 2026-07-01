# finding v0.4 W2 — 机制模型(GEM/FBA)代谢 case:E. coli KO growth(真跑)

> 目标:证明 PRAXIS 能接入**非神经网络的机制模型**(基因组尺度代谢模型 GEM / FBA),处理"虚拟细菌细胞"的 KO→growth 任务,并由 route_table 正确路由(bacteria growth → gem_fba,不走哺乳类 predictor)。证据类型:`[Mac确定性]`(cobrapy 自带 e_coli_core,无联网、确定性可复跑)。
> 对应 `docs/PLAN-v0.4-species-applications.md` 步骤 W2.1(E. coli);W2.2(yeast)见 §3。

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

## 4. W2.2 — yeast growth/flux(pending,D 类数据门)

- yeast-GEM(Yeast8 SBML)**非** cobrapy 自带,需外部 SBML 文件 → 按 PLAN 停在 D 类数据门。
- 接口已就绪:`EcoliGEM(sbml_path=...)` 已支持传入任意 SBML;yeast 只需提供 Yeast8 SBML 路径即可复用同一 FBA/KO/case 管线(或另写 `yeast_gem.py` 薄封装)。
- **待用户提供**:Yeast8 SBML 本地路径(如 `yeast-GEM.xml`)→ 即可跑 carbon-source / gene-deletion → growth/flux case。
