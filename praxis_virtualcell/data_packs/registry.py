"""In-memory registry for explicitly validated local Packs."""

from __future__ import annotations

from pathlib import Path

from praxis_virtualcell.data_packs.anndata_adapter import load_anndata_view
from praxis_virtualcell.data_packs.errors import PackRegistryError
from praxis_virtualcell.data_packs.manifest import PackManifest
from praxis_virtualcell.data_packs.mudata_adapter import load_mudata_view
from praxis_virtualcell.data_packs.validator import validate_pack

PackKey = tuple[str, str]


class PackRegistry:
    def __init__(self) -> None:
        self._packs: dict[PackKey, PackManifest] = {}

    def register(self, pack_root: str | Path) -> PackManifest:
        manifest = validate_pack(pack_root)
        if manifest.schema_version == "vc.pack.v0.2":
            with load_anndata_view(pack_root) as view:
                manifest = view.manifest
        elif manifest.schema_version == "vc.pack.v0.3":
            with load_mudata_view(pack_root) as view:
                manifest = view.manifest
        key = (manifest.pack_id, manifest.pack_version)
        current = self._packs.get(key)
        if current is not None:
            if current.fingerprint() != manifest.fingerprint():
                raise PackRegistryError(f"conflicting Pack identity: {key}")
            return current
        self._packs[key] = manifest
        return manifest

    def get(self, pack_id: str, pack_version: str) -> PackManifest:
        key = (pack_id, pack_version)
        try:
            return self._packs[key]
        except KeyError as exc:
            raise PackRegistryError(f"unregistered Pack: {key}") from exc

    def keys(self) -> list[PackKey]:
        return sorted(self._packs)

    def fingerprint(self, pack_id: str, pack_version: str) -> str:
        return self.get(pack_id, pack_version).fingerprint()
