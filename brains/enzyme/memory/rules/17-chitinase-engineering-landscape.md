---
rule_id: 17-chitinase-engineering-landscape
schema_version: 1
rule_type: landscape
applies_to:
  cazy_families: [GH18, AA10]            # GH18 hydrolytic + AA10 oxidative LPMO 协同
  property: substrate_specificity        # 主线: processivity / endo-exo mode 选择 / chito-oligo 长度控制
  enzyme_classes: [hydrolase, oxidoreductase]
evidence_cases:
  - GH18-horn-2006-febsj                 # Sm ChiA/B/C processivity 系统比较
  - AA10-vaaje-kolstad-2010-science      # AA10 LPMO + chitinase 协同 paradigm
confidence: cold_start                   # 仅 2 evidence cases, 但跨 hydrolytic + oxidative 两类
last_updated: 2026-04-28
---

## 规则

几丁质降解酶工程化按以下决策树:

1. **首先识别协同 system, 不只是单酶**: 工业 / 高效 chitin 降解 必须 GH18 chitinase + AA10 LPMO 协同 — single-enzyme 工程化路线收益有限
2. **选 GH18 sub-mode 据目标产物**:
   - 短链 chito-oligo (DP 2-4): processive exo (ChiA-类, ChiB-类), 单 binding 内多次切, 产物均一
   - 长链 chito-oligo (DP 4-8) + endo cut: non-processive endo (ChiC-类), 起切 internal
   - 完全降解 chitin → GlcNAc 单体: 需 chitinase + β-N-acetylhexosaminidase 配合
3. **GH18 单 catalytic Glu (DXE / DXDXE motif) 严格保留**: 与 GH7 / GH11 双 Asp/Glu 不同, GH18 仅一 acidic residue
4. **Processivity 调控 = +1/+2 subsite aromatic stacking**: cleft 内 Trp / Tyr 数量决定 substrate sliding 模式; mutate aromatic 切换 processive ↔ endo
5. **AA10 LPMO 必需 reductant + Cu**: 工程化 AA10 时 reductant supply (ascorbate / cellobiose dehydrogenase) 是 system-level 变量, 不是单酶变量
6. **Substrate scope (chitin vs cellulose vs β-glucan) 由 substrate-binding flat surface aromatic patch 决定**: AA9 偏 cellulose, AA10 偏 chitin, 跨家族 mutation 转移率低

**强制排除区**:
- **GH18**: 唯一 catalytic Glu (DXE/DXDXE motif) ±3 残基 + 二级 sphere proton transfer Tyr/Asp + substrate-binding aromatic Trp/Tyr (凡 mutate 必须显式测试 mode 切换)
- **AA10**: His brace (N-端 His + 内部 His Cu 配位) + N-端 N(δ) methylation site (真菌 AA9 必需, 细菌 AA10 多无 methyl 但 backbone 重要) + substrate-binding flat aromatic patch

## 依据

| evidence_case | 关键观察 |
|---------------|---------|
| `GH18-horn-2006-febsj` | Sm 三个 chitinase (ChiA / ChiB / ChiC) 系统比较 mode + processivity; +1/+2 aromatic stacking 是 mode 控制位 |
| `AA10-vaaje-kolstad-2010-science` | CBP21 (AA10) + chitinase 协同显著提升 chitin 降解效率; LPMO 单酶不是高 kcat 酶, 工程化必须 system-level |

## 边界

- 仅 GH18 + AA10 两个家族; GH19 plant chitinase 是不同 fold (lysozyme-like), 单独 landscape (待补 case)
- AA10 reductant supply 是 fundamental requirement, 不是 enzyme 工程化可解决
- chitinase 单酶降解 crystalline chitin 不可期待; 必须 + LPMO + 部分 enzymes 协同
- **跨 LPMO 家族 (AA9 ↔ AA10 ↔ AA11)** mutation 转移率低 (AA9 偏 cellulose, AA10 偏 chitin, AA11 偏 chitin 与 cellulose 中间态)

## How to apply

- **Scoping Agent**: 识别用户目标 (chito-oligo 长度 / 完全降解 / 等) → 选 endo vs exo + 是否需 LPMO 协同
- **Design Agent**: 按 GH18 mode 选 mutation 策略; processivity 调用 +1/+2 aromatic stacking; cofactor 系统 (Cu / reductant) 列入 system-level requirements
- **Execution Agent**: HPLC / MS 检 chito-oligo product distribution 验证 mode (不只 single kinetic 数据)
- **Reviewer**: 检 GH18 catalytic Glu 排除 + AA10 His brace 排除; 检 reductant supply 是否 explicit; 检 chitinase + LPMO 协同 是否考虑

## 升级路径

升 `confidence: medium` 需要再增 ≥1 GH19 evidence case + ≥1 AA11 / AA13 LPMO case + 至少 1 chitinase 工程化失败案例.
