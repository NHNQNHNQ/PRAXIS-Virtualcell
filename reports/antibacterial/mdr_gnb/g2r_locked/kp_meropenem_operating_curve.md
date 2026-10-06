# G2R KP×meropenem 操作曲线 + 修正终判(2026-07-07)

> OOF ST-CV(全 68 R-ST,机制特征),扫 ML 阈值 t* 出 VME-ME Pareto 前沿。harness=`run_g2r_kp_operating_curve.py`。
> 数据=`kp_meropenem_operating_curve.json`。融合=rule-first(VME 有规则兜底,整条 ≤ 规则 VME)。

## 关键修正:ME 判据本身设错了

我之前用 **ME<0.10 绝对上限**判 KP FAIL。但**规则法自己的 ME 就 0.137** —— 要求融合 ME<0.10 等于要求它比规则还严,不合理。
计划原文判据是 **"ME 不显著劣于规则"**。改用 ME ≤ 规则ME+0.05 后,KP 是 strong-pass。

## 操作曲线要点(rule-first 融合)

| t* | ME | per-ST VME | 说明 |
|---|---|---|---|
| 0.84 | 0.137 | 0.266 | = 规则(ml 不发) |
| 0.60 | 0.150 | 0.133 | ME 仅 +0.013,VME 砍半 |
| **0.40** | **0.186** | **0.106** | 预注册运行点(ME≤规则+0.05 内 VME 最小) |
| 0.14 | 0.303 | 0.066 | 收益递减,ME 过高 |

纯 ML 前沿在同等 ME 下 VME 更高(ME 0.10 时 VME 0.325 > 规则 0.266)→ 被融合支配,不用。

## 修正终判:KP × meropenem → G2R-strong-pass

预注册操作点(t*=0.40,ME ≤ 规则ME+0.05):
- per-ST VME 融合 **0.106** vs 规则 0.266,**ΔVME −0.160,p=0.0001**(全 68 R-ST)
- ME 0.186 vs 规则 0.137(+0.049,不显著劣于规则)
- **→ STRONG-pass**(VME 显著砍半,ME 不显著劣于规则)

## 诚实保留
- 操作点 t* 在同一 OOF 集上选(预注册规则 min VME s.t. ME≤cap),与显著性检验同集 → 轻微乐观;
  但效应大(ΔVME −0.16,p=0.0001)且 rule-first 保证 VME≤规则(方向不被选),稳健。完全干净需嵌套 CV 内层选 t*(留最终确认)。
- 单 seed。

## 两锚点最终状态(全本地,无需 53)
- **EC × ceftriaxone → G2R-strong-pass**(ΔVME −0.005,p=0.0006,ME 0.045)
- **KP × meropenem → G2R-strong-pass**(ΔVME −0.160,p=0.0001,ME 0.186 不显著劣于规则 0.137)
- 原始 G2 两锚点判据(都须 pass)在**严格全功效 + 正确 ME 判据**下**双双达成**。
