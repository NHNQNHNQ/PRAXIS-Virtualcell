# sm_activity 证据分层(E1-E5 验证层)— escherichia_coli

**当前证据级:E4**(化合物 27175、scaffold 8724)

## 阶梯(累积,数据驱动定级)

| 级 | 判据 | 达成 |
|--|--|:-:|
| E1 | E1 QSAR artifact 在 | ✅ |
| E2 | E2 确定性 E2E 预测 | ✅ |
| E3 | E3 scaffold-split CV(防泄漏)+ 优于均值 | ✅ |
| E4 | E4 **显著**优于 1-NN 相似性检索(配对 bootstrap p<0.05) | ✅ |
| E5 | E5 外部数据集(换来源/年份)holdout | ❌ |

## 指标(与 B0.1 qsar_metrics.csv 同源)

- R²=0.5654  RMSE(RF)=0.7133  RMSE(1-NN)=0.8268  RMSE(均值)=1.0837(log10-MIC 空间)

- **E4 显著性检验**(配对 bootstrap,2000次,seed=0):RF vs 1-NN ΔMSE=0.1748, p<0.0005 → 显著优于(win_rate=0.5114, dz=0.1282);RF vs 均值 p<0.0005。

- 诚实解读:E4 显著性来自 RF 在大误差样本上的改善;逐化合物 win_rate=0.5114(1-NN 在重复化合物上精确命中),效应量 dz=0.1282 偏小——'显著优于'成立,但非全面碾压。

## 诚实边界(为何不是 E5)

- **无外部数据集(换来源/换年份)holdout;当前仅 ChEMBL EC 内部 scaffold-split CV**。E5 须在外部来源/年份数据集 holdout 上复现方能声称;当前仅内部 scaffold-split,骨架相同≠机制相同,对全新骨架外推仍可能高估。

