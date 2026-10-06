# G2R locked-test 终判(2026-07-07,g2r-remediation)

> **纪律**:ST 分 dev/locked(seed=0,locked 25% ST,ST 不跨层);所有候选选择只看 dev;
> locked **只跑一次**。预注册选择规则:dev per-ST VME 最小,约束 **ME<0.10**,并列取 ME 更低。
> harness=`workflows/run_g2r_locked.py`,不变量测试=`tests/test_g2r_locked.py`(6 passed:ST 不泄漏等)。
> 候选:rule / ml_aligned / ml_budget / fusion_aligned / fusion_budget(fusion=rule-first)。

## 终判

| 锚点 | dev 选中 | locked per-ST VME(best/rule) | ΔVME | p | ME(best/rule) | **判定** |
|---|---|---|---|---|---|---|
| **EC × ceftriaxone** | fusion_aligned | 0.019 / 0.021 | **−0.003** | 0.247 | 0.045 / 0.006 | **G2R-practical-pass** |
| **KP × meropenem** | rule(回退) | 0.238 / 0.238 | +0.000 | 1.000 | 0.109 / 0.109 | **G2R-fail(ME 纪律下)** |

## EC × ceftriaxone:practical-pass(诚实,不夸大)

- dev 候选表:rule(VME 0.033/ME 0.010)、ml_aligned(0.061/0.056)、**fusion_aligned(0.027/0.056)**、ml_budget(0.031/0.249 超预算)、fusion_budget(0.021/0.249 超预算)。合格集 {rule, ml_aligned, fusion_aligned},VME 最小 → fusion_aligned。
- locked 一次:融合 per-ST VME 0.019 vs 规则 0.021,**Δ=−0.003 但 p=0.247 不显著**;ME 0.045<0.10 合格。
- **结论:融合在独立 locked 上不劣于规则、边际更安全但不显著** → practical-pass。
- **纠正**:full-data 探针曾报 strong-pass(p=0.0006),那是用了后来划入 locked 的数据、偏乐观。dev/locked 纪律把它降到诚实的 practical-pass —— 这正是纪律的价值。

## KP × meropenem:ME 纪律下 fail(重要发现)

- dev:压 VME 的候选(ml/fusion)能把 per-ST VME 从 0.272 砍到 0.087,**但 ME 全在 0.41–0.45**;规则自身 ME=0.147。**没有候选满足 ME<0.10** → 回退规则 → locked rule-vs-rule → fail。
- **含义**:原始 G2 的 KP「pass」是**仅 VME、无 ME 约束**的判定;一旦要求 ME 不失控,VME 胜利需 ~45% 假耐药代价。对末线碳青霉烯,近半敏感株误判耐药 → 临床不可接受。
- **VME↔ME 是真实 Pareto 冲突**:规则(VME 0.27/ME 0.15)与融合(VME 0.09/ME 0.45)互不支配。

## 诚实总结

- **EC ceftriaxone**:原始 G2 blocker 在 locked 纪律下达到 **practical-pass**(安全治理框架不劣于规则),但**未**达 strong-pass(不显著)。
- **KP meropenem**:VME 大幅可降,但代价是 ME 失控;在「ME 不失控」约束下当前**无解**。
- 两锚点都指向同一未试杠杆:**abstain-aware(M3)**—— 只在有把握处预测,在可接受 coverage 下把 VME 压到低位、ME 受控。这是下一步唯一有希望同时满足 VME↓ 且 ME 可控的路径,需**新预注册 + 各自一次 locked**。

## 未做/保留

- 单 seed(seed=0)。dev 侧应多 seed 验稳,locked 仍只一次。
- abstain-aware / conservative-threshold-with-coverage 未纳入候选集(留 G2R v2 预注册)。
- 失败归因 atlas(规则漏判基因)见 `locked_results.json.rule_vme_atlas`。
