---
case_id: pharma-005-fih-dose-escalation
task: first_in_human_dose_design
indication: oncology (cytotoxic agent example)
inputs: [preclinical_NOAEL, allometric_HED, MABEL]
tools: [FDA FIH guidance, EMA risk-based approach, mrgsolve, BLRM (Bayesian Logistic Regression Model)]
key_paper_doi: 10.1038/sj.bjp.0707305
status: validated
---

# First-in-Human dose 设计 + Bayesian dose escalation

## Background
FIH dose 决定 phase I 试验起点。两套方法：(1) 传统 NOAEL × 1/10 (FDA "MRSD" 方法)；(2) MABEL (Minimum Anticipated Biological Effect Level，特别 immune-modulator after TGN1412 disaster 2006)。Dose escalation 用 BLRM 替代旧 3+3 设计。

## What I actually did
1. **Preclinical NOAEL**：rat 50 mg/kg, dog 30 mg/kg，most sensitive species 选 dog
2. **HED (Human Equivalent Dose)**：dog HED = 30 × (0.541 / 1.86)^0.33 = 30 × 0.66 = ~20 mg/kg = 1400 mg/70kg
3. **Safety factor**：MRSD = HED / 10 = 140 mg starting dose
4. **MABEL alternative (immune modulator)**：from in vitro receptor occupancy → minimum dose to give 10% receptor occupancy → typically lower than MRSD
5. **Dose escalation设计**：
   - **3+3 (传统)**：3 patient per dose level，DLT 发生再 escalate；保守，慢
   - **BLRM (Bayesian)**：每患者 informative，prior + posterior 更新 max tolerated dose；快、信息利用率高
6. **DLT (dose-limiting toxicity) definition**：CTCAE grade 3+ non-hematologic / grade 4 hematologic
7. **MTD (max tolerated dose)**：dose with DLT rate ≤ 33%
8. **Output**：starting dose recommendation + escalation scheme + stopping rules

## ★ 排除/不做的事
- **Single safety factor (10) for all**：novel mechanism / immune modulator / biologic 需 higher safety factor (50-100)
- **NOAEL only ignore MABEL**：immune modulator 必须 MABEL approach (TGN1412 lesson)
- **3+3 design 仍 default**：BLRM more efficient + ethical
- **DLT defined post hoc**：必须 protocol-defined
- **Single species NOAEL**：multi-species comparison
- **Body surface area scaling for biologics**：biologics 用 BW (linear) scaling not BSA

## ★ 失败模式
- **TGN1412 disaster (2006)**：CD28 superagonist anti-CD28 mAb，FIH 0.1 mg/kg → 6 healthy volunteer cytokine storm hospitalize；NOAEL approach 失败 → MABEL 后建立
- **Cross-species extrapolation gap**：first-in-human 实际 PK / PD 与 prediction 偏 2-10×
- **Immunogenicity in human**：biologic ADA (anti-drug antibody) 改变 PK
- **Schedule effect**：daily vs weekly schedule 不同 max tolerated
- **Special population not included**：trial 在 healthy volunteer，patient population 不同 (特别 cancer trial 是 diseased)

## Lessons → seeds for rules
1. **MABEL approach for immune modulator** mandatory (post-TGN1412)
2. **BLRM > 3+3** for efficiency + ethics
3. **Multi-species NOAEL** + most sensitive species
4. **HED scaling method**：BSA for small mol, BW for biologic
5. **Protocol-defined DLT** + stopping rules
6. **Safety factor calibration**：10 default; immune modulator 50-100
7. **Real-time PK monitoring** during escalation
