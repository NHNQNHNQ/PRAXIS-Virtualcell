"""P2 contracts for VirtualCellPack v0.1 manifests and validation."""

from __future__ import annotations

import ast
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.data_packs.errors import (
    PackAssetHashMismatch,
    PackAssetMissing,
    PackManifestError,
    PackPathError,
    PackRegistryError,
)
from praxis_virtualcell.data_packs.manifest import PackManifest, load_manifest
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.data_packs.validator import validate_pack

_FIXTURES = Path(__file__).parent / "fixtures" / "data_packs"
_VALID = _FIXTURES / "valid_tiny"
_FINGERPRINT = "5973dc852f8d7d0cb73ce333d3f99beb2f94c66b7cdf4e6d2e7fc4c422651192"


def _raw_valid() -> dict:
    return yaml.safe_load((_VALID / "manifest.yaml").read_text(encoding="utf-8"))


def test_valid_tiny_pack_covers_contract_and_has_stable_fingerprint():
    manifest = validate_pack(_VALID)
    encoded = json.loads(json.dumps(manifest.to_dict(), allow_nan=False))

    assert set(encoded) == {
        "schema_version",
        "pack_id",
        "pack_version",
        "taxon",
        "assembly",
        "identity",
        "modality",
        "feature_namespace",
        "assets",
        "condition",
        "split",
        "provenance",
        "license",
    }
    assert manifest.schema_version == "vc.pack.v0.1"
    assert manifest.taxon.ontology_id == "NCBITaxon:9606"
    assert manifest.assets[0].sha256 == (
        "cc84599566d64cb451305dbe4b38b33720f4d7add9354bc0841972f2678ac302"
    )
    assert manifest.fingerprint() == _FINGERPRINT
    assert PackManifest.from_dict(encoded) == manifest
    assert load_manifest(_VALID / "manifest.yaml") == manifest


def test_fingerprint_ignores_mapping_order_but_preserves_list_order():
    raw = _raw_valid()
    reordered = dict(reversed(list(raw.items())))
    reversed_split = deepcopy(raw)
    reversed_split["split"]["values"].reverse()

    assert PackManifest.from_dict(reordered).fingerprint() == _FINGERPRINT
    assert PackManifest.from_dict(reversed_split).fingerprint() != _FINGERPRINT


@pytest.mark.parametrize(
    "fixture,field",
    [
        ("missing_taxon", "taxon"),
        ("missing_license", "license"),
        ("missing_hash", "sha256"),
        ("unknown_schema_version", "schema_version"),
    ],
)
def test_invalid_manifest_fixtures_fail_closed(fixture, field):
    with pytest.raises(PackManifestError, match=field):
        load_manifest(_FIXTURES / fixture / "manifest.yaml")


@pytest.mark.parametrize("fixture", ["absolute_path", "path_traversal", "escaping_symlink"])
def test_unsafe_asset_path_fixtures_fail_closed(fixture):
    with pytest.raises(PackPathError):
        validate_pack(_FIXTURES / fixture)


def test_escaping_symlink_fixture_is_a_real_external_link():
    link = _FIXTURES / "escaping_symlink" / "asset.txt"

    assert link.is_symlink()
    assert link.resolve() == (_FIXTURES / "outside_asset.txt").resolve()


def test_asset_hash_mismatch_fails_closed(tmp_path):
    pack = tmp_path / "pack"
    shutil.copytree(_VALID, pack)
    asset = pack / "assets" / "counts.csv"
    asset.write_text(asset.read_text(encoding="utf-8").replace("cell-1", "cell-X"), encoding="utf-8")

    with pytest.raises(PackAssetHashMismatch):
        validate_pack(pack)


def test_missing_asset_fails_closed(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    shutil.copy2(_VALID / "manifest.yaml", pack / "manifest.yaml")

    with pytest.raises(PackAssetMissing):
        validate_pack(pack)


def test_unknown_fields_and_duplicate_scientific_ids_are_rejected():
    unknown = {**_raw_valid(), "future_guess": True}
    duplicate = _raw_valid()
    duplicate["assets"].append(dict(duplicate["assets"][0]))

    with pytest.raises(PackManifestError):
        PackManifest.from_dict(unknown)
    with pytest.raises(PackManifestError, match="asset ids"):
        PackManifest.from_dict(duplicate)


def test_duplicate_yaml_keys_fail_closed(tmp_path):
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        (_VALID / "manifest.yaml").read_text(encoding="utf-8")
        + "\npack_id: silently-shadowed\n",
        encoding="utf-8",
    )

    with pytest.raises(PackManifestError, match="duplicate"):
        load_manifest(manifest_path)


def test_unhashable_yaml_mapping_key_uses_pack_error_boundary(tmp_path):
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text("? [a, b]\n: value\n", encoding="utf-8")

    with pytest.raises(PackManifestError, match="unhashable"):
        load_manifest(manifest_path)


def test_manifest_symlink_must_not_escape_pack_root(tmp_path):
    pack = tmp_path / "pack"
    shutil.copytree(_VALID, pack)
    outside = tmp_path / "outside-manifest.yaml"
    (pack / "manifest.yaml").replace(outside)
    (pack / "manifest.yaml").symlink_to(outside)

    with pytest.raises(PackManifestError, match="manifest.*root"):
        validate_pack(pack)


def test_windows_absolute_asset_path_fails_closed():
    raw = _raw_valid()
    raw["assets"][0]["path"] = "C:/data/counts.csv"
    manifest = PackManifest.from_dict(raw)

    with pytest.raises(PackPathError):
        from praxis_virtualcell.data_packs.validator import resolve_asset_path

        resolve_asset_path(_VALID.resolve(), manifest.assets[0].path)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda raw: raw["split"].update(strategy="random"),
        lambda raw: raw["condition"].update(values=["control", "control"]),
        lambda raw: raw["split"].update(values=["train", "train"]),
    ],
)
def test_manifest_never_randomizes_or_deduplicates_declared_groups(mutation):
    raw = _raw_valid()
    mutation(raw)

    with pytest.raises(PackManifestError):
        PackManifest.from_dict(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", None),
        ("leakage_guard", []),
    ],
)
def test_v01_rejects_v02_split_fields_even_when_empty(field, value):
    raw = _raw_valid()
    raw["split"][field] = value

    with pytest.raises(PackManifestError, match="vc.pack.v0.2 semantic fields"):
        PackManifest.from_dict(raw)


def test_registry_only_registers_validated_packs_and_is_idempotent():
    registry = PackRegistry()

    first = registry.register(_VALID)
    second = registry.register(_VALID)

    assert second is first
    assert registry.keys() == [("tiny-human-scrna", "0.1.0")]
    assert registry.get("tiny-human-scrna", "0.1.0") is first
    assert registry.fingerprint("tiny-human-scrna", "0.1.0") == _FINGERPRINT
    with pytest.raises(PackRegistryError):
        registry.get("missing", "0.1.0")


def test_base_pack_modules_do_not_read_h5ad_or_connect_runtime():
    package = Path(__file__).parents[1] / "data_packs"
    imports: set[str] = set()
    calls: set[str] = set()
    sources = (
        path
        for path in package.glob("*.py")
        if not path.name.startswith("._") and path.name != "anndata_adapter.py"
    )
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports |= {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports |= {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        calls |= {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }

    assert not any(
        name.startswith(("anndata", "scanpy", "h5py"))
        or name.startswith("praxis_virtualcell.core.runtime")
        or name.startswith("praxis_virtualcell.model_zoo")
        for name in imports
    )
    assert "read_h5ad" not in calls
    assert not list(_FIXTURES.rglob("*.h5ad"))
