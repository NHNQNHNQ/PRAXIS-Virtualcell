"""API 请求 schema(pydantic v2)。字段与 run_mdr_query 的 raw 一一对应。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class DrugEntry(BaseModel):
    drug: str
    drug_class: str = ""

    @field_validator("drug")
    @classmethod
    def require_nonempty_drug(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("drug_required")
        return value


class PredictRequest(BaseModel):
    species: str
    drug_panel: list[DrugEntry] = Field(default_factory=list, validate_default=True)
    requested_outputs: list[str] = Field(default_factory=lambda: ["SIR"])
    amr_profile: dict[str, Any] = Field(default_factory=dict)
    # 线B 三方向共用一个请求体(仅按 requested_outputs 分派):
    # compound=化合物标识符(名称/CID/ChEMBL/DrugBank,后端解析→SMILES);
    # smiles=化合物结构(canonical SMILES,不联网);sequence=抗菌肽序列。
    compound: str | None = None
    smiles: str | None = None
    sequence: str | None = None

    @field_validator("drug_panel")
    @classmethod
    def require_exactly_one_drug(cls, value: list[DrugEntry]) -> list[DrugEntry]:
        if len(value) != 1:
            raise ValueError("exactly_one_drug_required")
        return value

    def to_raw(self) -> dict[str, Any]:
        """还原成 run_mdr_query 吃的 raw dict(确定性:字段顺序不影响 canonical hash)。

        线B 字段(compound/smiles/sequence)仅在非空时进 raw:纯 SIR 请求的 raw 保持 4 键
        原样 → task_id 不漂移、既有缓存/回放不失效。"""
        raw: dict[str, Any] = {
            "species": self.species,
            "drug_panel": [{"drug": d.drug, "drug_class": d.drug_class}
                           for d in self.drug_panel],
            "requested_outputs": list(self.requested_outputs),
            "amr_profile": dict(self.amr_profile),
        }
        if self.compound:
            raw["compound"] = self.compound
        if self.smiles:
            raw["smiles"] = self.smiles
        if self.sequence:
            raw["sequence"] = self.sequence
        return raw
