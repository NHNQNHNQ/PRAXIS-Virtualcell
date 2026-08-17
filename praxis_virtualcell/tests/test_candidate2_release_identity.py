"""Candidate-2 P12 identity closure without execution, evidence, or policy."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from praxis_virtualcell.model_zoo.capability_registry import ModelCard
from praxis_virtualcell.model_zoo.registry_v2 import ModelRegistryV2
from scripts import candidate2_release_identity as subject

_MANIFEST = Path(__file__).parents[2] / "data/golden/norman_2019/additive_train_only_candidate2_release.json"


def test_checked_in_candidate2_release_is_closed_path_free_and_reproducible() -> None:
    raw = _MANIFEST.read_bytes()
    value = json.loads(raw)
    card = ModelCard.from_dict(value["model_card"])
    registry = ModelRegistryV2.from_dict(value["registry"])
    receipt = value["receipt"]
    release = registry.releases[0]
    state = registry.state(release.fingerprint())

    assert raw == subject._canonical_bytes(value) + b"\n"
    assert len(registry.artifacts) == len(card.assets) == 4
    assert {artifact.cache_key.rsplit("/", 1)[-1] for artifact in registry.artifacts} == {
        "baseline.json",
        "candidate-record.json",
        "linear_coefficients.npy",
        "linear_intercept.npy",
    }
    assert all(artifact.safe_load_policy == "data_only" for artifact in registry.artifacts)
    assert registry.evidence_records == registry.policy_records == ()
    assert release.evidence_fingerprints == ()
    assert release.policy_fingerprint is None
    assert state.cataloged is state.artifact_ready is True
    assert state.revoked is False and state.superseded_by is None
    assert receipt["model_fingerprint"] == card.fingerprint() == release.model_fingerprint
    assert receipt["release_fingerprint"] == release.fingerprint()
    assert receipt["registry_fingerprint"] == registry.fingerprint()
    assert receipt["research_execution_authorized"] is False
    assert receipt["benchmark_passed"] is None
    assert receipt["scientifically_validated"] is None
    assert receipt["promotion_eligible"] is None
    assert receipt["production_promoted"] is False
    assert receipt["default_route_changed"] is False

    public = registry.public_catalog()["releases"][0]
    assert public["benchmark_passed"] is None
    assert public["scientifically_validated"] is None
    assert public["promotion_eligible"] is None
    assert public["policy_present"] is public["production_promoted"] is False
    assert "research_execution_authorized" not in public
    rendered = raw.decode("utf-8")
    assert all(value not in rendered for value in ("/Users/", "/Volumes/", "file://"))

    exact_root = os.environ.get("PRAXIS_CANDIDATE2_ARTIFACT_ROOT")
    if exact_root is not None:
        assert subject.candidate2_release_identity_bytes(exact_root) == raw


def test_builder_requires_exact_regular_single_link_four_file_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "candidate"
    root.mkdir()
    specs = {}
    for index, (name, (_, _, media_type)) in enumerate(subject._ARTIFACT_SPECS.items()):
        data = f"candidate2-fixture-{index}".encode()
        (root / name).write_bytes(data)
        specs[name] = (len(data), hashlib.sha256(data).hexdigest(), media_type)
    for apple_double in root.glob("._*"):
        apple_double.unlink()
    monkeypatch.setattr(subject, "_ARTIFACT_SPECS", specs)

    built = subject.build_candidate2_release_identity(root)
    assert len(built["registry"]["artifacts"]) == 4
    assert str(tmp_path) not in json.dumps(built, sort_keys=True)
    with pytest.raises(RuntimeError, match="identity-only"):
        subject.Candidate2IdentityOnlyWrapper().run_prediction({})

    unexpected = root / "unexpected"
    unexpected.write_bytes(b"x")
    with pytest.raises(ValueError, match="exactly four files"):
        subject.build_candidate2_release_identity(root)
    unexpected.unlink()
    (root / "._unexpected").unlink(missing_ok=True)

    original = tmp_path / "baseline-original"
    (root / "baseline.json").replace(original)
    (root / "baseline.json").symlink_to(original)
    (root / "._baseline.json").unlink(missing_ok=True)
    with pytest.raises(ValueError, match="artifact is unavailable"):
        subject.build_candidate2_release_identity(root)
