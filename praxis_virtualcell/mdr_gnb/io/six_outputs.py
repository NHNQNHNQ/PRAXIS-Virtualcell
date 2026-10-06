"""六件套输出编排(Phase 5):把 run_mdr_query 结果 → 6 个可审计文件。

report.json / report.md / provenance.json / active_learning_queue.json / ledger.jsonl /
validation_plan.md。流程:report → attach_evidence_level(E0-E5,Phase4)→ attach_active_learning
(AMR advisory,Phase5)→ 渲染落盘。

红线:全程 advisory 只加 provenance 键(evidence_level / active_learning),**裁决字段一字不改**
(byte-identical);确定性(json sort_keys,无 wall-clock/随机),report.md 走 VC 镜像渲染器。
"""
from __future__ import annotations

import json
import os

from praxis_virtualcell.io.report_markdown import render_report_md
from praxis_virtualcell.mdr_gnb.coordinator.active_learning import attach_active_learning
from praxis_virtualcell.mdr_gnb.coordinator.evidence_level import attach_evidence_level
from praxis_virtualcell.mdr_gnb.io.ledger_writer import write_ledger
from praxis_virtualcell.mdr_gnb.io.validation_plan_writer import write_validation_plan

SIX_FILES = (
    "report.json", "report.md", "provenance.json",
    "active_learning_queue.json", "ledger.jsonl", "validation_plan.md",
)


def _vc_job(report: dict, request: dict | None) -> dict:
    """把 MDR report 组装成 VC report_markdown 期望的 job(不改镜像,只做视图适配)。

    MDR 用 `abstained`,VC 渲染器读 `abstain`;MDR 队列存 provenance.active_learning,
    渲染器读 provenance.learning_queue —— 此处只做只读键别名,不动裁决。
    """
    view = dict(report)
    view["abstain"] = bool(report.get("abstained"))
    if not view["abstain"]:
        pred: dict = {}
        if report.get("sir") is not None:
            pred["sir"] = report.get("sir")
            pred["sir_prob"] = report.get("sir_prob")
        if report.get("mic_range") is not None:
            pred["mic_range"] = report.get("mic_range")
        if report.get("activity") is not None:          # 线B:化合物活性预测(sm_activity)
            pred["activity"] = report.get("activity")
        view["prediction"] = pred or None
    # provenance 键别名:active_learning → learning_queue(供 VC 渲染器读验证计划段)
    prov = dict(report.get("provenance") or {})
    if "active_learning" in prov:
        prov = dict(prov)
        prov["learning_queue"] = prov["active_learning"]
    view["provenance"] = prov
    return {"report": view, "request": request or {}, "mode": "offline", "provenance": prov}


def enrich_report(result: dict, *, request: dict | None = None,
                  module_plan=None, evidence_level: dict | None = None) -> dict:
    """report → 挂 evidence_level(E0-E5)+ active_learning(AMR advisory)。返回新 report。"""
    report = result.get("report") or {}
    disagreement = result.get("disagreement") or {}
    rep = attach_evidence_level(report, disagreement=disagreement, request=request)
    ev = rep["provenance"]["evidence_level"]
    if evidence_level is not None:              # 外部显式覆盖(可选)
        ev = evidence_level
    rep = attach_active_learning(rep, evidence_level=ev, module_plan=module_plan,
                                 request=request, disagreement=disagreement)
    if module_plan is not None:                 # module_plan 只读入 provenance(展示层)
        prov = dict(rep.get("provenance") or {})
        prov["module_plan"] = module_plan.to_dict() if hasattr(module_plan, "to_dict") else module_plan
        rep = dict(rep)
        rep["provenance"] = prov
    return rep


def write_six_outputs(out_dir: str, *, result: dict, request: dict | None = None,
                      module_plan=None, evidence_level: dict | None = None) -> dict:
    """落六件套到 out_dir,返回 {文件名: 绝对路径}。advisory 只加 provenance,不改裁决(红线)。"""
    os.makedirs(out_dir, exist_ok=True)
    rep = enrich_report(result, request=request, module_plan=module_plan,
                        evidence_level=evidence_level)
    prov = rep.get("provenance") or {}
    queue = prov.get("active_learning") or {"items": [], "notes": []}
    paths = {name: os.path.join(out_dir, name) for name in SIX_FILES}

    # 1. report.json(完整 report,含 provenance.evidence_level/active_learning)
    with open(paths["report.json"], "w", encoding="utf-8") as f:
        f.write(json.dumps(rep, ensure_ascii=False, sort_keys=True, indent=2))
    # 2. report.md(VC 镜像渲染器,只读 artifact)
    with open(paths["report.md"], "w", encoding="utf-8") as f:
        f.write(render_report_md(_vc_job(rep, request)))
    # 3. provenance.json
    with open(paths["provenance.json"], "w", encoding="utf-8") as f:
        f.write(json.dumps(prov, ensure_ascii=False, sort_keys=True, indent=2))
    # 4. active_learning_queue.json
    with open(paths["active_learning_queue.json"], "w", encoding="utf-8") as f:
        f.write(json.dumps(queue, ensure_ascii=False, sort_keys=True, indent=2))
    # 5. ledger.jsonl(append 一行;特征无标签泄漏)
    write_ledger(paths["ledger.jsonl"], rep, request)
    # 6. validation_plan.md
    write_validation_plan(paths["validation_plan.md"], queue, report=rep)
    return paths
