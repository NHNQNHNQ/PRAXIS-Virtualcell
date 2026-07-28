"""Strict public-data catalog and quarantined upload storage."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import uuid
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from yaml.constructor import ConstructorError

from praxis_virtualcell.workflows.run_virtualcell_query import SUPPORTED_SPECIES

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TAXON = re.compile(r"^NCBITaxon:[0-9]+$")
_ACCEPTED_EXTENSIONS = (
    ".csv",
    ".csv.gz",
    ".h5ad",
    ".h5mu",
    ".mtx",
    ".mtx.gz",
    ".tar.gz",
    ".tsv",
    ".tsv.gz",
    ".zip",
)
_DEFAULT_MAX_FILE_BYTES = 5 * 1024**3
_DEFAULT_TOTAL_QUOTA_BYTES = 20 * 1024**3
_MULTIPART_OVERHEAD_BYTES = 1024**2
_CHUNK_BYTES = 1024 * 1024


class DataPortalError(Exception):
    """Base class for stable API error mapping."""


class DataPortalConfigError(DataPortalError):
    pass


class UnsupportedSpecies(DataPortalError):
    pass


class DatasetNotFound(DataPortalError):
    pass


class DatasetFileNotFound(DataPortalError):
    pass


class DatasetFileUnavailable(DataPortalError):
    pass


class DatasetIntegrityError(DataPortalError):
    pass


class UploadRejected(DataPortalError):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


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


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


def _nonempty(value: str) -> str:
    if not value.strip():
        raise ValueError("must be a non-empty string")
    return value


def _https(value: str) -> str:
    value = _nonempty(value)
    if not value.startswith("https://"):
        raise ValueError("URL must use https")
    return value


def _safe_relative_path(value: str) -> str:
    relative = PurePosixPath(value)
    if (
        "\\" in value
        or relative.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or not relative.parts
        or any(part in (".", "..") for part in relative.parts)
        or str(relative) != value
    ):
        raise ValueError("path must be a canonical safe POSIX relative path")
    return value


class CatalogSpecies(_StrictModel):
    runtime_id: Literal["human", "mouse", "yeast", "bacteria"]
    taxon_id: str
    scientific_name: str

    @field_validator("taxon_id")
    @classmethod
    def _valid_taxon(cls, value: str) -> str:
        if not _TAXON.fullmatch(value):
            raise ValueError("taxon_id must use NCBITaxon:<digits>")
        return value

    @field_validator("scientific_name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        return _nonempty(value)


class CatalogSource(_StrictModel):
    landing_page: str
    citation: str

    @field_validator("landing_page")
    @classmethod
    def _valid_landing_page(cls, value: str) -> str:
        return _https(value)

    @field_validator("citation")
    @classmethod
    def _valid_citation(cls, value: str) -> str:
        return _nonempty(value)


class CatalogTerms(_StrictModel):
    id: str
    name: str
    url: str

    @field_validator("id", "name")
    @classmethod
    def _valid_text(cls, value: str) -> str:
        return _nonempty(value)

    @field_validator("url")
    @classmethod
    def _valid_url(cls, value: str) -> str:
        return _https(value)


class CatalogFile(_StrictModel):
    id: str
    filename: str
    path: str
    media_type: str
    size_bytes: int = Field(gt=0)
    sha256: str
    source_url: str

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError("file id must be lower-kebab-case")
        return value

    @field_validator("filename")
    @classmethod
    def _valid_filename(cls, value: str) -> str:
        if not _safe_upload_filename(value):
            raise ValueError("filename is unsafe")
        return value

    @field_validator("path")
    @classmethod
    def _valid_path(cls, value: str) -> str:
        return _safe_relative_path(value)

    @field_validator("media_type")
    @classmethod
    def _valid_media_type(cls, value: str) -> str:
        return _nonempty(value)

    @field_validator("sha256")
    @classmethod
    def _valid_hash(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return value

    @field_validator("source_url")
    @classmethod
    def _valid_source_url(cls, value: str) -> str:
        return _https(value)


class CatalogDataset(_StrictModel):
    id: str
    version: str
    title: str
    species: CatalogSpecies
    modality: str
    value_semantics: str
    observations: int = Field(gt=0)
    features: int = Field(gt=0)
    source: CatalogSource
    terms: CatalogTerms
    usage_status: Literal["download_only"]
    scientifically_validated: Literal[False]
    files: list[CatalogFile]

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError("dataset id must be lower-kebab-case")
        return value

    @field_validator("version", "title", "modality", "value_semantics")
    @classmethod
    def _valid_text(cls, value: str) -> str:
        return _nonempty(value)

    @field_validator("files")
    @classmethod
    def _files_required(cls, value: list[CatalogFile]) -> list[CatalogFile]:
        if not value:
            raise ValueError("dataset files must not be empty")
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("dataset file ids must be unique")
        return value

    @model_validator(mode="after")
    def _supported_species(self):
        if self.species.runtime_id not in SUPPORTED_SPECIES:
            raise ValueError("dataset species is not supported by the runtime")
        return self


class DataCatalog(_StrictModel):
    schema_version: Literal["vc.data-catalog.v1"]
    datasets: list[CatalogDataset]

    @field_validator("datasets")
    @classmethod
    def _valid_datasets(
        cls, value: list[CatalogDataset]
    ) -> list[CatalogDataset]:
        if not value:
            raise ValueError("catalog datasets must not be empty")
        ids = [item.id for item in value]
        paths = [file.path for item in value for file in item.files]
        if len(ids) != len(set(ids)):
            raise ValueError("catalog dataset ids must be unique")
        if len(paths) != len(set(paths)):
            raise ValueError("catalog file paths must be unique")
        return value


def _catalog_path() -> Path:
    configured = os.environ.get("PRAXIS_VC_DATA_CATALOG")
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            raise DataPortalConfigError("catalog path must be absolute")
        return path
    return Path(str(files("praxis_virtualcell.catalogs").joinpath("data_catalog.yaml")))


def load_catalog() -> DataCatalog:
    try:
        path = _catalog_path()
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
        return DataCatalog.model_validate(document)
    except (
        OSError,
        UnicodeError,
        ValidationError,
        ConstructorError,
        yaml.YAMLError,
        TypeError,
        ValueError,
    ) as exc:
        raise DataPortalConfigError("data catalog is invalid") from exc


def _positive_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    if not raw.isascii() or not raw.isdecimal():
        raise DataPortalConfigError(f"{name} must be a positive integer")
    value = int(raw)
    if value <= 0:
        raise DataPortalConfigError(f"{name} must be a positive integer")
    return value


def _data_root() -> Path:
    raw = os.environ.get("PRAXIS_VC_DATA_ROOT")
    if not raw:
        raise DataPortalConfigError("PRAXIS_VC_DATA_ROOT is not configured")
    path = Path(raw)
    if not path.is_absolute():
        raise DataPortalConfigError("PRAXIS_VC_DATA_ROOT must be absolute")
    return path.resolve()


def upload_capability() -> dict:
    try:
        root = _data_root()
        token = os.environ.get("PRAXIS_VC_UPLOAD_TOKEN", "")
        max_bytes = _positive_env(
            "PRAXIS_VC_UPLOAD_MAX_BYTES", _DEFAULT_MAX_FILE_BYTES
        )
        total_bytes = _positive_env(
            "PRAXIS_VC_UPLOAD_TOTAL_BYTES", _DEFAULT_TOTAL_QUOTA_BYTES
        )
        enabled = len(token) >= 32 and total_bytes >= max_bytes and root.is_absolute()
    except DataPortalConfigError:
        max_bytes = _DEFAULT_MAX_FILE_BYTES
        total_bytes = _DEFAULT_TOTAL_QUOTA_BYTES
        enabled = False
    return {
        "enabled": enabled,
        "quarantine_only": True,
        "max_file_bytes": max_bytes,
        "total_quota_bytes": total_bytes,
        "accepted_extensions": list(_ACCEPTED_EXTENSIONS),
    }


def authorize_upload(authorization: str | None) -> None:
    capability = upload_capability()
    token = os.environ.get("PRAXIS_VC_UPLOAD_TOKEN", "")
    if not capability["enabled"]:
        raise UploadRejected("uploads_disabled", 503)
    supplied = authorization or ""
    expected = f"Bearer {token}"
    if not secrets.compare_digest(supplied, expected):
        raise UploadRejected("upload_unauthorized", 401)


def upload_body_limit() -> int:
    return upload_capability()["max_file_bytes"] + _MULTIPART_OVERHEAD_BYTES


def validate_upload_content_length(content_length: str | None) -> None:
    """Reject ordinary multipart oversize bodies before Starlette spools them."""
    if content_length is None:
        return
    if not content_length.isascii() or not content_length.isdecimal():
        raise UploadRejected("invalid_content_length")
    if int(content_length) > upload_body_limit():
        raise UploadRejected("upload_too_large", 413)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _public_file(file: CatalogFile, *, verify: bool) -> Path | None:
    try:
        public_root = (_data_root() / "public").resolve(strict=True)
        candidate = public_root.joinpath(*PurePosixPath(file.path).parts)
        resolved = candidate.resolve(strict=True)
    except (DataPortalConfigError, FileNotFoundError, NotADirectoryError):
        return None
    if not resolved.is_relative_to(public_root):
        if verify:
            raise DatasetIntegrityError("dataset file escapes public root")
        return None
    try:
        file_stat = resolved.stat()
    except OSError:
        return None
    try:
        integrity_matches = (
            stat.S_ISREG(file_stat.st_mode)
            and file_stat.st_size == file.size_bytes
            and _hash_file(resolved) == file.sha256
        )
    except OSError as exc:
        if verify:
            raise DatasetIntegrityError("dataset file cannot be verified") from exc
        return None
    if not integrity_matches:
        if verify:
            raise DatasetIntegrityError("dataset file integrity mismatch")
        return None
    return resolved


def _dataset_payload(dataset: CatalogDataset) -> dict:
    payload = dataset.model_dump(exclude={"files"})
    payload["files"] = [
        {
            "id": file.id,
            "filename": file.filename,
            "media_type": file.media_type,
            "size_bytes": file.size_bytes,
            "sha256": file.sha256,
            "source_url": file.source_url,
            "available": _public_file(file, verify=False) is not None,
            "download_url": (
                f"/api/data-catalog/{dataset.id}/files/{file.id}/download"
            ),
        }
        for file in dataset.files
    ]
    return payload


def catalog_payload(species: str | None = None) -> dict:
    catalog = load_catalog()
    seen: set[str] = set()
    species_options = []
    for dataset in catalog.datasets:
        runtime_id = dataset.species.runtime_id
        if runtime_id not in seen:
            seen.add(runtime_id)
            species_options.append(
                {
                    "id": runtime_id,
                    "taxon_id": dataset.species.taxon_id,
                    "scientific_name": dataset.species.scientific_name,
                }
            )
    if species is not None and species not in seen:
        raise UnsupportedSpecies(species)
    selected = [
        dataset
        for dataset in catalog.datasets
        if species is None or dataset.species.runtime_id == species
    ]
    return {
        "schema_version": catalog.schema_version,
        "species": species_options,
        "datasets": [_dataset_payload(dataset) for dataset in selected],
        "upload": upload_capability(),
    }


def resolve_download(dataset_id: str, file_id: str) -> tuple[Path, CatalogFile]:
    catalog = load_catalog()
    dataset = next(
        (item for item in catalog.datasets if item.id == dataset_id),
        None,
    )
    if dataset is None:
        raise DatasetNotFound(dataset_id)
    file = next((item for item in dataset.files if item.id == file_id), None)
    if file is None:
        raise DatasetFileNotFound(file_id)
    path = _public_file(file, verify=True)
    if path is None:
        raise DatasetFileUnavailable(file_id)
    return path, file


def _safe_upload_filename(filename: str) -> bool:
    if (
        not filename
        or len(filename) > 200
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
        or any(ord(char) < 32 or ord(char) == 127 for char in filename)
    ):
        return False
    try:
        filename.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _extension(filename: str) -> str | None:
    return next(
        (extension for extension in _ACCEPTED_EXTENSIONS if filename.endswith(extension)),
        None,
    )


def _quarantine_usage(quarantine: Path) -> int:
    total = 0
    if not quarantine.is_dir():
        return total
    for path in quarantine.glob("*/payload"):
        try:
            file_stat = path.lstat()
        except OSError:
            continue
        if stat.S_ISREG(file_stat.st_mode):
            total += file_stat.st_size
    return total


def _upload_directory(path: Path, parent: Path) -> Path:
    if path.is_symlink():
        raise DataPortalConfigError("upload directory must not be a symlink")
    try:
        path.mkdir(parents=False, exist_ok=True, mode=0o700)
        file_stat = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise DataPortalConfigError("upload directory is unavailable") from exc
    if not stat.S_ISDIR(file_stat.st_mode) or resolved.parent != parent:
        raise DataPortalConfigError("upload directory escapes data root")
    return resolved


def _upload_paths() -> tuple[Path, Path, Path]:
    root = _data_root()
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root = root.resolve(strict=True)
    except OSError as exc:
        raise DataPortalConfigError("data root is unavailable") from exc
    uploads = _upload_directory(root / "uploads", root)
    quarantine = _upload_directory(uploads / "quarantine", uploads)
    lock_path = uploads / ".upload.lock"
    if lock_path.is_symlink():
        raise DataPortalConfigError("upload lock must not be a symlink")
    return uploads, quarantine, lock_path


def store_upload(
    *,
    filename: str,
    species: str,
    content_type: str | None,
    stream: BinaryIO,
) -> dict:
    catalog = load_catalog()
    supported = {dataset.species.runtime_id for dataset in catalog.datasets}
    if species not in supported:
        raise UploadRejected("unsupported_species")
    if not _safe_upload_filename(filename):
        raise UploadRejected("unsafe_upload_filename")
    if _extension(filename) is None:
        raise UploadRejected("unsupported_upload_type")

    capability = upload_capability()
    if not capability["enabled"]:
        raise UploadRejected("uploads_disabled", 503)
    max_bytes = capability["max_file_bytes"]
    quota_bytes = capability["total_quota_bytes"]
    _uploads, quarantine, lock_path = _upload_paths()
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        lock_fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise DataPortalConfigError("upload lock is unavailable") from exc

    with os.fdopen(lock_fd, "a+b") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        except OSError as exc:
            raise DataPortalConfigError("upload lock is unavailable") from exc
        used_bytes = _quarantine_usage(quarantine)
        upload_id = str(uuid.uuid4())
        upload_dir = quarantine / upload_id
        try:
            upload_dir.mkdir(mode=0o700)
        except OSError as exc:
            raise DataPortalConfigError("upload storage is unavailable") from exc
        part = upload_dir / "payload.part"
        payload_path = upload_dir / "payload"
        digest = hashlib.sha256()
        size_bytes = 0
        try:
            with part.open("xb") as output:
                os.chmod(part, 0o600)
                while chunk := stream.read(_CHUNK_BYTES):
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        raise UploadRejected("upload_too_large", 413)
                    if used_bytes + size_bytes > quota_bytes:
                        raise UploadRejected("upload_quota_exceeded", 413)
                    output.write(chunk)
                    digest.update(chunk)
            if size_bytes == 0:
                raise UploadRejected("empty_upload")
            os.replace(part, payload_path)
            os.chmod(payload_path, 0o600)
            receipt = {
                "schema_version": "vc.upload-receipt.v1",
                "upload_id": upload_id,
                "status": "quarantined",
                "species": species,
                "filename": filename,
                "size_bytes": size_bytes,
                "sha256": digest.hexdigest(),
                "declared_content_type": content_type,
                "created_at": datetime.now(UTC)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
            }
            receipt_part = upload_dir / "receipt.json.part"
            receipt_part.write_text(
                json.dumps(
                    receipt,
                    ensure_ascii=False,
                    sort_keys=True,
                    allow_nan=False,
                )
                + "\n",
                encoding="utf-8",
            )
            os.chmod(receipt_part, 0o600)
            os.replace(receipt_part, upload_dir / "receipt.json")
            return receipt
        except OSError as exc:
            shutil.rmtree(upload_dir, ignore_errors=True)
            raise DataPortalConfigError("upload storage is unavailable") from exc
        except BaseException:
            shutil.rmtree(upload_dir, ignore_errors=True)
            raise
        finally:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
