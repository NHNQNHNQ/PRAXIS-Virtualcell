"""ModulePlan:module-aware 路由的产物 + Phase 4 LLM 编排的输入契约。

纯数据结构(不进 bus、无 LLM/torch/cobra 依赖),可序列化。构造即校验(module ∈ MODULE_ORDER、
engine ∈ ENGINES),fail-closed。verdict 保守合成:route_disposition 与 species_verdict 取更保守,
mismatch 命中再降级。overall_verdict = 所有 entry verdict 取最保守。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from praxis_virtualcell.agents.route_table import ENGINES
from praxis_virtualcell.biological_modules import modules as M

# 保守优先级:数字越大越保守。abstain 与 reject 同为"不出结论",并列最保守。
_SEVERITY = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3, "reject": 3}
_LEGAL_ROLES = ("primary", "secondary")


def synthesize_verdict(route_disposition: str, species_verdict: str,
                       mismatch: str | None) -> str:
    """取 route_disposition / species_verdict / mismatch 三者中最保守。fail-closed。"""
    candidates = [route_disposition, species_verdict]
    if mismatch:
        candidates.append(mismatch)
    return max(candidates, key=lambda v: _SEVERITY.get(v, 3))   # 未知 → 当最保守


@dataclass
class ModulePlanEntry:
    module: str
    display_name: str
    role: str
    engine: str
    route_disposition: str
    species_support: str
    species_verdict: str
    caution_flags: list[str] = field(default_factory=list)
    data_gated: bool = False
    pillars: list[str] = field(default_factory=list)
    available_models: list[str] = field(default_factory=list)
    reason: str = ""
    mismatch: str | None = None
    verdict: str | None = None   # None → __post_init__ 合成;显式传入则尊重(测试可覆写)

    def __post_init__(self) -> None:
        if self.module not in M.MODULE_ORDER:
            raise ValueError(f"module 越白名单: {self.module}(须 ∈ MODULE_ORDER)")
        if self.engine not in ENGINES:
            raise ValueError(f"engine 越白名单: {self.engine}(须 ∈ route_table.ENGINES)")
        if self.role not in _LEGAL_ROLES:
            raise ValueError(f"非法 role: {self.role}(须 ∈ {_LEGAL_ROLES})")
        if self.verdict is None:
            self.verdict = synthesize_verdict(
                self.route_disposition, self.species_verdict, self.mismatch)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModulePlan:
    species: str
    request: dict
    primary: str
    secondary: list[str]
    entries: list[ModulePlanEntry]
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.primary not in M.MODULE_ORDER:
            raise ValueError(f"primary 越白名单: {self.primary}")
        entry_modules = {e.module for e in self.entries}
        if self.primary not in entry_modules:
            raise ValueError(f"primary={self.primary} 必须在 entries 中")
        for s in self.secondary:
            if s not in M.MODULE_ORDER:
                raise ValueError(f"secondary 越白名单: {s}")

    @property
    def overall_verdict(self) -> str:
        """所有 entry verdict 取最保守;无 entry → abstain。"""
        if not self.entries:
            return "abstain"
        return max((e.verdict for e in self.entries),
                   key=lambda v: _SEVERITY.get(v, 3))

    def to_dict(self) -> dict:
        return {
            "species": self.species,
            "request": self.request,
            "primary": self.primary,
            "secondary": list(self.secondary),
            "overall_verdict": self.overall_verdict,
            "entries": [e.to_dict() for e in self.entries],
            "notes": list(self.notes),
        }
