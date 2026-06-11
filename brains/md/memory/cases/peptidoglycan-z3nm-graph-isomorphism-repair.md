---
case_id: md-peptidoglycan-z3nm-graph-isomorphism-repair
sim_type: standard
domain: polymer_assembly_md
target: "肽聚糖 z3nm 体系 (peptidoglycan + DAA/DAF 药物插入)"
tools: [GROMACS, CHARMM36, networkx]
status: validated
schema_version: 1
source: agent_run
tags: [GROMACS, peptidoglycan, graph-isomorphism, PBC-error, PGSHEET, topology-rebuild, insert-molecules, neutralization, energy-minimization, CHARMM36]
---

# 肽聚糖 z3nm 体系图同构坐标修复与药物插入复盘

- 领域: molecular_simulation
- 标签: GROMACS, peptidoglycan, graph-isomorphism, PBC-error, PGSHEET, topology-rebuild, insert-molecules, neutralization, energy-minimization, CHARMM36

## 背景

在 `peptidoglycan-layer-pre-equilibration` 案例的 `pgsheet6` 体系基础上，本轮需要：

1. 构建 z3nm 长度周期的肽聚糖层新基底（盒长从约 19.7 nm 缩短到约 13.3 nm）
2. 将新基底复制到 `tangju_A`（含 10 个 DAA 配体）和 `tangju_F`（含 10 个 DAF 配体）两个独立体系目录
3. 完成溶剂化、中和、NVT/NPT 预平衡和 500 ns 生产 MD
4. 将经验安全写回大脑

## 核心问题

### 问题 1：mdrun 报 inconsistent shifts over periodic boundaries

在 `tangju_A` 体系上首次运行能量最小化时，mdrun 报错：

```
Fatal error: There are inconsistent shifts over periodic boundaries
in a molecule type consisting of 7101 atoms.
The longest distance involved in such interactions is 7.446 nm
which is above half the box length.
```

这个 7101 是 PGSHEET（3 条链 × 每链 2369 原子 + 配体 + 溶剂）的大分子原子数。

**根因**：旧 PDB 坐标文件的原子顺序与 `PGSHEET.itp` 拓扑顺序不一致。用 PGSHEET.itp 的键索引去量坐标中的原子对，出现了大量假长键（7214 条键中 6829 条 > 1.0 nm），导致 GROMACS 认为存在跨越半个盒子的键，从而触发 PBC 不自洽错误。

**为什么旧坐标顺序是错的**：`3_5_7_danwei_reordered_aligned_cba_z.pdb` 中三链的 CONECT 记录完整度不一致（B 链完整 7214 条，C 链部分 2148 条，A 链为 0），排序依赖 CONECT 导致原子被错误分组。

### 问题 2：常规 PBC 修复手段全部无效

尝试了以下方法，均失败：

- BFS 整分子展开：展开后原子跨度达 122 nm（因为越盒原子被错误拉向另一侧）
- `gmx trjconv -pbc mol`：同样报 inconsistent shifts
- 放大盒子到 15.5 nm、30 nm：largest excluded 数值增大但 PBC 错误持续
- 整体平移 0.05/0.10 nm：同样失败

**根本原因**：问题的根源不是"某些原子在盒外"，而是"原子顺序与拓扑不匹配"，放大盒子不能解决根本问题。

## 过程摘要

### 步骤 1：图同构建立精确原子映射

使用 `networkx.algorithms.isomorphism.GraphMatcher` 进行图同构分析：

1. 用 `PGSHEET.itp` 的 7214 条 bonds 构建参考图 G_ref，节点为原子编号，原子类型属性为 "name"
2. 从 PDB 的 B 链 CONECT（完整 7214 条边）构建比较图 G_B
3. 用 `GraphMatcher(categorical_node_match('name', None))` 验证：B 链 ↔ PGSHEET.itp **严格图同构**，mapping 长度 = 2369
4. 将该映射应用到 A 链（原子名分布与 B 完全一致），验证后键长 max = 0.155 nm，完美

关键代码：
```python
from networkx import Graph
from networkx.algorithms.isomorphism import GraphMatcher, categorical_node_match

def build_graph_from_itp(itp_path):
    G = Graph()
    # bonds section...
    return G

def build_graph_from_conect(pdb_path, chain):
    # parse CONECT records for given chain
    return G

GM = GraphMatcher(G_B, G_ref, node_match=categorical_node_match('name', None))
if GM.is_isomorphic():
    mapping = GM.mapping  # 建立原子编号映射
```

### 步骤 2：重建正确坐标文件

- 将 B 链图同构映射应用到三链（原子名相同，套用相同映射）
- 用 C→B→A 质心方向定义为新 Z 轴，做旋转变换
- 坐标平移：将所有原子移入 `[0, box)` 范围（shift = -mins + [0.5, 0.5, 0.5] nm）
- 手动写入 `system_z3nm_correct.gro`：手动构造 gro 的 title/atoms/box 行，box = `12.06130 7.05730 13.30200`
- 验证键长：max bond = 0.1556 nm（优秀），largest excluded distance = 0.396 nm（正常）

### 步骤 3：溶剂化与药物插入

- `gmx solvate`：生成 `system_z3nm_correct_solv.gro`（PGSHEET 3 + SOL 30207）
- 复制到 `tangju_A/` 和 `tangju_F/` 作为 `system_z3nm.gro`
- 生成药物插入坐标文件 `ligand_insert_centered.gro`（药物质心放在盒子中心）
- `gmx insert-molecules -try 20000 -dr 2 2 2 -rot xyz`：tangju_A 插入 10 个 DAA，tangju_F 插入 10 个 DAF
- 同步更新 `topol.top`：`[ molecules ]` 中 PGSHEET 3, SOL, SOD, DAA/DAF 数量

### 步骤 4：中和与 EM 验证

- `gmx genion`：中和电荷（`SOD 64`），生成 `system25_z3nm_neutral.gro`
- 逐原子检查 SOD 坐标是否在盒内（`x % box[n]` 逐条验证）
- `gmx grompp + gmx mdrun`：能量最小化
  - tangju_A: Steepest Descents 收敛到 Fmax < 500，耗时 4746 步，Fmax = 485
  - tangju_F: 收敛耗时 3281 步，Fmax = 469

## 结果与学到什么

- **拓扑顺序与坐标原子顺序必须一致**：这是 GROMACS 能正确处理 PBC 的前提。对于非标准聚合体系（如肽聚糖），CONECT 记录的完整度可能是误导——完整不等于正确，需要图同构验证。
- **图同构是建立拓扑-坐标映射的最可靠方法**：`categorical_node_match('name', None)` 可以正确处理原子类型名的匹配，零误匹配。
- **放大盒子不能解决根本问题**：如果原子顺序错了，任何基于"让原子在盒内"的技巧都是表面修复。
- **药物插入用 `-try 20000`**：当体系较稠密时，`-try 3000` 可能只插入 8-9/10，`-try 20000` 能稳定插入全部 10 个。
- **genion 后的 topol.top 必须同步更新**：`grompp` 会严格按照 gro 文件中的分子计数，不一致会导致 invalid order。
- **中和后逐原子验证 SOD 在盒内**：中和引入的新原子可能越盒，这恰好是 inconsistent shifts 错误的直接触发点。
- **能量最小化成功（Fmax < 500）是体系质量的最低可信标准**：即使前几步通过 grompp，如果 EM 爆炸或报 PBC 错误，说明体系存在根本性拓扑/几何问题。

## 关联案例

- `peptidoglycan-layer-pre-equilibration`：本案例的前序，建立了 PGSHEET 拓扑和 pgsheet6 体系经验
- `peptidoglycan-z3nm-graph-isomorphism-repair`：本案例，z3nm 新基底 + 图同构修复 + tangju_A/F 药物插入
