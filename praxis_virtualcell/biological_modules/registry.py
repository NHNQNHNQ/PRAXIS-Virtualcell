"""Read species module_support.yaml and query support, verdicts, and biological mismatches. Library code is
separate from SpeciesContextAgent bus integration.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.core.config import RuntimeConfig

_SPECIES = ("human", "mouse", "yeast", "bacteria")


_VERDICT = {"strong": "accept", "medium": "accept", "weak": "caution", "unsupported": "reject"}


class ModuleRegistry:
    def __init__(self, brains_root: str | None = None) -> None:
        self.root = Path(brains_root or RuntimeConfig().brains_root)
        self._cache: dict[str, dict] = {}

    def _load(self, species: str) -> dict:
        if species not in self._cache:
            fp = self.root / species / "module_support.yaml"
            self._cache[species] = (yaml.safe_load(fp.read_text(encoding="utf-8"))
                                    if fp.is_file() else {"species": species, "modules": {}})
        return self._cache[species]

    def support(self, species: str, module_id: str) -> dict:
        """Return support metadata; unknown species/modules are unsupported."""
        if module_id not in M.MODULES:
            raise KeyError(f"unknown module: {module_id}")
        rec = (self._load(species).get("modules") or {}).get(module_id)
        if not rec:
            return {"support": "unsupported", "reason": f"{species} has no declared support for this module"}
        return rec

    def default_verdict(self, species: str, module_id: str) -> str:
        return _VERDICT[self.support(species, module_id)["support"]]

    def matrix(self) -> dict[str, dict[str, dict]]:
        """4×8 support matrix:{species: {module_id: support_record}}."""
        return {sp: {mid: self.support(sp, mid) for mid in M.MODULE_ORDER} for sp in _SPECIES}

    def biological_mismatch(self, species: str, query: str) -> str | None:
        """Return a biological-mismatch reject/caution verdict or None when no mismatch applies."""
        for m in (self._load(species).get("biological_mismatch") or []):
            if m.get("query") == query:
                return m.get("verdict")
        return None

    def display_name(self, species: str, module_id: str) -> str:
        return M.display_name(module_id, species=species)
