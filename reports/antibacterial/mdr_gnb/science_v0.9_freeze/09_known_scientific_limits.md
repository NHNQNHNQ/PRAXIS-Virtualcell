# 09 诚实科学边界(Science v0.9)

面向"这套东西到底证明了什么、不能声称什么",逐条钉死。

## 覆盖面
- **5 物种有 SIR 模型**:acinetobacter_baumannii / escherichia_coli / klebsiella_pneumoniae /
  pseudomonas_aeruginosa / salmonella_enterica(共 127 个 genotype→SIR artifact)。
- 其余物种 **fail-closed**:无模型即弃权,不臆测(不是 5/5 全覆盖)。
- 132 组合有证据分层,127 组合有落地模型;差额组合走规则 / no_baseline 路径。

## 每层能声称什么
- **strong(26)**:在冻结版 AMRFinderPlus 对照下,融合 per-ST VME **统计显著优于**规则法
  (量级通常小但显著)。**仅这 26 条**可说"优于冻结基线"。
- **practical(24)**:融合**不劣于**规则法但**未显著优于**(输出带 warning)。不得声称更优。
- **no_baseline(67)**:冻结规则表未收录该药,**无对照** → ML-only,未经规则验证。
- **unevaluated(15)**:artifact 存在且确定性可加载,但**本地缺 phenotype/ST 数据未做 ST-CV**
  (需 53 环境)——未评估,不得当作已验证。

## 已知弱点(不藏)
- 部分 strong 组合**绝对 ME 偏高**(如 KP×meropenem ME≈0.19):因规则法自身 ME 就高
  (KP×meropenem 规则 ME≈0.14),融合在「ME 不显著劣于规则」判据下过关,但绝对误报率不低。
- ML 特征与 AMRFinderPlus 基因调用**同源**,融合只能"规则兜底 + ML 补漏";要在锚点上拿到**显著**
  优于规则,需引入规则法没有的新信息(k-mer / porin / CARD),依赖真实工具链——现为天花板。
- 全程**单 seed(seed=0)**;运行点 t* 与显著性检验多为同集选取,轻微乐观(rule-first 方向稳健)。

## 用途边界
- **仅科研筛选**,非临床决策;任何组合的输出都不构成给药建议。
- 冻结基线是**版本冻结的 AMRFinderPlus 规则法**,不代表当前临床折点或最新数据库。
