"""六件套输出:report.md/report.json/ledger.jsonl/provenance.json/validation_plan.md/
active_learning_queue.json(Phase 5)。红线:advisory 不改裁决;ledger 特征无标签泄漏;确定性。"""
import json
import os

from praxis_virtualcell.mdr_gnb.io.six_outputs import write_six_outputs, SIX_FILES
from praxis_virtualcell.mdr_gnb.io.ledger_writer import extract_features
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query


def _raw(species="klebsiella_pneumoniae", drug="meropenem", drug_class="carbapenems",
         amr_profile=None):
    return {"species": species,
            "drug_panel": [{"drug": drug, "drug_class": drug_class}],
            "requested_outputs": ["SIR"],
            "amr_profile": amr_profile or {"blaKPC-2": True, "blaOXA-48": True, "blaNDM-1": True}}


def _run(**kw):
    raw = _raw(**kw)
    result = run_mdr_query(raw, seed_task_id="t-six")
    (drug_entry,) = raw["drug_panel"]
    request = {"species": raw["species"], "drug": drug_entry["drug"],
               "drug_class": drug_entry["drug_class"],
               "amr_profile": raw["amr_profile"], "requested_outputs": raw["requested_outputs"]}
    return result, request


def test_six_files_all_present(tmp_path):
    result, request = _run()
    out = write_six_outputs(str(tmp_path), result=result, request=request)
    for name in SIX_FILES:
        assert name in out
        assert os.path.exists(out[name]), f"缺 {name}"
        assert os.path.getsize(out[name]) > 0, f"{name} 为空"


def test_report_json_valid_and_has_decision(tmp_path):
    result, request = _run()
    out = write_six_outputs(str(tmp_path), result=result, request=request)
    rep = json.loads(open(out["report.json"]).read())
    assert "abstained" in rep and "sir" in rep
    assert "evidence_level" in rep["provenance"]
    assert "active_learning" in rep["provenance"]


def test_ledger_features_no_label_leak(tmp_path):
    result, request = _run()
    out = write_six_outputs(str(tmp_path), result=result, request=request)
    line = open(out["ledger.jsonl"]).read().strip().splitlines()[0]
    row = json.loads(line)
    feats = row["features"]
    # 防泄漏红线:特征不得含标签(sir/sir_prob/mic)
    for banned in ("sir", "sir_prob", "mic", "mic_range", "label"):
        assert banned not in feats, f"特征泄漏标签 {banned}"
    # extract_features 单测同样无标签
    ef = extract_features(result["report"], request)
    assert "sir" not in ef and "mic" not in ef
    assert ef["species"] == "klebsiella_pneumoniae"


def test_queue_json_valid(tmp_path):
    result, request = _run()
    out = write_six_outputs(str(tmp_path), result=result, request=request)
    q = json.loads(open(out["active_learning_queue.json"]).read())
    assert "items" in q


def test_report_md_nonempty(tmp_path):
    result, request = _run()
    out = write_six_outputs(str(tmp_path), result=result, request=request)
    md = open(out["report.md"]).read()
    assert "Report" in md and len(md) > 100


def test_validation_plan_md_nonempty(tmp_path):
    result, request = _run()
    out = write_six_outputs(str(tmp_path), result=result, request=request)
    vp = open(out["validation_plan.md"]).read()
    assert len(vp) > 20


def test_advisory_does_not_change_decision(tmp_path):
    # 红线:六件套里的裁决字段 == run_mdr_query 原 report(只多 provenance 键)
    result, request = _run()
    orig = json.loads(json.dumps(result["report"]))   # 深拷贝快照
    out = write_six_outputs(str(tmp_path), result=result, request=request)
    rep = json.loads(open(out["report.json"]).read())
    for k in ("sir", "sir_prob", "abstained", "abstain_reasons", "downgrade_reasons",
              "caution_flags", "critic_violations", "drug", "task_id", "output_kind"):
        assert rep[k] == orig[k], f"裁决字段 {k} 被改"


def test_deterministic_bytes(tmp_path):
    # 确定性:同输入两次输出 → report.json/queue/ledger 字节一致
    result, request = _run()
    d1, d2 = tmp_path / "a", tmp_path / "b"
    d1.mkdir(); d2.mkdir()
    o1 = write_six_outputs(str(d1), result=result, request=request)
    result2, request2 = _run()
    o2 = write_six_outputs(str(d2), result=result2, request=request2)
    for name in ("report.json", "active_learning_queue.json", "ledger.jsonl", "provenance.json"):
        assert open(o1[name]).read() == open(o2[name]).read(), f"{name} 非确定性"
