# 冻结:v0.9 现状下的 G2 科学门真实状态(2026-07-07)

> 来源:`data/mdr_gnb/reports/gates/*.md`(2026-07-04 combo_gate 真跑产物),harness=`workflows/run_combo_eval.py`。
> 本文件是**冻结基线**,g2r-remediation 分支的所有补强以此为对照起点,不得覆盖。

## 一、两个锚点(原始 G2 判据:两者都须 pass)

| 锚点 | 判定 | n_strains | VME(ML) | VME(rule) | ΔVME | p |
|---|---|---|---|---|---|---|
| **KP × meropenem** | ✅ **pass** | 768 | 0.102 | 0.266 | **−0.164** | 0.0001 |
| **EC × ceftriaxone** | ❌ **degrade** | 6852 | 0.050 | 0.030 | **+0.020** | 0.983 |

**结论:原始 G2 = 1/2 锚点通过。** KP 锚点 ML 显著更安全(VME 减半);EC 锚点 ML 反而比规则法差,未通过。
2026-07-04 是「用户有条件通过、全景铺开」绕过,**不是干净科学通过**。

## 二、全景 28 组合(KP/EC × 14 药):ML 显著胜出 8/28

- **KP 侧强**(碳青霉烯酶/ESBL 富集,ML 学到基因组合):ceftriaxone/meropenem/aztreonam/gentamicin/amikacin/tetracycline pass。
- **EC 侧弱**(稀有耐药药物 ML 坍缩为"判 S"):仅 ampicillin/cefepime pass;ceftriaxone/aztreonam/tetracycline/fosfomycin ML 反而更差。
- **危险点 EC × meropenem:VME(ML)=0.683**(漏 2/3 耐药株)vs rule 0.187 —— EC 碳青霉烯耐药极稀有(32/6232 ST),RF 坍缩判 S。已被 combo_gate 诚实降级为规则法,但暴露 ML 在稀有耐药下的系统性失效。

## 三、方法学(harness 已具备,可复现)

`run_combo_eval.py`:ST 分组 5 折 → 每折训 GenotypeToSIR(ML)+ 冻结 RuleBaselineSIR →
**操作点对齐**(ML 阈值在 train 上对齐规则法 ME,test 应用,防调阈泄漏)→ OOF 汇聚 →
per-ST VME + paired permutation test + bootstrap CI → combo_gate。
- 基线真实:`predictors/rule_baseline.py` = 版本冻结 AMRFinderPlus 基因族→SIR 规则(`rules/amrfinder_sir_rules.yaml`)。
- 划分真实:`data/mdr_gnb/splits/<物种>/<药>.json`(ST 分组,unknown_st 单列)。
- **红队自陈(harness docstring)**:ML 特征 == AMRFinderPlus 基因调用,与规则法**同源**;ST 去泄漏后 ML 增量可能坍缩。→ ML 只能靠"非线性基因组合"赢,无法引入规则没有的信息(k-mer/porin/MIC)除非加新特征。

## 四、对 G2R 的启示(基于真实数字)

1. **KP 锚点已 strong-pass**(真实,无需补强)。
2. **EC ceftriaxone practical-pass 可达**:rule-first 融合(rule=R→R,否则 ML)数学上 VME ≤ 规则法(0.030)< ML(0.050),必不劣于规则。
3. **EC strong-pass 难**:要真正压低 EC VME 且显著,需引入规则法没有的**新特征**(k-mer/porin markers/CARD)——这依赖真实工具链(阶段 7),对 EC 锚点可能需提前。
4. NCBI-only 无 MIC → 计划里的「折点附近耐药株子集 near_breakpoint」**不可评**,G2R 用全 test 集 per-ST VME。
