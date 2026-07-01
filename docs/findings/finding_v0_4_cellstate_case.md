# finding v0.4 W5.2 — Human 免疫激活 cell-state case:IFN-β → ISG 激活(真跑)

> 目标:**填补 State/fate 空白应用**。把输出从"表达/生长"扩到 **cell state 迁移**:IFN-β 刺激 → 干扰素刺激基因(ISG)激活评分 → ctrl vs stim state transition。证据类型:`[Mac确定性]`(committed 子集,确定性可复跑)。**自主完成**:公开数据(Kang 2018)自取。
> 对应 `docs/PLAN-v0.4-species-applications.md` 步骤 W5.2(应用 3 State/fate,例 3B immune activation)。

## 1. 数据(公开,自主获取)

- **来源**:Kang et al. 2018(GSE96583),IFN-β 刺激 vs control PBMC,via `pertpy.data.kang_2018()`(24673 cells × 15706 genes)。
- **committed 子集**:`data/cellstate/kang_isg_subset.json`(2232 cells × 25 ISG + 8 housekeeping,原始 counts,分层抽样 seed=1;564KB)。完整 h5ad 由 pertpy 缓存,未入库。provenance:`data/cellstate/PROVENANCE.json`。

## 2. 分析(marker-based state scoring)

每 cell 归一(CP10k+log1p)→ **ISG 激活评分 = mean(ISG) − mean(housekeeping)** → ctrl vs stim 的 Cohen's d。route_table 加 `state_scoring` 引擎:`(human, *, state) → state_scoring`。

**整体**:ctrl −2.462 → stim −0.749,**Cohen's d = 2.49**,marker 覆盖 100% → **accept(state transition detected)**。

**per cell type(实跑,d 降序)**:

| cell type | Cohen's d | ctrl→stim |
|---|---|---|
| Dendritic cells | **6.20** | −2.92 → −0.58 |
| CD14+ Monocytes | **6.08** | −2.53 → −0.10 |
| FCGR3A+ Monocytes | 4.46 | −2.24 → −0.24 |
| B cells | 3.47 | −2.74 → −1.19 |
| CD4 T cells | 3.07 | −2.71 → −1.33 |
| CD8 T cells | 2.77 | −2.69 → −1.29 |
| NK cells | 2.76 | −2.26 → −0.72 |
| **Megakaryocytes** | **0.20** | −0.41 → −0.30 |

→ **髓系(DC/单核)IFN 响应最强,淋巴系中等,巨核细胞几乎不响应**——与已知 type-I IFN 生物学一致(真实、可检验,非 mock)。

## 3. 治理点(R6 防过度承诺)

- **整体强迁移 → accept**;但 **Megakaryocytes d=0.20** 暴露在 raw_output.per_cell_type:若单独查巨核细胞,效应阈规则(d<0.3→downgrade)会**主动降级**,不硬说"激活"。
- **marker 覆盖不足 → downgrade**:panel 覆盖 <50%(如给错基因)→ 不硬说,`low_marker_coverage`。测试 `test_cellstate_case.py`(6 passed)覆盖 accept / low-coverage downgrade / per-cell-type。
- **无 ctrl/stim 分组 → abstain**。

## 4. 诚实边界

- ISG 激活评分是 **marker-based 相对量**(CP10k+log1p,ISG−housekeeping),**非**绝对通路活性或 per-cell 预测。
- Kang 2018 是 **PBMC scRNA 子集**;效应阈(accept d≥0.8)、ISG panel(教科书)、CP10k 为**设定默认**(写明,非调优)。
- downgrade 表"证据不足以确证 state 迁移",非"无迁移"。
- 本 case 证明的是**"agent 能把输出扩到 cell-state 并受治理产出真实迁移分析"**,非免疫激活的完备刻画。**不训练模型**。

## 5. 架构

- `praxis_virtualcell/predictors/state/cell_state.py`:`CellStateDB` + `run_cellstate_case`;route `state_scoring` 引擎。
- 运行时**不需 scanpy/pertpy**(读 committed JSON 子集);二者仅重建子集用。**State/fate 空白应用已落地**。
