"""model zoo 注册表:读 model_zoo/registry.yaml,提供 schema 校验 + name/module/species 查询 + status。
照抄 biological_modules/registry.py 的 yaml+白名单校验模式。纯库(不进 message bus;broker 在 Task 2.6)。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.biological_modules import modules as M

LEGAL_TYPES = ("public_model", "self_trained")
LEGAL_STATUS = ("available", "planned", "missing")

_REQUIRED_FIELDS = ("name", "type", "species", "module", "task", "source",
                    "license", "status", "wrapper", "version")

_DEFAULT_REGISTRY = Path(__file__).parent / "registry.yaml"


class ModelZooRegistry:
    def __init__(self, registry_path: str | None = None) -> None:
        self.path = Path(registry_path or _DEFAULT_REGISTRY)
        self._models: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        models = doc.get("models") or {}
        for name, entry in models.items():
            self._validate(name, entry)
            self._models[name] = entry

    @staticmethod
    def _validate(name: str, entry: dict) -> None:
        """schema 校验(fail-closed:任何非法字段 → ValueError,不静默接受坏条目)。"""
        for f in _REQUIRED_FIELDS:
            if f not in entry:
                raise ValueError(f"model_zoo 条目 {name} 缺必填字段: {f}")
        if entry["name"] != name:
            raise ValueError(f"model_zoo 条目 key({name})与 name({entry['name']})不一致")
        if entry["type"] not in LEGAL_TYPES:
            raise ValueError(f"{name} 非法 type: {entry['type']}(合法: {LEGAL_TYPES})")
        if entry["status"] not in LEGAL_STATUS:
            raise ValueError(f"{name} 非法 status: {entry['status']}(合法: {LEGAL_STATUS})")
        if entry["module"] not in M.MODULE_ORDER:
            raise ValueError(f"{name} module 越白名单: {entry['module']}(须 ∈ MODULE_ORDER)")
        if not isinstance(entry["species"], list) or not entry["species"]:
            raise ValueError(f"{name} species 必须是非空 list")
        if not isinstance(entry.get("requires", []), list):
            raise ValueError(f"{name} requires 必须是 list")

    # ---- 查询 ----
    def names(self) -> list[str]:
        return list(self._models)

    def get(self, name: str) -> dict:
        if name not in self._models:
            raise KeyError(f"未知模型: {name}(已注册: {sorted(self._models)})")
        return self._models[name]

    def status(self, name: str) -> str:
        return self.get(name)["status"]

    def is_available(self, name: str) -> bool:
        return self.get(name)["status"] == "available"

    def by_module(self, module_id: str) -> list[dict]:
        if module_id not in M.MODULES:
            raise KeyError(f"未知模块: {module_id}")
        return [e for e in self._models.values() if e["module"] == module_id]

    def by_species(self, species: str) -> list[dict]:
        return [e for e in self._models.values() if species in e["species"]]
