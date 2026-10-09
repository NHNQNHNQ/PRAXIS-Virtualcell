"""Immutable Model Registry v2 identities and append-only lifecycle reduction.

This module records identity and policy facts. It does not download assets, run
models, create scientific evidence, or make operator decisions.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MODEL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_PUBLIC_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]*$")
_PACKAGE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ARTIFACT_URI_SCHEMES = frozenset({"https", "s3", "gs", "hf"})
_RFC3339 = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must be valid UTF-8 text") from exc
    return value


def _public_identifier(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _PUBLIC_IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a canonical path-safe public identifier")
    return value


def public_model_version(value: str) -> str | None:
    """Return a path-safe display value without changing internal model identity."""
    return value if isinstance(value, str) and _PUBLIC_IDENTIFIER.fullmatch(value) else None


def _pep503_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _texts(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array")
    values = tuple(_text(item, field) for item in value)
    if not allow_empty and not values:
        raise ValueError(f"{field} must not be empty")
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates")
    return values


def _fingerprint(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _fingerprints(
    value: Any,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    values = _texts(value, field, allow_empty=allow_empty)
    return tuple(_fingerprint(item, field) for item in values)


def _canonical_fingerprint(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _relative_path(value: Any, field: str) -> str:
    value = _text(value, field)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value == "."
        or ".." in path.parts
        or "\\" in value
        or "\x00" in value
        or str(path) != value
    ):
        raise ValueError(f"{field} must be a canonical relative POSIX path")
    return value


def _rfc3339(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _RFC3339.fullmatch(value):
        raise ValueError(f"{field} must be an RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return value


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise ValueError(f"{cls.__name__} must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            messages = []
            for error in exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            ):
                location = ".".join(
                    str(item)
                    if isinstance(item, int) or (isinstance(item, str) and item in cls.model_fields)
                    else "<field>"
                    for item in error["loc"]
                )
                messages.append(f"{location}: {error['msg']}")
            raise ValueError(f"{cls.__name__} validation failed: {'; '.join(messages)}") from None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.to_dict())


class PackageIdentity(_Contract):
    name: str
    version: str | None

    @field_validator("name", mode="before")
    @classmethod
    def _valid_name(cls, value):
        return _text(value, "packages.name")

    @field_validator("version", mode="before")
    @classmethod
    def _valid_version(cls, value):
        return None if value is None else _text(value, "packages.version")


class ArtifactIdentity(_Contract):
    schema_version: Literal["vc.model-artifact.v1"]
    artifact_id: str
    model_fingerprint: str
    uri: str | None
    cache_key: str
    size_bytes: int | None
    sha256: str
    media_type: str
    license: str
    source: str
    safe_load_policy: Literal[
        "data_only",
        "restricted_deserializer",
        "isolated_runtime",
        "unavailable",
    ]
    legacy_incomplete: bool = False

    @field_validator("artifact_id", "media_type", "license", "source", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("model_fingerprint", "sha256", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("cache_key", mode="before")
    @classmethod
    def _valid_cache_key(cls, value):
        return _relative_path(value, "cache_key")

    @field_validator("uri", mode="before")
    @classmethod
    def _valid_uri(cls, value):
        if value is None:
            return None
        value = _text(value, "uri")
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() not in _ARTIFACT_URI_SCHEMES
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("uri must use an approved https/s3/gs/hf authority without credentials")
        return value

    @field_validator("size_bytes")
    @classmethod
    def _valid_size(cls, value):
        if value is not None and value <= 0:
            raise ValueError("size_bytes must be positive")
        return value

    @model_validator(mode="after")
    def _complete_or_explicitly_legacy(self):
        if self.legacy_incomplete:
            if self.safe_load_policy != "unavailable":
                raise ValueError("legacy-incomplete artifacts must use unavailable safe_load_policy")
        elif self.size_bytes is None or self.safe_load_policy == "unavailable":
            raise ValueError("native artifact identity requires size and a safe load policy")
        return self


class EnvironmentIdentity(_Contract):
    schema_version: Literal["vc.model-environment.v1"]
    environment_id: str
    python_version: str | None
    cpu_architecture: str | None
    packages: tuple[PackageIdentity, ...]
    lock_digest: str | None
    image_digest: str | None
    resources: tuple[str, ...]
    accelerators: tuple[str, ...]
    adapter_fingerprints: tuple[str, ...]
    legacy_incomplete: bool = False

    @field_validator("environment_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _text(value, "environment_id")

    @field_validator("python_version", "cpu_architecture", mode="before")
    @classmethod
    def _valid_optional_text(cls, value, info):
        return None if value is None else _text(value, info.field_name)

    @field_validator("packages", mode="before")
    @classmethod
    def _valid_packages(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("packages must be an array")
        return tuple(value)

    @field_validator("lock_digest", "image_digest", mode="before")
    @classmethod
    def _valid_optional_fingerprint(cls, value, info):
        return None if value is None else _fingerprint(value, info.field_name)

    @field_validator("resources", "accelerators", mode="before")
    @classmethod
    def _valid_texts(cls, value, info):
        return _texts(value, info.field_name, allow_empty=True)

    @field_validator("adapter_fingerprints", mode="before")
    @classmethod
    def _valid_adapters(cls, value):
        return _fingerprints(value, "adapter_fingerprints", allow_empty=True)

    @model_validator(mode="after")
    def _complete_or_explicitly_legacy(self):
        if len({package.name for package in self.packages}) != len(self.packages):
            raise ValueError("environment package names must be unique")
        normalized_names = [_pep503_name(package.name) for package in self.packages]
        if self.legacy_incomplete:
            return self
        if len(set(normalized_names)) != len(self.packages):
            raise ValueError("native environment distribution names must be unique")
        if any(
            package.name != normalized or not _PACKAGE_NAME.fullmatch(package.name)
            for package, normalized in zip(self.packages, normalized_names, strict=True)
        ):
            raise ValueError("native packages.name must use canonical PEP 503 lowercase spelling")
        if self.python_version is None:
            raise ValueError("native environment identity requires python_version")
        if self.cpu_architecture is None:
            raise ValueError("native environment identity requires cpu_architecture")
        if self.lock_digest is None and self.image_digest is None:
            raise ValueError("native environment identity requires lock_digest or image_digest")
        if any(package.version is None for package in self.packages):
            raise ValueError("native environment package versions must be explicit")
        if not self.adapter_fingerprints:
            raise ValueError("native environment identity requires adapter fingerprints")
        return self


class ArtifactSnapshotBudgetPolicyV1(_Contract):
    """Versioned capacity identity for private artifact snapshot handoff."""

    schema_version: Literal["vc.artifact-snapshot-budget-policy.v1"]
    max_live_snapshot_payload_bytes: int
    max_snapshot_entries_per_execution: int
    retention_scope: Literal["execution_only"]

    @field_validator(
        "max_live_snapshot_payload_bytes",
        "max_snapshot_entries_per_execution",
        mode="before",
    )
    @classmethod
    def _valid_positive_exact_int(cls, value, info):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{info.field_name} must be a positive exact integer")
        return value


class EnvironmentIdentityV2(EnvironmentIdentity):
    """Write-new environment identity that binds snapshot capacity policy."""

    schema_version: Literal["vc.model-environment.v2"]
    artifact_snapshot_budget_policy: ArtifactSnapshotBudgetPolicyV1


EnvironmentIdentityRecord = Annotated[
    EnvironmentIdentity | EnvironmentIdentityV2,
    Field(discriminator="schema_version"),
]


class AdapterIdentity(_Contract):
    schema_version: Literal["vc.model-adapter.v1"]
    adapter_id: str
    version: str
    implementation: str
    task: str
    outputs: tuple[str, ...]
    input_contract_fingerprint: str | None
    output_contract_fingerprint: str | None
    legacy_incomplete: bool = False

    @field_validator("adapter_id", "version", "implementation", "task", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("outputs", mode="before")
    @classmethod
    def _valid_outputs(cls, value):
        return _texts(value, "outputs")

    @field_validator("input_contract_fingerprint", "output_contract_fingerprint", mode="before")
    @classmethod
    def _valid_optional_fingerprint(cls, value, info):
        return None if value is None else _fingerprint(value, info.field_name)

    @model_validator(mode="after")
    def _complete_or_explicitly_legacy(self):
        if not self.legacy_incomplete and (
            self.input_contract_fingerprint is None or self.output_contract_fingerprint is None
        ):
            raise ValueError("native adapter identity requires input and output contracts")
        return self


class ValidationEvidence(_Contract):
    schema_version: Literal["vc.model-validation-evidence.v1"]
    evidence_id: str
    pack_fingerprint: str | None
    model_fingerprint: str | None
    environment_fingerprint: str | None
    adapter_fingerprints: tuple[str, ...]
    protocol_fingerprint: str | None
    baseline_fingerprint: str | None
    metric_name: str
    metric_direction: Literal["lower_is_better", "higher_is_better"]
    result_sha256: str
    benchmark_passed: bool
    scientifically_validated: bool
    promotion_eligible: bool
    legacy_incomplete: bool = False
    binding_errors: tuple[str, ...] = ()

    @field_validator("evidence_id", "metric_name", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "pack_fingerprint",
        "model_fingerprint",
        "environment_fingerprint",
        "protocol_fingerprint",
        "baseline_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_optional_fingerprint(cls, value, info):
        return None if value is None else _fingerprint(value, info.field_name)

    @field_validator("result_sha256", mode="before")
    @classmethod
    def _valid_result_sha(cls, value):
        return _fingerprint(value, "result_sha256")

    @field_validator("adapter_fingerprints", mode="before")
    @classmethod
    def _valid_adapters(cls, value):
        return _fingerprints(value, "adapter_fingerprints", allow_empty=True)

    @field_validator("binding_errors", mode="before")
    @classmethod
    def _valid_errors(cls, value):
        return _texts(value, "binding_errors", allow_empty=True)

    @model_validator(mode="after")
    def _strict_binding_and_state(self):
        if self.legacy_incomplete or self.binding_errors:
            raise ValueError("legacy or unbound results must remain migration receipts")
        if (
            any(
                value is None
                for value in (
                    self.pack_fingerprint,
                    self.model_fingerprint,
                    self.environment_fingerprint,
                    self.protocol_fingerprint,
                    self.baseline_fingerprint,
                )
            )
            or not self.adapter_fingerprints
        ):
            raise ValueError("validation evidence requires exact complete identity bindings")
        if self.scientifically_validated and not self.benchmark_passed:
            raise ValueError("scientifically_validated requires benchmark_passed")
        if self.promotion_eligible and not (self.benchmark_passed and self.scientifically_validated):
            raise ValueError("promotion_eligible requires benchmark and scientific validation")
        return self


class OperatorPolicyRecord(_Contract):
    schema_version: Literal["vc.model-operator-policy.v1"]
    policy_id: str
    capability_fingerprint: str
    evidence_fingerprints: tuple[str, ...]
    production_promoted: bool
    decision_kind: Literal["operator_decision"]
    operator_id: str
    decided_at: str
    reason: str

    @field_validator("policy_id", "operator_id", "reason", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("capability_fingerprint", mode="before")
    @classmethod
    def _valid_capability(cls, value):
        return _fingerprint(value, "capability_fingerprint")

    @field_validator("evidence_fingerprints", mode="before")
    @classmethod
    def _valid_evidence(cls, value):
        return _fingerprints(value, "evidence_fingerprints", allow_empty=True)

    @field_validator("decided_at", mode="before")
    @classmethod
    def _valid_decided_at(cls, value):
        return _rfc3339(value, "decided_at")

    @model_validator(mode="after")
    def _promotion_has_evidence(self):
        if not self.evidence_fingerprints:
            raise ValueError("operator decisions require exact evidence fingerprints")
        return self


class OperatorPolicyRecordV2(_Contract):
    """Versioned non-clinical execution authorization, distinct from promotion."""

    schema_version: Literal["vc.model-operator-policy.v2"]
    policy_id: str
    capability_fingerprint: str
    evidence_fingerprints: tuple[str, ...]
    production_promoted: bool
    research_execution_authorized: bool
    research_execution_scope: Literal["research_only"] | None
    decision_kind: Literal["operator_decision"]
    operator_id: str
    decided_at: str
    reason: str

    @field_validator("policy_id", "operator_id", "reason", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("capability_fingerprint", mode="before")
    @classmethod
    def _valid_capability(cls, value):
        return _fingerprint(value, "capability_fingerprint")

    @field_validator("evidence_fingerprints", mode="before")
    @classmethod
    def _valid_evidence(cls, value):
        return _fingerprints(value, "evidence_fingerprints", allow_empty=True)

    @field_validator("decided_at", mode="before")
    @classmethod
    def _valid_decided_at(cls, value):
        return _rfc3339(value, "decided_at")

    @model_validator(mode="after")
    def _execution_authorization_has_exact_scope(self):
        if not self.evidence_fingerprints:
            raise ValueError("operator decisions require exact evidence fingerprints")
        if self.research_execution_authorized and self.production_promoted:
            raise ValueError("research execution authorization cannot be production promotion")
        if self.research_execution_authorized != (self.research_execution_scope == "research_only"):
            raise ValueError("research execution authorization requires research_only scope")
        return self


class ModelReleaseRecord(_Contract):
    schema_version: Literal["vc.model-release.v1"]
    release_id: str
    model_name: str
    model_version: str
    model_fingerprint: str
    pack_fingerprints: tuple[str, ...]
    artifact_fingerprints: tuple[str, ...]
    environment_fingerprint: str | None
    adapter_fingerprints: tuple[str, ...]
    evidence_fingerprints: tuple[str, ...]
    policy_fingerprint: str | None
    migration_status: Literal["native", "legacy_incomplete"]
    legacy_status: Literal["available", "planned", "missing"] | None = None
    incomplete_reasons: tuple[str, ...]

    @field_validator("release_id", mode="before")
    @classmethod
    def _valid_release_id(cls, value):
        return _public_identifier(value, "release_id")

    @field_validator("model_version", mode="before")
    @classmethod
    def _valid_model_version(cls, value):
        return _text(value, "model_version")

    @field_validator("model_name", mode="before")
    @classmethod
    def _valid_model_name(cls, value):
        value = _text(value, "model_name")
        if not _MODEL_NAME.fullmatch(value):
            raise ValueError("model_name must be canonical lower_snake_case")
        return value

    @field_validator("model_fingerprint", mode="before")
    @classmethod
    def _valid_model_fingerprint(cls, value):
        return _fingerprint(value, "model_fingerprint")

    @field_validator(
        "pack_fingerprints",
        "artifact_fingerprints",
        "adapter_fingerprints",
        "evidence_fingerprints",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprints(value, info.field_name, allow_empty=True)

    @field_validator("environment_fingerprint", "policy_fingerprint", mode="before")
    @classmethod
    def _valid_optional_fingerprint(cls, value, info):
        return None if value is None else _fingerprint(value, info.field_name)

    @field_validator("incomplete_reasons", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        return _texts(value, "incomplete_reasons", allow_empty=True)

    @model_validator(mode="after")
    def _native_or_legacy(self):
        if self.migration_status == "native":
            if self.incomplete_reasons:
                raise ValueError("native releases cannot contain incomplete reasons")
            if self.legacy_status is not None:
                raise ValueError("native releases cannot contain legacy_status")
            if public_model_version(self.model_version) is None:
                raise ValueError("native model_version must be a path-safe public identifier")
            if (
                len(self.pack_fingerprints) != 1
                or not self.artifact_fingerprints
                or self.environment_fingerprint is None
                or not self.adapter_fingerprints
            ):
                raise ValueError(
                    "native release requires exactly one Pack and complete artifact/environment/adapter refs"
                )
        else:
            if not self.incomplete_reasons:
                raise ValueError("legacy-incomplete releases require explicit reasons")
            if self.legacy_status is None:
                raise ValueError("legacy-incomplete releases require legacy_status")
            if self.evidence_fingerprints or self.policy_fingerprint is not None:
                raise ValueError("legacy migration cannot create evidence or policy bindings")
        return self

    def capability_fingerprint(self) -> str:
        return _canonical_fingerprint(
            {
                "model_name": self.model_name,
                "model_version": self.model_version,
                "model_fingerprint": self.model_fingerprint,
                "pack_fingerprints": list(self.pack_fingerprints),
                "artifact_fingerprints": list(self.artifact_fingerprints),
                "environment_fingerprint": self.environment_fingerprint,
                "adapter_fingerprints": list(self.adapter_fingerprints),
                "evidence_fingerprints": list(self.evidence_fingerprints),
            }
        )


class RegistryLifecycleEvent(_Contract):
    schema_version: Literal["vc.model-registry-event.v1"]
    event_id: str
    sequence: int
    previous_event_fingerprint: str | None
    release_fingerprint: str
    action: Literal["cataloged", "artifact_ready", "revoke", "supersede"]
    target_release_fingerprint: str | None
    recorded_at: str
    operator_id: str
    reason: str

    @field_validator("event_id", "operator_id", "reason", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("recorded_at", mode="before")
    @classmethod
    def _valid_recorded_at(cls, value):
        return _rfc3339(value, "recorded_at")

    @field_validator(
        "previous_event_fingerprint",
        "target_release_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_optional_fingerprint(cls, value, info):
        return None if value is None else _fingerprint(value, info.field_name)

    @field_validator("release_fingerprint", mode="before")
    @classmethod
    def _valid_release(cls, value):
        return _fingerprint(value, "release_fingerprint")

    @field_validator("sequence")
    @classmethod
    def _valid_sequence(cls, value):
        if value < 1:
            raise ValueError("sequence must be positive")
        return value

    @model_validator(mode="after")
    def _valid_target(self):
        if self.action == "supersede":
            if self.target_release_fingerprint is None:
                raise ValueError("supersede requires target_release_fingerprint")
            if self.target_release_fingerprint == self.release_fingerprint:
                raise ValueError("a release cannot supersede itself")
        elif self.target_release_fingerprint is not None:
            raise ValueError("target_release_fingerprint is only valid for supersede")
        return self


class RegistryState(_Contract):
    schema_version: Literal["vc.model-registry-state.v1"]
    release_fingerprint: str
    cataloged: bool
    artifact_ready: bool
    revoked: bool
    superseded_by: str | None
    event_fingerprints: tuple[str, ...]

    @field_validator("release_fingerprint", mode="before")
    @classmethod
    def _valid_release(cls, value):
        return _fingerprint(value, "release_fingerprint")

    @field_validator("superseded_by", mode="before")
    @classmethod
    def _valid_superseded_by(cls, value):
        return None if value is None else _fingerprint(value, "superseded_by")

    @field_validator("event_fingerprints", mode="before")
    @classmethod
    def _valid_events(cls, value):
        return _fingerprints(value, "event_fingerprints", allow_empty=True)

    @model_validator(mode="after")
    def _valid_state(self):
        if (self.artifact_ready or self.revoked or self.superseded_by is not None) and not self.cataloged:
            raise ValueError("registry lifecycle state requires cataloged")
        if self.revoked and self.superseded_by is not None:
            raise ValueError("a release cannot be both revoked and superseded")
        return self


def reduce_lifecycle(
    release_fingerprint: str,
    events: Iterable[RegistryLifecycleEvent],
) -> RegistryState:
    release_fingerprint = _fingerprint(release_fingerprint, "release_fingerprint")
    cataloged = False
    artifact_ready = False
    revoked = False
    superseded_by = None
    used: list[str] = []
    for event in events:
        if event.release_fingerprint != release_fingerprint:
            continue
        if revoked or superseded_by is not None:
            raise ValueError("closed releases cannot accept later lifecycle events")
        if event.action == "cataloged":
            if cataloged:
                raise ValueError("cataloged cannot be repeated")
            cataloged = True
        elif event.action == "artifact_ready":
            if not cataloged or artifact_ready:
                raise ValueError("artifact_ready requires one prior cataloged event")
            artifact_ready = True
        elif event.action == "revoke":
            if not cataloged:
                raise ValueError("revoke requires cataloged")
            revoked = True
        elif event.action == "supersede":
            if not cataloged:
                raise ValueError("supersede requires cataloged")
            superseded_by = event.target_release_fingerprint
        used.append(event.fingerprint())
    return RegistryState(
        schema_version="vc.model-registry-state.v1",
        release_fingerprint=release_fingerprint,
        cataloged=cataloged,
        artifact_ready=artifact_ready,
        revoked=revoked,
        superseded_by=superseded_by,
        event_fingerprints=used,
    )


class ModelRegistryV2(_Contract):
    schema_version: Literal["vc.model-registry.v2"]
    artifacts: tuple[ArtifactIdentity, ...] = ()
    environments: tuple[EnvironmentIdentityRecord, ...] = ()
    adapters: tuple[AdapterIdentity, ...] = ()
    evidence_records: tuple[ValidationEvidence, ...] = ()
    policy_records: tuple[OperatorPolicyRecord | OperatorPolicyRecordV2, ...] = ()
    releases: tuple[ModelReleaseRecord, ...] = ()
    lifecycle_events: tuple[RegistryLifecycleEvent, ...] = ()

    @field_validator(
        "artifacts",
        "environments",
        "adapters",
        "evidence_records",
        "policy_records",
        "releases",
        "lifecycle_events",
        mode="before",
    )
    @classmethod
    def _valid_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{info.field_name} must be an array")
        return tuple(value)

    @staticmethod
    def _index(records, kind: str):
        indexed = {record.fingerprint(): record for record in records}
        if len(indexed) != len(records):
            raise ValueError(f"duplicate {kind} fingerprint")
        return indexed

    @model_validator(mode="after")
    def _consistent_graph(self):
        artifacts = self._index(self.artifacts, "artifact")
        environments = self._index(self.environments, "environment")
        adapters = self._index(self.adapters, "adapter")
        evidence_records = self._index(self.evidence_records, "evidence")
        policies = self._index(self.policy_records, "policy")
        releases = self._index(self.releases, "release")

        for records, field in (
            (self.artifacts, "artifact_id"),
            (self.environments, "environment_id"),
            (self.adapters, "adapter_id"),
            (self.evidence_records, "evidence_id"),
            (self.policy_records, "policy_id"),
            (self.releases, "release_id"),
            (self.lifecycle_events, "event_id"),
        ):
            values = [getattr(record, field) for record in records]
            if len(set(values)) != len(values):
                raise ValueError(f"duplicate {field}")

        cache_keys = [unicodedata.normalize("NFC", artifact.cache_key).casefold() for artifact in self.artifacts]
        if len(set(cache_keys)) != len(cache_keys):
            raise ValueError("duplicate artifact cache_key")

        for release in self.releases:
            release_artifacts = []
            for fingerprint in release.artifact_fingerprints:
                try:
                    artifact = artifacts[fingerprint]
                except KeyError as exc:
                    raise ValueError("release references unknown artifact") from exc
                if artifact.model_fingerprint != release.model_fingerprint:
                    raise ValueError("artifact is bound to a different model")
                release_artifacts.append(artifact)

            environment = None
            if release.environment_fingerprint is not None:
                try:
                    environment = environments[release.environment_fingerprint]
                except KeyError as exc:
                    raise ValueError("release references unknown environment") from exc
            for fingerprint in release.adapter_fingerprints:
                if fingerprint not in adapters:
                    raise ValueError("release references unknown adapter")
            if environment is not None and (environment.adapter_fingerprints != release.adapter_fingerprints):
                raise ValueError("environment and release adapter bindings differ")

            release_evidence = []
            for fingerprint in release.evidence_fingerprints:
                try:
                    evidence = evidence_records[fingerprint]
                except KeyError as exc:
                    raise ValueError("release references unknown evidence") from exc
                if (
                    evidence.model_fingerprint != release.model_fingerprint
                    or evidence.environment_fingerprint != release.environment_fingerprint
                    or evidence.adapter_fingerprints != release.adapter_fingerprints
                    or evidence.pack_fingerprint != release.pack_fingerprints[0]
                ):
                    raise ValueError("evidence identity does not match release capability")
                release_evidence.append(evidence)

            if release.policy_fingerprint is not None:
                try:
                    policy = policies[release.policy_fingerprint]
                except KeyError as exc:
                    raise ValueError("release references unknown policy") from exc
                if policy.capability_fingerprint != release.capability_fingerprint():
                    raise ValueError("policy is bound to a different capability")
                if policy.evidence_fingerprints != release.evidence_fingerprints:
                    raise ValueError("policy and release evidence bindings differ")
                if policy.production_promoted and not (
                    release_evidence
                    and all(
                        evidence.benchmark_passed and evidence.scientifically_validated and evidence.promotion_eligible
                        for evidence in release_evidence
                    )
                ):
                    raise ValueError("production promotion exceeds scientific evidence")

            if release.migration_status == "native" and any(
                artifact.legacy_incomplete for artifact in release_artifacts
            ):
                raise ValueError("native release cannot reference incomplete artifacts")
            if (
                release.migration_status == "native"
                and environment is not None
                and (
                    environment.legacy_incomplete
                    or any(adapters[item].legacy_incomplete for item in release.adapter_fingerprints)
                )
            ):
                raise ValueError("native release cannot reference incomplete environment or adapters")

        for environment in self.environments:
            if any(item not in adapters for item in environment.adapter_fingerprints):
                raise ValueError("environment references unknown adapter")
        for evidence in self.evidence_records:
            if evidence.environment_fingerprint not in environments:
                raise ValueError("evidence references unknown environment")
            if any(item not in adapters for item in evidence.adapter_fingerprints):
                raise ValueError("evidence references unknown adapter")
        release_capabilities = {release.capability_fingerprint() for release in self.releases}
        for policy in self.policy_records:
            if any(item not in evidence_records for item in policy.evidence_fingerprints):
                raise ValueError("policy references unknown evidence")
            if policy.capability_fingerprint not in release_capabilities:
                raise ValueError("policy references unknown release capability")

        referenced_artifacts = {item for release in self.releases for item in release.artifact_fingerprints}
        if set(artifacts) != referenced_artifacts:
            raise ValueError("artifact records must be referenced by the release closure")
        referenced_environments = {
            release.environment_fingerprint for release in self.releases if release.environment_fingerprint is not None
        }
        if set(environments) != referenced_environments:
            raise ValueError("environment records must be referenced by the release closure")
        referenced_adapters = {item for release in self.releases for item in release.adapter_fingerprints}
        if set(adapters) != referenced_adapters:
            raise ValueError("adapter records must be referenced by the release closure")
        referenced_evidence = {item for release in self.releases for item in release.evidence_fingerprints}
        if set(evidence_records) != referenced_evidence:
            raise ValueError("evidence records must be referenced by the release closure")
        referenced_policies = {
            release.policy_fingerprint for release in self.releases if release.policy_fingerprint is not None
        }
        if set(policies) != referenced_policies:
            raise ValueError("policy records must be referenced by the release closure")

        previous = None
        for expected_sequence, event in enumerate(self.lifecycle_events, start=1):
            if event.sequence != expected_sequence:
                raise ValueError("lifecycle event sequence must be contiguous and append-only")
            if event.previous_event_fingerprint != previous:
                raise ValueError("lifecycle event hash chain is broken")
            if event.release_fingerprint not in releases:
                raise ValueError("lifecycle event references unknown release")
            if event.target_release_fingerprint is not None and event.target_release_fingerprint not in releases:
                raise ValueError("supersede target is not registered")
            if event.action == "supersede":
                target_state = reduce_lifecycle(
                    event.target_release_fingerprint,
                    self.lifecycle_events[: expected_sequence - 1],
                )
                if not target_state.cataloged or target_state.revoked or target_state.superseded_by is not None:
                    raise ValueError("supersede target must already be active and cataloged")
            previous = event.fingerprint()

        for fingerprint, release in releases.items():
            state = reduce_lifecycle(fingerprint, self.lifecycle_events)
            if state.artifact_ready and (
                release.migration_status != "native"
                or not release.artifact_fingerprints
                or any(artifacts[item].legacy_incomplete for item in release.artifact_fingerprints)
            ):
                raise ValueError("artifact_ready requires complete native artifact identities")
        return self

    def _lookup(self, records, fingerprint: str, kind: str):
        fingerprint = _fingerprint(fingerprint, f"{kind}_fingerprint")
        for record in records:
            if record.fingerprint() == fingerprint:
                return record
        raise KeyError(f"unknown {kind} fingerprint: {fingerprint}")

    def artifact(self, fingerprint: str) -> ArtifactIdentity:
        return self._lookup(self.artifacts, fingerprint, "artifact")

    def environment(self, fingerprint: str) -> EnvironmentIdentityRecord:
        return self._lookup(self.environments, fingerprint, "environment")

    def adapter(self, fingerprint: str) -> AdapterIdentity:
        return self._lookup(self.adapters, fingerprint, "adapter")

    def evidence(self, fingerprint: str) -> ValidationEvidence:
        return self._lookup(self.evidence_records, fingerprint, "evidence")

    def policy(self, fingerprint: str) -> OperatorPolicyRecord | OperatorPolicyRecordV2:
        return self._lookup(self.policy_records, fingerprint, "policy")

    def release(self, fingerprint: str) -> ModelReleaseRecord:
        return self._lookup(self.releases, fingerprint, "release")

    def state(self, release_fingerprint: str) -> RegistryState:
        self.release(release_fingerprint)
        return reduce_lifecycle(release_fingerprint, self.lifecycle_events)

    def append(self, event: RegistryLifecycleEvent) -> ModelRegistryV2:
        if not isinstance(event, RegistryLifecycleEvent):
            raise TypeError("append requires RegistryLifecycleEvent")
        value = self.to_dict()
        value["lifecycle_events"].append(event.to_dict())
        return type(self).from_dict(value)

    def public_catalog(self) -> dict[str, Any]:
        releases = []
        for release in self.releases:
            release_fingerprint = release.fingerprint()
            state = self.state(release_fingerprint)
            evidence = [self.evidence(item) for item in release.evidence_fingerprints]
            policy = self.policy(release.policy_fingerprint) if release.policy_fingerprint is not None else None
            releases.append(
                {
                    "release_id": release.release_id,
                    "release_fingerprint": release_fingerprint,
                    "model_name": release.model_name,
                    "model_version": public_model_version(release.model_version),
                    "model_fingerprint": release.model_fingerprint,
                    "pack_fingerprints": list(release.pack_fingerprints),
                    "artifact_fingerprints": list(release.artifact_fingerprints),
                    "environment_fingerprint": release.environment_fingerprint,
                    "adapter_fingerprints": list(release.adapter_fingerprints),
                    "evidence_fingerprints": list(release.evidence_fingerprints),
                    "policy_fingerprint": release.policy_fingerprint,
                    "migration_status": release.migration_status,
                    "legacy_status": release.legacy_status,
                    "cataloged": state.cataloged,
                    "artifact_ready": state.artifact_ready,
                    "revoked": state.revoked,
                    "superseded_by": state.superseded_by,
                    "benchmark_passed": (all(item.benchmark_passed for item in evidence) if evidence else None),
                    "scientifically_validated": (
                        all(item.scientifically_validated for item in evidence) if evidence else None
                    ),
                    "promotion_eligible": (all(item.promotion_eligible for item in evidence) if evidence else None),
                    "policy_present": policy is not None,
                    "production_promoted": bool(policy is not None and policy.production_promoted),
                    **(
                        {
                            "research_execution_authorized": (policy.research_execution_authorized),
                            "research_execution_scope": (policy.research_execution_scope),
                        }
                        if isinstance(policy, OperatorPolicyRecordV2)
                        else {}
                    ),
                }
            )
        return {
            "schema_version": "vc.model-registry-catalog.v2",
            "registry_fingerprint": self.fingerprint(),
            "releases": sorted(releases, key=lambda item: item["release_id"]),
        }

    @classmethod
    def from_v1_cards(cls, cards: Iterable[Any]) -> ModelRegistryV2:
        artifacts: list[ArtifactIdentity] = []
        environments: list[EnvironmentIdentityRecord] = []
        adapters: list[AdapterIdentity] = []
        releases: list[ModelReleaseRecord] = []
        events: list[RegistryLifecycleEvent] = []
        previous = None
        seen_names: set[str] = set()
        for card in sorted(cards, key=lambda item: item.name):
            if card.schema_version != "vc.model-card.v1":
                raise ValueError("from_v1_cards accepts only vc.model-card.v1")
            if card.name in seen_names:
                raise ValueError(f"duplicate v1 model card: {card.name}")
            seen_names.add(card.name)
            model_fingerprint = card.fingerprint()

            card_artifacts = []
            for asset in card.assets:
                artifact = ArtifactIdentity(
                    schema_version="vc.model-artifact.v1",
                    artifact_id=f"{card.name}:{asset.filename}",
                    model_fingerprint=model_fingerprint,
                    uri=None,
                    cache_key=f"{card.name}/{asset.filename}",
                    size_bytes=None,
                    sha256=asset.sha256,
                    media_type=asset.media_type,
                    license=card.license,
                    source="legacy_model_card",
                    safe_load_policy="unavailable",
                    legacy_incomplete=True,
                )
                artifacts.append(artifact)
                card_artifacts.append(artifact.fingerprint())

            adapter = AdapterIdentity(
                schema_version="vc.model-adapter.v1",
                adapter_id=f"legacy-wrapper:{card.name}",
                version=card.version,
                implementation=card.wrapper,
                task=card.task,
                outputs=card.output,
                input_contract_fingerprint=None,
                output_contract_fingerprint=None,
                legacy_incomplete=True,
            )
            adapters.append(adapter)
            adapter_fingerprint = adapter.fingerprint()
            resources = tuple(card.resources.required)
            environment = EnvironmentIdentity(
                schema_version="vc.model-environment.v1",
                environment_id=f"legacy-environment:{card.name}:{card.version}",
                python_version=None,
                cpu_architecture=None,
                packages=tuple(PackageIdentity(name=name, version=None) for name in card.resources.python_dependencies),
                lock_digest=None,
                image_digest=None,
                resources=resources,
                accelerators=tuple(item for item in resources if item != "cpu"),
                adapter_fingerprints=(adapter_fingerprint,),
                legacy_incomplete=True,
            )
            environments.append(environment)
            safe_version = card.version if _PUBLIC_IDENTIFIER.fullmatch(card.version) else f"legacy-{model_fingerprint}"
            release = ModelReleaseRecord(
                schema_version="vc.model-release.v1",
                release_id=f"{card.name}@{safe_version}",
                model_name=card.name,
                model_version=card.version,
                model_fingerprint=model_fingerprint,
                pack_fingerprints=(),
                artifact_fingerprints=tuple(card_artifacts),
                environment_fingerprint=environment.fingerprint(),
                adapter_fingerprints=(adapter_fingerprint,),
                evidence_fingerprints=(),
                policy_fingerprint=None,
                migration_status="legacy_incomplete",
                legacy_status=card.status,
                incomplete_reasons=(
                    "legacy_model_card_has_no_complete_artifact_identity",
                    "legacy_environment_has_no_lock_or_image_digest",
                    "legacy_adapter_has_no_versioned_io_contract",
                    "legacy_validation_evidence_unbound",
                    "operator_policy_absent",
                ),
            )
            releases.append(release)
            event = RegistryLifecycleEvent(
                schema_version="vc.model-registry-event.v1",
                event_id=f"migration-catalog-{card.name}",
                sequence=len(events) + 1,
                previous_event_fingerprint=previous,
                release_fingerprint=release.fingerprint(),
                action="cataloged",
                target_release_fingerprint=None,
                recorded_at="2026-08-02T00:00:00Z",
                operator_id="system:migration",
                reason=f"migrated vc.model-card.v1 status={card.status}; no state promotion",
            )
            events.append(event)
            previous = event.fingerprint()

        return cls(
            schema_version="vc.model-registry.v2",
            artifacts=artifacts,
            environments=environments,
            adapters=adapters,
            evidence_records=(),
            policy_records=(),
            releases=releases,
            lifecycle_events=events,
        )


@dataclass(frozen=True)
class ComposedModelRegistryV2:
    """Read-only, role-bound view over two independently auditable registries.

    A composed view must not synthesize a third lifecycle chain.  Source
    registries retain their own append-only lifecycle identities, while this
    object only supplies the exact lookup surface needed by planning/runtime.
    """

    base: ModelRegistryV2
    domain: ModelRegistryV2

    def __post_init__(self) -> None:
        if not isinstance(self.base, ModelRegistryV2) or not isinstance(self.domain, ModelRegistryV2):
            raise TypeError("base and domain must be ModelRegistryV2")
        if self.base.fingerprint() == self.domain.fingerprint():
            raise ValueError("base and domain cannot share lifecycle authorities")
        self._validate_conflicts()

    @classmethod
    def compose(
        cls,
        base: ModelRegistryV2,
        domain: ModelRegistryV2,
    ) -> ComposedModelRegistryV2:
        return cls(base=base, domain=domain)

    def to_dict(self) -> dict[str, str]:
        return {
            "schema_version": "vc.model-registry-composition.v1",
            "base_registry_fingerprint": self.base.fingerprint(),
            "domain_registry_fingerprint": self.domain.fingerprint(),
        }

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.to_dict())

    def _validate_conflicts(self) -> None:
        for field, identifier in (
            ("artifacts", "artifact_id"),
            ("environments", "environment_id"),
            ("adapters", "adapter_id"),
            ("evidence_records", "evidence_id"),
            ("policy_records", "policy_id"),
            ("releases", "release_id"),
        ):
            seen: dict[str, str] = {}
            for source in (self.base, self.domain):
                for record in getattr(source, field):
                    key = getattr(record, identifier)
                    fingerprint = record.fingerprint()
                    if key in seen and seen[key] != fingerprint:
                        raise ValueError(f"composed registry has conflicting {identifier}")
                    seen[key] = fingerprint

        cache_keys: dict[str, str] = {}
        for source in (self.base, self.domain):
            for artifact in source.artifacts:
                key = unicodedata.normalize("NFC", artifact.cache_key).casefold()
                fingerprint = artifact.fingerprint()
                if key in cache_keys and cache_keys[key] != fingerprint:
                    raise ValueError("composed registry has conflicting artifact cache_key")
                cache_keys[key] = fingerprint

        base_releases = {item.fingerprint() for item in self.base.releases}
        domain_releases = {item.fingerprint() for item in self.domain.releases}
        if base_releases & domain_releases:
            raise ValueError("a release cannot have two lifecycle authorities")

        routes: dict[tuple[str, str, str, str], str] = {}
        for source in (self.base, self.domain):
            for release in source.releases:
                for pack_fingerprint in release.pack_fingerprints:
                    key = (
                        release.model_name,
                        release.model_version,
                        release.model_fingerprint,
                        pack_fingerprint,
                    )
                    release_fingerprint = release.fingerprint()
                    if key in routes and routes[key] != release_fingerprint:
                        raise ValueError("composed registry has ambiguous release routing")
                    routes[key] = release_fingerprint

    @staticmethod
    def _merged_records(base_records, domain_records):
        result = []
        seen: set[str] = set()
        for record in (*base_records, *domain_records):
            fingerprint = record.fingerprint()
            if fingerprint not in seen:
                result.append(record)
                seen.add(fingerprint)
        return tuple(result)

    @property
    def artifacts(self) -> tuple[ArtifactIdentity, ...]:
        return self._merged_records(self.base.artifacts, self.domain.artifacts)

    @property
    def environments(self) -> tuple[EnvironmentIdentityRecord, ...]:
        return self._merged_records(self.base.environments, self.domain.environments)

    @property
    def adapters(self) -> tuple[AdapterIdentity, ...]:
        return self._merged_records(self.base.adapters, self.domain.adapters)

    @property
    def evidence_records(self) -> tuple[ValidationEvidence, ...]:
        return self._merged_records(
            self.base.evidence_records,
            self.domain.evidence_records,
        )

    @property
    def policy_records(self) -> tuple[OperatorPolicyRecord | OperatorPolicyRecordV2, ...]:
        return self._merged_records(self.base.policy_records, self.domain.policy_records)

    @property
    def releases(self) -> tuple[ModelReleaseRecord, ...]:
        return self._merged_records(self.base.releases, self.domain.releases)

    def _lookup(self, records, fingerprint: str, kind: str):
        fingerprint = _fingerprint(fingerprint, f"{kind}_fingerprint")
        for record in records:
            if record.fingerprint() == fingerprint:
                return record
        raise KeyError(f"unknown {kind} fingerprint: {fingerprint}")

    def artifact(self, fingerprint: str) -> ArtifactIdentity:
        return self._lookup(self.artifacts, fingerprint, "artifact")

    def environment(self, fingerprint: str) -> EnvironmentIdentityRecord:
        return self._lookup(self.environments, fingerprint, "environment")

    def adapter(self, fingerprint: str) -> AdapterIdentity:
        return self._lookup(self.adapters, fingerprint, "adapter")

    def evidence(self, fingerprint: str) -> ValidationEvidence:
        return self._lookup(self.evidence_records, fingerprint, "evidence")

    def policy(self, fingerprint: str) -> OperatorPolicyRecord | OperatorPolicyRecordV2:
        return self._lookup(self.policy_records, fingerprint, "policy")

    def release(self, fingerprint: str) -> ModelReleaseRecord:
        return self._lookup(self.releases, fingerprint, "release")

    def state(self, release_fingerprint: str) -> RegistryState:
        release_fingerprint = _fingerprint(
            release_fingerprint,
            "release_fingerprint",
        )
        owners = tuple(
            source
            for source in (self.base, self.domain)
            if any(item.fingerprint() == release_fingerprint for item in source.releases)
        )
        if len(owners) != 1:
            raise KeyError(f"unknown release fingerprint: {release_fingerprint}")
        return owners[0].state(release_fingerprint)

    def append(self, _event: RegistryLifecycleEvent):
        raise TypeError("composed registries have no merged lifecycle authority")

    def public_catalog(self) -> dict[str, Any]:
        releases = [
            *self.base.public_catalog()["releases"],
            *self.domain.public_catalog()["releases"],
        ]
        return {
            "schema_version": "vc.model-registry-catalog.v3",
            "registry_fingerprint": self.fingerprint(),
            "composition": self.to_dict(),
            "releases": sorted(releases, key=lambda item: item["release_id"]),
        }


def compose_model_registries(
    base: ModelRegistryV2,
    domain: ModelRegistryV2,
) -> ComposedModelRegistryV2:
    """Compose explicit sources without changing either source identity."""
    return ComposedModelRegistryV2.compose(base, domain)


class LegacyMigrationReceipt(_Contract):
    schema_version: Literal["vc.model-registry-legacy-receipt.v1"]
    receipt_id: str
    source_path: str
    size_bytes: int
    sha256: str
    declared_pack_fingerprint: str | None
    available: bool | None
    benchmark_passed: Literal[False] | None
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False] | None
    binding_status: Literal["unbound"]
    reason_codes: tuple[str, ...]

    @field_validator("receipt_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _text(value, "receipt_id")

    @field_validator("source_path", mode="before")
    @classmethod
    def _valid_source_path(cls, value):
        return _relative_path(value, "source_path")

    @field_validator("size_bytes")
    @classmethod
    def _valid_size(cls, value):
        if value <= 0:
            raise ValueError("size_bytes must be positive")
        return value

    @field_validator("sha256", mode="before")
    @classmethod
    def _valid_sha(cls, value):
        return _fingerprint(value, "sha256")

    @field_validator("declared_pack_fingerprint", mode="before")
    @classmethod
    def _valid_pack(cls, value):
        return None if value is None else _fingerprint(value, "declared_pack_fingerprint")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        return _texts(value, "reason_codes")


class LegacyMigrationReport(_Contract):
    schema_version: Literal["vc.model-registry-legacy-migration-report.v1"]
    source_model_names: tuple[str, ...]
    release_fingerprints: tuple[str, ...]
    receipts: tuple[LegacyMigrationReceipt, ...]
    evidence_admitted: Literal[False]
    production_promoted: Literal[False]

    @field_validator("source_model_names", mode="before")
    @classmethod
    def _valid_names(cls, value):
        values = _texts(value, "source_model_names", allow_empty=True)
        if any(not _MODEL_NAME.fullmatch(item) for item in values):
            raise ValueError("source_model_names must be canonical lower_snake_case")
        return values

    @field_validator("release_fingerprints", mode="before")
    @classmethod
    def _valid_releases(cls, value):
        return _fingerprints(value, "release_fingerprints", allow_empty=True)

    @field_validator("receipts", mode="before")
    @classmethod
    def _valid_receipts(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("receipts must be an array")
        return tuple(value)

    @model_validator(mode="after")
    def _unique_receipts(self):
        ids = [receipt.receipt_id for receipt in self.receipts]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate receipt_id")
        if len({receipt.fingerprint() for receipt in self.receipts}) != len(self.receipts):
            raise ValueError("duplicate migration receipt fingerprint")
        return self


def legacy_migration_report(
    registry: ModelRegistryV2,
    receipts: Iterable[LegacyMigrationReceipt],
) -> LegacyMigrationReport:
    if not isinstance(registry, ModelRegistryV2):
        raise TypeError("registry must be ModelRegistryV2")
    if any(release.migration_status != "legacy_incomplete" for release in registry.releases):
        raise ValueError("legacy migration report requires only legacy-incomplete releases")
    if registry.evidence_records or registry.policy_records:
        raise ValueError("legacy migration report cannot admit evidence or policy records")
    values = tuple(receipts)
    if any(not isinstance(item, LegacyMigrationReceipt) for item in values):
        raise TypeError("receipts must contain LegacyMigrationReceipt")
    return LegacyMigrationReport(
        schema_version="vc.model-registry-legacy-migration-report.v1",
        source_model_names=tuple(sorted(release.model_name for release in registry.releases)),
        release_fingerprints=tuple(sorted(release.fingerprint() for release in registry.releases)),
        receipts=values,
        evidence_admitted=False,
        production_promoted=False,
    )
