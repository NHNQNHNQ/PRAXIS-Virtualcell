"""W5.4(v0.4,Phase II):Cell-cell communication case —— ligand-receptor 共表达(填补 Communication 空白应用)。

数据:Kang 2018 的 L-R 子集(`data/cellstate/kang_lr_subset.json`,8 配体-受体对 × cell types × ctrl/stim)。
分析:communication score(sender→receiver) = mean_lognorm(ligand in sender) × mean_lognorm(receptor in
receiver)(共表达乘积),比较 ctrl vs stim。

可检验生物学:IFN-β 强诱导 **CXCL10**(单核)→ **CXCR3**(T/NK),经典趋化因子通讯轴 → stim 通讯 score 骤升。
治理(R6):ligand 或 receptor 未表达 → downgrade/abstain(无通讯证据,不虚构);两端都表达且 score 明显 → accept。

科学默认:CP10k+log1p;communication score = ligand×receptor 平均表达乘积(NicheNet/CellPhoneDB 同思路);
表达阈 0.5;score 是**共表达代理**,非实测信号转导。
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
_BOUNDARY = ("communication score 是 ligand×receptor 共表达代理(CP10k+log1p 均值乘积,NicheNet/CellPhoneDB "
             "思路),**非**实测信号转导或通量;Kang 2018 PBMC 子集;ligand/receptor 未表达即弃权,"
             "不代表无通讯,仅表'共表达证据不足'。")


class LRCommDB:
    """Kang L-R 子集:按 (cell_type, label) 聚合基因平均 lognorm 表达。"""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._d = json.loads(Path(json_path or _DEFAULT_SUBSET).read_text(encoding="utf-8"))
        self._genes = self._d["gene_order"]
        self._idx = {g: i for i, g in enumerate(self._genes)}
        self._pairs = {p[0]: p[1] for p in self._d["lr_pairs"]}   # ligand → receptor
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
    """Cell-cell communication case → 7 部分 CaseReport(真实 L-R 共表达 + 受治理裁决)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "communication":
        raise ValueError(f"communication case 期望 communication,route 给了 {dec.engine}")
    db = db or LRCommDB()

    ligand = norm["perturbation_targets"][0]
    sender = raw_req.get("sender_cell_type", "CD14+ Monocytes")
    receiver = raw_req.get("receiver_cell_type", "CD8 T cells")
    receptor = db.receptor_of(ligand)

    if receptor is None:
        report = _report(raw_req, norm, dec, ligand, None, sender, receiver, None, None,
                         "abstain", [f"ligand_not_in_lr_db:{ligand}"])
        return report, dec

    ctrl = db.comm_score(ligand, receptor, sender, receiver, "ctrl")
    stim = db.comm_score(ligand, receptor, sender, receiver, "stim")
    if ctrl is None or stim is None:
        return _report(raw_req, norm, dec, ligand, receptor, sender, receiver, ctrl, stim,
                       "abstain", ["ligand_or_receptor_cell_type_missing"]), dec

    # 治理:两端都需表达(取 stim/ctrl 中较高)才有通讯证据
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

    return _report(raw_req, norm, dec, ligand, receptor, sender, receiver, ctrl, stim,
                   disposition, flags), dec


def _report(raw_req, norm, dec, ligand, receptor, sender, receiver, ctrl, stim, disposition, flags):
    fold = None
    if ctrl and stim and ctrl["score"] > 0:
        fold = round(stim["score"] / ctrl["score"], 2)
    return CaseReport(
        case_id=raw_req.get("case_id", "S_lr_communication"),
        structured_input=dict(raw_req),
        object_normalization={"species": norm["species"], "perturbation_object": norm["perturbation_object"],
                              "ligand": ligand, "receptor": receptor,
                              "sender": sender, "receiver": receiver, "target_output": norm["target_output"]},
        models_tools_selected={"engine": dec.engine, "tool": "Kang 2018 + L-R 共表达(NicheNet/CellPhoneDB 思路)",
                               "method": "ligand×receptor 平均表达乘积(sender→receiver)", "reason": dec.reason},
        raw_output={"ligand": ligand, "receptor": receptor, "sender": sender, "receiver": receiver,
                    "ctrl": ctrl, "stim": stim, "score_fold_stim_vs_ctrl": fold},
        baseline_comparison={"baseline": "unstimulated (ctrl) communication score",
                             "ctrl_score": ctrl["score"] if ctrl else None,
                             "stim_score": stim["score"] if stim else None, "fold": fold},
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={"tool": "pertpy Kang 2018 + L-R co-expression",
                             "source": "pertpy.data.kang_2018 (GSE96583)",
                             "provenance_file": "data/cellstate/PROVENANCE.json",
                             "rules_hit": [dec.reason], "boundary": _BOUNDARY},
    )
