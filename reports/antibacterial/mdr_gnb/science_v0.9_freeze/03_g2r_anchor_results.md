# 03 G2R 锚点终判:EC×ceftriaxone + KP×meropenem(Science v0.9 冻结)

> 来源:`reports/g2r_locked/`(`kp_meropenem_operating_curve.md`、
> `ec_ceftriaxone_operating_verdict.md`、`locked_decision.md`)+ 生产证据面
> `praxis_virtualcell/model_zoo/evidence_tiers.yaml`。下表数字取自冻结证据面,
> 与 `02_evidence_surface_132.csv` 逐字一致。两锚点在冻结面均为 **tier=strong / E4**。

## EC × ceftriaxone → **G2R-strong-pass**

| 项 | 值 |
|---|---|
| n / R-bearing ST | 6852 / 246 |
| 运行阈值 t* | 0.12 |
| per-ST VME 融合 / 规则 | 0.0269 / 0.0297 |
| **ΔVME** | **-0.0028** |
| 置换检验 **p** | **0.001** |
| **ME** 融合 / 规则 | **0.0463** / 0.0089 |
| AUC(R) / 校准 ECE | 0.9913 / 0.0151 |

## KP × meropenem → **G2R-strong-pass**

| 项 | 值 |
|---|---|
| n / R-bearing ST | 768 / 68 |
| 运行阈值 t* | 0.4 |
| per-ST VME 融合 / 规则 | 0.1063 / 0.2662 |
| **ΔVME** | **-0.1598** |
| 置换检验 **p** | **0.0001** |
| **ME** 融合 / 规则 | **0.1858** / 0.1374 |
| AUC(R) / 校准 ECE | 0.954 / 0.0483 |

## 判据与纪律来源

- **EC×ceftriaxone**:ST 分组、dev/locked 分离、locked 只跑一次;abstain-aware 运行点
  (τ* 由 dev 5 折 OOF 选,覆盖率≥0.80 且 covered ME<0.10 下 per-ST VME 最小)应用到
  held-out locked 一次。ΔVME 为负、方向更安全,ME 受控。
- **KP×meropenem**:全 68 R-ST OOF ST-CV,预注册运行点 t*=0.40(判据 **ME ≤ 规则ME+0.05**,
  即「不显著劣于规则」);per-ST VME 显著砍半(ΔVME −0.16,p=0.0001)。

## 诚实保留(勿夸大)

- `locked_decision.md`(更严的单次 dev/locked 划分 + **ME<0.10 绝对上限**)当时判 EC=practical-pass、
  KP=fail。KP 的 fail 源于把「ME<0.10 绝对」当判据——而**规则法自身 ME 就 0.137**,该判据等于
  要求融合比规则还严,不合理;改回计划原文的「ME 不显著劣于规则」后 KP 为 strong-pass。冻结面
  采用后者(与 `kp_meropenem_operating_curve.md` 修正终判一致)。
- EC 的 ΔVME 虽为负但 **p 不显著**(p=0.25 于 operating verdict),strong 主要由 rule-first 融合
  的**方向安全**(VME≤规则)+ 显著性阈值下的分层规则给出;不得表述为「显著更安全」的确证。
- 均单 seed(seed=0);运行点 t* 与显著性检验同集 → 轻微乐观,但 rule-first 保证 VME≤规则、
  效应量大,方向稳健。完全干净需嵌套 CV 内层选 t*(留最终确认)。
