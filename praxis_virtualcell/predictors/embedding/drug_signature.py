"""Curated Enrichr LINCS L1000 drug-signature MOA analysis using consensus top-100 up/down genes. Similarity=(up
Jaccard+down Jaccard)/2; enrichment compares the best same-MOA partner with the cross-MOA mean. Default
threshold=1.5, requiring at least 50% higher similarity. Weak signals/no partner downgrade and missing drugs
abstain. Raw library size is about 30MB; provenance stores URL/sha256. No model is trained.
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "drug_signatures" / "curated_subset.json"
_ENRICH_THRESHOLD = 1.5

_BOUNDARY = (
    'LINCS L1000 signatures are noisy bulk/population consensus up/down gene sets, not '
    'per-cell expression predictions. MOA annotations are curated pharmacological '
    'knowledge, not new findings from this analysis; the enrichment threshold 1.5 is a '
    'configured default. Weak signals or singleton drugs are downgraded for insufficient '
    'MOA-consistency evidence, without implying drug inefficacy.'
)


def _jaccard(a, b) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a | b) else 0.0


class DrugSignatureDB:
    """Curated LINCS L1000 consensus up/down signatures and MOA annotations, keyed by lowercase drug names."""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._db = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))

    def has(self, drug: str) -> bool:
        return str(drug).strip().lower() in self._db

    def _get(self, drug: str) -> dict:
        return self._db[str(drug).strip().lower()]

    def moa(self, drug: str) -> str:
        return self._get(drug)["moa"]

    def up(self, drug: str) -> list:
        return self._get(drug)["up"]

    def down(self, drug: str) -> list:
        return self._get(drug)["down"]

    def similarity(self, a: str, b: str) -> float:
        """Compute (up Jaccard+down Jaccard)/2 for bidirectional signature consistency."""
        return (_jaccard(self.up(a), self.up(b)) + _jaccard(self.down(a), self.down(b))) / 2

    def moa_enrichment(self, drug: str) -> dict:
        """Compare the best same-MOA similarity with the cross-MOA mean; absent same-MOA references return
        partner=None.
        """
        d = str(drug).strip().lower()
        moa = self.moa(d)
        same = [x for x in self._db if x != d and self._db[x]["moa"] == moa]
        cross = [x for x in self._db if self._db[x]["moa"] != moa]
        cross_mean = (sum(self.similarity(d, x) for x in cross) / len(cross)) if cross else 0.0
        if not same:
            return {"partner": None, "same_sim": 0.0, "cross_mean": cross_mean, "enrichment": 0.0}
        partner = max(same, key=lambda x: self.similarity(d, x))
        same_sim = self.similarity(d, partner)
        enr = (same_sim / cross_mean) if cross_mean else 0.0
        return {"partner": partner, "same_sim": same_sim, "cross_mean": cross_mean, "enrichment": enr}


_ORDER = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3}


def run_drug_response_case(raw_req: dict, db: DrugSignatureDB | None = None,
                           threshold: float = _ENRICH_THRESHOLD):
    """Run the human drug-signature case and return a 7-part CaseReport with RouteDecision."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "embedding":
        raise ValueError(f"drug case expected embedding; routing selected {dec.engine}")
    db = db or DrugSignatureDB()

    per_drug, dispositions, flags = [], [], []
    for drug in norm["perturbation_targets"]:
        if not db.has(drug):
            per_drug.append({"drug": drug, "in_db": False, "moa": None, "moa_enrichment": None})
            dispositions.append("abstain")
            flags.append(f"drug_not_in_db:{drug}")
            continue
        enr = db.moa_enrichment(drug)
        rec = {"drug": drug, "in_db": True, "moa": db.moa(drug),
               "same_moa_partner": enr["partner"],
               "same_moa_similarity": round(enr["same_sim"], 4),
               "cross_moa_mean_similarity": round(enr["cross_mean"], 4),
               "moa_enrichment": round(enr["enrichment"], 3),
               "top_up_genes": db.up(drug)[:10]}
        per_drug.append(rec)
        if enr["partner"] is None:
            dispositions.append("downgrade")
            flags.append(f"no_same_moa_reference:{drug}")
        elif enr["enrichment"] >= threshold:
            dispositions.append("accept")
        else:
            dispositions.append("downgrade")
            flags.append(f"weak_moa_consistency:{drug}")

    disposition = max(dispositions, key=lambda x: _ORDER[x]) if dispositions else "abstain"

    report = CaseReport(
        case_id=raw_req.get("case_id", "C6_drug_response"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "normalized_targets": norm["perturbation_targets"],
                              "target_output": norm["target_output"], "dose": norm.get("dose")},
        models_tools_selected={"engine": dec.engine, "tool": "LINCS L1000 Chem Pert (Enrichr) signature DB",
                               "method": "signature MOA-consistency (Jaccard enrichment)", "reason": dec.reason},
        raw_output={"per_drug": per_drug, "enrichment_threshold": threshold},
        baseline_comparison={"baseline": "cross-MOA mean signature similarity",
                             "interpretation": (
                                 'Enrichment = within-MOA similarity / cross-MOA mean; MOA consistency requires '
                                 'exceeding the threshold'
                             )},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "LINCS L1000 Chem Pert (Enrichr)",
                             "source": "https://maayanlab.cloud/Enrichr (LINCS_L1000_Chem_Pert_up/down)",
                             "provenance_file": "data/drug_signatures/PROVENANCE.json",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    )
    return report, dec
