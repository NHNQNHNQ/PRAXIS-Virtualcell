"""模块注册表:读 brains/virtualcell/<species>/module_support.yaml,提供支持度/裁决/错配查询。
纯库(不进 message bus;SpeciesContextAgent 的 bus 接线在 Phase 3)。"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.core.config import RuntimeConfig

_SPECIES = ("human", "mouse", "yeast", "bacteria")

# support 等级 → 默认裁决(与 route_table 四态对齐)
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
        """返回 {support, reason?, models?, tools?, ...}。未知物种/模块 → unsupported。"""
        if module_id not in M.MODULES:
            raise KeyError(f"未知模块: {module_id}")
        rec = (self._load(species).get("modules") or {}).get(module_id)
        if not rec:
            return {"support": "unsupported", "reason": f"{species} 未声明该模块支持度"}
        return rec

    def default_verdict(self, species: str, module_id: str) -> str:
        return _VERDICT[self.support(species, module_id)["support"]]

    def matrix(self) -> dict[str, dict[str, dict]]:
        """4×8 support matrix:{species: {module_id: support_record}}。"""
        return {sp: {mid: self.support(sp, mid) for mid in M.MODULE_ORDER} for sp in _SPECIES}

    def biological_mismatch(self, species: str, query: str) -> str | None:
        """生物学错配查询 → verdict(reject/caution)或 None(无错配)。"""
        for m in (self._load(species).get("biological_mismatch") or []):
            if m.get("query") == query:
                return m.get("verdict")
        return None

    def display_name(self, species: str, module_id: str) -> str:
        return M.display_name(module_id, species=species)
