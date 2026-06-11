---
case_id: pharma-009-pkpd-emax
task: pk_pd_modeling_emax
target_drug: anti-PD-1 (pembrolizumab, immune checkpoint inhibitor)
endpoint: receptor occupancy / tumor response
tools: [mrgsolve, nlmixr2, Pumas.jl, Berkeley Madonna]
key_paper_doi: 10.1158/1078-0432.CCR-14-2607
status: validated
_doi_provenance: Patnaik A et al. 2015 Clin Cancer Res 21:4286–4293 "Phase I Study of Pembrolizumab (MK-3475; Anti-PD-1 Monoclonal Antibody) in Patients with Advanced Solid Tumors" — original dose-finding paper used to establish 200 mg q3w flat-dose rationale.
---

# PK/PD Emax：immune checkpoint inhibitor 的 dose-response 解析

## Background
PK/PD 把 drug exposure 与 effect 关联。Emax model = Effect = Emax × C / (EC50 + C)。Pembrolizumab (anti-PD-1)：dose 200 mg q3w 或 400 mg q6w 给 ~99% receptor occupancy → flat dose-response (saturated)。**意义**：不需 weight-based dosing，flat dose 即可——临床简化 huge。

## What I actually did
1. **PK model**：1-compartment IV antibody PK + linear elimination + small protein-binding component
2. **PD model**：receptor occupancy = C / (Kd + C)；PD endpoint 是 occupancy 而非 tumor size
3. **Tumor PD model (longer term)**：tumor size dynamics with drug effect on growth/death rate
4. **Joint model**：simultaneous fit PK + PD (sequential or joint)
5. **Dose-response simulation**：跨 dose level (50, 100, 200, 400, 600 mg) → predict trough occupancy
6. **At 200 mg q3w**：trough Cmin 30-40 μg/mL → ~99% receptor occupancy
7. **Conclusion**：dose escalation > 200 mg 几乎无 incremental efficacy → 200 mg flat dose 推荐
8. **Validation**：phase II/III 数据复盘 confirm

## ★ 排除/不做的事
- **Dose-finding without PK/PD**：浪费 dose levels in dose escalation；Emax 揭示 saturated region
- **Only Emax for tumor outcome**：tumor 是 long-term integrative，single sample 不够
- **Population variability ignored**：population PK + PD reveal subgroup
- **Body weight dosing 自动假设**：immune-onc 多数 flat dose adequate（contrary to chemo paradigm）
- **No exposure-response (E-R) analysis**：FDA 要求 oncology BLA include E-R
- **Single endpoint**：efficacy + safety E-R 必须分别建模

## ★ 失败模式
- **Receptor occupancy ≠ clinical response**：occupancy high 但 tumor escape mechanism (T cell exhaustion 等) 让 efficacy 不到位
- **Time-delayed PD**：tumor response 延迟 weeks-months
- **Hysteresis**：concentration vs effect time lag
- **Resistance evolution**：long treatment 减效
- **Immune-related AE non-Emax**：irAE 更复杂 dose-response
- **Patient heterogeneity**：tumor type / mutation / TIL 差异决定 response

## Lessons → seeds for rules
1. **Emax model for saturable** target
2. **Receptor occupancy as PD biomarker** for biologic
3. **Tumor PD as integrative endpoint**
4. **Joint PK-PD or sequential**
5. **E-R analysis FDA requirement** for oncology
6. **Flat dose vs weight-based** evaluation for biologics
7. **Efficacy + safety E-R** separately
