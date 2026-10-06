"""NL / 半结构化输入 → MDRGNBMessage。LLM 只做解析(抽取 species/drug/amr_profile),
绝不产 SIR/MIC/abstain 等裁决字段——parser 用白名单投影强制剥离任何越权字段(fail-safe)。

无 llm_call 时走纯确定性路径(要求输入已是 dict);有 llm_call 时(自由文本)调用 LLM 抽取,
但仍经同一 _project 白名单过滤。boundaries 记录解析层告警(如 species 缺失、LLM 剥离字段),
供 mdr_router / abstain 决策。"""
from __future__ import annotations

from typing import Any, Callable

from praxis_virtualcell.mdr_gnb.message import MDRGNBMessage

# 允许进 MDRGNBMessage 的解析字段(裁决字段一律不在此列)
# smiles:化合物结构输入(canonical SMILES);compound:标识符(名称/CID/ChEMBL/DrugBank),B2 解析器→smiles。
_ALLOWED = {"species", "strain_id", "genome_path", "amr_profile",
            "drug_panel", "assay_context", "requested_outputs", "smiles", "compound",
            "sequence"}   # 线B B5:抗菌肽序列输入
_ADJUDICATION = {"sir", "mic_range", "mic_scalar", "abstain", "confidence",
                 "mechanism", "sir_prob"}

_DEFAULT_OUTPUTS = ["MIC_range", "SIR", "mechanism", "confidence", "experiment_priority"]


def require_exactly_one_drug_entry(drug_panel: Any) -> dict[str, Any]:
    """Return the only executable drug entry or reject the request.

    Parsing remains permissive enough to describe incomplete input through its
    boundaries.  Execution, however, must never silently select a first drug
    from a panel or invent one for an empty panel.
    """
    if not isinstance(drug_panel, list) or len(drug_panel) != 1:
        raise ValueError("exactly_one_drug_required")
    (drug_entry,) = drug_panel
    if not isinstance(drug_entry, dict):
        raise ValueError("invalid_drug_entry")
    drug = drug_entry.get("drug")
    if not isinstance(drug, str) or not drug.strip():
        raise ValueError("drug_required")
    return drug_entry


def _project(d: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """只保留白名单字段;命中裁决字段记入 boundaries 告警。"""
    boundaries: list[str] = []
    stripped = sorted(k for k in d if k in _ADJUDICATION)
    if stripped:
        boundaries.append(f"llm_adjudication_fields_stripped:{stripped}")
    clean = {k: v for k, v in d.items() if k in _ALLOWED}
    return clean, boundaries


def parse_task(raw: Any, *, task_id: str,
               llm_call: Callable[[str], dict[str, Any]] | None = None) -> MDRGNBMessage:
    boundaries: list[str] = []
    if isinstance(raw, str):
        if llm_call is None:
            raise ValueError("自由文本输入需提供 llm_call;无 LLM 时请传结构化 dict")
        parsed = llm_call(_build_prompt(raw))
        boundaries.append("llm_parsed")
    elif isinstance(raw, dict):
        parsed = raw
    else:
        raise TypeError(f"不支持的输入类型:{type(raw)!r}")

    clean, strip_notes = _project(parsed)
    boundaries.extend(strip_notes)

    species = clean.get("species", "") or ""
    if not species:
        boundaries.append("species_unspecified")
    drug_panel = clean.get("drug_panel") or []
    if not drug_panel:
        boundaries.append("empty_drug_panel")

    return MDRGNBMessage(
        task_id=task_id,
        species=species,
        strain_id=clean.get("strain_id"),
        genome_path=clean.get("genome_path"),
        compound=clean.get("compound"),
        smiles=clean.get("smiles"),
        sequence=clean.get("sequence"),
        amr_profile=dict(clean.get("amr_profile") or {}),
        drug_panel=list(drug_panel),
        assay_context=dict(clean.get("assay_context") or {}),
        requested_outputs=list(clean.get("requested_outputs") or _DEFAULT_OUTPUTS),
        evidence=[],
        boundaries=boundaries,
    )


def _build_prompt(text: str) -> str:
    return (
        "你是抗菌药敏查询的**解析器**,只抽取结构化字段,严禁给出任何 SIR/MIC/abstain 结论。\n"
        "输出 JSON,键限:species(拉丁名下划线目录名)、strain_id、genome_path、amr_profile"
        "(基因/突变→bool)、drug_panel([{drug:...}])、assay_context、requested_outputs。\n"
        f"用户查询:{text}"
    )
