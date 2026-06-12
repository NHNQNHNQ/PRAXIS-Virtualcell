"""agent 间通讯消息 + predictor 结果 + 可靠性决策(全 @dataclass)。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# status 取值:success | rejected | failed
PredictorStatus = str
# reliability 取值:high | medium | low
ReliabilityLevel = str


@dataclass
class AgentMessage:
    message_id: str
    sender: str
    receiver: str
    message_type: str
    payload: dict[str, Any]
    timestamp: str
    parent_message_id: str | None = None


@dataclass
class PredictorResultMessage:
    agent_name: str
    status: PredictorStatus
    prediction: dict[str, Any] | None
    uncertainty: dict[str, Any] | None
    applicability_score: float
    evidence: list[str]
    rejection_reason: str | None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReliabilityDecision:
    reliability: ReliabilityLevel
    abstain: bool
    reasons: list[str]
    failed_checks: list[str]
    model_disagreement: dict[str, Any] | None = None
