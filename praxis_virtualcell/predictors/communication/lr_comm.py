"""Kang 2018 L-R subset with 8 pairs across cell types and ctrl/stim. Score sender→receiver as mean log-normalized
ligand times mean log-normalized receptor, then compare conditions. IFN-beta CXCL10/CXCR3 is a testable axis.
Use CP10k+log1p and expression threshold 0.5; coexpression is a proxy rather than measured signal transduction.
Missing endpoints abstain/downgrade.
"""

from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.state.scoring import lognorm

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "cellstate" / "kang_lr_subset.json"
_EXPR_MIN = 0.5
_BOUNDARY = (
    "communication score is a ligand×receptor coexpression proxy (product of CP10k+log1p "
    "means, inspired by NicheNet/CellPhoneDB), not measured signal transduction or flux. "
    "Kang 2018 PBMC subset; absent ligand/receptor expression causes abstention, which "
    "indicates insufficient coexpression evidence rather than absence of communication."
)


class LRCommDB:
    """Aggregate Kang L-R log-normalized expression by (cell_type, label)."""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))
        self._genes = self._d["gene_order"]
        self._idx = {g: i for i, g in enumerate(self._genes)}
        self._pairs = {p[0]: p[1] for p in self._d["lr_pairs"]}  # ligand → receptor
        self._agg = self._aggregate()

    def _aggregate(self) -> dict:
        acc: dict = {}
        for c in self._d["cells"]:
            key = (c["cell_type"], c["label"])
            ln = lognorm(c["counts"], c["total_counts"])
            a = acc.setdefault(key, {"n": 0, "sum": [0.0] * len(self._genes)})
            a["n"] += 1
            for i in range(len(self._genes)):
                a["sum"][i] += ln[i]
        return {k: {"n": v["n"], "mean": [s / v["n"] for s in v["sum"]]} for k, v in acc.items()}

    def expr(self, gene: str, cell_type: str, label: str) -> float | None:
        if gene not in self._idx or (cell_type, label) not in self._agg:
            return None
        return self._agg[(cell_type, label)]["mean"][self._idx[gene]]

    def receptor_of(self, ligand: str) -> str | None:
        return self._pairs.get(ligand)

    def comm_score(self, ligand: str, receptor: str, sender: str, receiver: str, label: str):
        lg = self.expr(ligand, sender, label)
        rc = self.expr(receptor, receiver, label)
        if lg is None or rc is None:
            return None
        return {"ligand_expr": round(lg, 3), "receptor_expr": round(rc, 3), "score": round(lg * rc, 4)}


def run_communication_case(raw_req: dict, db: LRCommDB | None = None):
    """Return a 7-part communication case report with measured L-R coexpression and governance."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "communication":
        raise ValueError(f"communication case expected communication; routing selected {dec.engine}")
    db = db or LRCommDB()

    ligand = norm["perturbation_targets"][0]
    sender = raw_req.get("sender_cell_type", "CD14+ Monocytes")
    receiver = raw_req.get("receiver_cell_type", "CD8 T cells")
    receptor = db.receptor_of(ligand)

    if receptor is None:
        report = _report(
            raw_req, norm, dec, ligand, None, sender, receiver, None, None, "abstain", [f"ligand_not_in_lr_db:{ligand}"]
        )
        return report, dec

    ctrl = db.comm_score(ligand, receptor, sender, receiver, "ctrl")
    stim = db.comm_score(ligand, receptor, sender, receiver, "stim")
    if ctrl is None or stim is None:
        return _report(
            raw_req,
            norm,
            dec,
            ligand,
            receptor,
            sender,
            receiver,
            ctrl,
            stim,
            "abstain",
            ["ligand_or_receptor_cell_type_missing"],
        ), dec

    ligand_ok = max(ctrl["ligand_expr"], stim["ligand_expr"]) >= _EXPR_MIN
    receptor_ok = max(ctrl["receptor_expr"], stim["receptor_expr"]) >= _EXPR_MIN
    if not (ligand_ok and receptor_ok):
        flags = []
        if not ligand_ok:
            flags.append("ligand_not_expressed")
        if not receptor_ok:
            flags.append("receptor_not_expressed")
        disposition = "downgrade"
    elif stim["score"] > ctrl["score"] * 2 or stim["score"] >= 1.0:
        disposition, flags = "accept", []
    else:
        disposition, flags = "caution", ["weak_communication_shift"]

    return _report(raw_req, norm, dec, ligand, receptor, sender, receiver, ctrl, stim, disposition, flags), dec


def _report(raw_req, norm, dec, ligand, receptor, sender, receiver, ctrl, stim, disposition, flags):
    fold = None
    if ctrl and stim and ctrl["score"] > 0:
        fold = round(stim["score"] / ctrl["score"], 2)
    return CaseReport(
        case_id=raw_req.get("case_id", "S_lr_communication"),
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
            "tool": "Kang 2018 + L-R coexpression (inspired by NicheNet/CellPhoneDB)",
            "method": "Product of mean ligand×receptor expression (sender → receiver)",
            "reason": dec.reason,
        },
        raw_output={
            "ligand": ligand,
            "receptor": receptor,
            "sender": sender,
            "receiver": receiver,
            "ctrl": ctrl,
            "stim": stim,
            "score_fold_stim_vs_ctrl": fold,
        },
        baseline_comparison={
            "baseline": "unstimulated (ctrl) communication score",
            "ctrl_score": ctrl["score"] if ctrl else None,
            "stim_score": stim["score"] if stim else None,
            "fold": fold,
        },
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={
            "tool": "pertpy Kang 2018 + L-R co-expression",
            "source": "pertpy.data.kang_2018 (GSE96583)",
            "provenance_file": "data/cellstate/PROVENANCE.json",
            "rules_hit": [dec.reason],
            "boundary": _BOUNDARY,
        },
    )
