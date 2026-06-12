"""虚拟细胞结构化请求。第一阶段真支持 human/scRNA/gene/predict_delta_expression;
其余字段(drug/mutation/bacteria/yeast/mouse/...)schema 预留,本周不实现逻辑。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from praxis_virtualcell.core.exceptions import InputValidationError

_REQUIRED = (
    "request_id", "species", "perturbation_type", "perturbation_targets",
    "input_modality", "output_modality", "task_type",
)


@dataclass
class VirtualCellRequest:
    request_id: str
    species: str
    perturbation_type: str
    perturbation_targets: list[str]
    input_modality: str
    output_modality: str
    task_type: str
    cell_type: str | None = None
    tissue: str | None = None
    perturbation_dose: float | None = None
    perturbation_time: str | None = None
    baseline_context: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VirtualCellRequest":
        for k in _REQUIRED:
            if d.get(k) in (None, ""):
                raise InputValidationError(f"VirtualCellRequest 缺必填字段: {k}")
        if not isinstance(d["perturbation_targets"], list):
            raise InputValidationError("perturbation_targets 必须是 list[str]")
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})
