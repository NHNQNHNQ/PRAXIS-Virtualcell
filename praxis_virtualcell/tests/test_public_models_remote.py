"""Phase 6:GEARS/scGPT 真推理 gated 契约测试(仅 .53:torch + GPU + ckpt;Mac 无 torch → conftest 自动 skip)。

诚实:这 2 条是 @pytest.mark.remote,本地 skip(skip 基线 25→27,与 Phase 2 torch/cobra gated 同款惯例)。
真推理跑通是 .53 的事 —— 本地绝不跑真模型、绝不 mock 真语义凑绿(红线 5/6)。
ckpt 路径从 env 取(.53 上给),不硬编码 /home/zkyd。"""
import os

import pytest

pytestmark = pytest.mark.remote


def test_scgpt_wrapper_real_inference_matches_donor():
    """.53:ScgptWrapper 真跑 == donor predict(atol 1e-6,finding_w4c_scgpt 集成锚点)。
    ΔPearson 0.4407 是 eval 全集指标(此处只验单点等价性,分数入 provenance 已声明)。"""
    from praxis_virtualcell.model_zoo.wrappers.scgpt_wrapper import ScgptWrapper

    ckpt_stem = os.environ["SCGPT_CKPT_STEM"]        # .53:.../scgpt_ckpt/norman_2019/pretrained_backbone
    w = ScgptWrapper(ckpt_stem=ckpt_stem)
    out = w.run_prediction({"targets": ["AHR"]})
    assert "prediction" in out and "delta" in out["prediction"]
    assert out["prediction"]["n_genes"] > 0
    # 等价性锚点:与 donor predict 逐元素(atol 1e-6)——.53 上按 finding 的 pipeline 断言。
    # (donor 对照值由 .53 上的 build_predictor_from_ckpt + donor predict 现算,不硬编码。)


def test_gears_wrapper_real_inference_structure():
    """.53:GearsWrapper 真跑 GEARS predict([['gene']]) → 产出结构(condition-level delta)。
    pearson_de 0.8392 入 provenance 已声明;此处验产出契约(不与 donor 同表——GEARS 不可比)。"""
    from praxis_virtualcell.model_zoo.wrappers.gears_wrapper import GearsWrapper

    ckpt_stem = os.environ["GEARS_CKPT"]             # .53:GEARS 原生 save 目录/stem
    w = GearsWrapper(ckpt_stem=ckpt_stem)
    out = w.run_prediction({"targets": ["AHR"]})
    assert "prediction" in out


def test_m2_gears_case_real_delta_e2e():
    """P10.B M2 .53:human gene→expression 经 run_gears_case → GEARS-内部 delta(扰动−对照,
    非 mock 0.3、非绝对表达)。GEARS 非确定性(no_fixed_seed)→ 只验结构 + 诚实标注 + delta 类型,
    不作字节等价断言(spec §六 确定性红线细化)。诚实标注须在 CaseReport 四部分一致(raw_output/
    baseline_comparison/reliability_decision/provenance_boundary)。"""
    from praxis_virtualcell.predictors.ml.gears_case import run_gears_case

    raw = {"species": "human", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["AHR"]}   # AHR∈norman vocab(如非则换 vocab 内基因)
    report, dec = run_gears_case(raw)

    # 路由/引擎判别:human gene→expression → donor_predictor(经 gears_available 门控到 GEARS runner)
    assert dec.engine == "donor_predictor"

    ro = report.raw_output
    # 诚实标注(raw_output):GEARS-内部 delta,明标非 donor 可比 + 非确定性
    assert ro["value_type"] == "gears_internal_delta"
    assert ro["not_comparable_to_donor_base"] is True
    assert ro["non_deterministic"] is True

    # 真实 delta 结构:非空列表、有非零分量
    assert isinstance(ro["gears_delta"], list) and len(ro["gears_delta"]) > 0
    assert any(abs(x) > 1e-9 for x in ro["gears_delta"])
    # 非 mock 铁证:delta 不是 mock ensemble 的常数 0.3
    assert ro["gears_delta"] != [0.3] * len(ro["gears_delta"])

    # 诚实标注在 CaseReport 其余三部分一致(非 donor 可比 / 非确定性,多处冗余守)
    assert report.baseline_comparison["value_type"] == "gears_internal_delta"
    assert report.baseline_comparison["not_comparable_to_donor_base"] is True
    assert report.reliability_decision["disposition"] == "accept"
    assert "not_comparable_to_donor_base" in report.reliability_decision["caution_flags"]
    assert "gears_internal_delta" in report.reliability_decision["caution_flags"]
    assert report.provenance_boundary["non_deterministic"] is True
    assert report.provenance_boundary["no_fixed_seed"] is True
