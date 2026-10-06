"""ledger_writer:审计台账(ledger.jsonl)一行一 query。

红线(防泄漏):extract_features **只含推理特征**(species/drug/药类/amr 基因/assay/请求输出),
绝不含标签(sir/sir_prob/mic)—— 台账若日后训 reliability 模型,特征不得泄漏结论。
标签作为 outcome 与 features 分区记录(供审计,不混入特征)。确定性:json sort_keys,无 wall-clock。
"""
from __future__ import annotations

import json

# 明令禁入特征的标签键(防泄漏白名单反面)
_LABEL_KEYS = ("sir", "sir_prob", "mic", "mic_range", "label")


def extract_features(report: dict, request: dict | None = None) -> dict:
    """抽推理特征(无标签)。features 与预测结论严格分离,防标签泄漏(红线)。"""
    req = request or {}
    amr = req.get("amr_profile") or {}
    genes = sorted(str(k) for k, v in amr.items() if v)   # 存在的耐药基因/突变(无标签)
    feats = {
        "species": str(req.get("species", "")),
        "drug": str(report.get("drug", "")),
        "drug_class": str(req.get("drug_class", "")),
        "assay_context": dict(req.get("assay_context") or {}),
        "requested_outputs": list(req.get("requested_outputs") or []),
        "amr_genes_present": genes,
        "n_amr_genes": len(genes),
    }
    # 兜底断言:任何标签键都不得出现在特征里(红线自检)
    assert not any(k in feats for k in _LABEL_KEYS), "特征泄漏标签"
    return feats


def build_ledger_row(report: dict, request: dict | None = None) -> dict:
    """一行台账:features(无标签)+ outcome(标签/裁决,审计用,与特征分区)+ 证据等级。"""
    prov = report.get("provenance") or {}
    ev = prov.get("evidence_level") or {}
    return {
        "task_id": report.get("task_id"),
        "drug": report.get("drug"),
        "features": extract_features(report, request),
        "outcome": {                                    # 结论/标签 —— 审计区,非特征
            "abstained": bool(report.get("abstained")),
            "sir": report.get("sir"),
            "output_kind": report.get("output_kind"),
        },
        "evidence_level": ev.get("level"),
        "disposition": prov.get("route"),
    }


def write_ledger(path: str, report: dict, request: dict | None = None) -> str:
    """追加一行 jsonl(确定性 sort_keys)。返回 path。"""
    row = build_ledger_row(report, request)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path
