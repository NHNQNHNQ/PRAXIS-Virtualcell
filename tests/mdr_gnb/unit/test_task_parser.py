"""task_parser:NL/半结构化 → MDRGNBMessage,LLM 只解析不裁决。"""
from praxis_virtualcell.mdr_gnb.coordinator.task_parser import parse_task
from praxis_virtualcell.mdr_gnb.message import MDRGNBMessage


def test_structured_input_passthrough():
    raw = {
        "species": "escherichia_coli", "strain_id": "EC001",
        "amr_profile": {"blaNDM-5": True}, "drug_panel": [{"drug": "meropenem"}],
        "assay_context": {"method": "broth_microdilution"},
        "requested_outputs": ["MIC_range", "SIR"],
    }
    msg = parse_task(raw, task_id="t1")
    assert isinstance(msg, MDRGNBMessage)
    assert msg.task_id == "t1"
    assert msg.species == "escherichia_coli"
    assert msg.drug_panel == [{"drug": "meropenem"}]
    assert msg.boundaries == []  # 结构化输入无解析告警


def test_llm_parse_never_adjudicates():
    # 假 LLM:返回带越权裁决字段的响应,parser 必须剥离,只保留结构化解析结果
    def fake_llm(_prompt):
        return {
            "species": "klebsiella_pneumoniae",
            "drug_panel": [{"drug": "meropenem"}],
            "amr_profile": {"blaKPC-2": True},
            # 越权:LLM 试图给结论,parser 必须丢弃
            "sir": "R", "mic_range": "<=0.25", "abstain": True,
        }
    msg = parse_task("KPC-2 阳性肺克对美罗培南什么结果?",
                     task_id="t2", llm_call=fake_llm)
    assert msg.species == "klebsiella_pneumoniae"
    assert msg.amr_profile == {"blaKPC-2": True}
    # 越权字段全部不得进 message
    assert "sir" not in msg.__dict__ and "mic_range" not in msg.__dict__
    assert msg.boundaries  # 应记录 "llm_parsed" 或字段剥离告警


def test_unparseable_species_flagged_not_guessed():
    msg = parse_task({"species": "", "drug_panel": [{"drug": "colistin"}]}, task_id="t3")
    assert msg.species == ""  # 不臆测
    assert any("species_unspecified" in b for b in msg.boundaries)
