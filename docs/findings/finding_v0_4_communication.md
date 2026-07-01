# finding v0.4 W5.4 — Cell-cell communication case:L-R 共表达(填补 Communication 空白应用)

> 目标:**填补最后一个空白应用(5 Communication)**。ligand-receptor 共表达分析:IFN-β 诱导的 CXCL10(单核)→CXCR3(T/NK)通讯轴。证据类型:`[Mac确定性]`。**自主完成**(复用 Kang 2018)。
> 对应 `docs/PLAN-v0.4-species-applications.md` W5.4(应用 5,例 5A tumor/免疫 sender→receiver)。

## 1. 数据 + 分析

- 数据:Kang 2018 L-R 子集(`data/cellstate/kang_lr_subset.json`,8 配体-受体对 × cell types × ctrl/stim,333KB)。
- route:`(human, *, communication) → communication` 引擎(W5.4 接入)。
- communication score(sender→receiver)= mean_lognorm(ligand in sender) × mean_lognorm(receptor in receiver)(NicheNet/CellPhoneDB 共表达思路);比较 ctrl vs stim。

## 2. 结果 + 治理(实跑)

**CXCL10(单核 sender)→ CXCR3(受体 receiver),ctrl vs stim**:

| sender→receiver | ctrl score | stim score | fold | 裁决 |
|---|---|---|---|---|
| CD14+ Mono → CD8 T | 0.049 | 2.52 | **51×** | **accept** |
| CD14+ Mono → NK | 0.059 | 1.89 | 32× | **accept** |
| CD14+ Mono → CD4 T | 0.017 | 0.81 | 47× | **downgrade** |

- IFN-β 强诱导 CXCL10(单核 ctrl 0.10→stim 4.98,~50×)→ 通讯 score 骤升 → **accept**(效应 T/NK 高表达 CXCR3)。
- **CD4 T → downgrade**:虽 fold 高,但 CD4 T 的 **CXCR3 受体表达低(<0.5 阈)**→ 受体证据不足 → 系统**不硬说通讯成立**。**这是生物学正确的治理**:CXCR3 主要在效应/记忆 T 与 NK 高表达,naive CD4 T 低。
- **ligand 不在 L-R 库 → abstain**(不虚构通讯)。测试 `test_communication_case.py`(5 passed)。

## 3. 治理点(R6)

同一 IFN-β 扰动,agent 对通讯 claim **按 sender/receiver 表达证据分别裁决**:CXCR3⁺ 受体(CD8T/NK)accept,CXCR3^low 受体(CD4T)downgrade。**不因"配体强诱导"就一律宣称通讯**——受体端证据不足即降级。

## 4. 诚实边界

- communication score 是 **ligand×receptor 共表达代理**(NicheNet/CellPhoneDB 思路),**非**实测信号转导/通量。
- Kang 2018 PBMC 子集;表达阈 0.5、8 对 L-R 为设定默认。
- downgrade 表"共表达证据不足",非"无通讯"。
- 本 case 证明**"agent 能组织多步通讯分析(sender/receiver/ligand/receptor/state shift)并受治理"**,非通讯的完备刻画。**不训练模型**。

## 5. 架构

- `praxis_virtualcell/predictors/communication/lr_comm.py`:`LRCommDB` + `run_communication_case`;复用 `state/scoring.lognorm`;route 加 `communication` 引擎。
- **Communication 空白应用已落地 → 5 个代表应用全部有真跑 case**。
