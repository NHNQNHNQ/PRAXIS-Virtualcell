"""M1(v0.3):Eval Ledger 单测。纯 Python,Mac 可跑(无 torch)。

合成 3 种 report(report.py 结构):正常 high / 分歧降级 / abstain,验证记录、聚合、jsonl 往返。
真实填充(真 predictor 跑 run_request_ml)在远端,见 finding_w9。
"""
from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger, LedgerEntry


def _report(rid, *, abstain=False, reliability="high", used=("MockLinear", "MockCPA", "MockGEARS"),
            dis_score=0.1, triggered=False, abstain_reasons=None, downgrade_reasons=None):
    return {
        "request_id": rid, "abstain": abstain, "reliability": reliability,
        "prediction": None if abstain else {"delta": [0.1, 0.2]},
        "models_used": list(used), "models_rejected": [], "models_failed": [],
        "abstain_reasons": abstain_reasons or [], "downgrade_reasons": downgrade_reasons or [],
        "failed_checks": [], "critic_violations": [],
        "model_disagreement": {"score": dis_score, "triggered": triggered, "n_models": len(used),
                               "n_zero_vector_pairs": 0, "threshold": 0.5},
        "caution_flags": {}, "provenance": {},
    }


def test_record_three_report_kinds_and_summary():
    led = EvalLedger()
    led.record(_report("s1"), request={"species": "human", "perturbation_targets": ["AHR"]},
               delta_pearson=0.67, seen_in_train=True)
    led.record(_report("s2", reliability="medium", dis_score=0.8, triggered=True,
                       downgrade_reasons=["downgrade:model_disagreement_too_high"]),
               request={"species": "human", "perturbation_targets": ["ZZZZ9"]},
               delta_pearson=0.30, seen_in_train=False)
    led.record(_report("s3", abstain=True, reliability="low", used=[],
                       abstain_reasons=["all_predictors_rejected"]),
               request={"species": "bacteria", "perturbation_targets": ["recA"]})

    assert len(led.entries) == 3
    s = led.summary()
    assert s["n"] == 3
    assert s["abstain_rate"] == 1 / 3
    assert s["downgrade_rate"] == 1 / 3
    assert s["disagreement_triggered_rate"] == 1 / 3
    assert s["n_evaluated"] == 2  # 仅 s1/s2 有 delta_pearson
    assert abs(s["delta_pearson_mean"] - (0.67 + 0.30) / 2) < 1e-9
    assert s["reliability_counts"] == {"high": 1, "medium": 1, "low": 1}

    # 字段抽取正确性
    e2 = led.entries[1]
    assert e2.disagreement_score == 0.8 and e2.disagreement_triggered is True
    assert e2.seen_in_train is False and "downgrade:model_disagreement_too_high" in e2.downgrade_reasons
    e3 = led.entries[2]
    assert e3.abstain is True and e3.models_used == [] and "all_predictors_rejected" in e3.abstain_reasons


def test_jsonl_roundtrip(tmp_path):
    led = EvalLedger()
    led.record(_report("s1"), request={"species": "human", "perturbation_targets": ["AHR"]},
               delta_pearson=0.67, seen_in_train=True)
    p = tmp_path / "ledger.jsonl"
    led.to_jsonl(p)
    led2 = EvalLedger.from_jsonl(p)
    assert len(led2.entries) == 1
    assert isinstance(led2.entries[0], LedgerEntry)
    assert led2.entries[0].as_dict() == led.entries[0].as_dict()
    assert led2.summary() == led.summary()
