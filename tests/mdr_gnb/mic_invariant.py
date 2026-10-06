"""MIC ↔ log10_mic 一致性守卫的共享判据(容差由舍入误差**推导**,不是拍脑袋选的)。

背景——为什么需要这条守卫:
科学验证层(workflows/science_v2/validation/t1_predictive.py:217,332)验的是 **log10_mic**:
golden、R²、MAE、面值锚点(ciprofloxacin_log10_lt_0 / magainin2_log10_in_1_2)全在 log10 空间。
而网站展示给用户的是 **mic_ug_ml / mic_um**
(praxis_vc_react/src/mdr/pages/PredictionResult.tsx:79,131)。这个数由 6 处独立计算、
零处交叉校验;API 层旧断言只查字段名在不在,不查值。

**实测结论(6 处逐个改成 10**(log10_mic+3) 即错 1000 倍,隔离 worktree 跑全套 614),
不要把它讲大**:
  - 逃逸的只有 **predictor 那 2 处**(small_molecule_model.py:104 /
    peptide_activity_model.py:101)→ 614 全绿穿过。但该值被 ensembler 丢弃
    (ensembler.py:102,120 只读 log10_mic 自己重算),连 trace 载荷都不外泄
    (run_mdr_query.py:141 只带 {"spec","status"})→ **从不到达用户,是没人管的死字段**。
  - 用户**真看到**的 ens→rb 那 4 处,**装本守卫前既有桩测试已拦得住**
    (test_*_log10_mean / test_report_*_field)。
  所以这**不是**「用户看的数无人管」,而是「死字段没测」。

本守卫的真实增量:①补上真逃逸的那 2 处;②**第一次在真 artifact 路径(真 app + 真 HTTP)
上做值断言**——此前所有值覆盖都是合成桩(桩测不到真数据路径上的问题)。

放在 tests/ 下(不是生产代码):这是补测试,不改科学核心。
"""
from __future__ import annotations

import math

# 两个数各自独立舍入到 4 位小数 → 单次舍入的最大偏差 = 半个最低位 = 5e-5
_HALF_ULP_4DP = 0.5e-4
# d(10^x)/10^x = ln(10)·dx:log10 上的舍入经 10^x 放大成 MIC 上的**相对**误差
_LN10 = math.log(10.0)


def report_mic_tolerance(mic: float) -> float:
    """报告层 |mic - 10**log10_mic| 的最大允许偏差(绝对值),由下面的推导给出。

    report_builder(coordinator/report_builder.py:27-28,44-45)把两个数**各自独立**舍入:
        log10_mic = round(L, 4)         # L = 未舍入的原始 log10-MIC
        mic       = round(10 ** L, 4)   # 关键:从**未舍入**的 L 算,不是从 round(L,4) 算
    所以 mic == 10**log10_mic 必然不成立。偏差有两个独立来源,上界取二者之**和**:

      (1) log10 的舍入 δ = |L - round(L,4)| ≤ 5e-5,经 10^x 放大成**相对**误差:
          |10**L - 10**round(L,4)| = 10**L·|10**δ - 1| ≲ ln(10)·δ·mic ≤ 1.1513e-4 · mic
      (2) mic 自身舍入到 4 位 → **绝对**误差 ≤ 5e-5。

      合计:|mic - 10**log10_mic| ≤ 5e-5 + ln(10)·5e-5·mic

    为什么两项都要、且必须**相加**(下列数字是实测值,非纸上推理):
      - 纯**绝对**容差:(1) 项随 MIC 线性增长 → 大 MIC 上误报。
        肽 magainin2 MIC≈27.12 → (1) 项达 3.1e-3,是 5e-5 的 62 倍。
      - 纯**相对**容差:(2) 项在小 MIC 上的相对占比爆炸 → 小 MIC 上误报。
        小分子 cipro MIC≈0.166 → (2) 项的相对贡献 5e-5/0.166 = 3.0e-4,
        比 (1) 的 1.15e-4 还大 → rel=1.15e-4 的纯相对容差最坏情况下会假红。
      - pytest.approx(rel=, abs=) 的容差是 max(rel*expected, abs) 而**非**二者之和:
        cipro 处 max(1.9e-5, 5e-5)=5e-5 < 真上界 6.9e-5 → 覆盖不住,故此处显式写和。

    仍紧到能抓真错:MIC 错 1000 倍 → 偏差 999·mic,比本上界大约 6 个数量级。
    """
    return _HALF_ULP_4DP + _LN10 * _HALF_ULP_4DP * abs(mic)


def assert_report_mic_matches_log10(activity: dict, mic_key: str) -> None:
    """守卫:报告里**展示给用户**的 MIC 必须与同一报告里**被验证过**的 log10_mic 自洽。

    activity: 报告的 activity(小分子)或 peptide_activity(肽)分栏。
    mic_key:  "mic_ug_ml"(µg/mL,小分子)或 "mic_um"(µM,肽)。

    不是同义反复:log10_mic 由验证层真验(golden/R²/面值锚点),本断言把"展示的数"
    钉死在"验证过的数"上——两者一起才封住 MIC 这条路径。缺字段直接 KeyError 报错,
    不会静默恒真。
    """
    log10_mic = activity["log10_mic"]
    expected = 10.0 ** log10_mic
    got = activity[mic_key]
    tol = report_mic_tolerance(expected)
    assert abs(got - expected) <= tol, (
        f"{mic_key}={got!r} 与 log10_mic={log10_mic!r} 不自洽:期望 ≈ {expected!r}"
        f"(=10**log10_mic),实际偏差 {abs(got - expected):.3g} > 舍入上界 {tol:.3g}。"
        f"展示给用户的 MIC 与验证过的 log10 脱节。")
