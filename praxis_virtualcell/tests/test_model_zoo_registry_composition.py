"""Explicit composition of generic model-card registries."""

from __future__ import annotations

import copy

import pytest
import yaml

from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import CapabilityRegistry
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.model_zoo.registry_v2 import ComposedModelRegistryV2
from praxis_virtualcell.tests.test_capability_runtime import _card


def _zoo(tmp_path, filename: str, name: str, *, source: str = "test-only"):
    value = copy.deepcopy(_card())
    value["name"] = name
    value["source"] = source
    path = tmp_path / filename
    path.write_text(
        yaml.safe_dump({"models": {name: value}}, sort_keys=False),
        encoding="utf-8",
    )
    return ModelZooRegistry(registry_path=str(path), enable_v2=True)


def test_model_zoo_explicitly_composes_distinct_base_and_domain(tmp_path) -> None:
    base = _zoo(tmp_path, "base.yaml", "test_only_base_model")
    domain = _zoo(tmp_path, "domain.yaml", "test_only_domain_model")

    composed = ModelZooRegistry.from_components(base, domain)

    assert composed.capability_names() == [
        "test_only_base_model",
        "test_only_domain_model",
    ]
    assert composed.card("test_only_base_model") == base.card("test_only_base_model")
    assert composed.card("test_only_domain_model") == domain.card("test_only_domain_model")
    assert isinstance(composed.registry_v2, ComposedModelRegistryV2)
    assert CapabilityRegistry(composed, ModelCache(root=str(tmp_path / "cache"))).registry_v2 is composed.registry_v2


def test_model_zoo_composition_rejects_conflicting_model_cards(tmp_path) -> None:
    base = _zoo(tmp_path, "base.yaml", "test_only_same_model", source="base-source")
    domain = _zoo(
        tmp_path,
        "domain.yaml",
        "test_only_same_model",
        source="domain-source",
    )

    with pytest.raises(ValueError, match="model card"):
        ModelZooRegistry.from_components(base, domain)
