"""Read and validate model_zoo registry YAML, then query name/module/species/status. Pure library code; message-bus
governance is handled by the broker.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import yaml
from yaml.constructor import ConstructorError

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.model_zoo.capability_registry import ModelCard
from praxis_virtualcell.model_zoo.registry_v2 import (
    ComposedModelRegistryV2,
    ModelRegistryV2,
    compose_model_registries,
)

LEGAL_TYPES = ("public_model", "self_trained")
LEGAL_STATUS = ("available", "planned", "missing")

_REQUIRED_FIELDS = ("name", "type", "species", "module", "task", "source", "license", "status", "wrapper", "version")

_DEFAULT_REGISTRY = Path(__file__).parent / "registry.yaml"


class _UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"unhashable mapping key: {key!r}",
                    key_node.start_mark,
                ) from exc
            if key in mapping:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key: {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


class ModelZooRegistry:
    def __init__(
        self,
        registry_path: str | None = None,
        *,
        enable_v2: bool | None = None,
        registry_v2: ModelRegistryV2 | ComposedModelRegistryV2 | None = None,
    ) -> None:
        self.path = Path(registry_path or _DEFAULT_REGISTRY)
        self._models: dict[str, dict] = {}
        self._cards: dict[str, ModelCard] = {}
        self._enable_v2 = registry_path is None if enable_v2 is None else enable_v2
        self._provided_registry_v2 = registry_v2
        self._registry_v2: ModelRegistryV2 | ComposedModelRegistryV2 | None = None
        self._load()

    def _load(self) -> None:
        try:
            doc = (
                yaml.load(
                    self.path.read_text(encoding="utf-8"),
                    Loader=_UniqueKeyLoader,
                )
                or {}
            )
        except OSError:
            raise ValueError("model_zoo registry is unavailable") from None
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid model_zoo YAML: {exc}") from exc
        if not isinstance(doc, dict) or set(doc) not in (
            {"models"},
            {"models", "registry_v2"},
        ):
            raise ValueError("model_zoo root must contain models and optional registry_v2")
        models = doc.get("models") or {}
        if not isinstance(models, dict):
            raise ValueError("model_zoo models must be an object")
        for name, entry in models.items():
            if not isinstance(entry, dict):
                raise ValueError(f"model_zoo entry {name} must be an object")
            if "schema_version" in entry:
                card = ModelCard.from_dict(entry)
                if card.name != name:
                    raise ValueError(f"model_zoo entry key({name}) differs from name({card.name})")
                self._cards[name] = card
                self._models[name] = card.to_dict()
            else:
                self._validate(name, entry)
                self._models[name] = entry
        embedded = doc.get("registry_v2")
        if embedded is not None and self._provided_registry_v2 is not None:
            raise ValueError("model_zoo registry_v2 cannot be both embedded and injected")
        if embedded is not None:
            self._registry_v2 = ModelRegistryV2.from_dict(embedded)
        elif self._provided_registry_v2 is not None:
            if not isinstance(
                self._provided_registry_v2,
                (ModelRegistryV2, ComposedModelRegistryV2),
            ):
                raise TypeError("registry_v2 must be ModelRegistryV2 or ComposedModelRegistryV2")
            self._registry_v2 = self._provided_registry_v2
        elif self._enable_v2:
            self._registry_v2 = ModelRegistryV2.from_v1_cards(self._cards.values())
        if self._registry_v2 is not None:
            self._validate_v2_bindings(self._registry_v2)

    def _validate_v2_bindings(
        self,
        registry: ModelRegistryV2 | ComposedModelRegistryV2,
    ) -> None:
        for release in registry.releases:
            try:
                card = self._cards[release.model_name]
            except KeyError as exc:
                raise ValueError("registry_v2 release has no matching model card") from exc
            if release.model_version != card.version or release.model_fingerprint != card.fingerprint():
                raise ValueError("registry_v2 release is bound to a different model card")

    @staticmethod
    def _validate(name: str, entry: dict) -> None:
        """Validate schema and raise ValueError on invalid fields instead of accepting malformed entries."""
        for f in _REQUIRED_FIELDS:
            if f not in entry:
                raise ValueError(f"model_zoo entry {name} missing required fields: {f}")
        if entry["name"] != name:
            raise ValueError(f"model_zoo entry key({name}) differs from name({entry['name']})")
        if entry["type"] not in LEGAL_TYPES:
            raise ValueError(f"{name} invalid type: {entry['type']}(allowed: {LEGAL_TYPES})")
        if entry["status"] not in LEGAL_STATUS:
            raise ValueError(f"{name} invalid status: {entry['status']}(allowed: {LEGAL_STATUS})")
        if entry["module"] not in M.MODULE_ORDER:
            raise ValueError(f"{name} module outside allowlist: {entry['module']}(must be in MODULE_ORDER)")
        if not isinstance(entry["species"], list) or not entry["species"]:
            raise ValueError(f"{name} species must be a nonempty list")
        if not isinstance(entry.get("requires", []), list):
            raise ValueError(f"{name} requires must be a list")

        if entry["type"] == "self_trained":
            card = entry.get("training_card")
            required_card = ("training_data", "split", "baseline", "metrics", "provenance")
            if not isinstance(card, dict):
                raise ValueError(f"{name} is self_trained but lacks the required training_card")
            missing = [k for k in required_card if k not in card]
            if missing:
                raise ValueError(f"{name} training_card missing fields: {missing}")

            if not isinstance(card["metrics"], dict):
                raise ValueError(
                    f"{name} training_card.metrics must be a dict (received {type(card['metrics']).__name__})"
                )
            for k in ("training_data", "split", "baseline", "provenance"):
                v = card[k]
                if not isinstance(v, str) or not v.strip():
                    raise ValueError(f"{name} training_card.{k} must be a nonempty str (received {v!r});fail-closed")

        assets = entry.get("assets")
        if assets is not None:
            if not isinstance(assets, list):
                raise ValueError(f"{name} assets must be a list")
            for a in assets:
                if not isinstance(a, dict) or "filename" not in a or "sha256" not in a:
                    raise ValueError(f"{name} asset entries must contain filename and sha256 keys: {a}")

    def names(self) -> list[str]:
        return list(self._models)

    def capability_names(self) -> list[str]:
        return sorted(self._cards)

    @property
    def registry_v2(self) -> ModelRegistryV2 | ComposedModelRegistryV2 | None:
        return self._registry_v2

    @classmethod
    def from_components(
        cls,
        base: ModelZooRegistry,
        domain: ModelZooRegistry,
    ) -> ModelZooRegistry:
        """Compose two already-validated registries without path discovery.

        The caller assigns the roles explicitly.  Name collisions are never
        resolved by precedence: identical entries may be shared, anything else
        is rejected before the v2 lifecycle view is composed.
        """
        if not isinstance(base, cls) or not isinstance(domain, cls):
            raise TypeError("base and domain must be ModelZooRegistry")
        if not isinstance(base.registry_v2, ModelRegistryV2) or not isinstance(
            domain.registry_v2,
            ModelRegistryV2,
        ):
            raise ValueError("base and domain require independent ModelRegistryV2 sources")

        models = deepcopy(base._models)
        cards = dict(base._cards)
        for name, entry in domain._models.items():
            if name not in models:
                models[name] = deepcopy(entry)
                if name in domain._cards:
                    cards[name] = domain._cards[name]
                continue

            base_card = base._cards.get(name)
            domain_card = domain._cards.get(name)
            if base_card is not None and domain_card is not None:
                if base_card.fingerprint() != domain_card.fingerprint():
                    raise ValueError("composed registry has conflicting model card")
                continue
            if base_card is not None or domain_card is not None:
                raise ValueError("composed registry cannot mix model card and legacy entry")
            if json.dumps(
                models[name],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ) != json.dumps(
                entry,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ):
                raise ValueError("composed registry has conflicting legacy model entry")

        composed = cls.__new__(cls)
        composed.path = None
        composed._models = models
        composed._cards = cards
        composed._enable_v2 = True
        composed._provided_registry_v2 = None
        composed._registry_v2 = compose_model_registries(
            base.registry_v2,
            domain.registry_v2,
        )
        composed._validate_v2_bindings(composed._registry_v2)
        return composed

    def card(self, name: str) -> ModelCard:
        if name not in self._models:
            raise KeyError(f"unknown model: {name}(registered: {sorted(self._models)})")
        if name not in self._cards:
            raise ValueError(f"legacy model entry has no vc.model-card.v1 contract: {name}")
        return self._cards[name]

    def get(self, name: str) -> dict:
        if name not in self._models:
            raise KeyError(f"unknown model: {name}(registered: {sorted(self._models)})")
        return deepcopy(self._models[name])

    def status(self, name: str) -> str:
        return self.get(name)["status"]

    def is_available(self, name: str) -> bool:
        return self.get(name)["status"] == "available"

    def by_module(self, module_id: str) -> list[dict]:
        if module_id not in M.MODULES:
            raise KeyError(f"unknown module: {module_id}")
        return [deepcopy(entry) for entry in self._models.values() if entry["module"] == module_id]

    def by_species(self, species: str) -> list[dict]:
        return [deepcopy(entry) for entry in self._models.values() if species in entry["species"]]
