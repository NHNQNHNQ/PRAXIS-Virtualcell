"""Two-step sender→receiver proxy analysis using L-R coexpression and receiver ISG state. Step 1 tests IFN-induced
sender CXCL10 and receiver CXCR3; step 2 tests receiver ISG activation. Both steps must support the chain for
accept; weak links downgrade and unavailable ligands abstain. This is marker-based analysis, without model
training.
"""

from __future__ import annotations

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.communication.lr_comm import LRCommDB
from praxis_virtualcell.predictors.state.cell_state import CellStateDB

_RECEIVER_D_ACCEPT = 0.8
_COMM_FOLD = 2.0
_BOUNDARY = (
    "Both chain steps are proxies: communication uses ligand×receptor coexpression and "
    "receiver response uses ISG markers; neither measures signal transduction. Kang 2018 "
    "PBMC is not a true co-culture experiment (sender/receiver cell types and stimulation "
    "are used as proxies); downgrade indicates 'incomplete chain evidence'."
)


def run_coculture_case(raw_req: dict, comm_db: LRCommDB | None = None, state_db: CellStateDB | None = None):
    """Return a 7-part sender→receiver case report with two-step evidence and governance."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "communication":
        raise ValueError(f"co-culture case expected communication; routing selected {dec.engine}")
    comm_db = comm_db or LRCommDB()
    state_db = state_db or CellStateDB()

    ligand = norm["perturbation_targets"][0]
    sender = raw_req.get("sender_cell_type", "CD14+ Monocytes")
    receiver = raw_req.get("receiver_cell_type", "CD8 T cells")
    receptor = comm_db.receptor_of(ligand)

    if receptor is None:
        return _report(
            raw_req, norm, dec, ligand, None, sender, receiver, None, None, "abstain", [f"ligand_not_in_lr_db:{ligand}"]
        ), dec

    ctrl = comm_db.comm_score(ligand, receptor, sender, receiver, "ctrl")
    stim = comm_db.comm_score(ligand, receptor, sender, receiver, "stim")
    comm_induced = bool(ctrl and stim and (stim["score"] > ctrl["score"] * _COMM_FOLD))

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

    return _report(
        raw_req,
        norm,
        dec,
        ligand,
        receptor,
        sender,
        receiver,
        {"ctrl": ctrl, "stim": stim, "induced": comm_induced},
        {"receiver_isg_cohens_d": rstate["cohens_d"], "activated": receiver_activated},
        disposition,
        flags,
    ), dec


def _report(raw_req, norm, dec, ligand, receptor, sender, receiver, comm, recv, disposition, flags):
    return CaseReport(
        case_id=raw_req.get("case_id", "S_coculture"),
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"],
            "perturbation_object": norm["perturbation_object"],
            "ligand": ligand,
            "receptor": receptor,
            "sender": sender,
            "receiver": receiver,
            "target_output": norm["target_output"],
        },
        models_tools_selected={
            "engine": dec.engine,
            "tool": "Kang 2018: L-R coexpression (communication) + ISG state (receiver response)",
            "method": "Two-step chain: sender → ligand-receptor → receiver state",
            "reason": dec.reason,
        },
        raw_output={"step1_communication": comm, "step2_receiver_response": recv},
        baseline_comparison={
            "baseline": "ctrl (unstimulated) communication + receiver state",
            "chain_complete": disposition == "accept",
        },
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={
            "tool": "pertpy Kang 2018 + L-R + ISG two-step chain",
            "source": "pertpy.data.kang_2018 (GSE96583)",
            "provenance_file": "data/cellstate/PROVENANCE.json",
            "rules_hit": [dec.reason],
            "boundary": _BOUNDARY,
        },
    )
