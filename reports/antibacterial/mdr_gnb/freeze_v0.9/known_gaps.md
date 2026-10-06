# 冻结:v0.9 已知缺口(2026-07-07,g2r-remediation 起点)

> 诚实清单。对外口径必须与此一致,不得夸大。

## 对外允许口径
> PRAXIS-MDR-GNB 已完成 5 个物种、127 个 SIR 模型的确定性预测框架、trace replay、abstain/critic 治理与 GEM FBA 原型;10 物种全景架构已搭建,但其中 5 个物种尚无生产模型,真实临床泛化仍在 G2/G2R 验证中。

## 不得声称
- ❌ 10 物种平台已完成 —— 实为 5 物种有模型 + 5 物种空骨架
- ❌ 模型已证明优于 AMRFinderPlus —— 实为 8/28 组合胜出,EC 锚点未过
- ❌ 可临床预测 —— 仅科研筛选
- ❌ 机理层已证明因果 —— 机理层是结构占位,未做独立功能验证

## 科学缺口(P0)
1. **G2 未干净通过**:EC×ceftriaxone ΔVME +0.020(p=0.983),EC×meropenem VME(ML)=0.683。需 G2R。
2. **127 模型无泛化性能入 registry**:registry 只记 n/R/S/nfeat,无 VME/ME/AUC/calibration/coverage。
3. **ML 特征与规则法同源**(均为 AMRFinderPlus 基因调用):无 k-mer/porin/CARD/MIC → ML 增量上限受限。

## 覆盖缺口(P1)
4. **5/10 物种无模型**:enterobacter/serratia/stenotrophomonas/proteus/morganella 端到端只 abstain。
5. **多物种 E2E 只测 KP+EC**;PA/AB/SE 有模型但端到端未走。
6. **模型账目**:盘上 133 joblib,MANIFEST/registry 各 127;6 个 AB orphan joblib 不在 MANIFEST,需清或补录。

## 生产/工具链缺口(P2)
7. **LLM 真集成从未测**:只有 fake/disabled client,真 DeepSeek 未调用过。
8. **数据工具链**:AMRFinder/CARD/DBAASP loader 是 `NotImplementedError`;MLST 二进制未装(测试 mock);NCBI/BV-BRC 网络层零测试。
9. **后端/前端**:FastAPI/PG/Redis/React 骨架在,HTTP E2E/DB/前端零测试;仓库大盘有 14 个 praxis2 后端失败(asyncssh,与 MDR-GNB 无关)。

## 环境坑
10. **exFAT 即时重生 `._*`**:`._*` 会在每次写盘时由 macOS 自动重建,`find -delete` 是徒劳。真解:gitignore(已做)+ 所有计数/测试逻辑必须过滤 `._*`(不能用 naive `ls`/find 计数模型)。`data/` 长期应迁 APFS。
