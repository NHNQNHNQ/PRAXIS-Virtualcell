# Finding W4c — GEARS 训练 + 集成(Phase 1)

> GEARS 原生 norman pipeline 跑通(env 破解 → donor 数据适配 → **6 轮兼容坑破解** → train → eval)。GEARS `pearson_de` **0.8392**。⚠ 与 donor base **不可比**(不同指标/split)。

## 训练(virtualcell, GPU)
- donor norman h5ad(118856×2000)适配 GEARS PertData:`condition`(ctrl / GENE+ctrl / A+B)+ `gene_name`(var_names)+ `cell_type`(K562);**复用 donor 本地 gene2go/essential**(不重下 dataverse)。
- GEARS GNN(hidden=64)train 5 epoch(2308s ≈ 38min)。
- metrics(GEARS `compute_metrics`):**pearson 0.9834, pearson_de 0.8392, mse 0.0068, mse_de 0.1756**。

## 6 轮兼容坑(GEARS 0.0.2 老包 vs 新 scipy/pandas/anndata —— p2b 实录)
1. **dataverse 下载慢**(远端 25kiB/s,数小时)→ 改用 donor norman h5ad + 本地辅助数据。
2. **`AttributeError: Series.nonzero`**:GEARS 用 `sparse_X[pandas_Series_mask]`,新 scipy `_validate_indices` 调 `Series.nonzero()`(pandas 2.x 已移除)。
3. **`sp.issparse` 对 anndata `SparseCSRMatrixView` 返回 False** → `if issparse` 的 dense fix 被跳过。
4. **`adata.X = toarray()` 赋值被 anndata 转回 sparse view**(改 adata 这条路无效)。
5. **解法:monkey-patch `pd.Series.nonzero = lambda s: s.to_numpy().nonzero()`**(最小,不碰 adata)→ GEARS 构造通过 + 训练启动。
6. **`KeyError: IER5L+ctrl`**:IER5L 不在 GEARS GO graph(早先 warning)却仍在 split/训练 batch → 过滤 IER5L cells + 重 `new_data_process`(norman_donor2)。

## ⚠ 不可比(ADR-W4c-1)
GEARS metrics = **pearson on absolute expression**(含 baseline → pearson 0.98 偏高;pearson_de 0.84 是 DE 基因);donor base = **delta_pearson on 扰动效应**(0.6-0.7)。两者**指标不同 + split 不同**,不可同表对比。用户选「GEARS 原生」(prototype-first),原生 split 与 donor 不可比(早已声明)。donor norman 适配为同表可比留 backlog。

## 集成
GEARS 接口 `predict([['gene']])`(gene names,不用 pert_emb)与 donor predictor 不同;训练脚本 `benchmarks/gears_norman.py`(env=virtualcell)。communicative predictor-agent 适配(GEARS.predict → PredictorResultMessage)留 backlog(接口差异 + GEARS 自有 save/load + 跨 env 测试)。

## 结论
GEARS 原生 norman pipeline **全通**(task-specific GNN,pearson_de 0.84);6 轮老包坑逐个破解,是 [[p2b_external_models_blocked]] 外部模型工程的完整实录。与 base 不可比(诚实)。
