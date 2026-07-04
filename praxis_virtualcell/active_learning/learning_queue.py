"""learning_queue:主动学习的"该测什么"优先队列(纯数据结构,可序列化,零 LLM/bus 依赖)。

advisory 规划产物 —— 建议下一步实验,**不碰 prediction/verdict 终决/provenance ledger/裁决**。
items 按 information_gain 降序(等 gain 保持插入序,可复现);空候选 → 空 items + note(不虚构实验)。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class LearningQueueItem:
    candidate: str                 # 该测什么(如 "genetic_hub@human:AHR")
    module: str                    # 归属模块(MODULE_ORDER 之一)
    information_gain: float        # acquisition.information_gain 打分
    drivers: list[str] = field(default_factory=list)   # 驱动信号(disagreement_high/ood_unknown/evidence_E4/module_weak)
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LearningQueue:
    items: list[LearningQueueItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # 按 information_gain 降序;等 gain 用负号保持稳定插入序(Python sort 稳定)
        self.items = sorted(self.items, key=lambda it: it.information_gain, reverse=True)

    def to_dict(self) -> dict:
        return {"items": [it.to_dict() for it in self.items], "notes": list(self.notes)}
