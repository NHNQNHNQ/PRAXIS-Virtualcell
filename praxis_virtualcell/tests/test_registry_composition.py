"""Generic base/domain Registry v2 composition stays source-preserving."""

from __future__ import annotations

import copy

import pytest

from praxis_virtualcell.model_zoo.capability_registry import ModelCard
from praxis_virtualcell.model_zoo.registry_v2 import (
    ModelRegistryV2,
    ModelReleaseRecord,
    compose_model_registries,
)
from praxis_virtualcell.tests.test_capability_runtime import _card
from praxis_virtualcell.tests.test_model_registry_v2 import complete_registry_payload


def _legacy_registry(name: str, *, source: str = "test-only") -> ModelRegistryV2:
    value = copy.deepcopy(_card())
    value["name"] = name
    value["source"] = source
    return ModelRegistryV2.from_v1_cards((ModelCard.from_dict(value),))


def test_base_and_domain_registry_composition_preserves_source_lifecycle() -> None:
    base = _legacy_registry("test_only_base_model")
    domain = _legacy_registry("test_only_domain_model")
    base_snapshot = (base.to_dict(), base.fingerprint(), base.public_catalog())
    domain_snapshot = (
        domain.to_dict(),
        domain.fingerprint(),
        domain.public_catalog(),
    )

    composed = compose_model_registries(base, domain)

    assert composed.fingerprint() == compose_model_registries(base, domain).fingerprint()
    assert composed.fingerprint() != compose_model_registries(domain, base).fingerprint()
    assert base_snapshot == (base.to_dict(), base.fingerprint(), base.public_catalog())
    assert domain_snapshot == (
        domain.to_dict(),
        domain.fingerprint(),
        domain.public_catalog(),
    )
    assert composed.release(base.releases[0].fingerprint()) == base.releases[0]
    assert composed.release(domain.releases[0].fingerprint()) == domain.releases[0]
    assert composed.state(base.releases[0].fingerprint()) == base.state(
        base.releases[0].fingerprint()
    )
    assert composed.state(domain.releases[0].fingerprint()) == domain.state(
        domain.releases[0].fingerprint()
    )

    public = composed.public_catalog()
    assert public["schema_version"] == "vc.model-registry-catalog.v3"
    assert public["composition"] == {
        "schema_version": "vc.model-registry-composition.v1",
        "base_registry_fingerprint": base.fingerprint(),
        "domain_registry_fingerprint": domain.fingerprint(),
    }
    assert {item["model_name"] for item in public["releases"]} == {
        "test_only_base_model",
        "test_only_domain_model",
    }


def test_registry_composition_rejects_domain_shadowing() -> None:
    base = _legacy_registry("test_only_model", source="base-source")
    domain = _legacy_registry("test_only_model", source="domain-source")

    with pytest.raises(ValueError, match="conflicting"):
        compose_model_registries(base, domain)


def test_registry_composition_rejects_two_lifecycle_authorities() -> None:
    base = _legacy_registry("test_only_base_model")

    with pytest.raises(ValueError, match="lifecycle authorities"):
        compose_model_registries(base, base)


def test_registry_composition_rejects_ambiguous_release_route() -> None:
    base = ModelRegistryV2.from_dict(complete_registry_payload())
    domain_payload = complete_registry_payload()
    replacement = ModelReleaseRecord.from_dict(
        {
            **domain_payload["releases"][0],
            "release_id": "test-model@domain-copy",
        }
    )
    domain_payload["releases"] = [replacement.to_dict()]
    domain_payload["lifecycle_events"][0]["release_fingerprint"] = replacement.fingerprint()
    domain = ModelRegistryV2.from_dict(domain_payload)

    with pytest.raises(ValueError, match="routing"):
        compose_model_registries(base, domain)
