---
case_id: synth-008-biosensor-design
task: biosensor_circuit_design
target_analyte: arabinose (small molecule, model case for sugar/metabolite sensor)
host_organism: E. coli
mechanism: AraC TF + pBAD reporter
tools: [iBioSim, Cello (logic gate), Sensemaker, SBML circuit simulators]
key_paper_doi: 10.1038/nbt.3865
status: validated
---

# Arabinose biosensor：TF-based small molecule sensor design

## Background
Whole-cell biosensor = 把 TF + responsive promoter + reporter 接成 circuit，在 cell 中检测 small molecule。AraC + pBAD-GFP 是 model：arabinose 浓度→GFP 强度。**关键设计参数**：dynamic range, leaky basal, response speed, specificity。

## What I actually did
1. **Topology**：AraC TF gene under constitutive promoter → AraC binds arabinose → activates pBAD → GFP
2. **Dose-response characterization**：plate reader GFP vs arabinose (0.001-100 mM) → Hill curve fit
3. **Tune parameters**：
   - **Dynamic range** (max/basal)：换 RBS strength on AraC + GFP
   - **Sensitivity (EC50)**：直接受 TF binding affinity 限，难大改
   - **Leaky basal**：strict promoter / repressor combination
4. **Specificity**：cross-reactivity 测试（lactose / glucose / other sugars）
5. **Response time**：10-30 min after add ligand
6. **Validation**：spike known concentration → GFP readout 与 expected agree within 2x
7. **Application**：metabolic engineering screen（产 arabinose 的 strain GFP+） / environmental sensing

## ★ 排除/不做的事
- **Single sensor topology trial**：multiple RBS / promoter strength combination 几个 try
- **Forget specificity panel**：sensor 在 single ligand validate 不够
- **Dynamic range < 5x 接受**：dynamic range 太小 readout 区分困难
- **Leaky basal 不优化**：高 basal 让 hit 难 distinguish
- **Plate reader bulk only**：cell-to-cell variability 大，flow cytometry 看 single cell
- **不评估 ligand uptake**：cell membrane 透过性影响实际 in-cell concentration

## ★ 失败模式
- **AraC dimerization variation**：AraC TF 高浓度时 self-aggregate
- **Catabolite repression**：glucose 共存 down-regulate pBAD
- **Reporter maturation time**：GFP fold + chromophore mature 需 ~30 min；快速 dynamics miss
- **TF degradation rate**：短半衰期 TF 让 sensor 反应快但 baseline noisy
- **Cell growth phase**：log vs stationary phase response 不同
- **Plasmid copy number variation**：cell-to-cell circuit 表达 variable

## Lessons → seeds for rules
1. **Dose-response characterization** mandatory
2. **Dynamic range ≥ 10×** preferred for clean signal
3. **Specificity panel** （5-10 cross-reactant test）
4. **Single-cell flow cytometry** for noise
5. **Catabolite repression check** for sugar sensors
6. **Reporter maturation aware** for kinetics
7. **Multiple parameter combination** try
