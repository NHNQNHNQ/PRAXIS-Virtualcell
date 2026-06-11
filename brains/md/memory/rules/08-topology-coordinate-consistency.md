# 08 非标准聚合体系拓扑-坐标一致性

## 核心规则

对于非标准聚合物（大分子拼接、非标准聚合体系），仅验证坐标文件在盒内是不够的；必须确认拓扑文件（.itp）的原子顺序与坐标文件（.gro/.pdb）的原子顺序一致。不一致时，mdrun 会报 `inconsistent shifts over periodic boundaries` 或 `largest distance involved in such interactions is X nm which is above half the box length`，且放大盒子无法解决根本问题。

## 必查项

### 第一步：拓扑→图构建

从 .itp 文件的 `[ bonds ]` 等区块提取所有原子对，构建拓扑图 G_ref：
```python
from networkx import Graph
from networkx.algorithms.isomorphism import GraphMatcher, categorical_node_match

G_ref = Graph()
for bond in itp_bonds:
    G_ref.add_edge(bond[0], bond[1])
```

### 第二步：PDB CONECT→图构建

从 PDB 的 CONECT 记录提取连通边，构建分子图 G_pdb；注意不同链的 CONECT 完整度可能不同（B 链完整，C 链部分，A 链可能缺失）。

### 第三步：图同构验证

```python
GM = GraphMatcher(G_pdb, G_ref, node_match=categorical_node_match('name', None))
if GM.is_isomorphic():
    mapping = GM.mapping  # 建立拓扑原子编号 → 坐标原子编号的映射
```

### 第四步：键长验证

应用映射后，用拓扑的键列表逐条测量坐标中的键长：
- 正常键：≤ 0.16 nm
- 异常键（拓扑有边但坐标距离 > 1.0 nm）：说明原子顺序不一致

### 第五步：坐标重排

如果键长异常，用映射结果对坐标原子重新排序，重新生成 gro 文件。

## 适用

- 非标准聚合体系（肽聚糖、合成聚合物、拼接大分子）
- 手工拼接的 PDB 坐标
- 任意从非标准来源得到的坐标文件
- mdrun 报 `inconsistent shifts` 错误

## 为什么

- mdrun 的 PBC 错误根因不一定是"原子越盒"，也可能是"拓扑键索引到的原子对在坐标中实际不是邻居"
- CONECT 记录完整 ≠ 原子顺序正确；完整度不一致时尤其要小心
- 图同构提供了拓扑-坐标映射的数学保证，不依赖人工判断

## 修复后的验证

- max bond length ≤ 0.16 nm
- largest excluded distance ≤ ~0.4 nm
- gmx grompp → 生成 .tpr
- gmx mdrun → EM 成功收敛（Fmax < 500）
