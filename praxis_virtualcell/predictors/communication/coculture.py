"""R6(v0.5):Co-culture / two-cell sender→receiver case —— 多步通讯链(填应用 5 例 5C)。

复用 `lr_comm.LRCommDB`(通讯)+ `state.cell_state.CellStateDB`(receiver 状态),做**两步链**:
  step1 通讯:sender IFN 诱导 CXCL10 → receiver CXCR3(ctrl vs stim,是否诱导)
  step2 receiver 响应:receiver 细胞的 ISG 激活状态(ctrl vs stim,是否被激活)

治理(R6 多步):**两步都成立**(通讯诱导 AND receiver 激活)→ accept 完整信号链;任一弱 → downgrade
(不硬报完整链);ligand 不在库 → abstain。证明 agent 能组织 sender/ligand/receptor/receiver-state 多步分析。
不训练模型。
"""
from __future__ import annotations

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.communication.lr_comm import LRCommDB
from praxis_virtualcell.predictors.state.cell_state import CellStateDB

_RECEIVER_D_ACCEPT = 0.8      # receiver ISG 激活效应阈
_COMM_FOLD = 2.0              # 通讯诱导阈(stim/ctrl)
_BOUNDARY = ("两步链均为代理:通讯=ligand×receptor 共表达,receiver 响应=ISG marker 评分;**非**实测信号"
             "转导;Kang 2018 PBMC 非真 co-culture(以 sender/receiver 细胞类型 + 刺激模拟);downgrade 表"
             "'链证据不完整'。")


def run_coculture_case(raw_req: dict, comm_db: LRCommDB | None = None, state_db: CellStateDB | None = None):
    """Co-culture sender→receiver case → 7 部分 CaseReport(两步链 + 受治理裁决)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "communication":
        raise ValueError(f"co-culture case 期望 communication,route 给了 {dec.engine}")
    comm_db = comm_db or LRCommDB()
    state_db = state_db or CellStateDB()

    ligand = norm["perturbation_targets"][0]
    sender = raw_req.get("sender_cell_type", "CD14+ Monocytes")
    receiver = raw_req.get("receiver_cell_type", "CD8 T cells")
    receptor = comm_db.receptor_of(ligand)

    if receptor is None:
        return _report(raw_req, norm, dec, ligand, None, sender, receiver, None, None,
                       "abstain", [f"ligand_not_in_lr_db:{ligand}"]), dec

    # step1 通讯诱导
    ctrl = comm_db.comm_score(ligand, receptor, sender, receiver, "ctrl")
    stim = comm_db.comm_score(ligand, receptor, sender, receiver, "stim")
    comm_induced = bool(ctrl and stim and (stim["score"] > ctrl["score"] * _COMM_FOLD))
    # step2 receiver ISG 激活
    rstate = state_db.state_shift(cell_type=receiver)
    receiver_activated = bool(rstate["cohens_d"] is not None and rstate["cohens_d"] >= _RECEIVER_D_ACCEPT)

    flags = []
    if comm_induced and receiver_activated:
        disposition = "accept"
    else:
        disposition = "downgrade"
        if not comm_induced:
            flags.append("communication_not_induced")
        if not receiver_activated:
            flags.append(f"receiver_not_activated:d={rstate['cohens_d']}")

    return _report(raw_req, norm, dec, ligand, receptor, sender, receiver,
                   {"ctrl": ctrl, "stim": stim, "induced": comm_induced},
                   {"receiver_isg_cohens_d": rstate["cohens_d"], "activated": receiver_activated},
                   disposition, flags), dec


def _report(raw_req, norm, dec, ligand, receptor, sender, receiver, comm, recv, disposition, flags):
    return CaseReport(
        case_id=raw_req.get("case_id", "S_coculture"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "ligand": ligand, "receptor": receptor, "sender": sender, "receiver": receiver,
                              "target_output": norm["target_output"]},
        models_tools_selected={"engine": dec.engine,
                               "tool": "Kang 2018:L-R 共表达(通讯)+ ISG 状态(receiver 响应)",
                               "method": "两步链:sender→ligand-receptor→receiver 状态", "reason": dec.reason},
        raw_output={"step1_communication": comm, "step2_receiver_response": recv},
        baseline_comparison={"baseline": "ctrl(未刺激)通讯 + receiver 状态",
                             "chain_complete": disposition == "accept"},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "pertpy Kang 2018 + L-R + ISG 两步链",
                             "source": "pertpy.data.kang_2018 (GSE96583)",
                             "provenance_file": "data/cellstate/PROVENANCE.json",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    )
