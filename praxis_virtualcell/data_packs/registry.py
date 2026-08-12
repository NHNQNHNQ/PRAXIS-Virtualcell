"""In-memory registry for explicitly validated local Packs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from praxis_virtualcell.data_packs.anndata_adapter import load_anndata_view
from praxis_virtualcell.data_packs.errors import PackRegistryError
from praxis_virtualcell.data_packs.manifest import PackManifest
from praxis_virtualcell.data_packs.mudata_adapter import load_mudata_view
from praxis_virtualcell.data_packs.selected_content import (
    PreparedSelectedContentV1,
    SelectedContentReceiptV1,
    SelectedContentRequestV1,
)
from praxis_virtualcell.data_packs.selected_content import (
    materialize_selected_content as _materialize_selected_content,
)
from praxis_virtualcell.data_packs.validator import validate_pack

PackKey = tuple[str, str]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _fingerprint(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class RegisteredPack:
    """A Pack identity that can only be issued after full registry validation."""

    manifest: PackManifest
    root: Path
    fingerprint: str


@dataclass(frozen=True)
class PackViewAssetV1:
    """Path-free identity for one declared Pack asset."""

    asset_id: str
    media_type: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, str) and value and value.strip() == value
            for value in (self.asset_id, self.media_type, self.sha256)
        ):
            raise ValueError("Pack view asset text fields must be exact non-empty strings")
        if _SHA256.fullmatch(self.sha256) is None:
            raise ValueError("Pack view asset sha256 must be lowercase SHA-256")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ValueError("Pack view asset size must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "media_type": self.media_type,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class PackViewReceiptV1:
    """Public receipt for the path-free Pack identity passed to one adapter."""

    schema_version: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    taxonomy_id: str
    assembly_accession: str
    assets: tuple[PackViewAssetV1, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "vc.prepared-pack-view-receipt.v1":
            raise ValueError("unsupported Pack view receipt schema")
        if not all(
            isinstance(value, str) and value and value.strip() == value
            for value in (
                self.pack_id,
                self.pack_version,
                self.pack_fingerprint,
                self.taxonomy_id,
                self.assembly_accession,
            )
        ):
            raise ValueError("Pack view receipt text fields must be exact non-empty strings")
        if _SHA256.fullmatch(self.pack_fingerprint) is None:
            raise ValueError("Pack view receipt fingerprint must be lowercase SHA-256")
        if not self.assets or any(type(asset) is not PackViewAssetV1 for asset in self.assets):
            raise ValueError("Pack view receipt requires exact declared asset identities")
        if len({asset.asset_id for asset in self.assets}) != len(self.assets):
            raise ValueError("Pack view receipt asset ids must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "pack_fingerprint": self.pack_fingerprint,
            "taxonomy_id": self.taxonomy_id,
            "assembly_accession": self.assembly_accession,
            "assets": [asset.to_dict() for asset in self.assets],
        }

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True)
class PackViewReceiptV2:
    """Write-new v0.4 input receipt with its exact selected-content contract."""

    schema_version: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    taxonomy_id: str
    assembly_accession: str
    assets: tuple[PackViewAssetV1, ...]
    split_name: str
    split_values: tuple[str, ...]
    split_fingerprint: str
    selected_content_asset_id: str
    selected_content_contract_fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != "vc.prepared-pack-view-receipt.v2":
            raise ValueError("unsupported Pack view receipt schema")
        if not all(
            isinstance(value, str) and value and value.strip() == value
            for value in (
                self.pack_id,
                self.pack_version,
                self.pack_fingerprint,
                self.taxonomy_id,
                self.assembly_accession,
                self.split_name,
                self.split_fingerprint,
                self.selected_content_asset_id,
                self.selected_content_contract_fingerprint,
            )
        ):
            raise ValueError("Pack view receipt text fields must be exact non-empty strings")
        if any(
            _SHA256.fullmatch(value) is None
            for value in (
                self.pack_fingerprint,
                self.split_fingerprint,
                self.selected_content_contract_fingerprint,
            )
        ):
            raise ValueError("Pack view receipt fingerprint must be lowercase SHA-256")
        if not self.assets or any(type(asset) is not PackViewAssetV1 for asset in self.assets):
            raise ValueError("Pack view receipt requires exact declared asset identities")
        if len({asset.asset_id for asset in self.assets}) != len(self.assets):
            raise ValueError("Pack view receipt asset ids must be unique")
        if (
            not self.split_values
            or any(
                not isinstance(value, str) or not value or value.strip() != value
                for value in self.split_values
            )
            or len(set(self.split_values)) != len(self.split_values)
            or self.selected_content_asset_id
            not in {asset.asset_id for asset in self.assets}
        ):
            raise ValueError("Pack view v2 selected-content identity is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "pack_fingerprint": self.pack_fingerprint,
            "taxonomy_id": self.taxonomy_id,
            "assembly_accession": self.assembly_accession,
            "assets": [asset.to_dict() for asset in self.assets],
            "split_name": self.split_name,
            "split_values": list(self.split_values),
            "split_fingerprint": self.split_fingerprint,
            "selected_content_asset_id": self.selected_content_asset_id,
            "selected_content_contract_fingerprint": self.selected_content_contract_fingerprint,
        }

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


PackViewReceipt = PackViewReceiptV1 | PackViewReceiptV2


def _pack_view_assets(value: dict[str, Any]) -> tuple[PackViewAssetV1, ...]:
    if not isinstance(value.get("assets"), list):
        raise ValueError("Pack view receipt has an invalid public shape")
    assets = []
    for asset in value["assets"]:
        if not isinstance(asset, dict) or set(asset) != {
            "asset_id",
            "media_type",
            "sha256",
            "size_bytes",
        }:
            raise ValueError("Pack view receipt asset has an invalid public shape")
        assets.append(
            PackViewAssetV1(
                asset_id=asset["asset_id"],
                media_type=asset["media_type"],
                sha256=asset["sha256"],
                size_bytes=asset["size_bytes"],
            )
        )
    return tuple(assets)


def pack_view_receipt_from_dict(value: dict[str, Any]) -> PackViewReceipt:
    """Parse a public Pack-view receipt without accepting a filesystem path."""

    common = {
        "schema_version",
        "pack_id",
        "pack_version",
        "pack_fingerprint",
        "taxonomy_id",
        "assembly_accession",
        "assets",
    }
    if not isinstance(value, dict):
        raise ValueError("Pack view receipt has an invalid public shape")
    if value.get("schema_version") == "vc.prepared-pack-view-receipt.v1":
        if set(value) != common:
            raise ValueError("Pack view receipt has an invalid public shape")
        return PackViewReceiptV1(
            schema_version=value["schema_version"],
            pack_id=value["pack_id"],
            pack_version=value["pack_version"],
            pack_fingerprint=value["pack_fingerprint"],
            taxonomy_id=value["taxonomy_id"],
            assembly_accession=value["assembly_accession"],
            assets=_pack_view_assets(value),
        )
    v2 = common | {
        "split_name",
        "split_values",
        "split_fingerprint",
        "selected_content_asset_id",
        "selected_content_contract_fingerprint",
    }
    if (
        value.get("schema_version") != "vc.prepared-pack-view-receipt.v2"
        or set(value) != v2
        or not isinstance(value.get("split_values"), list)
    ):
        raise ValueError("Pack view receipt has an invalid public shape")
    return PackViewReceiptV2(
        schema_version=value["schema_version"],
        pack_id=value["pack_id"],
        pack_version=value["pack_version"],
        pack_fingerprint=value["pack_fingerprint"],
        taxonomy_id=value["taxonomy_id"],
        assembly_accession=value["assembly_accession"],
        assets=_pack_view_assets(value),
        split_name=value["split_name"],
        split_values=tuple(value["split_values"]),
        split_fingerprint=value["split_fingerprint"],
        selected_content_asset_id=value["selected_content_asset_id"],
        selected_content_contract_fingerprint=value["selected_content_contract_fingerprint"],
    )


def validate_selected_content_receipt_binding(
    receipt: SelectedContentReceiptV1,
    pack_view_receipt: PackViewReceipt,
) -> bool:
    """Verify that a selected-content receipt names one exact Pack-view asset."""

    if type(receipt) is not SelectedContentReceiptV1 or type(pack_view_receipt) is not PackViewReceiptV2:
        return False
    if not (
        receipt.pack_id == pack_view_receipt.pack_id
        and receipt.pack_version == pack_view_receipt.pack_version
        and receipt.pack_fingerprint == pack_view_receipt.pack_fingerprint
        and receipt.pack_view_receipt_fingerprint == pack_view_receipt.fingerprint()
    ):
        return False
    source = next(
        (
            asset
            for asset in pack_view_receipt.assets
            if asset.asset_id == pack_view_receipt.selected_content_asset_id
        ),
        None,
    )
    return (
        source is not None
        and receipt.source_asset_id == pack_view_receipt.selected_content_asset_id
        and receipt.content_contract_fingerprint
        == pack_view_receipt.selected_content_contract_fingerprint
        and receipt.split_name == pack_view_receipt.split_name
        and receipt.record_split in pack_view_receipt.split_values
        and receipt.split_fingerprint == pack_view_receipt.split_fingerprint
        and (
        source.media_type,
        source.sha256,
        source.size_bytes,
        )
        == (
            receipt.source_asset_media_type,
            receipt.source_asset_sha256,
            receipt.source_asset_size_bytes,
        )
    )


@dataclass(frozen=True)
class PreparedPackViewV1:
    """Broker-issued Pack metadata with no filesystem path or raw content.

    The view deliberately exposes only registered identity metadata.  A
    data-required adapter must wait for a separately versioned core content
    materializer; it must never receive a local Pack root or arbitrary bytes.
    """

    schema_version: str
    pack_id: str
    pack_version: str
    fingerprint: str
    taxonomy_id: str
    assembly_accession: str
    assets: tuple[PackViewAssetV1, ...]
    receipt: PackViewReceiptV1

    def __post_init__(self) -> None:
        if self.schema_version != "vc.prepared-pack-view.v1":
            raise ValueError("unsupported prepared Pack view schema")
        expected = PackViewReceiptV1(
            schema_version="vc.prepared-pack-view-receipt.v1",
            pack_id=self.pack_id,
            pack_version=self.pack_version,
            pack_fingerprint=self.fingerprint,
            taxonomy_id=self.taxonomy_id,
            assembly_accession=self.assembly_accession,
            assets=self.assets,
        )
        if type(self.receipt) is not PackViewReceiptV1 or self.receipt.to_dict() != expected.to_dict():
            raise ValueError("prepared Pack view receipt does not bind its identity")

    @property
    def asset_ids(self) -> tuple[str, ...]:
        return tuple(asset.asset_id for asset in self.assets)

    def asset(self, asset_id: str) -> PackViewAssetV1:
        if not isinstance(asset_id, str):
            raise KeyError(asset_id)
        for item in self.assets:
            if item.asset_id == asset_id:
                return item
        raise KeyError(asset_id)


@dataclass(frozen=True)
class PreparedPackViewV2:
    """Write-new path-free v0.4 view with selected-input provenance."""

    schema_version: str
    pack_id: str
    pack_version: str
    fingerprint: str
    taxonomy_id: str
    assembly_accession: str
    assets: tuple[PackViewAssetV1, ...]
    split_name: str
    split_values: tuple[str, ...]
    split_fingerprint: str
    selected_content_asset_id: str
    selected_content_contract_fingerprint: str
    receipt: PackViewReceiptV2

    def __post_init__(self) -> None:
        if self.schema_version != "vc.prepared-pack-view.v2":
            raise ValueError("unsupported prepared Pack view schema")
        expected = PackViewReceiptV2(
            schema_version="vc.prepared-pack-view-receipt.v2",
            pack_id=self.pack_id,
            pack_version=self.pack_version,
            pack_fingerprint=self.fingerprint,
            taxonomy_id=self.taxonomy_id,
            assembly_accession=self.assembly_accession,
            assets=self.assets,
            split_name=self.split_name,
            split_values=self.split_values,
            split_fingerprint=self.split_fingerprint,
            selected_content_asset_id=self.selected_content_asset_id,
            selected_content_contract_fingerprint=self.selected_content_contract_fingerprint,
        )
        if type(self.receipt) is not PackViewReceiptV2 or self.receipt.to_dict() != expected.to_dict():
            raise ValueError("prepared Pack view receipt does not bind its identity")

    @property
    def asset_ids(self) -> tuple[str, ...]:
        return tuple(asset.asset_id for asset in self.assets)

    def asset(self, asset_id: str) -> PackViewAssetV1:
        if not isinstance(asset_id, str):
            raise KeyError(asset_id)
        for item in self.assets:
            if item.asset_id == asset_id:
                return item
        raise KeyError(asset_id)


PreparedPackView = PreparedPackViewV1 | PreparedPackViewV2


class PackRegistry:
    def __init__(self) -> None:
        self._packs: dict[PackKey, PackManifest] = {}
        self._roots: dict[PackKey, Path] = {}

    def register(self, pack_root: str | Path) -> PackManifest:
        root = Path(pack_root).resolve()
        manifest = self._validated_manifest(root)
        key = (manifest.pack_id, manifest.pack_version)
        current = self._packs.get(key)
        if current is not None:
            if current.fingerprint() != manifest.fingerprint():
                raise PackRegistryError(f"conflicting Pack identity: {key}")
            return current
        self._packs[key] = manifest
        self._roots[key] = root
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

    def record(self, pack_id: str, pack_version: str) -> RegisteredPack:
        key = (pack_id, pack_version)
        manifest = self.get(pack_id, pack_version)
        return RegisteredPack(
            manifest=manifest,
            root=self._roots[key],
            fingerprint=manifest.fingerprint(),
        )

    @staticmethod
    def _validated_manifest(root: Path) -> PackManifest:
        manifest = validate_pack(root)
        if manifest.schema_version == "vc.pack.v0.2":
            with load_anndata_view(root) as view:
                manifest = view.manifest
        elif manifest.schema_version == "vc.pack.v0.3":
            with load_mudata_view(root) as view:
                manifest = view.manifest
        return manifest

    def revalidate(self, pack: RegisteredPack) -> bool:
        """Recheck a registered Pack's current bytes before direct execution.

        This returns a boolean rather than exposing validation exceptions to a
        model adapter. Callers must treat any false result as a hard gate and
        never pass the Pack on for input preparation.
        """

        if not isinstance(pack, RegisteredPack):
            return False
        key = (pack.manifest.pack_id, pack.manifest.pack_version)
        registered_manifest = self._packs.get(key)
        registered_root = self._roots.get(key)
        if (
            registered_manifest is None
            or registered_root != pack.root
            or registered_manifest.fingerprint() != pack.fingerprint
            or pack.manifest.fingerprint() != pack.fingerprint
        ):
            return False
        try:
            current = self._validated_manifest(pack.root)
        except Exception:  # noqa: BLE001 - Pack byte/path failures are a hard gate
            return False
        return (
            current.pack_id == pack.manifest.pack_id
            and current.pack_version == pack.manifest.pack_version
            and current.fingerprint() == pack.fingerprint
        )

    def issue_execution_view(self, pack: RegisteredPack) -> PreparedPackView:
        """Issue the only Pack object that direct-v2 may pass to an adapter.

        The registry keeps the root private.  The returned view captures only
        already validated Pack identity and declared asset receipts; it does
        not expose raw asset bytes or a path that an adapter could reopen.
        """

        if type(pack) is not RegisteredPack or not self.revalidate(pack):
            raise PackRegistryError("cannot issue a view for a drifted or unregistered Pack")
        manifest = pack.manifest
        assets = tuple(
            PackViewAssetV1(
                asset_id=asset.id,
                media_type=asset.media_type,
                sha256=asset.sha256,
                size_bytes=asset.size_bytes,
            )
            for asset in manifest.assets
        )
        if manifest.schema_version == "vc.pack.v0.4":
            selected = manifest.selected_content
            if selected is None or manifest.split.name is None:
                raise PackRegistryError("v0.4 Pack selected-content identity is unavailable")
            split_fingerprint = _fingerprint(manifest.split.model_dump(mode="json"))
            content_contract_fingerprint = _fingerprint(selected.model_dump(mode="json"))
            receipt_v2 = PackViewReceiptV2(
                schema_version="vc.prepared-pack-view-receipt.v2",
                pack_id=manifest.pack_id,
                pack_version=manifest.pack_version,
                pack_fingerprint=pack.fingerprint,
                taxonomy_id=manifest.taxon.ontology_id,
                assembly_accession=manifest.assembly.accession,
                assets=assets,
                split_name=manifest.split.name,
                split_values=manifest.split.values,
                split_fingerprint=split_fingerprint,
                selected_content_asset_id=selected.asset,
                selected_content_contract_fingerprint=content_contract_fingerprint,
            )
            return PreparedPackViewV2(
                schema_version="vc.prepared-pack-view.v2",
                pack_id=manifest.pack_id,
                pack_version=manifest.pack_version,
                fingerprint=pack.fingerprint,
                taxonomy_id=manifest.taxon.ontology_id,
                assembly_accession=manifest.assembly.accession,
                assets=assets,
                split_name=manifest.split.name,
                split_values=manifest.split.values,
                split_fingerprint=split_fingerprint,
                selected_content_asset_id=selected.asset,
                selected_content_contract_fingerprint=content_contract_fingerprint,
                receipt=receipt_v2,
            )
        receipt = PackViewReceiptV1(
            schema_version="vc.prepared-pack-view-receipt.v1",
            pack_id=manifest.pack_id,
            pack_version=manifest.pack_version,
            pack_fingerprint=pack.fingerprint,
            taxonomy_id=manifest.taxon.ontology_id,
            assembly_accession=manifest.assembly.accession,
            assets=assets,
        )
        return PreparedPackViewV1(
            schema_version="vc.prepared-pack-view.v1",
            pack_id=manifest.pack_id,
            pack_version=manifest.pack_version,
            fingerprint=pack.fingerprint,
            taxonomy_id=manifest.taxon.ontology_id,
            assembly_accession=manifest.assembly.accession,
            assets=assets,
            receipt=receipt,
        )

    def materialize_selected_content(
        self,
        pack: RegisteredPack,
        *,
        request,
        selection: SelectedContentRequestV1,
        pack_view: PreparedPackViewV2,
    ) -> PreparedSelectedContentV1:
        """Read one selected v0.4 vector after revalidating its exact Pack."""

        if (
            type(pack) is not RegisteredPack
            or type(pack_view) is not PreparedPackViewV2
            or not isinstance(selection, SelectedContentRequestV1)
            or not self.revalidate(pack)
            or pack_view.fingerprint != pack.fingerprint
            or pack_view.receipt.pack_fingerprint != pack.fingerprint
        ):
            raise PackRegistryError("selected-content Pack identity is invalid or drifted")
        content = _materialize_selected_content(
            root=pack.root,
            manifest=pack.manifest,
            pack_fingerprint=pack.fingerprint,
            pack_view_receipt_fingerprint=pack_view.receipt.fingerprint(),
            request=request,
            selection=selection,
        )
        if not (
            validate_selected_content_receipt_binding(content.receipt, pack_view.receipt)
            and content.receipt.split_name == pack.manifest.split.name
            and content.receipt.record_split in pack.manifest.split.values
            and content.receipt.split_fingerprint
            == _fingerprint(pack.manifest.split.model_dump(mode="json"))
        ):
            raise PackRegistryError("selected-content receipt does not bind the Pack view")
        return content

    def verify_selected_content(
        self,
        pack: RegisteredPack,
        *,
        request,
        selection: SelectedContentRequestV1,
        pack_view: PreparedPackViewV2,
        content: PreparedSelectedContentV1,
    ) -> bool:
        """Re-read Pack bytes after adapter preparation; drift never executes."""

        if not isinstance(content, PreparedSelectedContentV1):
            return False
        try:
            fresh = self.materialize_selected_content(
                pack,
                request=request,
                selection=selection,
                pack_view=pack_view,
            )
        except (PackRegistryError, TypeError, ValueError):
            return False
        return (
            fresh.receipt.to_dict() == content.receipt.to_dict()
            and fresh.values == content.values
            and fresh.feature_contract == content.feature_contract
            and fresh.alignment_report.to_dict() == content.alignment_report.to_dict()
            and fresh.model_input == content.model_input
        )
