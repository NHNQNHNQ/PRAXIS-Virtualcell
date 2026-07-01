"""R6(v0.5):Co-culture sender→receiver 两步链 case —— 真跑(填应用 5 例 5C)。

复用 Kang L-R(通讯)+ ISG(receiver 状态)。断言:
- CXCL10 Mono→CD8T:通讯诱导(fold~51)+ CD8T ISG 激活(d~2.8)→ 两步成立 → accept;
- receiver=Megakaryocytes:ISG 几乎不激活(d~0.2)→ 链不完整 → downgrade。
"""
import pytest

from praxis_virtualcell.predictors.communication.coculture import run_coculture_case
from praxis_virtualcell.predictors.communication.lr_comm import LRCommDB, _DEFAULT_SUBSET as _LR
from praxis_virtualcell.predictors.state.cell_state import CellStateDB, _DEFAULT_SUBSET as _ISG
from praxis_virtualcell.agents.case_report import validate_case_report

if not (_LR.is_file() and _ISG.is_file()):
    pytest.skip("Kang L-R / ISG 子集缺失", allow_module_level=True)


@pytest.fixture(scope="module")
def dbs():
    return LRCommDB(), CellStateDB()


def test_full_chain_accept(dbs):
    comm_db, state_db = dbs
    report, dec = run_coculture_case({
        "case_id": "S_cc", "species": "human", "perturbation_object": "ligand",
        "perturbation_targets": ["CXCL10"], "target_output": "communication",
        "sender_cell_type": "CD14+ Monocytes", "receiver_cell_type": "CD8 T cells",
    }, comm_db=comm_db, state_db=state_db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "communication"
    assert d["raw_output"]["step1_communication"]["induced"] is True
    assert d["raw_output"]["step2_receiver_response"]["activated"] is True
    assert d["reliability_decision"]["disposition"] == "accept"


def test_weak_receiver_downgrades(dbs):
    comm_db, state_db = dbs
    # Megakaryocytes ISG 几乎不激活 → 链不完整 → downgrade
    report, _ = run_coculture_case({
        "species": "human", "perturbation_object": "ligand", "perturbation_targets": ["CXCL10"],
        "target_output": "communication", "sender_cell_type": "CD14+ Monocytes",
        "receiver_cell_type": "Megakaryocytes",
    }, comm_db=comm_db, state_db=state_db)
    d = report.to_dict()
    assert d["reliability_decision"]["disposition"] == "downgrade"
    assert any("receiver_not_activated" in f for f in d["reliability_decision"]["caution_flags"])


def test_unknown_ligand_abstains(dbs):
    comm_db, state_db = dbs
    report, _ = run_coculture_case({
        "species": "human", "perturbation_object": "ligand", "perturbation_targets": ["NOTALIGAND"],
        "target_output": "communication", "sender_cell_type": "CD14+ Monocytes",
        "receiver_cell_type": "CD8 T cells",
    }, comm_db=comm_db, state_db=state_db)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"
