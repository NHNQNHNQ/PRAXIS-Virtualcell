---
case_id: pharma-006-nca-pk
task: noncompartmental_analysis
input_data: clinical PK plasma concentration vs time
tools: [PKNCA (R), Phoenix WinNonlin (commercial), nlmixr2, mrgsolve, ncappc]
key_paper_doi: 10.1007/BF01068419
status: validated
_doi_provenance: Schuirmann DJ 1987 J Pharmacokin Biopharm 15:657–680 "A comparison of the Two One-Sided Tests Procedure and the Power Approach for assessing the equivalence of average bioavailability" — the canonical TOST-based bioequivalence statistical method that NCA reports underpin.
---

# Noncompartmental analysis (NCA)：bioequivalence + early phase 标准

## Background
NCA 不假设 PK model 形态，用 trapezoidal rule + log linear regression 直接算 AUC / Cmax / t1/2 / Cl / Vd。**适合**：early phase 数据探索、bioequivalence 比较。**不适合**：dose extrapolation、population PK、复杂 PK (non-linear, time-dependent)。

## What I actually did
1. **Input**：subject × timepoint × concentration table; dose; route (PO/IV)
2. **PKNCA in R**：
   - `pk.calc.cmax`, `pk.calc.tmax` (peak concentration & time)
   - `pk.calc.auclast` (AUC to last sample, linear/log trapezoidal)
   - `pk.calc.aucinf.obs` (AUC to infinity, requires λz fit)
   - `pk.calc.half.life` (terminal half-life from λz)
   - `pk.calc.cl.obs` (clearance), `pk.calc.vss.obs` (Vss)
3. **Lambda_z (terminal slope) selection**：通常 last 3-4 points log-linear regression, R² > 0.9
4. **AUC extrapolation**：< 20% extrapolated AUC = good; > 20% = inadequate sampling, less reliable
5. **Bioavailability (F)**：oral / IV AUC ratio
6. **Bioequivalence**：test vs reference 90% CI of (AUC, Cmax) ratio in 80-125% bound
7. **QC**：dose 一致性 + missing data + LLOQ 处理

## ★ 排除/不做的事
- **Pre-dose nonzero concentration**：washout 不充分，结果污染
- **AUC extrapolation > 20%**：terminal phase under-sampled，t1/2 不可信
- **Single subject NCA report mean**：individual 之间差大，individual table + summary stat
- **Lambda_z fit < 3 points**：cannot establish terminal phase
- **LLOQ handling 不一致**：BLOQ value 处理 (zero / 1/2 LLOQ / NA) 影响 AUC
- **Mixed dose level mean**：不同 dose 不要一起 average

## ★ 失败模式
- **Multiphase concentration**：peak shoulder (multiple absorption peaks) NCA 假设单峰失败
- **Enterohepatic circulation peak**：second peak 让 t1/2 计算偏
- **Steady state NCA mistaken for single dose**：accumulation factor confusing
- **Sample dilution / contamination**：单 subject outlier
- **NCA on simulation data**：people sometimes NCA model output → 失去 modeling 意义
- **Bioequivalence with insufficient n**：n < 24 power 弱

## Lessons → seeds for rules
1. **Lambda_z selection 自动 + manual review**
2. **AUC extrapolation < 20%** for valid t1/2
3. **Individual subject table + summary**
4. **BLOQ handling protocol-defined**
5. **Pre-dose concentration check** for washout
6. **Sample size adequate** for bioequivalence (≥ 24)
7. **Enterohepatic / multiphase warning**
