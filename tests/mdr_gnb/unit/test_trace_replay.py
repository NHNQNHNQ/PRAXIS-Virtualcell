"""G4 门:端到端 mdr_gnb 智能体链确定性 trace replay + critic 不变量全过。"""
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


def _run():
    return run_mdr_query({
        "species": "escherichia_coli", "strain_id": "EC001",
        "amr_profile": {"blaNDM-5": True},
        "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
        "assay_context": {"method": "broth_microdilution"},
        "requested_outputs": ["MIC_range", "SIR"],
    }, seed_task_id="fixed")


def test_trace_is_deterministic_replay():
    a = _run(); b = _run()
    ta = [(m.message_id, m.timestamp, m.message_type) for m in a["trace"]]
    tb = [(m.message_id, m.timestamp, m.message_type) for m in b["trace"]]
    assert ta == tb, "trace 非确定性,replay 失败"
    assert a["report"] == b["report"]


def test_critic_invariants_all_pass():
    r = _run()
    assert r["report"]["critic_violations"] == []
    snapshot = r["report"]["provenance"]["governance_snapshot"]
    assert len(snapshot["governance_digest"]) == 64
    assert r["trace_metadata"]["governance_snapshot_digest"] == snapshot[
        "governance_digest"
    ]


def test_abstain_branch_replayable():
    r = run_mdr_query({
        "species": "",  # 触发 species_unspecified → abstain
        "drug_panel": [{"drug": "colistin", "drug_class": "polymyxins"}],
    }, seed_task_id="fixed2")
    assert r["report"]["abstained"] is True
    assert "species_uncertain" in r["report"]["abstain_reasons"] or \
           r["route"]["disposition"] == "abstain"
