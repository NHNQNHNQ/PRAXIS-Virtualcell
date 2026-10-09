# finding v0.4 W5.3 — Human 代谢通路 tendency case:治理对照(表达层弱信号→downgrade)

> 目标:补应用 4C(human expression → metabolic pathway/flux tendency,scFEA/Compass 思想),并给出 **R6 治理对照硬证据**:同一 IFN-β 扰动、同一批细胞,ISG 激活强(accept)vs 代谢通路表达层信号弱(downgrade),agent **按证据分别裁决**。证据类型:`[Mac确定性]`。**自主完成**(复用 Kang 2018)。
> 对应 `docs/PLAN-v0.4-species-applications.md` W5.3。

## 1. 分析

数据:Kang 2018 代谢子集(`data/cellstate/kang_metabolic_subset.json`,glycolysis/oxphos/hk panels,2232 cells)。route `(human, *, flux) → pathway_scoring`(表达层,哺乳类无机制 GEM 接入)。每 cell CP10k+log1p → 通路活性评分(panel−hk)→ ctrl vs stim Cohen's d。

| 通路 | ctrl | stim | Cohen's d |
|---|---|---|---|
| glycolysis | −2.279 | −2.217 | **0.10** |
| oxphos | −2.252 | −2.072 | **0.28** |

→ max |d| = 0.28 < 0.8 → **downgrade**。

## 2. 治理对照(R6 核心硬证据)

**同一 IFN-β 扰动、同一批 PBMC**:

| 维度 | 分析 | Cohen's d | 裁决 |
|---|---|---|---|
| ISG 激活(cell-state,W5.2) | 干扰素刺激基因 | **2.49** | **accept** |
| 代谢通路 tendency(W5.3) | 糖酵解/OXPHOS | **0.10–0.28** | **downgrade** |

→ **agent 不一刀切**:接受证据充分的 ISG 激活claim,降级证据不足的代谢重编程claim。这正是 **"reliability-governed reporting prevents overclaiming"** —— 不为"跑通"硬报一个表达层不存在的代谢信号。

## 3. 诚实边界

- 通路活性评分是**表达层代理**,**非真实代谢通量**(真通量需 scFEA/Compass/¹³C-flux)。
- downgrade 表"表达层无足够证据支持代谢重编程",**非"代谢无变化"**(IFN 的代谢效应可能在后转录/翻译层,或需更长时程)。
- Kang 2018 短时刺激 PBMC 子集;效应阈/panel 为设定默认。
- 本 case 的价值是**治理对照**(accept vs downgrade 同数据),非 human 代谢的完备刻画。**不训练模型**。

## 4. 架构复用

- 评分数学抽成 `predictors/state/scoring.py`(lognorm/panel_score/cohens_d),**cell_state 与 metabolic_tendency 共用**(不复制)。
- `predictors/state/metabolic_tendency.py`:`MetabolicDB` + `run_metabolic_tendency_case`;route 加 `pathway_scoring` 引擎。`test_metabolic_tendency_case.py`(4 passed)。
