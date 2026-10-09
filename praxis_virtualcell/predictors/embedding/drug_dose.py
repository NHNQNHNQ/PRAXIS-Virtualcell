"""LINCS L1000 dose-signature analysis using top-150 consensus genes. Define the reference as the dose with most
signal and recall=|dose_top∩ref|/|ref|. Spearman of dose versus recall measures monotonicity; accept
threshold=0.6, caution=0.3. Weak/negative evidence downgrades; parse dose from term suffixes without training a
model.
"""

from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "drug_signatures" / "dose_response_subset.json"
_SP_ACCEPT, _SP_CAUTION = 0.6, 0.3
_BOUNDARY = (
    "Dose response is measured by Spearman correlation between dose and recall relative "
    "to the signature at the dose with the most signal; LINCS bulk direction-level "
    "signatures are noisy; downgrade indicates insufficient signature evidence for dose "
    "dependence, not absence of a drug dose effect."
)


def _spearman(x, y) -> float:
    n = len(x)
    if n < 2:
        return 0.0

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0] * n
        for rank, i in enumerate(order):
            r[i] = rank
        return r

    rx, ry = ranks(x), ranks(y)
    dd = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return round(1 - 6 * dd / (n * (n * n - 1)), 3)


class DoseResponseDB:
    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))["drugs"]

    def has(self, drug: str) -> bool:
        return str(drug).strip().lower() in self._d

    def dose_response(self, drug: str) -> dict:
        rows = self._d[str(drug).strip().lower()]["doses"]
        if len(rows) < 3:
            return {"n_doses": len(rows), "spearman": 0.0, "recalls": [], "insufficient": True}
        ref_row = max(rows, key=lambda r: r["n_sig"])
        ref = set(ref_row["top_genes"])
        others = [r for r in rows if r is not ref_row]
        doses = [r["dose"] for r in others]
        recalls = [round(len(set(r["top_genes"]) & ref) / len(ref), 3) if ref else 0.0 for r in others]
        return {
            "n_doses": len(rows),
            "ref_dose": ref_row["dose"],
            "ref_n_sig": ref_row["n_sig"],
            "doses": doses,
            "recalls": recalls,
            "spearman": _spearman(doses, recalls),
            "insufficient": False,
        }


def run_drug_dose_case(raw_req: dict, db: DoseResponseDB | None = None):
    """Return a 7-part dose-response case report with signature monotonicity and governance."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "embedding":
        raise ValueError(f"drug dose case expected embedding; routing selected {dec.engine}")
    db = db or DoseResponseDB()
    drug = norm["perturbation_targets"][0]

    if not db.has(drug):
        dr, disposition, flags = None, "abstain", [f"drug_not_in_dose_db:{drug}"]
    else:
        dr = db.dose_response(drug)
        sp = dr["spearman"]
        max_recall = max(dr["recalls"], default=0.0)
        if dr["insufficient"]:
            disposition, flags = "downgrade", ["insufficient_doses"]
        elif max_recall < 0.05:
            disposition, flags = "downgrade", [f"weak_signature_overlap:max_recall={max_recall}"]
        elif sp >= _SP_ACCEPT:
            disposition, flags = "accept", []
        elif sp >= _SP_CAUTION:
            disposition, flags = "caution", [f"moderate_dose_monotonicity:spearman={sp}"]
        else:
            disposition, flags = "downgrade", [f"no_dose_response:spearman={sp}"]

    return CaseReport(
        case_id=raw_req.get("case_id", "S_drug_dose"),
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"],
            "perturbation_object": norm["perturbation_object"],
            "drug": drug,
            "target_output": norm["target_output"],
        },
        models_tools_selected={
            "engine": dec.engine,
            "tool": "LINCS L1000 dose subset",
            "method": "Dose-Spearman of recall against the maximum-signal dose reference",
            "reason": dec.reason,
        },
        raw_output={"drug": drug, "dose_response": dr},
        baseline_comparison={
            "baseline": "Dose-recall monotonicity (Spearman)",
            "interpretation": "Dose dependence requires Spearman≥0.6",
        },
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={
            "tool": "LINCS L1000 Chem Pert (Enrichr)",
            "provenance_file": "data/drug_signatures/PROVENANCE.json",
            "rules_hit": [dec.reason],
            "boundary": _BOUNDARY,
        },
    ), dec
