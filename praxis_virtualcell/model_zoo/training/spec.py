"""SelfTrainingSpec:自训模型的声明式训练契约。

把 registry.yaml training_card 的五字段(training_data/split/baseline/metrics/provenance)+
训练脚本坐标(training_script)+ 远端环境(remote_env)结构化,fail-closed 校验:
- 五文本字段须非空 str(空契约 → ValueError);
- metrics 须是 dict(可含 null 值——planned 未训诚实标注,但结构须完整);
- to_training_card() 产 registry.yaml training_card 五键 dict(单一真相源:registry 由 spec 派生)。

与 registry._validate 互补:registry 校 yaml 静态字段存在性;spec 校语义 + 提供派生。零 LLM。
"""
from __future__ import annotations

from dataclasses import dataclass, field

_TEXT_FIELDS = ("training_data", "split", "baseline", "provenance")


@dataclass
class SelfTrainingSpec:
    name: str
    training_data: str
    split: str
    baseline: str
    metrics: dict
    provenance: str
    training_script: str
    remote_env: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # fail-closed:文本字段非空(空契约不静默接受)
        for f in ("name",) + _TEXT_FIELDS + ("training_script",):
            v = getattr(self, f)
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"SelfTrainingSpec 字段 {f} 须非空 str(得 {v!r});fail-closed")
        # metrics 须是 dict(可含 null 值,但结构须完整)
        if not isinstance(self.metrics, dict) or not self.metrics:
            raise ValueError(f"SelfTrainingSpec.metrics 须是非空 dict(得 {self.metrics!r});fail-closed")
        if not isinstance(self.remote_env, dict):
            raise ValueError(f"SelfTrainingSpec.remote_env 须是 dict(得 {self.remote_env!r})")

    def to_training_card(self) -> dict:
        """产 registry.yaml training_card 五键 dict(与 registry._validate required_card 一致)。"""
        return {
            "training_data": self.training_data,
            "split": self.split,
            "baseline": self.baseline,
            "metrics": self.metrics,
            "provenance": self.provenance,
        }
