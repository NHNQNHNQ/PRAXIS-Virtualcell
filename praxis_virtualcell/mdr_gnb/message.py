"""MDR-GNB 智能体通讯消息类型(经 core.bus 传递)。字段名与共享契约锁定,不得自创。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MDRGNBMessage:
    """多物种×多药物耐药预测的任务消息。所有 agent 只经 bus 收发此类型。"""

    task_id: str
    species: str
    strain_id: str | None = None
    genome_path: str | None = None
    compound: str | None = None                   # 线B B2:化合物标识符(名称/CID/ChEMBL/DrugBank),经解析器→smiles
    smiles: str | None = None                     # 线B:化合物结构输入(canonical SMILES)
    sequence: str | None = None                   # 线B B5:抗菌肽序列输入(单字母 AA)
    amr_profile: dict = field(default_factory=dict)
    drug_panel: list[dict] = field(default_factory=list)
    assay_context: dict = field(default_factory=dict)
    requested_outputs: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    boundaries: list[str] = field(default_factory=list)
