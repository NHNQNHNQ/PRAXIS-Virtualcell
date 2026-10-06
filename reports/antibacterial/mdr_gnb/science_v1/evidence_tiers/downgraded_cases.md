# S6 降级组合 + 诚实边界(敢说哪些不能预测)

## 降级(67 个:全部 no_baseline 的 E3 → E2)

v0.9 冻结面把 **no_baseline**(有模型 + 确定性 E2E 预测,但规则表未收录该药、**无对照基线**)
一律记 E3,与真做过 ST-CV 的 practical 同级——这是 v0.9 的乐观。v1 诚实拆开:no_baseline 降为
**E2 model_only**。

这**不是能力回退**,是**诚实修正**:E2 组合有可跑的模型和确定性预测,但因规则表无该药、
没有对照基线,**无法声称优于规则**,也没做过 CV,故不配 E3。

降级分物种计数:{'acinetobacter_baumannii': 10, 'escherichia_coli': 24, 'klebsiella_pneumoniae': 22, 'pseudomonas_aeruginosa': 4, 'salmonella_enterica': 7}(共 67 个,均 no_baseline)。

## 诚实边界:哪些组合**不能**声称优于规则

### E2 model_only(67 个)— 有模型、无对照

有确定性 E2E 预测,但规则表未收录该药、无冻结 AMRFinderPlus 基线可对齐。**只能给预测,
不能声称比规则强**——因为压根没有规则基线可比。这是本证据面最大的一块诚实边界。

### E1 artifact(15 个)— 有 artifact、未评估、不能预测优劣

仅有 joblib artifact + 确定性加载,**从未做本地 CV**(PA/AB/SE 部分组合无评估数据)。
对这些组合**我们不声称任何预测能力优劣**,它们只是"模型文件存在"。其中包含 S3 本想评但
数据未收录进面的 **salmonella_enterica × ciprofloxacin**(见下)。

### E3_evaluated(12 个 practical 未升级)— 做过 CV 但未显著优于规则

S2 abstain-aware 复评后仍停在 practical:做过 ST-CV,融合不劣于规则,但**未达统计显著**,
且 abstain 也压不动(覆盖不足 / ML 无增益 / 规则已零漏判)。诚实说法:**不劣于规则,但不敢说更强**。
典型卡点(来自 S2 remained_practical):覆盖率 ≥0.70 内 covered ME 始终 ≥0.1(压 ME<0.10 须弃权>30%)、
ΔVME=0.0 p=1.0(ML 无增益)、rule_vme 已 0(规则无漏判无提升空间)。

## S3 lineage holdout 跳过的组合(诚实标注,未给 E5)

以下 anchor 虽在 S3 名单内,但未收录进可评估的冻结面 132(或收录但 unevaluated),无冻结基线
对齐,**本次跳过 holdout,不给 E5**:

- **acinetobacter_baumannii × tigecycline**:不在冻结证据面 132,无此行(待 53 数据收录进面后再评)。
- **salmonella_enterica × ciprofloxacin**:在面内但 tier=unevaluated → v1 记 **E1_artifact**,未做 holdout。

另:PA/AB/SA 的 temporal/source holdout(S3.2/S3.3)未做,当前 E5 仅代表"稀有谱系群 lineage 外推"
一种外推,不等于时间/地域外推也稳。
