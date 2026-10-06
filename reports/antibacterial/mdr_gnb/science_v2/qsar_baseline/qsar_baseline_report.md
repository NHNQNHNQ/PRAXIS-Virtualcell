# B0.1:QSAR baseline(化合物结构 → log10-MIC)— escherichia_coli

line B 第一个从 SMILES 预测 MIC 的模型。把 Science v1 的三条纪律迁到化学空间:**scaffold 分组防泄漏**(同 Bemis-Murcko 骨架不跨折)、**化学 OOD 弃权**(对训练集最大 Tanimoto 低=不可信)、**证据分层**(QSAR 须显著优于均值预测 + 1-NN 两个平凡 baseline)。

## 方法(写死)

- 特征:RDKit Morgan 指纹(radius=2, nBits=2048)。baseline 用指纹,不上 GNN。
- 交叉验证:scaffold-GroupKFold(5 折,groups=scaffold),拼全 OOF。
- 模型:RandomForestRegressor(n_estimators=300, random_state=0, n_jobs=-1)。
- baseline:(a) 均值预测(train 的 log10-MIC 均值);(b) 1-NN(train 里 Tanimoto 最近邻的 log10-MIC)。
- 不确定度:RF 各树预测 std。OOD:对 train 最大 Tanimoto,阈 0.3。

## 一键复现
```bash
.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.qsar_baseline --species escherichia_coli
```

确定性:seed=0;scaffold 分组/训练确定性(RF n_jobs=-1 有 ULP 噪声,指标稳定)。

## 结果(log10-MIC 空间)

- 化合物 27175(丢弃 invalid SMILES 0);scaffold 8724(最大骨架占比 2.1%,singleton 骨架占 61.9%)。

- **RF**:R²=0.5654  MAE=0.5132  RMSE=0.7133。

- baseline RMSE:均值预测=1.0837、1-NN=0.8268。

- **证据分层判据**:RF 优于均值=True、优于 1-NN=True → ✅ 显著优于两个平凡 baseline,QSAR 有效。

## 化学空间 OOD(coverage-RMSE 曲线)

按对训练集最大 Tanimoto 降序保留(相似=更可信),各覆盖率下 RMSE:

| 覆盖率 | 保留数 | RMSE | 保留集最低相似 |
|--:|--:|--:|--:|
| 1.0 | 27175 | 0.7133 | 0.0312 |
| 0.9 | 24458 | 0.6809 | 0.4194 |
| 0.8 | 21740 | 0.6643 | 0.5208 |
| 0.7 | 19022 | 0.6593 | 0.5926 |
| 0.6 | 16305 | 0.6575 | 0.6481 |
| 0.5 | 13588 | 0.6475 | 0.6923 |

- 满覆盖 RMSE=0.7133 → 留最相似 50% RMSE=0.6475 → ✅ 有区分度(相似=更可信)。

- OOD(最大 Tanimoto<0.3):516 个(1.9%),fail-closed 下应弃权不预测。

## 诚实边界

- **仅 escherichia_coli**、**仅 Morgan 指纹 baseline**:未做多物种、未上分子描述符 / 图神经网络。
- 这是 baseline,允许不完美:若 R² 低或不优于 baseline,如实反映——指纹不够时下一步是理化描述符或 GNN。
- scaffold 分组是化学版防泄漏核心不变量(gate 硬校验同 scaffold 不跨折),但骨架相同≠机制相同,仍可能高估对全新骨架的外推。
- MIC 本身有测量噪声与截断(chembl_pull 已取中位去噪、只留 relation='=');log10-MIC 回归未建模 censoring。

