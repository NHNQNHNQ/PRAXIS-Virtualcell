---
case_id: drug-009-fep-relative-affinity
project_phase: lead_opt
target_uniprot: P00533 (EGFR)
target_pdb: 1M17
target_class: kinase
indication: NSCLC
modality: small_mol_inhibitor
hit_id_method: na (lead optimization)
tools: [OpenFE 0.7, pmx, GROMACS 2024, OpenMM, Schrödinger FEP+ (commercial reference)]
key_paper_doi: 10.1021/ja512751q   # Wang et al. JACS 2015 — corrected from 10.1021/jacs.5b03720 (404 on CrossRef)
status: validated
validated: true
source: praxis_seed
---

# FEP relative binding affinity：lead 优化时挑哪个 mutation 测

## Background
Lead 优化阶段需在多个候选 R-group 修饰中选 1-3 个进 wet lab。docking score 区分度太低（同 scaffold ± 1-2 kcal/mol），需要更精确的 free energy method。FEP（Free Energy Perturbation）是金标准计算方法，error ~ 1 kcal/mol，但贵（每对 perturbation GPU-h 量级）。

## What I actually did
1. **Setup**：lead compound + 5 个 R-group 修饰候选（一组结构相关 series）
2. **Map 构建**：定 perturbation map（哪个对哪个），尽量 small change（ΔΔG 易收敛）；hub-and-spoke（lead 为 hub）vs chain
3. **Solvent leg + Complex leg**：每对 perturbation 跑 solvated ligand + complex with protein 两套；ΔG_binding = ΔG_complex - ΔG_solvent
4. **Lambda windows**：典型 12-16 window，每 window MD 5-10 ns equilibration + 5 ns production
5. **OpenFE pipeline**：preset network construction + run via OpenFE Atomic-Mapper 自动 atom mapping
6. **Hysteresis check**：forward vs backward 自由能差 < 0.5 kcal/mol = converged
7. **Cycle closure**：当 perturbation 形成 cycle (A→B→C→A) 时 ΔG sum 应 ≈ 0；> 1 kcal/mol = not converged
8. **Validate against experimental** (when available)：top 5 候选 wet lab IC50 vs 计算 ΔΔG，Spearman > 0.7 = OK

## ★ 排除/不做的事
- **跨 scaffold 跑 FEP**：FEP 假设 small perturbation；scaffold hopping 大 change 不可信
- **Single lambda window 数**：< 11 window 收敛性差
- **跳过 cycle closure check**：发现自相矛盾就晚了
- **不区分 protonation states**：候选化合物 pH 7.4 不同 charge state，必须同 charge state 比较
- **Bound water 处理粗糙**：active site water 影响 FEP 结果，需 GCMC water sampling 或显式包含
- **Force field 单一**：GAFF2 vs OpenFF 2.x 给的 ΔΔG 差 1-2 kcal/mol；至少 cross-check
- **不报 statistical error**：FEP 给点估计但 std ~ 0.5-1 kcal/mol，不报 error 等于谎报精度
- **Hysteresis 不查**：forward only run 不可信

## ★ 失败模式
- **Slow degree of freedom 没 sample 到**：active site 中 conformational change（如 P-loop flip）需 100+ ns，5 ns/window 抓不到
- **End state 不稳**：unphysical lambda 中间态原子 collide → simulation crash
- **Net charge change**：从 neutral 到 + 1 charge ligand 的 FEP 需特殊处理（添加 counter-ion + alchemical 修正）
- **Macrocycle / large flexible ligand**：结构 sampling 差，convergence 差
- **Convergence 假象**：5 ns 看似收敛，实际 stuck 在 local minimum
- **Force field 系统偏差**：某个 functional group force field 参数差（如 sulfonamide），整套 FEP 偏
- **Crystal water 决定性**：保留/删除单个关键 water 改变 ΔΔG 1 kcal/mol +

## Lessons → seeds for rules
1. **FEP only for small modifications**（同 scaffold，单 R-group 替换）；scaffold-hop 用 docking + MD
2. **Cycle closure + hysteresis check 必跑**——任一不通过 reject
3. **Lambda windows ≥ 12** + 每 window ≥ 5 ns production
4. **Statistical error 必报**（block average / bootstrap）
5. **Bound water 处理 explicit**（GCMC 或保留 crystal water）
6. **Validate against ≥ 1 experimental data point**——纯 prediction 不发 wet lab
7. **Resource estimate**：1 perturbation ~ 50-200 GPU-h；预算按这个估
