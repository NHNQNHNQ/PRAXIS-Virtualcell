---
case_id: dock-016-protac-ternary-vhl-brd4
docking_type: protein_protein_with_restraints
target_pdb: 5T35
target_uniprot: [P40337, O60885]
target_class: PROTAC_ternary
ligand_type: protein
system_specifics:
  interface_type: induced_protac
tools: [PRosettaC, Schrodinger PROTAC, Glide-Maestro, AlphaFold-Multimer, HADDOCK with custom topology]
flexibility_required: backbone_flex
validation_benchmark: CAPRI
key_paper_doi: 10.1038/nchembio.1858
status: validated
source: praxis_seed
tags: [PROTAC, ternary, VHL, BRD4, MZ1, induced_proximity, 5T35, E3_ligase]
---

# PROTAC ternary complex (VHL + MZ1 + BRD4): 诱导邻近 docking 的特殊性

## Background
PROTAC (PROteolysis-TArgeting Chimera) 由 E3 连接酶 ligand + linker + 目标蛋白 ligand 组成（heterobifunctional），诱导 E3-target 三元复合物形成 → 目标蛋白泛素化降解。
docking 难点：
1. **三元复合物 (E3 + linker + target)** ≠ 标准 PP docking — linker 长度/构象决定可成相对方位；
2. **Cooperativity (α factor)**：positive cooperative PROTAC 的 protein-protein interface 比 ligand-only binding 更 stable；
3. **Crystal-validated cases sparse**: 5T35 (MZ1 in VHL+BRD4), 6BOY, 6HAY, 6HAX 等少量复合物；
4. **Linker conformational sampling**：~10-20 旋转键的柔性 PEG/烷基链需 ensemble。
Gadd 2017 (5T35) 是 PROTAC ternary docking 的金标准 reference。

## What I actually did
1. **Binary inputs prep**:
   - VHL (E3 substrate-recognition subunit): apo / holo from 4WQO chain V (with VHL ligand bound at its pocket)
   - BRD4 BD1 (target): apo from 5T35 chain B 或 holo with JQ1
2. **Linker library**: MZ1 SMILES `OC1CCC(O)C(=N1)C1=NN(C2=CC=CC=C2C3=CC=CC=C3)C(=N1)NC(=O)CCCCCN(C(=O)CCCN[C@@H](C(=O)N1CC[C@H](C1)O)C(C)(C)C)C(C)(C)C` (~50 atoms, ~14 rotatable bonds) — split linker (PEG3) from VHL ligand and JQ1 ligand
3. **Three-method consensus**:
   - **PRosettaC** (Eisenberg lab): rigid-body PP sampling + linker MC sampling + Rosetta scoring → top ternary models
   - **AlphaFold-Multimer + AF3-style with bound ligand**: sequence + ligand co-fold (Boltz-1 supports this)
   - **HADDOCK custom topology**: ligand atoms 作 ambiguous restraints between the two pockets
4. **Validation against 5T35 crystal**: top model interface RMSD < 3 Å (CAPRI medium); linker conformer matches crystal Φ/Ψ
5. **Cooperativity α calc**: dock target-only K1, dock E3-only K2, dock ternary K3 → α = K3/(K1·K2) → α > 1 = positive cooperative
6. **Linker SAR**: change PEG length 2/3/4 → re-dock → predict α change (4 was optimal in MZ1 paper)

## ★ 排除/不做的事
- **Single-step三元 docking via standard PP docker**: linker 在 docking 中 unfolds → false negatives
- **Skip linker conformational sampling**: rigid linker assumption gives single (often wrong) ternary geometry
- **Use linker SMILES alone with vina_gnina_dock on bare target**: ignores E3 contribution; PROTAC efficacy = 三元 stability not单 ligand affinity
- **AlphaFold-Multimer without ligand co-fold**: protein-protein only预测 misses ligand-induced 接触面
- **Apo-apo docking (both proteins ligand-free)**: PROTAC is 诱导邻近 — need bound state of at least one side
- **Predict cell efficacy from docking score alone**: degradation efficiency ≠ ternary stability (proteasome accessibility, ubiquitination kinetics also matter)
- **Forget intracellular E3 expression**: VHL ubiquitous, but CRBN tissue-specific; selectivity from E3 expression not pure docking

## ★ 失败模式
- **Hook effect at high PROTAC concentrations**: 高浓度 PROTAC 占满 binary binding sites → 三元 complex 减少 → docking 不直接预测
- **Negative cooperativity** (α < 1): some PROTAC linkers actively disrupt 接触面 — docking score gives no warning, only cell degradation assay confirms
- **Linker length suboptimal**: PEG3 vs PEG4 vs PEG5 can change α by 10x — docking sampling at each length needed
- **E3 cycle dependency**: VHL needs Cul2-Rbx1-ElonginB/C; PROTAC works only when full E3 ligase complex assembles — docking 单 VHL 部分不够
- **Off-target degradation**: BRD4 vs BRD2 vs BRD3 selectivity from PROTAC linker — 难 capture by ligand-only docking
- **Resistance via E3 mutation**: VHL HIF1α-binding residues mutated in some clear cell carcinoma → PROTAC fails — docking needs WT E3 reference
- **Non-degrader binders (false positives)**: high α ternary stability without degradation if proteasome can't access target lysines

## Lessons → seeds for rules
1. **PROTAC docking 用 PRosettaC / Boltz-with-ligand-co-fold / HADDOCK custom**, NOT standard PP docking
2. **Linker conformational ensemble (5-10 representative conformers) mandatory** — 不能 rigid linker
3. **Cooperativity α calculation**: K_ternary / (K1 × K2); α > 1 = positive
4. **5T35-class CAPRI quality** (interface RMSD < 3 Å) is the reference benchmark
5. **E3-target combinatorics**: 任何 new PROTAC project must check VHL/CRBN/IAP/MDM2 — selectivity 来自 E3 choice
6. **Cell efficacy ≠ docking score**: bind validation + degradation assay 两步独立
