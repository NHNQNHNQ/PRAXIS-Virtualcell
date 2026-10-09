"""Narrow, core-owned selected-content reader for ``vc.pack.v0.4``.

The reader owns the only transition from verified Pack bytes to numerical
values.  It deliberately supports one strict CSV record-vector shape; wider
Pack formats keep their existing fail-closed direct-v2 behavior until they get
their own versioned reader.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError, field_validator, model_validator

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2, _freeze_json
from praxis_virtualcell.data_packs.errors import PackRegistryError
from praxis_virtualcell.data_packs.feature_alignment import (
    AlignmentReport,
    ModelFeatureContract,
)
from praxis_virtualcell.data_packs.manifest import PackManifest
from praxis_virtualcell.data_packs.schema import SchemaObject
from praxis_virtualcell.data_packs.validator import resolve_asset_path

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?(?:0|[1-9][0-9]*))?$")


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


def _exact_text(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or any(char in value for char in ("\r", "\n", '"', ","))
    ):
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    return value


def _finite_decimal(value: Any) -> float:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError("selected-content CSV contains an invalid finite vector")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("selected-content CSV contains an invalid finite vector")
    return parsed


def _record_split_fingerprint(
    *,
    selection_fingerprint: str,
    split_name: str,
    record_split: str,
    split_fingerprint: str,
) -> str:
    return _fingerprint(
        {
            "schema_version": "vc.selected-content-record-split.v1",
            "selection_fingerprint": selection_fingerprint,
            "split_name": split_name,
            "record_split": record_split,
            "split_fingerprint": split_fingerprint,
        }
    )


def _fingerprint_text(value: Any, field: str) -> str:
    value = _exact_text(value, field)
    if _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _shape(value: Any, field: str) -> tuple[int, int]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value)
    ):
        raise ValueError(f"{field} must be a positive two-dimensional shape")
    return tuple(value)


def _tensor_shape(value: Any, field: str) -> tuple[int, ...]:
    if (
        not isinstance(value, (list, tuple))
        or not value
        or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value)
    ):
        raise ValueError(f"{field} must be a positive tensor shape")
    return tuple(value)


def _text_array(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{field} must be a non-empty array")
    values = tuple(_exact_text(item, field) for item in value)
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates")
    return values


class SelectedContentRequestV1(SchemaObject):
    """A value-free adapter request for one request-selected Pack record."""

    schema_version: Literal["vc.selected-content-request.v1"]
    record_id: str
    feature_contract: ModelFeatureContract

    @field_validator("record_id", mode="before")
    @classmethod
    def _record_id(cls, value):
        return _exact_text(value, "record_id")

    @model_validator(mode="after")
    def _exact_feature_contract(self):
        contract = self.feature_contract
        if contract.reorder or contract.drop or contract.fill or contract.mapping_asset is not None:
            raise ValueError("selected-content v0.4 permits exact feature identity only")
        return self

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SelectedContentRequestV1:
        if not isinstance(value, dict):
            raise ValueError("SelectedContentRequestV1 must be a JSON object")
        try:
            return cls.model_validate(value)
        except (TypeError, ValidationError, ValueError) as exc:
            raise ValueError("invalid SelectedContentRequestV1") from exc

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


class SelectedContentReceiptV1(SchemaObject):
    """Public, path- and value-free proof of core materialization."""

    schema_version: Literal["vc.selected-content-receipt.v1"]
    reader_id: str
    reader_version: str
    model_id: str
    model_version: str
    content_contract_fingerprint: str
    request_fingerprint: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    pack_view_receipt_fingerprint: str
    source_asset_id: str
    source_asset_media_type: str
    source_asset_sha256: str
    source_asset_size_bytes: int
    split_name: str
    record_split: str
    split_fingerprint: str
    record_split_fingerprint: str
    selection_fingerprint: str
    selected_values_fingerprint: str
    feature_contract_fingerprint: str
    alignment_fingerprint: str
    observation_count: int
    source_feature_ids: tuple[str, ...]
    source_shape: tuple[int, int]
    target_shape: tuple[int, ...]
    unit: str

    @field_validator(
        "reader_id",
        "reader_version",
        "model_id",
        "model_version",
        "pack_id",
        "pack_version",
        "source_asset_id",
        "source_asset_media_type",
        "split_name",
        "record_split",
        "unit",
        mode="before",
    )
    @classmethod
    def _text(cls, value, info):
        return _exact_text(value, info.field_name)

    @field_validator(
        "content_contract_fingerprint",
        "request_fingerprint",
        "pack_fingerprint",
        "pack_view_receipt_fingerprint",
        "source_asset_sha256",
        "selection_fingerprint",
        "selected_values_fingerprint",
        "feature_contract_fingerprint",
        "alignment_fingerprint",
        "split_fingerprint",
        "record_split_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint_text(value, info.field_name)

    @field_validator("source_asset_size_bytes", "observation_count", mode="before")
    @classmethod
    def _positive_int(cls, value, info):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{info.field_name} must be a positive integer")
        return value

    @field_validator("source_feature_ids", mode="before")
    @classmethod
    def _feature_ids(cls, value):
        return _text_array(value, "source_feature_ids")

    @field_validator("source_shape", mode="before")
    @classmethod
    def _shapes(cls, value, info):
        return _shape(value, info.field_name)

    @field_validator("target_shape", mode="before")
    @classmethod
    def _target_shape(cls, value):
        return _tensor_shape(value, "target_shape")

    @model_validator(mode="after")
    def _consistent(self):
        if (
            self.source_shape[0] != self.observation_count
            or self.source_shape[1] != len(self.source_feature_ids)
            or self.target_shape != (len(self.source_feature_ids),)
            or self.record_split_fingerprint
            != _record_split_fingerprint(
                selection_fingerprint=self.selection_fingerprint,
                split_name=self.split_name,
                record_split=self.record_split,
                split_fingerprint=self.split_fingerprint,
            )
        ):
            raise ValueError("selected-content receipt shape is inconsistent")
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


def selected_content_receipt_from_dict(value: dict[str, Any]) -> SelectedContentReceiptV1:
    """Parse an untrusted public receipt without accepting values or paths."""

    if not isinstance(value, dict):
        raise ValueError("selected-content receipt must be a JSON object")
    try:
        return SelectedContentReceiptV1.model_validate(value)
    except (TypeError, ValidationError, ValueError) as exc:
        raise ValueError("selected-content receipt is invalid") from exc


@dataclass(frozen=True)
class PreparedSelectedContentV1:
    """Core-private selected values given to a registered direct-v2 adapter."""

    receipt: SelectedContentReceiptV1
    values: tuple[float, ...]
    feature_contract: ModelFeatureContract
    alignment_report: AlignmentReport
    model_input: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, SelectedContentReceiptV1):
            raise TypeError("receipt must be SelectedContentReceiptV1")
        if not self.values or any(
            isinstance(value, bool) or not isinstance(value, float) or not math.isfinite(value) for value in self.values
        ):
            raise ValueError("selected content values must be finite floats")
        if not isinstance(self.feature_contract, ModelFeatureContract) or not isinstance(
            self.alignment_report, AlignmentReport
        ):
            raise TypeError("selected content feature alignment is invalid")
        if not (
            self.receipt.feature_contract_fingerprint == self.feature_contract.fingerprint()
            and self.receipt.model_id == self.feature_contract.model_id
            and self.receipt.model_version == self.feature_contract.model_version
            and self.receipt.target_shape == (len(self.values),)
            and self.receipt.record_split_fingerprint
            == _record_split_fingerprint(
                selection_fingerprint=self.receipt.selection_fingerprint,
                split_name=self.receipt.split_name,
                record_split=self.receipt.record_split,
                split_fingerprint=self.receipt.split_fingerprint,
            )
            and self.receipt.selected_values_fingerprint
            == _fingerprint(
                {
                    "schema_version": "vc.selected-content-values.v1",
                    "values": list(self.values),
                }
            )
        ):
            raise ValueError("selected content receipt does not bind its values or feature contract")
        if not isinstance(self.model_input, dict):
            raise TypeError("selected content model input must be a JSON object")
        if not (
            set(self.model_input)
            == {
                "schema_version",
                "request_id",
                "selected_content_receipt_fingerprint",
                "feature_ids",
                "values",
                "shape",
                "unit",
            }
            and self.model_input["schema_version"] == "vc.selected-content-model-input.v1"
            and isinstance(self.model_input["request_id"], str)
            and bool(self.model_input["request_id"])
            and self.model_input["selected_content_receipt_fingerprint"]
            == self.receipt.fingerprint()
            and self.model_input["feature_ids"] == self.feature_contract.feature_ids
            and self.model_input["values"] == self.values
            and self.model_input["shape"] == (len(self.values),)
            and self.model_input["unit"] == self.receipt.unit
        ):
            raise ValueError("selected content model input does not bind its receipt")


def _manifest_asset(manifest: PackManifest):
    selected = manifest.selected_content
    if manifest.schema_version != "vc.pack.v0.4" or selected is None:
        raise PackRegistryError("selected-content reader requires vc.pack.v0.4")
    asset = next((item for item in manifest.assets if item.id == selected.asset), None)
    if asset is None or asset.media_type != "text/csv":
        raise PackRegistryError("selected-content asset is not a declared CSV")
    return selected, asset


def _read_rows(root: Path, manifest: PackManifest):
    selected, asset = _manifest_asset(manifest)
    try:
        raw = resolve_asset_path(root, asset.path).read_bytes()
    except OSError as exc:
        raise PackRegistryError("cannot read selected-content asset") from exc
    if len(raw) != asset.size_bytes or hashlib.sha256(raw).hexdigest() != asset.sha256:
        raise PackRegistryError("selected-content asset drifted during read")
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or b'"' in raw:
        raise PackRegistryError("selected-content CSV must be unquoted UTF-8 LF without BOM")
    try:
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise PackRegistryError("selected-content CSV is not decodable") from exc
    try:
        expected_header = [
            _exact_text(value, "selected-content CSV header")
            for value in (
                selected.record_id_column,
                selected.split_column,
                *selected.value_columns,
            )
        ]
    except ValueError as exc:
        raise PackRegistryError("selected-content CSV header declaration is invalid") from exc
    if not rows or rows[0] != expected_header:
        raise PackRegistryError("selected-content CSV header does not match its declared contract")
    data_rows = rows[1:]
    if len(data_rows) != selected.shape[0]:
        raise PackRegistryError("selected-content CSV row count does not match its declared shape")
    records: dict[str, tuple[str, tuple[float, ...]]] = {}
    for row in data_rows:
        if len(row) != len(expected_header):
            raise PackRegistryError("selected-content CSV row width is invalid")
        try:
            record_id = _exact_text(row[0], "selected-content record id")
            split = _exact_text(row[1], "selected-content split")
        except ValueError as exc:
            raise PackRegistryError("selected-content CSV text field is invalid") from exc
        if split not in manifest.split.values:
            raise PackRegistryError("selected-content CSV has an undeclared split")
        if record_id in records:
            raise PackRegistryError("selected-content CSV has duplicate record ids")
        try:
            values = tuple(_finite_decimal(value) for value in row[2:])
        except ValueError as exc:
            raise PackRegistryError(str(exc)) from exc
        if len(values) != selected.shape[1]:
            raise PackRegistryError("selected-content CSV contains an invalid finite vector")
        records[record_id] = (split, values)
    return selected, asset, records


def validate_selected_content_pack(*, root: Path, manifest: PackManifest) -> None:
    """Validate the v0.4 CSV grammar when a Pack is registered."""

    _read_rows(root, manifest)


def materialize_selected_content(
    *,
    root: Path,
    manifest: PackManifest,
    pack_fingerprint: str,
    pack_view_receipt_fingerprint: str,
    request: VirtualCellRequestV2,
    selection: SelectedContentRequestV1,
) -> PreparedSelectedContentV1:
    """Materialize exactly one request-selected v0.4 Pack vector from bytes."""

    if not isinstance(request, VirtualCellRequestV2) or not isinstance(selection, SelectedContentRequestV1):
        raise TypeError("selected-content materialization requires exact request and selection")
    if request.pack_input is None or request.pack_input.record_id != selection.record_id:
        raise PackRegistryError("selected-content selector does not match the exact request record")
    if manifest.fingerprint() != _fingerprint_text(pack_fingerprint, "pack_fingerprint"):
        raise PackRegistryError("selected-content Pack fingerprint drift")
    selected, asset, records = _read_rows(root, manifest)
    contract = selection.feature_contract
    if not (
        request.species.taxonomy_id == manifest.taxon.ontology_id == contract.taxonomy_id
        and request.input_modality.name == manifest.modality.name == contract.modality
        and request.input_modality.ontology_id == manifest.modality.ontology_id
        and request.input_modality.feature_namespace == manifest.feature_namespace.name
        and request.input_modality.unit == selected.unit
        and contract.assembly_accession == manifest.assembly.accession
        and contract.feature_namespace == manifest.feature_namespace
        and contract.feature_id_format == manifest.feature_semantics.id_format
        and contract.feature_ids == selected.value_columns
    ):
        raise PackRegistryError("selected-content request, Pack, or feature contract drift")
    try:
        record_split, values = records[selection.record_id]
    except KeyError as exc:
        raise PackRegistryError("selected-content record is not registered in the Pack") from exc
    alignment = AlignmentReport(
        schema_version="vc.alignment-report.v1",
        contract_fingerprint=contract.fingerprint(),
        source_feature_ids=selected.value_columns,
        target_feature_ids=contract.feature_ids,
        source_shape=(1, len(values)),
        target_shape=(len(values),),
        steps=(),
        mapping_asset=None,
    )
    split_fingerprint = _fingerprint(manifest.split.model_dump(mode="json"))
    selection_fingerprint = selection.fingerprint()
    receipt = SelectedContentReceiptV1(
        schema_version="vc.selected-content-receipt.v1",
        reader_id="vc.pack-selected-csv-reader",
        reader_version="1",
        model_id=contract.model_id,
        model_version=contract.model_version,
        content_contract_fingerprint=_fingerprint(selected.model_dump(mode="json")),
        request_fingerprint=_fingerprint(request.to_dict()),
        pack_id=manifest.pack_id,
        pack_version=manifest.pack_version,
        pack_fingerprint=_fingerprint_text(pack_fingerprint, "pack_fingerprint"),
        pack_view_receipt_fingerprint=_fingerprint_text(pack_view_receipt_fingerprint, "pack_view_receipt_fingerprint"),
        source_asset_id=asset.id,
        source_asset_media_type=asset.media_type,
        source_asset_sha256=asset.sha256,
        source_asset_size_bytes=asset.size_bytes,
        split_name=manifest.split.name or "",
        record_split=record_split,
        split_fingerprint=split_fingerprint,
        record_split_fingerprint=_record_split_fingerprint(
            selection_fingerprint=selection_fingerprint,
            split_name=manifest.split.name or "",
            record_split=record_split,
            split_fingerprint=split_fingerprint,
        ),
        selection_fingerprint=selection_fingerprint,
        selected_values_fingerprint=_fingerprint(
            {"schema_version": "vc.selected-content-values.v1", "values": list(values)}
        ),
        feature_contract_fingerprint=contract.fingerprint(),
        alignment_fingerprint=_fingerprint(alignment.to_dict()),
        observation_count=1,
        source_feature_ids=selected.value_columns,
        source_shape=(1, len(values)),
        target_shape=(len(values),),
        unit=selected.unit,
    )
    model_input = _freeze_json(
        {
            "schema_version": "vc.selected-content-model-input.v1",
            "request_id": request.request_id,
            "selected_content_receipt_fingerprint": receipt.fingerprint(),
            "feature_ids": list(contract.feature_ids),
            "values": list(values),
            "shape": [len(values)],
            "unit": selected.unit,
        }
    )
    return PreparedSelectedContentV1(
        receipt=receipt,
        values=values,
        feature_contract=contract,
        alignment_report=alignment,
        model_input=model_input,
    )
