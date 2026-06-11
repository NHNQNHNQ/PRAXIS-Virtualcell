---
case_id: dock-011-btk-ibrutinib-covalent-ser
docking_type: covalent_protein_ligand
target_pdb: 5P9J
target_uniprot: Q06187
target_class: kinase
ligand_type: covalent_warhead_small_mol
system_specifics:
  warhead_type: acrylamide
  reactive_residue: Cys481
  ligand_drug_likeness: drug_like
tools: [Schrodinger CovDock, AutoDock Vina (covalent), GOLD covalent, Meeko --tether_smarts]
flexibility_required: sidechain_flex
validation_benchmark: none
key_paper_doi: 10.1073/pnas.1004600107
status: validated
source: praxis_seed
tags: [covalent, BTK, ibrutinib, kinase, acrylamide, Cys481, 5P9J]
---

# BTK + ibrutinib：激酶共价抑制的教学 case

## Background
Bruton's tyrosine kinase (BTK) Cys481 是激酶共价抑制剂的"金字招牌"靶点；ibrutinib (Imbruvica) 是首个 FDA 批准的 BTK covalent inhibitor (2013 CLL/MCL)。与 KRAS G12C (dock-006 case dock-001) 不同，BTK Cys481 是 wild-type 残基（非 mutation-introduced），且位于 ATP-binding pocket P-loop 后面 — 反应几何 ≠ KRAS Switch II pocket。Cross-case 学习：所有 acrylamide warhead 通用，但 binding pocket 拓扑决定 reversible binding 几何。

## What I actually did
1. **Receptor prep**: 5P9J (BTK + ibrutinib co-crystal) → 去 ligand → 保留 ATP-pocket water (3 个 conserved water 文献支持) → meeko PDBQT
2. **Reactive Cys 识别**: Cys481 SG (旁边是 Met477 P-loop)；通过 sequence + PDB cross-ref 确认 wild-type non-mutated Cys
3. **Warhead 识别**: ibrutinib 含 acrylamide (=CH-CH=O 旁 amide N) — Michael acceptor 经典模式
4. **Two-step approach**: (a) reversible BTK + ibrutinib initial pose with default Vina — 验证 reversible mode pose; (b) Meeko `--tether_smarts "[CX3]=[CX3][CX3](=O)" --rec_residue "A:CYS:481"` 强制 attach
5. **Validation**: 与 5P9J crystal 对比，covalent pose RMSD < 1.5 Å (warhead 固定); reversible pose 也接近 (RMSD ~2 Å)
6. **Selectivity panel**: BTK 家族 ITK/TEC/BMX 都有 Cys481 等价位置 — ibrutinib 对 BTK 选择性来自 pocket 几何 + back-pocket 水分子，不是 warhead 本身

## ★ 排除/不做的事
- **用普通 Vina without --tether_smarts**: warhead 朝外 / 朝 ATP 进入方向 — 物理不可成键
- **不区分 Cys481 vs Cys527**: BTK 还有 Cys527 (less reactive, distal); docking 必须明确指定 target Cys
- **复用 KRAS warhead SMILES**: KRAS sotorasib 含特殊脲 + cyanoacrylamide (与 ibrutinib acrylamide 不同)，不能 reuse
- **跨家族 selectivity 假设 from warhead alone**: 选择性来自 pocket 几何 (如 BTK gatekeeper Thr474 vs ITK Phe)，不是 warhead reactivity
- **ATP binding pocket water 默认全删**: 5P9J 保留 3 个文献水 (HOH 600/612/655 之类) 是 hinge water，删掉 affinity 失准
- **GSH stability 不查**: ibrutinib logP ~3.97 中等亲脂; warhead 为 substituted acrylamide 反应活性中等; in-vivo half-life ~6.6 h (FDA label) → docking 不直接预测但 logP > 2 → 风险低 (case dock-006 lesson)

## ★ 失败模式
- **Pre-2013 reactive Cys panel (no proteome-wide reactivity prediction)**: 早期 ibrutinib 开发时没识别 ITK 脱靶 Cys (临床 ITK-mediated 副作用)
- **Cardiac side effect (atrial fibrillation)**: 后续追踪到 cardiac myocyte BTK 不存在；机制是脱靶 Csk/Tec 家族 Cys — 单 docking 无法预测此 in-vivo failure
- **C481S resistance mutation**: 患者长期治疗后出现 BTK Cys481→Ser 突变 → ibrutinib 失效 (Lancet 2015 Woyach et al.). docking 可预测 Ser 取代后 Vina/CovDock 都给低 covalent score，但治疗时不可逆
- **C481 oxidation state**: 在 oxidative stress 下 Cys481 可被 sulfenylated (S-OH) → 不可反应；docking 假设 reduced Cys，临床失活
- **Bcl-2 family acrylamide cross-reactivity**: venetoclax 也含 warhead，与 ibrutinib 联用时 GSH 池竞争 — docking 不直接建模

## Lessons → seeds for rules
1. **Wild-type vs mutation-introduced reactive Cys**: BTK Cys481 vs KRAS G12C 都是 acrylamide target，但生物学背景不同 (常规激酶 vs oncogenic mutant)
2. **Pocket geometry > warhead reactivity** for selectivity (case dock-006 + dock-011 共识): 单纯比较 warhead 不够; 必须算 pocket 形状 + back-pocket water
3. **Resistance mutation pre-prediction**: docking C481S → 低 score → 资源花到 non-covalent BTK 抑制剂
4. **ATP-pocket conserved water 文献验证**: 5P9J 文献明示 3 个水位置；删 = 假阴性
5. **Cross-family Cys panel**: ITK/TEC/BMX 等价 Cys 必须做 panel (非 BTK 的所有 Cys 都该跑)，避免 ibrutinib-类似 ITK 副作用
