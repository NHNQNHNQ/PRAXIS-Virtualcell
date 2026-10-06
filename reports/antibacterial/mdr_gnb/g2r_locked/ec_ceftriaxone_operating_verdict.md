# G2R 正式 locked 终判:EC × ceftriaxone(abstain-aware 运行点,2026-07-07)

> **纪律**:运行点(置信阈值 τ*)完全从 **dev 5 折 OOF** 选(预注册:覆盖率≥0.80 且 covered ME<0.10 下
> per-ST VME 最小,并列取更高覆盖);τ* 应用到 **held-out locked 一次**,用**门的主指标 per-ST VME**
> + 配对置换检验。fusion 与 rule 在**同一 covered 子集**比。harness=`run_g2r_riskcoverage.py`
> (`dev_operating_point`/`locked_operating_verdict`),数据=`ec_ceftriaxone_operating_verdict.json`。

## 终判:**G2R-practical-pass**

| 项 | 值 |
|---|---|
| dev / locked 样本 | 5483 / 1369(ST 不跨层,seed=0) |
| locked 覆盖率 | **86.3%**(弃权 14% 最不确定者;n_covered=1181) |
| covered per-ST VME:融合 / 规则 | **0.0036 / 0.0062**(Δ=−0.0025) |
| 置换检验 p | **0.253(不显著)** |
| covered ME:融合 / 规则 | 0.0195 / 0.0069(均 <0.10,受控) |
| R-bearing ST 数 | 69 |

## 诚实解读

- **达到 practical-pass**(按计划定义:VME 不高于规则法 + 不确定性识别/fail-closed 更好):
  融合+弃权在选择回答的 86% 病例上 per-ST VME 0.0036(方向上比规则 0.0062 低约 40%),ME 受控,并对
  14% 最不确定病例诚实弃权。
- **未达 strong-pass**:Δ 虽为负但 **p=0.25 不显著**——在 69 个 R-ST、绝对 VME 已很低的情况下,融合相对规则的
  安全边际太小,统计上无法证明"优于"。
- **abstain 的实际贡献有限**:dev 上 per-ST VME 本就低且随弃权基本持平(~0.026 平台),practical-pass 主要由
  **rule-first 融合**驱动,弃权只是把 covered 子集的 per-ST VME 再压一点(0.019→0.0036 量级)。
- **这是现有特征的天花板**:ML 特征与 AMRFinderPlus 基因调用同源,融合只能"规则兜底 + ML 补漏"。要在
  EC ceftriaxone 上拿到**显著**优于规则(strong-pass),必须引入规则法没有的新信息(k-mer/porin/CARD),
  依赖真实工具链。

## 结论(可对外引用的诚实口径)

> 在 ST 分组、dev/locked 分离、locked 只跑一次的严格评估下,PRAXIS-MDR-GNB 的 rule-ML 融合 + 置信弃权
> 在 EC×ceftriaxone 上达到 **G2R-practical-pass**:以 86% 覆盖率提供不劣于冻结版 AMRFinderPlus 的
> 极重大误差(VME)、受控的重大误差(ME)与诚实弃权;**未**证明在 VME 上显著优于规则法。
> 价值定位是**安全治理框架**(fail-closed + 不确定性识别),而非"优于 AMRFinderPlus"。

## 保留
- 单 seed(seed=0)。dev 侧多 seed 稳定性未验(locked 仍应只一次)。
- practical-pass 的边际安全增益(Δ per-ST VME −0.0025)不显著,不得表述为"更安全"的确证。
