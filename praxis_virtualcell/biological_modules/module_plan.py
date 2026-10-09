"""Serializable ModulePlan contract, independent of bus/LLM/torch/cobra. Validate modules and engines against
allowlists at construction. Compose entry verdicts conservatively from routing, species support, and mismatches;
overall_verdict is the most conservative entry verdict.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from praxis_virtualcell.agents.route_table import ENGINES
from praxis_virtualcell.biological_modules import modules as M

_SEVERITY = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3, "reject": 3}
_LEGAL_ROLES = ("primary", "secondary")


def synthesize_verdict(route_disposition: str, species_verdict: str,
                       mismatch: str | None) -> str:
    """Select the most conservative routing, species, and mismatch verdict; fail closed."""
    candidates = [route_disposition, species_verdict]
    if mismatch:
        candidates.append(mismatch)
    return max(candidates, key=lambda v: _SEVERITY.get(v, 3))


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
    verdict: str | None = None

    def __post_init__(self) -> None:
        if self.module not in M.MODULE_ORDER:
            raise ValueError(f"module outside allowlist: {self.module}(must be in MODULE_ORDER)")
        if self.engine not in ENGINES:
            raise ValueError(f"engine outside allowlist: {self.engine}(must be in route_table.ENGINES)")
        if self.role not in _LEGAL_ROLES:
            raise ValueError(f"invalid role: {self.role}(must be in {_LEGAL_ROLES})")
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
            raise ValueError(f"primary outside allowlist: {self.primary}")
        entry_modules = {e.module for e in self.entries}
        if self.primary not in entry_modules:
            raise ValueError(f"primary={self.primary} must appear in entries")
        for s in self.secondary:
            if s not in M.MODULE_ORDER:
                raise ValueError(f"secondary outside allowlist: {s}")

    @property
    def overall_verdict(self) -> str:
        """Return the most conservative entry verdict; an empty entry list abstains."""
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
