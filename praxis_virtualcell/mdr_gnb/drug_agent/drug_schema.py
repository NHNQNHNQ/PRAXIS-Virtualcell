"""药物请求/结果 schema(pydantic v2,字段名锁定)。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class DrugTestRequest(BaseModel):
    """单次药敏预测请求。"""

    species: str
    strain_id: str | None = None
    amr_profile: dict = Field(default_factory=dict)
    drugs: list[str] = Field(default_factory=list)
    assay_context: dict = Field(default_factory=dict)
    requested_outputs: list[str] = Field(
        default_factory=lambda: ["MIC_range", "SIR", "mechanism", "confidence", "experiment_priority"]
    )


class DrugTestResult(BaseModel):
    """单药预测结果(含弃权分支)。"""

    drug: str
    mic_range: str | None = None
    sir: str | None = None
    sir_prob: dict | None = None
    confidence: str = "low"  # high | medium | low
    mechanism: str | None = None
    abstained: bool = False
    abstain_reason: str | None = None
    next_experiment: str | None = None
    evidence: list[dict] = Field(default_factory=list)
    breakpoint_source: str = ""
