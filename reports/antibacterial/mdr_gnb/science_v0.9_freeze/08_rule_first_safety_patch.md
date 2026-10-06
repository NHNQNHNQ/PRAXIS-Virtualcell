# 08 rule-first 安全补丁:rule=R 永不翻 S

## 保证
生产融合 `praxis_virtualcell/mdr_gnb/coordinator/fusion.py::fuse_sir` 采用 **rule-first**:
只要冻结版 AMRFinderPlus 规则法判该组合为 **R**,融合输出必为 **R**,ML 不得把它翻成 S。
数学后果:**融合的 per-ST VME(极重大误差,把真耐药漏判成敏感)≤ 规则法**——这是 G2R 全部
「不劣于规则」结论赖以成立的地基。

## 实现
- 有对照(规则表收录该药)时:`fused_r = (rule_r == 1) or (p_r >= t)`——规则 R 直接短路为 R,
  ML 只能在规则判 S 处补判 R,**永远无法反向下调**。
- 运行时自检断言(热路径内联,防未来重构破坏):
  `assert not (has_baseline and rule_r == 1 and fused_sir == "S")`,消息「融合违反安全保证:rule=R 被翻成 S」。
- 无对照(no_baseline)时 fail-open 到 ML-only 并打 warning(冻结规则表未收录该药,无规则验证);
  abstained / 非 sir_class 原样返回(fail-closed 保留)。

## 测试指针
- `praxis_virtualcell/mdr_gnb/tests/test_fusion.py::test_rule_R_never_flipped_to_S`
  ——构造 rule=R 但 ML 强判 S 的场景,断言融合仍输出 R。
- 运行:`.venv/bin/python -m pytest praxis_virtualcell/mdr_gnb/tests/test_fusion.py -q`
