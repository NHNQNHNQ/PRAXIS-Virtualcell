"""W3.1(v0.4):Human drug response case —— LINCS L1000 药物签名 MOA 一致性分析。

数据:Enrichr `LINCS_L1000_Chem_Pert_up/down`(公开,无凭证)的 curated 子集
(`data/drug_signatures/curated_subset.json`,每药 consensus top-100 up/down 基因 + MOA 标注)。
原始大库(~30MB)gitignore,provenance(URL+sha256)见 `data/drug_signatures/PROVENANCE.json`。

分析:drug → 签名(up/down 基因集)→ 与**同 MOA** 药物签名相似度 vs **跨 MOA** 基线 → 富集比。
治理(R6 防过度承诺):富集≥阈值→accept;富集<阈值(弱信号)→downgrade;无同 MOA 参考→downgrade;
药不在库→abstain。**不训练模型**,纯签名检索 + 相似度 + 受治理裁决。

科学默认(自定,写明依据):
- 相似度 = (up-基因 Jaccard + down-基因 Jaccard)/2(签名双向一致才算像);
- 富集阈值 = 1.5(同 MOA 相似度须比跨 MOA 均值高 ≥50% 才认"MOA-consistent");
- consensus top-100(每药跨条件最频繁基因,抗单条件噪声)。
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

_DEFAULT_SUBSET = Path(__file__).resolve().parents[3] / "data" / "drug_signatures" / "curated_subset.json"
_ENRICH_THRESHOLD = 1.5

_BOUNDARY = ("LINCS L1000 签名是 bulk/群体 consensus(方向级 up/down 基因集),噪声大,"
             "**非** per-cell 表达预测;MOA 标注为 curated 教科书药理(非本文新发现);"
             "富集阈值 1.5 为设定默认;弱信号/单例药主动降级,不代表药物无效,仅表'签名证据不足以确证 MOA 一致'。")


def _jaccard(a, b) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a | b) else 0.0


class DrugSignatureDB:
    """curated LINCS L1000 药物签名库(consensus up/down + MOA)。药名小写为键。"""

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
        """(up Jaccard + down Jaccard)/2 —— 双向签名一致性。"""
        return (_jaccard(self.up(a), self.up(b)) + _jaccard(self.down(a), self.down(b))) / 2

    def moa_enrichment(self, drug: str) -> dict:
        """同 MOA 最相似伙伴 相似度 vs 跨 MOA 均值 → 富集比。无同 MOA 伙伴 → partner=None。"""
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


_ORDER = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3}   # 越大越保守


def run_drug_response_case(raw_req: dict, db: DrugSignatureDB | None = None,
                           threshold: float = _ENRICH_THRESHOLD):
    """Human drug response case → 7 部分 CaseReport(真实签名 + 受治理裁决)。返回 (CaseReport, RouteDecision)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "embedding":
        raise ValueError(f"drug case 期望 embedding,route 给了 {dec.engine}")
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
                             "interpretation": "同 MOA 相似度 / 跨 MOA 均值 = 富集;>阈值才认 MOA-consistent"},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "LINCS L1000 Chem Pert (Enrichr)",
                             "source": "https://maayanlab.cloud/Enrichr (LINCS_L1000_Chem_Pert_up/down)",
                             "provenance_file": "data/drug_signatures/PROVENANCE.json",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    )
    return report, dec
