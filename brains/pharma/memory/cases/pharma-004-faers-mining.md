---
case_id: pharma-004-faers-mining
task: adverse_event_signal_detection
target_drug: rofecoxib (Vioxx, withdrawn 2004 due to MI risk)
tools: [openFDA API, AERSMine, OpenVigil, R PhViD package, disproportionality analysis]
key_paper_doi: 10.1002/pds.677
status: validated
---

# FAERS 不良事件信号挖掘：rofecoxib MI signal 历史复盘

## Background
FDA Adverse Event Reporting System (FAERS) 是公开 ADE database（>22M reports since 1969）。Rofecoxib 2004 因 myocardial infarction risk 撤市 — **早期 FAERS 数据已显示 MI signal**，但 disproportionality analysis 当时未及时 act on。Pharmacovigilance 经典 case。

## What I actually did
1. **Query FAERS via openFDA API**：drug = "rofecoxib" + ADE term = "myocardial infarction"
2. **Disproportionality measures**：
   - **PRR (Proportional Reporting Ratio)** = (a/(a+b)) / (c/(c+d))，where a = drug+ADE, b = drug+other ADE, c = other drug+ADE, d = other drug+other ADE
   - **ROR (Reporting Odds Ratio)** = (a/b) / (c/d)
   - **IC25 (lower 95% CI of Information Component)** Bayesian
3. **Threshold for signal**：PRR ≥ 2 + chi-square ≥ 4 + cases ≥ 3
4. **Comparator**：vs 全 FAERS database OR vs class (NSAIDs)
5. **Time series**：PRR 月度变化 → signal emergence 时序
6. **Confounders**：indication confounding（治疗 inflammation 的 patient 本身 elevated CV risk）
7. **Output**：rofecoxib MI ROR ~3-5 in pre-2004 data → would have flagged early

## ★ 排除/不做的事
- **Single disproportionality measure**：PRR + ROR + IC25 cross-check
- **Bulk count without comparator**：无 baseline comparison 不可解读
- **Signal accept without confounding analysis**：indication / age / comorbidity confounding 普遍
- **不查 latency / time-to-onset**：immediate vs delayed AE 不同 mechanism
- **不区分 MedDRA hierarchy**：PT (preferred term) vs HLT vs SOC 不同 level signal
- **Reporter bias 不评估**：post-publicity reporting bias 改变 PRR

## ★ 失败模式
- **Notoriety bias**：post-warning AE reports 涌入 → false signal up
- **Indication confounding**：drug 治疗 condition 本身有 AE risk
- **Reporting rate variability**：跨国家 / 跨时段 reporting rate 差大
- **Off-label use**：reported AE 在 off-label population，extrapolation 错
- **Delayed AE**：long latency AE (cancer) 难关联
- **Drug switching**：patient 换药期间 ADE，不知 attribute 哪
- **Death AE**：fatal vs non-fatal weighted differently

## Lessons → seeds for rules
1. **Multi-measure disproportionality** (PRR + ROR + IC25)
2. **Comparator选择** affects signal
3. **Confounding analysis** mandatory
4. **Time series** for signal emergence
5. **MedDRA hierarchy** (PT level granular)
6. **Cases ≥ 3** minimum
7. **Notoriety bias** check post-warning
