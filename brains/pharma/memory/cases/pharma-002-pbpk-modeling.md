---
case_id: pharma-002-pbpk-modeling
task: physiologically_based_pk_modeling
input_compound: midazolam (CYP3A4 substrate, well-characterized)
tools: [PK-Sim/MoBi (open source), GastroPlus (commercial), Simcyp (commercial), mrgsolve, OpenFOAM-PK]
key_paper_doi: 10.1002/psp4.12363
status: validated
---

# PBPK：基于生理结构的 PK 模型

## Background
PBPK (physiologically based pharmacokinetic) 模型 = 把 body 切成 organ compartment（肝、肾、脑、肌肉等），每 compartment 含 blood flow + tissue volume + partition coefficient + metabolism。比传统 compartmental model 更 mechanistic，**优势**：dose 外推、特殊人群（儿童/老人/疾病）、DDI 预测。**劣势**：参数多、setup 复杂。

## What I actually did
1. **Compound 物化性质**：MW 326, logP 3.9, pKa 6.0, fu 0.04 (high protein binding), Caco-2 Papp
2. **In vitro metabolism**：CYP3A4 K_m, V_max from human liver microsome
3. **Distribution**：tissue:plasma partition coefficient (Kp) using Rodgers-Rowland method
4. **Absorption (oral)**：dissolution model + permeability + transit time
5. **Build PBPK in PK-Sim**：standard 14-compartment model
6. **Simulate**：dose 7.5 mg po → predict plasma concentration vs time
7. **Validate vs clinical PK**：predicted Cmax / Tmax / AUC 与 published 比对，fall within 2-fold = success
8. **Application**：
   - **DDI prediction**：CYP3A4 inhibitor (ketoconazole) 共服 → AUC ratio prediction
   - **Pediatric**：scale to 6-year-old child (allometric + maturation function)
   - **Hepatic impairment**：reduce CYP3A4 activity → AUC change

## ★ 排除/不做的事
- **PBPK 不 verify with clinical data**：unvalidated PBPK 无 regulatory acceptance
- **Default partition coefficient**：错误 Kp 让 distribution 全错
- **CYP intrinsic clearance from single experiment**：跨 batch microsome variability ≥ 30%
- **Single compound modeling without DDI**：drug 几乎都 polypharmacy in real clinical
- **Pediatric scaling without ontogeny**：CYP enzymes 在儿童不同 maturation rate
- **Forget transporter**：P-gp / OATP / BCRP 等 transporter 决定 distribution
- **Membrane vs hepatocyte CL_int**：两者 method 不同 IVIVE factor

## ★ 失败模式
- **PBPK overfit**：参数太多，给 good in vitro fit 但不 generalize
- **Tissue partitioning method bias**：Rodgers-Rowland vs Poulin-Theil 给不同 Kp
- **Active transport not modeled**：efflux drug PBPK without P-gp 不准
- **Sink condition violation**：高浓度 dose binding saturation
- **Enterohepatic circulation**：bile excretion + reabsorption cycle 复杂
- **Disease state**：hepatic / renal impairment 不只 reduce enzyme，全身生理改变

## Lessons → seeds for rules
1. **Validate vs clinical** mandatory before predict
2. **Multiple Kp methods** cross-check
3. **Transporter modeling** for high-extraction / efflux drug
4. **Maturation function** for pediatric
5. **In vitro-in vivo correlation factor** carefully
6. **Sensitivity analysis** for top-3 parameters
7. **Confidence prediction interval** report
