---
name: auto-docking
description: 自动化蛋白-配体（enzyme-substrate / inhibitor / cofactor）分子对接的标准工作流。覆盖受体准备、配体准备、活性位点定位、对接执行、pose 验证以及对接结果向 MD 的交接。优先使用本地 AutoDock Vina / smina 路线，禁止默认依赖网页对接服务。
host_env: praxis-dock
---

# Auto-Docking Skill

## 目的

收到"对接 / docking / 配体识别 / 抑制剂结合 / 底物结合姿势 / 共价对接"类任务时，给出一条**本地、可复现、与下游 MD 自然衔接**的对接路线。这条 skill 不存案例细节，只保留可复用的方法、工具选型规则、参数默认值、失败兜底。

## 总判断（先回答这 5 个问题再动手）

1. **对接的目标**是什么？打分排序 / 结合姿势 / 关键接触识别 / 共价 warhead / 底物 vs 产物状态？
2. **受体是酶吗**？有催化残基（Asp/His/Glu/Cys/Ser）、辅因子（Mg²⁺、Zn²⁺、NAD/FAD/CoA、heme 等）、需要质子化态判定的话，必须按"催化-中心校准 + 正确质子化态"路线（见下文§3）。
3. **配体来源**是 SMILES、SDF/MOL、co-crystal、自合成？决定准备路线。
4. **是否需要共价对接**？如果是 warhead-亲电基团 → Cys/Ser 的酶（如 Mpro, Cathepsin, KRas G12C），走 covalent docking（§6.4）。
5. **下游做不做 MD**？做的话 pose 输出必须能直接进入 §7 hand-off。

如果以上任何一项不清楚，先问用户而不是凭猜想跑。

---

## §1 工具选型与默认路线

### 默认对接引擎（按推荐顺序）

| 引擎 | 适用 | 特点 | 何时用 |
|---|---|---|---|
| **AutoDock Vina v1.2+** | 标准非共价 | 最广泛验证，Python API + 命令行 | **默认首选** |
| **smina** | 标准非共价 | Vina fork，自动检测 box，支持 custom scoring | 当不知道精确 box 时；小分子库筛选 |
| **gnina** | 标准非共价 | smina + CNN 重打分 | 需要更可靠 ranking 时 |
| **AutoDock Vina (covalent)** | 共价 | 1.2+ 原生支持 covalent docking | warhead 已知的共价抑制剂 |
| **rDock** | 灵活 | 支持核酸 / 复杂 pocket | 配体 binding pocket 是 RNA / 含金属 |

### 禁止默认走的路线（hard rule 7 适用）

- ❌ 仅依赖 SwissDock / DockingPie / 任何网页对接服务作为主要结果（可作交叉验证，不能作主路线）
- ❌ 默认拿 `prepare_receptor4.py` / MGLTools 不报错就当受体准备完成（必须人工/脚本核对添加 H、电荷、PDBQT atom-types）
- ❌ 跳过 box 中心定义凭直觉框选（必须从 ligand co-crystal / fpocket / known catalytic residues 推导）
- ❌ 把 docking 输出 .pdbqt 直接当 MD 起始构象（pose 必须经 §5 验证 + §7 转换）

---

## §2 依赖前置检查

收到对接任务，先检查本地是否有：

```bash
which vina smina gnina obabel             # 对接 + 配体格式转换
which prepare_receptor4.py prepare_ligand4.py   # ADFR / MGLTools
python -c "import rdkit; import meeko; import vina"  # Python 路线必备
which fpocket                              # 活性位点检测
```

缺什么补什么。conda 安装顺序（写到 `md-dependency-bootstrap` 之外的 docking-bootstrap）：

```bash
conda install -c conda-forge autodock-vina openbabel rdkit meeko fpocket
pip install vina  # Python 接口
```

如果 ADFRsuite / MGLTools 不在 PATH，作为后备用 `meeko` 全 Python 路线（meeko 提供 `mk_prepare_ligand.py` / `mk_prepare_receptor.py`，能完全替代 prepare_*.py）。

不准在依赖未到位前用网页对接代替。

---

## §3 受体准备（酶专用路线）

### 标准 7 步

1. **下载/确认 PDB**：从 RCSB / PDB-REDO 取，优先共晶（含已知配体的 holo）作为 box 定位锚点。
2. **结构清洗**：删除 alt locs（保留 occupancy 最高）、删除 crystallographic waters（保留 catalytic / structural waters 单独标注），删除 polyethylene glycol / glycerol 等结晶辅料。
3. **缺失残基修复**：用 `pdbfixer` / `Modeller` / `pymol` 补 loop。如果是催化残基缺失，**停手报告**——这种 PDB 不能用。
4. **质子化态**：用 `pdb2pqr30 --ff=AMBER --with-ph 7.4` 或 `propka3`。**酶的催化残基必须人工 review 输出**，特别注意：
   - **His** in catalytic dyad/triad: HIE vs HID 决定亲核性方向（看与 Asp/Cys/Ser 的 H-bond 几何）
   - **Cys** thiolate (Cys−) vs thiol (CysH): 看 pKa 微环境，催化半胱（如 Mpro Cys145）pKa 通常 < 7
   - **Asp/Glu** in catalysis: 通常 ASH/GLH（质子化）或 ASP/GLU（去质子）—— 必须看催化机制
5. **辅因子保留**：对**酶**而言金属离子（Zn²⁺、Mg²⁺、Mn²⁺、Fe²⁺/³⁺）、heme、NAD/FAD/CoA、糖基化必须保留。这些不是杂质，是催化中心的一部分。
6. **加电荷 + 转 PDBQT**：
   ```bash
   prepare_receptor4.py -r receptor_clean.pdb -o receptor.pdbqt -A "checkhydrogens" -U "nphs_lps_waters_nonstdres"
   # 或 meeko:
   mk_prepare_receptor.py -i receptor_clean.pdb -o receptor.pdbqt --rigid_polymer
   ```
7. **核对 PDBQT**：grep 检查所有 catalytic residues 的原子都在；金属用 `Mg`, `Zn` 等正确原子类型而不是 `M`。

### 酶特异 review checklist（必须勾完才进入对接）

- [ ] 催化残基侧链都在
- [ ] 辅因子（金属/NAD/FAD/heme）参数正确
- [ ] 质子化态在催化 pH (默认 7.4) 下与机制一致
- [ ] 共价附着位点（如 Cys145 of Mpro）的 SG 原子可达
- [ ] 受体 box center 已锁定到催化中心（§4）

---

## §4 活性位点定位 / box 定义

### 三种来源（按优先级）

1. **co-crystal ligand**（首选）：从原 PDB 中保留一个共晶配体计算其几何中心 → 作为 box center；box size = ligand 尺寸 + 5 Å buffer。
   ```bash
   pymol -c -q -d "load receptor.pdb; select lig, resn <LIG>; print cmd.get_extent('lig')"
   ```
2. **literature / catalytic residues**：拿 1-3 个文献明确的催化残基（如 Mpro: Cys145+His41, Trypsin: Ser195+His57+Asp102）算 Cα 几何中心。
3. **fpocket / autodetect**：当 1, 2 都不可用时：
   ```bash
   fpocket -f receptor.pdb
   # 取打分最高的 pocket，从 pocket1_atm.pdb 计算几何中心
   ```

### Box 大小规则

- **小分子抑制剂 / substrate**：22 × 22 × 22 Å（默认）
- **柔性长配体（peptide-like, lipid head, MRTX1133-like）**：30 × 30 × 30 Å
- **Vina exhaustiveness**: 默认 32，重要 case 升到 64 - 128

---

## §5 配体准备 + 对接执行

### 配体准备（SMILES → PDBQT）

```bash
# RDKit 生成 3D + 优化
python -c "
from rdkit import Chem
from rdkit.Chem import AllChem
mol = Chem.MolFromSmiles('<SMILES>')
mol = Chem.AddHs(mol)
AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
AllChem.MMFFOptimizeMolecule(mol)
Chem.MolToMolFile(mol, 'lig.mol')
"
mk_prepare_ligand.py -i lig.mol -o lig.pdbqt   # meeko, gives correct partial charges
```

如果配体含有 stereocentres / tautomers ambiguous，必须**枚举**所有合理构象/质子化态（`enumerate_tautomers`, `EnumerateStereoisomers`），全部对接，最后按打分 + binding mode consistency 选。

### 对接执行（Vina 标准）

```bash
vina --receptor receptor.pdbqt \
     --ligand lig.pdbqt \
     --center_x <Cx> --center_y <Cy> --center_z <Cz> \
     --size_x 22 --size_y 22 --size_z 22 \
     --exhaustiveness 32 \
     --num_modes 20 \
     --energy_range 4 \
     --out lig_out.pdbqt --log lig.log --seed 42
```

### Pose 验证（必查 4 项）

1. **打分**：top pose ΔG ≤ −7 kcal/mol（弱结合 −5 到 −7，强结合 < −9）。
2. **关键接触**：top pose 必须命中至少 2/3 已知关键残基（从文献或 co-crystal 抽出）。脚本：
   ```python
   from rdkit import Chem
   import MDAnalysis as mda
   # 计算 lig 任意原子 ↔ key_res 任意原子 < 4.0 Å 的对数
   ```
3. **Pose 多样性**：top-5 中至少 3 个 pose RMSD < 2 Å（聚类一致），否则 binding mode 不可靠。
4. **几何合理性**：肉眼或 PyMOL 看不能有 sterically 撞到金属/骨架；H-bond 不能反向。

任何一项不过 → 回到 §3-§4 检查（最常见原因：质子化态错、box 偏移、配体构象未充分采样）。

---

## §6 特殊场景

### §6.1 金属配位酶（Zn / Mg / Fe / Mn）

- 金属作为 receptor 的一部分（不要去掉），用 Vina 的 metal-aware 设置：
  ```bash
  prepare_receptor4.py -r ... -A "checkhydrogens" -U "nphs_lps_waters_nonstdres" -e
  ```
- 配体若有金属配位基团（羧酸、磷酸、咪唑），打分往往低估，必须靠 §5 关键接触验证。
- 若 metal-binding 是核心（matrix metalloproteinase, carbonic anhydrase, HIV integrase），考虑 **rDock** 或专门的 GFN-FF/QM-MM scoring。

### §6.2 辅酶酶（NAD / FAD / heme）

- 辅酶在受体内**保留**，作为 rigid 部分。
- 底物在邻接 pocket（NAD pocket 旁的 substrate pocket）docking。
- 若需要看 hydride transfer / electron transfer 几何，建议用反应坐标分析而非 docking。

### §6.3 底物 vs 产物 / 反应中间体

- 底物 docking：用 ground-state geometry。
- 产物 docking：用 post-reaction geometry（C=O 改 C-OH 等），对比看产物释放路径。
- 反应中间体（tetrahedral intermediate, oxocarbenium）需要 QM/MM 才可靠，docking 仅作起点估计。

### §6.4 共价对接（warhead 已知）

- AutoDock Vina 1.2+ 原生支持：
  ```
  vina --receptor rec.pdbqt --ligand lig.pdbqt \
       --covalent_residue <chain>:<resname><resid>:<atom> \
       --covalent_lig_atoms a1,a2,a3 \
       ...
  ```
- 或用 GOLD / CovDock 路线。
- warhead 类型与对应 anchor 原子：
  - Michael acceptor（α,β-unsaturated carbonyl）→ Cys-SG
  - α-haloketone → Cys-SG
  - Aldehyde / nitrile → Cys-SG / Ser-OG（reversible）
  - Sulfonyl fluoride → Tyr-OH / Lys-NZ / Ser-OG / Cys-SG

### §6.5 Substrate-protein 对接（非小分子）

- 短 peptide 用 GalaxyPepDock / HPEPDOCK / Vina-flex (peptide mode)。
- 长 peptide / 蛋白-蛋白用 HADDOCK / ZDOCK / RoseTTAFold-AA 。

---

## §7 对接 → MD 交接（与 md-build-run skill 对接）

成功 pose 选定后，**直接进 MD 时必须做 4 件事**：

1. **从 PDBQT 转回 PDB**：`obabel lig_out.pdbqt -O lig_pose.pdb -d -h`，删除 PDBQT 特有 atom-type 后缀。
2. **配体重命名**：将配体的 resname 设为 3 字母 unique 标识（如 `LIG`），并和受体合并成单一 PDB（`pymol` 或 `cat`）。
3. **配体力场参数化**：走 `md-build-run` skill 的小分子参数化路线（CGenFF for CHARMM36，AmberTools antechamber + GAFF2 for AMBER）。**禁止**用 docking 出来的 PDBQT charge 当 MD charge。
4. **complex 验收**：`gmx grompp` 通过 = 进入 MD；不通过 = 回到 §3-§5 检查。

### MD 起始 box 建议

- 受体盒子 buffer 至少 1.2 nm（dodecahedral or cubic）
- 配体在 buffer 范围内，不要靠近 box 边
- 离子化用 `gmx genion -conc 0.15` 加 0.15 M NaCl
- 若是膜蛋白酶（如 GPCR with substrate），交给 `md-build-run` 的膜蛋白路线

---

## §8 写回（Hard Rule 8 适用）

对接任务结束后，仅以下内容值得入 memory / skill：

- **稳定的工具/参数选择**（如 "Mpro 共价对接走 Vina 1.2 covalent + Cys145:SG anchor"）
- **失败模式 + 修复**（"Zn 受体 Vina 默认会忽略金属 → 必须 -e 选项"）
- **对接 → MD 交接的踩坑**（"PDBQT 充电直接拿来当 MD 起始 charge → 拓扑错误"）

不准入：单次跑出来的具体打分值（不稳定）、网页对接结果包装（违反 hard rule 7）。

---

## 与其他 skill 的关系

- `pdb-literature-report`：受体来源 / 文献催化残基提取
- `md-build-run`：对接 pose → MD 起始构象
- `md-gromacs`：下游 grompp / mdrun
- `research`：把对接 + MD 联合证据组织成机制报告
- 案例参考（按相关性）：`hiv-1-md`（蛋白-抑制剂复合体 MD 模板）、`melatoninmt1-200ns-well-tempered-metadynamics`（结合姿势 + 自由能）、`iaa`（小分子穿膜 → 与 docking 思路差异）

## 不适用场景（明确写出避免误用）

- 蛋白-蛋白 docking（用 HADDOCK / ZDOCK，不在本 skill 范围）
- 核酸-小分子 docking（用 rDock / RNAcommender）
- 大分子折叠 / co-folding（用 AlphaFold-Multimer / RoseTTAFold-AA）
- 纯 virtual screening 百万级（用 GPU-Vina / Glide / OpenEye OEDocking 商业流水线）

## Forbidden behaviours

- ❌ 不做受体清洗就对接
- ❌ 没确认催化残基的质子化态就对接酶
- ❌ box center 凭感觉框
- ❌ 单一 pose 不做多样性验证就报告 binding mode
- ❌ 把 docking ΔG 直接当 binding affinity（必须做 §5 4 项验证再决定可信度）
- ❌ 把 docking 输出未经 force-field 重参数化直接进 MD

## 输出契约

```json
{
  "skill_id": "auto-docking",
  "receptor": "",
  "ligand": "",
  "best_affinity": 0.0,
  "poses": [
    {
      "rank": 1,
      "affinity_kcal_per_mol": 0.0,
      "pose_path": ""
    }
  ],
  "runtime_sec": 0.0,
  "diagnostics": {
    "brain": "Naruto-main",
    "archetype": "docking"
  }
}
```
