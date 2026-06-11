---
case_id: synth-005-toggle-switch-circuit
task: genetic_circuit_design
circuit_type: bistable toggle switch (Gardner/Cantor/Collins 2000)
host_organism: E. coli
tools: [iBioSim, COPASI, Tellurium SBML simulation, Cello (logic gate), MATLAB SimBiology]
key_paper_doi: 10.1038/35002131
status: validated
---

# Toggle switch：synthetic biology 经典 case

## Background
Gardner et al 2000 (Nature) 第一个 engineered bistable toggle switch in E.coli：两个 mutually-repressing transcription factors (LacI, TetR) 形成 latch，用 IPTG / aTc / heat 切 state。**parametric design** 关键：rep strength 太弱 → monostable；太强 → 切不动。

## What I actually did
1. **Topology**：Promoter1 (PL_tet) → LacI；Promoter2 (Ptrc) → TetR；LacI represses Ptrc, TetR represses PL_tet
2. **Mathematical model**：ODE (Hill function repression)
   - dx/dt = α/(1 + y^n) - x
   - dy/dt = α/(1 + x^n) - y
   - 双稳态需 α > some threshold + Hill coefficient n > 1
3. **Parameter sweep**：在 (α1, α2, n1, n2) 4D 空间找 robust bistable region
4. **Simulation (Tellurium / SBML)**：模拟切换 dynamics + 状态停留时间 + IPTG dose response
5. **Parts selection**：选合适 promoter strength（pBAD strong, pLac medium, pTet weak）
6. **Reporter**：GFP（state 1）+ mCherry（state 2）双色 readout
7. **Wet lab validation**：plate reader fluorescence 看 bimodal distribution → 真双稳

## ★ 排除/不做的事
- **不做 parametric simulation 直接 build**：参数空间一旦选错 monostable 没用
- **Hill coefficient n = 1 假设**：dimer/tetramer TF repression Hill > 1 才 bistable
- **Single readout state**：bimodal verify 需双 reporter
- **不评估 noise**：molecular noise 可让 robust 双稳 spontaneous switch
- **Plate reader bulk only**：bistable 在 single cell level，bulk 是 mixture average → 看 flow cytometry 才对
- **Forget growth phase effects**：log phase vs stationary 不同 expression

## ★ 失败模式
- **Symmetric design 但不对称 in vivo**：promoter strength 实际不对称 → 偏向一个 state
- **TF protein degradation rate**：half-life 不一让两边动力学不对称
- **Crosstalk**：LacI 弱结合 TetR 操作子 → asymmetric leak
- **Resource competition**：高表达 TF burden cell growth → 慢生长 cell selection
- **Plasmid copy number variation**：cell-to-cell copy variation 影响 state stability
- **Heritable state across division**：daughter cell state 不一定 inherit parent

## Lessons → seeds for rules
1. **ODE simulation + parameter sweep first**
2. **Parts selection** based on simulation suggestion
3. **Two reporters (双色)** for double-state readout
4. **Single-cell flow cytometry** for bimodal verify
5. **Noise modeling**（stochastic SSA）for robustness
6. **Crosstalk + leak measurement**
7. **Growth phase recording**
