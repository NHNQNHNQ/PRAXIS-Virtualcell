# G2R v2:abstain-aware risk-coverage 曲线(2026-07-07)

> 预测器 = rule-first 融合 + 置信度弃权(rule=R 恒保留;rule=S 用 ML,弃权 |prob−t*| 最小者)。
> 纪律:ST 分 dev/locked(seed=0),ML 训练只用 dev,曲线在 held-out locked 上一次算出。
> **度量 = pooled VME/ME**(选择性预测标准);注意与门的 per-ST VME 不同(见末尾)。
> harness=`workflows/run_g2r_riskcoverage.py`+`test_g2r_riskcoverage.py`(3 不变量)。数据=`riskcoverage_curves.json`。

## EC × ceftriaxone(locked n=1369,t*=0.24)—— abstain 真赢

| 覆盖率 | VME | ME |
|---|---|---|
| 规则法(参照) | 0.019 | 0.006 |
| 100% | 0.010 | 0.045 |
| **90%** | **0.003** | **0.020** |
| 70% | 0.003 | 0.026 |
| 40% | 0.000 | 0.067 |

**弃权 10%(覆盖 90%)→ VME 0.003(比规则 0.019 低 6 倍),ME 0.020(仍低)。** 安全增益真实、代价小。
这是 abstain-aware 的正面案例:不确定样本正是易错样本,弃掉它们同时压 VME 和 ME。

## KP × meropenem(locked n=200,t*=0.14)—— abstain 救不了

| 覆盖率 | VME | ME |
|---|---|---|
| 规则法(参照) | 0.091 | 0.109 |
| 100% | 0.020 | 0.376 |
| 80% | 0.020 | 0.452 |
| 65% | 0.000 | 0.771 |
| 50% | 0.000 | 1.000 |

**弃权越多 ME 反而爆(0.38→1.0)。** 原因:问题不是个别不确定样本,而是**操作点整体偏激进判 R**
(t*=0.14 很低 + rule-first 叠加);弃权移除的是 ML 的正确"S"判,covered 子集越发被"判 R"主导 → ME 飙升。
locked pooled 上**规则法本就均衡**(VME 0.091/ME 0.109),ML/融合是拿大 ME 换低 VME,abstain 不能调和。

## 关键诚实结论

1. **EC ceftriaxone**:abstain-aware 在 90% 覆盖给出真实安全增益(VME 6× 降、ME 受控)→ G2R 可用运行点。
2. **KP meropenem**:abstain 不能解 VME↔ME 冲突;在均衡度量下规则法竞争力已足,ML 优势代价过大。
3. **度量依赖警示(重要)**:门用 **per-ST VME**(抗克隆膨胀),KP 门"大胜 −0.164"主要来自**稀有耐药克隆**;
   本曲线用 **pooled VME**(按人群频率),KP 规则法 VME 仅 0.091 → ML 优势大幅缩水。**同一模型,两种度量,两种结论**——
   这正是"ML 特征与规则同源、增量脆弱"的体现,也是必须同时看 per-ST 与 pooled 的原因。

## 保留
- pooled 曲线;per-ST 版随覆盖变化 ST 集不稳,未纳入。
- 单 seed;locked 小(KP n=200)。运行点(如 EC 90%)的显著性/per-ST 未在此二次确认(留正式运行点 locked)。
