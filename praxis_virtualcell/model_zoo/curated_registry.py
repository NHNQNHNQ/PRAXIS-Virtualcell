"""Operator-curated, local Virtual Cell release registry.

The registry records exact release closures and catalog lifecycle only.  It does
not download or install assets, import wrapper code, execute models, create
scientific evidence, or make product-promotion decisions.

The registry denies imports and decisions unless their exact identities appear
in an operator-configured trust allowlist. Hashes do not authenticate
themselves; the allowlist and monotonic checkpoint must come from an
independent trust domain rather than an untrusted candidate release.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.benchmarks.system import (
    BenchmarkEvidenceBundleV1,
    compute_p21b_execution_fingerprint,
)
from praxis_virtualcell.model_zoo.registry_v2 import ModelRegistryV2
from praxis_virtualcell.pack_factory import FactoryRegisteredPackV1

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PUBLIC_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]*$")
_ENTRYPOINT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_RFC3339 = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
_STAGING_NAME = re.compile(r"^\.staging-[0-9a-f]{32}\.tmp$")
_HEAD_STAGING_NAME = re.compile(r"^\.head-staging-[0-9a-f]{32}\.tmp$")
_MARKER = ".curated-registry.json"
_MARKER_BYTES = b'{"schema_version":"vc.curated-virtual-cell-registry.v1"}\n'
_HEAD = ".registry.head"
_LOCK = ".registry.lock"
_MAX_FILE_BYTES = 32 * 1024 * 1024


class CuratedRegistryError(ValueError):
    """A curated-registry contract, trust boundary, or lifecycle gate failed."""


def _canonical_bytes(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", serialize_as_any=True)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CuratedRegistryError("value is not canonical JSON") from exc


def _canonical_fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must be valid UTF-8 text") from exc
    return value


def _public_id(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _PUBLIC_ID.fullmatch(value):
        raise ValueError(f"{field} must be a path-safe public identifier")
    return value


def _fingerprint(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _fingerprints(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array")
    values = tuple(_fingerprint(item, field) for item in value)
    if not allow_empty and not values:
        raise ValueError(f"{field} must not be empty")
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates")
    return values


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


def _json_object_bytes(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    try:
        value = json.loads(payload, object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CuratedRegistryError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise CuratedRegistryError(f"{label} must be a JSON object")
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


class VirtualCellContextV1(_Contract):
    schema_version: Literal["vc.virtual-cell-context.v1"]
    context_id: str
    organism: str
    cell_type: str
    intervention: str
    endpoint: str
    benchmark_scope_fingerprint: str

    @field_validator("context_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _public_id(value, "context_id")

    @field_validator("organism", "cell_type", "intervention", "endpoint", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("benchmark_scope_fingerprint", mode="before")
    @classmethod
    def _valid_scope(cls, value):
        return _fingerprint(value, "benchmark_scope_fingerprint")


class WrapperApprovalV1(_Contract):
    """External review provenance; P22 never resolves or imports the entrypoint."""

    schema_version: Literal["vc.virtual-cell-wrapper-approval.v1"]
    approval_id: str
    adapter_fingerprint: str
    entrypoint: str
    wrapper_source_sha256: str
    model_card_fingerprint: str
    reviewer_id: str
    reviewed_at: str
    reason: str
    approved: Literal[True]

    @field_validator("approval_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _public_id(value, "approval_id")

    @field_validator(
        "adapter_fingerprint",
        "wrapper_source_sha256",
        "model_card_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("entrypoint", mode="before")
    @classmethod
    def _valid_entrypoint(cls, value):
        value = _text(value, "entrypoint")
        if not _ENTRYPOINT.fullmatch(value):
            raise ValueError("entrypoint must be a fully-qualified Python path")
        return value

    @field_validator("reviewer_id", "reason", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("reviewed_at", mode="before")
    @classmethod
    def _valid_time(cls, value):
        return _rfc3339(value, "reviewed_at")


def _release_dependencies(
    *,
    context: VirtualCellContextV1,
    pack_registration: FactoryRegisteredPackV1,
    source_registry: ModelRegistryV2,
    model_release_fingerprint: str,
    benchmark_bundle: BenchmarkEvidenceBundleV1,
    p21b_execution_identity_fingerprint: str,
    wrapper_approvals: tuple[WrapperApprovalV1, ...],
) -> tuple[str, ...]:
    release = source_registry.release(model_release_fingerprint)
    values = {
        context.fingerprint(),
        pack_registration.fingerprint(),
        pack_registration.receipt_fingerprint,
        pack_registration.candidate_fingerprint,
        pack_registration.metadata_review_fingerprint,
        pack_registration.validation_report_fingerprint,
        pack_registration.operator_decision_fingerprint,
        source_registry.fingerprint(),
        model_release_fingerprint,
        benchmark_bundle.fingerprint(),
        benchmark_bundle.protocol.fingerprint(),
        benchmark_bundle.protocol.scope.fingerprint(),
        benchmark_bundle.protocol.threshold_policy.fingerprint(),
        *(item.fingerprint() for item in benchmark_bundle.protocol.ood_policy),
        benchmark_bundle.run.fingerprint(),
        benchmark_bundle.result.fingerprint(),
        benchmark_bundle.run.model_card_fingerprint,
        p21b_execution_identity_fingerprint,
        *release.artifact_fingerprints,
        *release.adapter_fingerprints,
        *release.evidence_fingerprints,
        *(item.fingerprint() for item in wrapper_approvals),
    }
    if release.environment_fingerprint is not None:
        values.add(release.environment_fingerprint)
    if release.policy_fingerprint is not None:
        values.add(release.policy_fingerprint)
    return tuple(sorted(values))


class VirtualCellReleaseV1(_Contract):
    """One-Pack/P21B v1 closure; trust is supplied separately at import.

    Multi-Pack and non-P21B evidence routes are intentionally outside this v1.
    Release license and source fields are curated metadata covered by the full
    import allowlist identity, not scientific facts derived by this module.
    """

    schema_version: Literal["vc.virtual-cell-release.v1"]
    virtual_cell_id: str
    release_version: str
    context: VirtualCellContextV1
    pack_registration: FactoryRegisteredPackV1
    source_registry: ModelRegistryV2
    source_registry_fingerprint: str
    model_release_fingerprint: str
    model_card_fingerprint: str
    benchmark_bundle: BenchmarkEvidenceBundleV1
    benchmark_bundle_fingerprint: str
    p21b_execution_identity_fingerprint: str
    validation_evidence_fingerprint: str
    policy_fingerprint: str
    wrapper_approvals: tuple[WrapperApprovalV1, ...]
    capability_scope_fingerprint: str
    ood_policy_fingerprints: tuple[str, ...]
    abstain_policy_fingerprint: str
    dependency_fingerprints: tuple[str, ...]
    publisher_id: str
    reviewer_id: str
    reviewed_at: str
    release_license: str
    source_name: str
    source_uri: str | None

    @field_validator("virtual_cell_id", "release_version", mode="before")
    @classmethod
    def _valid_public_id(cls, value, info):
        return _public_id(value, info.field_name)

    @field_validator(
        "source_registry_fingerprint",
        "model_release_fingerprint",
        "model_card_fingerprint",
        "benchmark_bundle_fingerprint",
        "p21b_execution_identity_fingerprint",
        "validation_evidence_fingerprint",
        "policy_fingerprint",
        "capability_scope_fingerprint",
        "abstain_policy_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("ood_policy_fingerprints", "dependency_fingerprints", mode="before")
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprints(value, info.field_name)

    @field_validator("wrapper_approvals", mode="before")
    @classmethod
    def _valid_approvals(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("wrapper_approvals must be a non-empty array")
        return tuple(value)

    @field_validator(
        "publisher_id",
        "reviewer_id",
        "release_license",
        "source_name",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("reviewed_at", mode="before")
    @classmethod
    def _valid_time(cls, value):
        return _rfc3339(value, "reviewed_at")

    @field_validator("source_uri", mode="before")
    @classmethod
    def _valid_source_uri(cls, value):
        if value is None:
            return None
        value = _text(value, "source_uri")
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("source_uri must be credential-free HTTPS without query or fragment")
        return value

    @model_validator(mode="after")
    def _immutable_closure_is_exact(self):
        if type(self.pack_registration) is not FactoryRegisteredPackV1:
            raise ValueError("pack_registration must be the exact P19 contract")
        pack_registration = FactoryRegisteredPackV1.from_dict(self.pack_registration.to_dict())
        if type(self.source_registry) is not ModelRegistryV2:
            raise ValueError("source_registry must be the exact P12 contract")
        registry = ModelRegistryV2.from_dict(self.source_registry.to_dict())
        if type(self.benchmark_bundle) is not BenchmarkEvidenceBundleV1:
            raise ValueError("benchmark_bundle must be the exact P21A contract")
        bundle = BenchmarkEvidenceBundleV1.from_dict(self.benchmark_bundle.to_dict())
        approvals = tuple(WrapperApprovalV1.from_dict(item.to_dict()) for item in self.wrapper_approvals)

        if registry.fingerprint() != self.source_registry_fingerprint:
            raise ValueError("source registry fingerprint is stale")
        if registry.lifecycle_events:
            raise ValueError("P22 imports a one-release identity closure without prior lifecycle")
        if len(registry.releases) != 1:
            raise ValueError("source registry must contain exactly one release closure")
        release = registry.releases[0]
        if release.fingerprint() != self.model_release_fingerprint:
            raise ValueError("model release fingerprint is stale")
        if release.migration_status != "native":
            raise ValueError("curated releases require a complete native model release")
        if len(release.evidence_fingerprints) != 1 or release.policy_fingerprint is None:
            raise ValueError("curated releases require exact evidence and policy")

        if bundle.fingerprint() != self.benchmark_bundle_fingerprint:
            raise ValueError("benchmark bundle fingerprint is stale")
        if compute_p21b_execution_fingerprint(bundle.run, bundle.result) != self.p21b_execution_identity_fingerprint:
            raise ValueError("P21B execution identity does not bind the bundle")
        evidence = registry.evidence(release.evidence_fingerprints[0])
        if not (evidence.benchmark_passed and evidence.scientifically_validated and evidence.promotion_eligible):
            raise ValueError("curated releases require pre-existing positive scientific evidence")
        if evidence.fingerprint() != self.validation_evidence_fingerprint:
            raise ValueError("validation evidence fingerprint is stale")
        if release.evidence_fingerprints != (evidence.fingerprint(),):
            raise ValueError("model release evidence does not match the P21B bundle")

        protocol = bundle.protocol
        run = bundle.run
        result = bundle.result
        if (
            evidence.evidence_id != f"benchmark:{result.result_id}"
            or evidence.pack_fingerprint != protocol.pack_fingerprint
            or evidence.model_fingerprint != run.candidate_model_fingerprint
            or evidence.environment_fingerprint != run.evaluation_environment_fingerprint
            or evidence.adapter_fingerprints != run.adapter_fingerprints
            or evidence.protocol_fingerprint != protocol.fingerprint()
            or evidence.baseline_fingerprint != protocol.baseline.baseline_fingerprint
            or evidence.metric_name != protocol.primary_metric.name
            or evidence.metric_direction != protocol.primary_metric.direction
            or evidence.result_sha256 != result.fingerprint()
        ):
            raise ValueError("pre-existing evidence does not bind the P21 run/result")

        policy = registry.policy(release.policy_fingerprint)
        if (
            policy.fingerprint() != self.policy_fingerprint
            or not policy.production_promoted
            or policy.evidence_fingerprints != (evidence.fingerprint(),)
        ):
            raise ValueError("curated releases require an exact promoted P21C policy")

        scope = protocol.scope
        if (
            self.context.benchmark_scope_fingerprint != scope.fingerprint()
            or self.capability_scope_fingerprint != scope.fingerprint()
            or (
                self.context.organism,
                self.context.cell_type,
                self.context.intervention,
                self.context.endpoint,
            )
            != (scope.organism, scope.cell_type, scope.intervention, scope.endpoint)
        ):
            raise ValueError("Virtual Cell context does not match the benchmark scope")
        if (
            pack_registration.fingerprint() != run.factory_registration_fingerprint
            or pack_registration.pack_fingerprint != protocol.pack_fingerprint
            or release.pack_fingerprints != (pack_registration.pack_fingerprint,)
        ):
            raise ValueError("Pack registration does not match release and benchmark identities")
        if (
            release.model_fingerprint != run.candidate_model_fingerprint
            or release.environment_fingerprint != run.evaluation_environment_fingerprint
            or release.adapter_fingerprints != run.adapter_fingerprints
            or run.artifact_fingerprint not in release.artifact_fingerprints
            or run.model_card_fingerprint != self.model_card_fingerprint
        ):
            raise ValueError("model release does not match the P20/P21 run identity")

        if tuple(item.adapter_fingerprint for item in approvals) != tuple(sorted(release.adapter_fingerprints)):
            raise ValueError("wrapper approvals must cover every adapter in canonical order")
        for approval in approvals:
            adapter = registry.adapter(approval.adapter_fingerprint)
            if (
                approval.entrypoint != adapter.implementation
                or approval.model_card_fingerprint != self.model_card_fingerprint
                or approval.reviewer_id != self.reviewer_id
                or not approval.approved
            ):
                raise ValueError("wrapper approval does not bind the adapter and reviewed code")

        expected_ood = tuple(item.fingerprint() for item in protocol.ood_policy)
        if self.ood_policy_fingerprints != expected_ood:
            raise ValueError("OOD policy fingerprints are stale")
        if self.abstain_policy_fingerprint != protocol.threshold_policy.fingerprint():
            raise ValueError("abstain policy fingerprint is stale")
        expected_dependencies = _release_dependencies(
            context=self.context,
            pack_registration=pack_registration,
            source_registry=registry,
            model_release_fingerprint=release.fingerprint(),
            benchmark_bundle=bundle,
            p21b_execution_identity_fingerprint=(self.p21b_execution_identity_fingerprint),
            wrapper_approvals=approvals,
        )
        if self.dependency_fingerprints != expected_dependencies:
            raise ValueError("release dependency closure is stale")
        return self


def build_virtual_cell_release(
    *,
    virtual_cell_id: str,
    release_version: str,
    context: VirtualCellContextV1,
    pack_registration: FactoryRegisteredPackV1,
    source_registry: ModelRegistryV2,
    benchmark_bundle: BenchmarkEvidenceBundleV1,
    p21b_execution_identity_fingerprint: str,
    wrapper_approvals: tuple[WrapperApprovalV1, ...],
    publisher_id: str,
    reviewer_id: str,
    reviewed_at: str,
    release_license: str,
    source_name: str,
    source_uri: str | None,
) -> VirtualCellReleaseV1:
    """Assemble an identity closure; this helper does not authenticate its inputs."""

    if type(context) is not VirtualCellContextV1:
        raise TypeError("context must be exact VirtualCellContextV1")
    if type(pack_registration) is not FactoryRegisteredPackV1:
        raise TypeError("pack_registration must be exact FactoryRegisteredPackV1")
    if type(source_registry) is not ModelRegistryV2:
        raise TypeError("source_registry must be exact ModelRegistryV2")
    if type(benchmark_bundle) is not BenchmarkEvidenceBundleV1:
        raise TypeError("benchmark_bundle must be exact BenchmarkEvidenceBundleV1")
    context = VirtualCellContextV1.from_dict(context.to_dict())
    pack_registration = FactoryRegisteredPackV1.from_dict(pack_registration.to_dict())
    source_registry = ModelRegistryV2.from_dict(source_registry.to_dict())
    benchmark_bundle = BenchmarkEvidenceBundleV1.from_dict(benchmark_bundle.to_dict())
    approvals = tuple(WrapperApprovalV1.from_dict(item.to_dict()) for item in wrapper_approvals)
    if len(source_registry.releases) != 1:
        raise CuratedRegistryError("source registry must contain exactly one release")
    model_release = source_registry.releases[0]
    if len(model_release.evidence_fingerprints) != 1:
        raise CuratedRegistryError("source release must have one immutable evidence record")
    evidence = source_registry.evidence(model_release.evidence_fingerprints[0])
    if model_release.policy_fingerprint is None:
        raise CuratedRegistryError("source release has no policy")
    return VirtualCellReleaseV1(
        schema_version="vc.virtual-cell-release.v1",
        virtual_cell_id=virtual_cell_id,
        release_version=release_version,
        context=context,
        pack_registration=pack_registration,
        source_registry=source_registry,
        source_registry_fingerprint=source_registry.fingerprint(),
        model_release_fingerprint=model_release.fingerprint(),
        model_card_fingerprint=benchmark_bundle.run.model_card_fingerprint,
        benchmark_bundle=benchmark_bundle,
        benchmark_bundle_fingerprint=benchmark_bundle.fingerprint(),
        p21b_execution_identity_fingerprint=p21b_execution_identity_fingerprint,
        validation_evidence_fingerprint=evidence.fingerprint(),
        policy_fingerprint=model_release.policy_fingerprint,
        wrapper_approvals=approvals,
        capability_scope_fingerprint=benchmark_bundle.protocol.scope.fingerprint(),
        ood_policy_fingerprints=tuple(item.fingerprint() for item in benchmark_bundle.protocol.ood_policy),
        abstain_policy_fingerprint=benchmark_bundle.protocol.threshold_policy.fingerprint(),
        dependency_fingerprints=_release_dependencies(
            context=context,
            pack_registration=pack_registration,
            source_registry=source_registry,
            model_release_fingerprint=model_release.fingerprint(),
            benchmark_bundle=benchmark_bundle,
            p21b_execution_identity_fingerprint=(p21b_execution_identity_fingerprint),
            wrapper_approvals=approvals,
        ),
        publisher_id=publisher_id,
        reviewer_id=reviewer_id,
        reviewed_at=reviewed_at,
        release_license=release_license,
        source_name=source_name,
        source_uri=source_uri,
    )


def compute_curated_import_fingerprint(release: VirtualCellReleaseV1) -> str:
    """Compute the exact import identity; the returned hash does not confer trust."""

    if type(release) is not VirtualCellReleaseV1:
        raise TypeError("release must be exact VirtualCellReleaseV1")
    release = VirtualCellReleaseV1.from_dict(release.to_dict())
    return _canonical_fingerprint(
        {
            "schema_version": "vc.curated-virtual-cell-import-identity.v1",
            "release_fingerprint": release.fingerprint(),
            "pack_registration_fingerprint": release.pack_registration.fingerprint(),
            "source_registry_fingerprint": release.source_registry_fingerprint,
            "benchmark_bundle_fingerprint": release.benchmark_bundle_fingerprint,
            "p21b_execution_identity_fingerprint": (release.p21b_execution_identity_fingerprint),
            "policy_fingerprint": release.policy_fingerprint,
            "wrapper_approval_fingerprints": [item.fingerprint() for item in release.wrapper_approvals],
        }
    )


class CuratedRegistryDecisionV1(_Contract):
    schema_version: Literal["vc.curated-registry-decision.v1"]
    decision_id: str
    action: Literal["approve_catalog", "quarantine", "revoke", "supersede"]
    release_fingerprint: str
    target_release_fingerprint: str | None
    curator_id: str
    recorded_at: str
    reason: str
    effect: Literal["catalog_metadata_only"]
    scientific_state_changed: Literal[False]
    policy_state_changed: Literal[False]
    assets_installed: Literal[False]
    execution_performed: Literal[False]

    @field_validator("decision_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _public_id(value, "decision_id")

    @field_validator("release_fingerprint", mode="before")
    @classmethod
    def _valid_release(cls, value):
        return _fingerprint(value, "release_fingerprint")

    @field_validator("target_release_fingerprint", mode="before")
    @classmethod
    def _valid_target(cls, value):
        return None if value is None else _fingerprint(value, "target_release_fingerprint")

    @field_validator("curator_id", "reason", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("recorded_at", mode="before")
    @classmethod
    def _valid_time(cls, value):
        return _rfc3339(value, "recorded_at")

    @model_validator(mode="after")
    def _target_matches_action(self):
        if self.action == "supersede":
            if self.target_release_fingerprint is None:
                raise ValueError("supersede requires target_release_fingerprint")
            if self.target_release_fingerprint == self.release_fingerprint:
                raise ValueError("a release cannot supersede itself")
        elif self.target_release_fingerprint is not None:
            raise ValueError("target_release_fingerprint is only valid for supersede")
        return self


class CuratedRegistryEntryV1(_Contract):
    schema_version: Literal["vc.curated-registry-entry.v1"]
    sequence: int
    previous_entry_fingerprint: str | None
    authorization_fingerprint: str
    record_fingerprint: str
    record: VirtualCellReleaseV1 | CuratedRegistryDecisionV1

    @field_validator("sequence", mode="before")
    @classmethod
    def _valid_sequence(cls, value):
        if type(value) is not int or value < 1:
            raise ValueError("sequence must be a positive integer")
        return value

    @field_validator("previous_entry_fingerprint", mode="before")
    @classmethod
    def _valid_previous(cls, value):
        return None if value is None else _fingerprint(value, "previous_entry_fingerprint")

    @field_validator("authorization_fingerprint", "record_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @model_validator(mode="after")
    def _entry_is_bound(self):
        if self.record.fingerprint() != self.record_fingerprint:
            raise ValueError("entry record fingerprint is stale")
        if (self.sequence == 1) != (self.previous_entry_fingerprint is None):
            raise ValueError("only the first entry may omit its predecessor")
        return self


class CuratedRegistryHeadV1(_Contract):
    schema_version: Literal["vc.curated-registry-head.v1"]
    entry_count: int
    last_entry_fingerprint: str | None

    @field_validator("entry_count", mode="before")
    @classmethod
    def _valid_count(cls, value):
        if type(value) is not int or value < 0:
            raise ValueError("entry_count must be a nonnegative integer")
        return value

    @field_validator("last_entry_fingerprint", mode="before")
    @classmethod
    def _valid_last(cls, value):
        return None if value is None else _fingerprint(value, "last_entry_fingerprint")

    @model_validator(mode="after")
    def _empty_state_is_consistent(self):
        if (self.entry_count == 0) != (self.last_entry_fingerprint is None):
            raise ValueError("only an empty head may omit the last entry")
        return self


class CuratedRegistryTrustV1(_Contract):
    """Operator-owned allowlist plus an externally persisted monotonic checkpoint."""

    schema_version: Literal["vc.curated-registry-trust.v1"]
    authority_id: str
    authorized_import_fingerprints: tuple[str, ...]
    authorized_decision_fingerprints: tuple[str, ...]
    checkpoint: CuratedRegistryHeadV1

    @field_validator("authority_id", mode="before")
    @classmethod
    def _valid_authority(cls, value):
        return _public_id(value, "authority_id")

    @field_validator(
        "authorized_import_fingerprints",
        "authorized_decision_fingerprints",
        mode="before",
    )
    @classmethod
    def _valid_allowlist(cls, value, info):
        values = _fingerprints(value, info.field_name, allow_empty=True)
        if values != tuple(sorted(values)):
            raise ValueError(f"{info.field_name} must use canonical order")
        return values

    @field_validator("checkpoint", mode="before")
    @classmethod
    def _valid_checkpoint(cls, value):
        if isinstance(value, CuratedRegistryHeadV1):
            value = value.to_dict()
        return CuratedRegistryHeadV1.from_dict(value)

    @classmethod
    def deny_all(cls) -> CuratedRegistryTrustV1:
        return cls(
            schema_version="vc.curated-registry-trust.v1",
            authority_id="deny-all",
            authorized_import_fingerprints=(),
            authorized_decision_fingerprints=(),
            checkpoint=CuratedRegistryHeadV1(
                schema_version="vc.curated-registry-head.v1",
                entry_count=0,
                last_entry_fingerprint=None,
            ),
        )

    def authorization_fingerprint(self, kind: Literal["import", "decision"], fingerprint: str) -> str:
        fingerprint = _fingerprint(fingerprint, "authorized_fingerprint")
        allowed = self.authorized_import_fingerprints if kind == "import" else self.authorized_decision_fingerprints
        if fingerprint not in allowed:
            raise CuratedRegistryError(f"configured authority does not allow this {kind}")
        return _canonical_fingerprint(
            {
                "schema_version": "vc.curated-registry-authorization-reference.v1",
                "authority_id": self.authority_id,
                "authorization_kind": kind,
                "authorized_fingerprint": fingerprint,
            }
        )


class CuratedReleaseStateV1(_Contract):
    schema_version: Literal["vc.curated-release-state.v1"]
    release_fingerprint: str
    cataloged: bool
    quarantined: bool
    revoked: bool
    superseded_by: str | None
    event_fingerprints: tuple[str, ...]

    @field_validator("release_fingerprint", mode="before")
    @classmethod
    def _valid_release(cls, value):
        return _fingerprint(value, "release_fingerprint")

    @field_validator("superseded_by", mode="before")
    @classmethod
    def _valid_superseded(cls, value):
        return None if value is None else _fingerprint(value, "superseded_by")

    @field_validator("event_fingerprints", mode="before")
    @classmethod
    def _valid_events(cls, value):
        return _fingerprints(value, "event_fingerprints", allow_empty=True)

    @model_validator(mode="after")
    def _state_is_consistent(self):
        active = int(self.cataloged) + int(self.quarantined) + int(self.revoked) + int(self.superseded_by is not None)
        if active != 1:
            raise ValueError("a curated release must have exactly one lifecycle state")
        return self


@dataclass(frozen=True)
class StoredCuratedRegistryEntry:
    entry: CuratedRegistryEntryV1
    path: Path

    @property
    def sequence(self) -> int:
        return self.entry.sequence

    @property
    def entry_fingerprint(self) -> str:
        return self.entry.fingerprint()

    @property
    def record_fingerprint(self) -> str:
        return self.entry.record_fingerprint


def _read_descriptor(descriptor: int, *, max_bytes: int) -> bytes:
    chunks = []
    remaining = max_bytes + 1
    while remaining:
        chunk = os.read(descriptor, min(65536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    payload = b"".join(chunks)
    if len(payload) > max_bytes:
        raise CuratedRegistryError("registry file exceeds its byte ceiling")
    return payload


def _read_regular_at(
    parent_descriptor: int,
    name: str,
    *,
    label: str,
    max_bytes: int = _MAX_FILE_BYTES,
) -> bytes:
    if not isinstance(name, str) or not name or "/" in name or "\x00" in name:
        raise CuratedRegistryError(f"{label} name is not a safe basename")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise CuratedRegistryError(f"cannot read {label} safely") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
            raise CuratedRegistryError(f"{label} must be a bounded regular file")
        payload = _read_descriptor(descriptor, max_bytes=max_bytes)
        after = os.fstat(descriptor)
        try:
            named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        except OSError as exc:
            raise CuratedRegistryError(f"{label} pathname changed while being read") from exc
        if (
            len(payload) != before.st_size
            or (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
            or (
                named.st_dev,
                named.st_ino,
                named.st_size,
                named.st_mtime_ns,
                named.st_ctime_ns,
            )
            != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
        ):
            raise CuratedRegistryError(f"{label} changed while being read")
        if not stat.S_ISREG(named.st_mode):
            raise CuratedRegistryError(f"{label} pathname is no longer regular")
        return payload
    finally:
        os.close(descriptor)


def _atomic_publish_directory(
    source: Path,
    target: Path,
    *,
    parent_descriptor: int,
    source_descriptor: int,
    source_identity: tuple[int, int],
) -> None:
    held = os.fstat(source_descriptor)
    try:
        named = os.stat(source.name, dir_fd=parent_descriptor, follow_symlinks=False)
    except OSError as exc:
        raise CuratedRegistryError("registry staging directory is unavailable") from exc
    if (
        source.parent != target.parent
        or not stat.S_ISDIR(held.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or (held.st_dev, held.st_ino) != source_identity
        or (named.st_dev, named.st_ino) != source_identity
    ):
        raise CuratedRegistryError("registry staging directory identity changed")
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        operation = getattr(libc, "renameatx_np", None)
        if operation is None:  # pragma: no cover
            raise CuratedRegistryError("atomic no-replace registry creation is unavailable")
        operation.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        operation.restype = ctypes.c_int
        result = operation(
            parent_descriptor,
            os.fsencode(source.name),
            parent_descriptor,
            os.fsencode(target.name),
            0x00000004,
        )
    elif sys.platform.startswith("linux"):
        operation = getattr(libc, "renameat2", None)
        if operation is None:  # pragma: no cover
            raise CuratedRegistryError("atomic no-replace registry creation is unavailable")
        operation.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        operation.restype = ctypes.c_int
        result = operation(
            parent_descriptor,
            os.fsencode(source.name),
            parent_descriptor,
            os.fsencode(target.name),
            1,
        )
    else:  # pragma: no cover
        raise CuratedRegistryError("atomic no-replace registry creation is unavailable")
    if result == 0:
        published = os.stat(target.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISDIR(published.st_mode)
            or (
                published.st_dev,
                published.st_ino,
            )
            != source_identity
        ):
            raise CuratedRegistryError("published registry root identity changed")
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise CuratedRegistryError("registry root must be write-new")
    raise CuratedRegistryError("atomic registry creation failed") from OSError(error, os.strerror(error))


def _apply_decision(
    states: dict[str, CuratedReleaseStateV1],
    releases: dict[str, VirtualCellReleaseV1],
    decision: CuratedRegistryDecisionV1,
) -> None:
    try:
        current = states[decision.release_fingerprint]
        release = releases[decision.release_fingerprint]
    except KeyError as exc:
        raise CuratedRegistryError("decision references an unknown release") from exc
    if current.revoked or current.superseded_by is not None:
        raise CuratedRegistryError("closed releases cannot accept later decisions")
    events = (*current.event_fingerprints, decision.fingerprint())
    if decision.action == "approve_catalog":
        if not current.quarantined:
            raise CuratedRegistryError("approval requires a quarantined release")
        state = CuratedReleaseStateV1(
            schema_version="vc.curated-release-state.v1",
            release_fingerprint=decision.release_fingerprint,
            cataloged=True,
            quarantined=False,
            revoked=False,
            superseded_by=None,
            event_fingerprints=events,
        )
    elif decision.action == "quarantine":
        if current.quarantined:
            raise CuratedRegistryError("release is already quarantined")
        state = CuratedReleaseStateV1(
            schema_version="vc.curated-release-state.v1",
            release_fingerprint=decision.release_fingerprint,
            cataloged=False,
            quarantined=True,
            revoked=False,
            superseded_by=None,
            event_fingerprints=events,
        )
    elif decision.action == "revoke":
        state = CuratedReleaseStateV1(
            schema_version="vc.curated-release-state.v1",
            release_fingerprint=decision.release_fingerprint,
            cataloged=False,
            quarantined=False,
            revoked=True,
            superseded_by=None,
            event_fingerprints=events,
        )
    else:
        assert decision.target_release_fingerprint is not None
        try:
            target = releases[decision.target_release_fingerprint]
            target_state = states[decision.target_release_fingerprint]
        except KeyError as exc:
            raise CuratedRegistryError("supersession target is unknown") from exc
        if (
            not current.cataloged
            or not target_state.cataloged
            or release.virtual_cell_id != target.virtual_cell_id
            or release.release_version == target.release_version
        ):
            raise CuratedRegistryError("supersession requires an active different version of the same Virtual Cell")
        state = CuratedReleaseStateV1(
            schema_version="vc.curated-release-state.v1",
            release_fingerprint=decision.release_fingerprint,
            cataloged=False,
            quarantined=False,
            revoked=False,
            superseded_by=decision.target_release_fingerprint,
            event_fingerprints=events,
        )
    states[decision.release_fingerprint] = state


def _authorization_subject(
    record: VirtualCellReleaseV1 | CuratedRegistryDecisionV1,
) -> tuple[Literal["import", "decision"], str]:
    if type(record) is VirtualCellReleaseV1:
        return "import", compute_curated_import_fingerprint(record)
    if type(record) is CuratedRegistryDecisionV1:
        return "decision", record.fingerprint()
    raise CuratedRegistryError("registry contains an unsupported authorization subject")


def _validate_log(
    stored: tuple[StoredCuratedRegistryEntry, ...],
) -> tuple[dict[str, VirtualCellReleaseV1], dict[str, CuratedReleaseStateV1]]:
    releases: dict[str, VirtualCellReleaseV1] = {}
    states: dict[str, CuratedReleaseStateV1] = {}
    logical_keys: dict[tuple[str, str], str] = {}
    decision_ids: dict[str, str] = {}
    record_fingerprints: set[str] = set()
    previous = None
    for sequence, item in enumerate(stored, start=1):
        entry = item.entry
        if entry.sequence != sequence or entry.previous_entry_fingerprint != previous:
            raise CuratedRegistryError("registry sequence or predecessor chain is broken")
        if entry.record_fingerprint in record_fingerprints:
            raise CuratedRegistryError("registry contains a duplicate record")
        record = entry.record
        if type(record) is VirtualCellReleaseV1:
            release = VirtualCellReleaseV1.from_dict(record.to_dict())
            fingerprint = release.fingerprint()
            key = (release.virtual_cell_id, release.release_version)
            if fingerprint in releases:
                raise CuratedRegistryError("registry contains a duplicate release")
            prior = logical_keys.get(key)
            if prior is not None and prior != fingerprint:
                raise CuratedRegistryError("Virtual Cell ID/version binds conflicting bytes")
            logical_keys[key] = fingerprint
            releases[fingerprint] = release
            states[fingerprint] = CuratedReleaseStateV1(
                schema_version="vc.curated-release-state.v1",
                release_fingerprint=fingerprint,
                cataloged=False,
                quarantined=True,
                revoked=False,
                superseded_by=None,
                event_fingerprints=(entry.record_fingerprint,),
            )
        elif type(record) is CuratedRegistryDecisionV1:
            decision = CuratedRegistryDecisionV1.from_dict(record.to_dict())
            prior = decision_ids.get(decision.decision_id)
            if prior is not None and prior != decision.fingerprint():
                raise CuratedRegistryError("decision ID binds conflicting bytes")
            if prior is not None:
                raise CuratedRegistryError("registry contains a duplicate decision")
            decision_ids[decision.decision_id] = decision.fingerprint()
            _apply_decision(states, releases, decision)
        else:  # pragma: no cover - union validation already rejects this
            raise CuratedRegistryError("registry contains an unsupported record")
        record_fingerprints.add(entry.record_fingerprint)
        previous = entry.fingerprint()
    return releases, states


class CuratedVirtualCellRegistry:
    """Write-new, append-only local registry for pre-existing release truth."""

    def __init__(
        self,
        root: Path,
        *,
        trust: CuratedRegistryTrustV1 | None = None,
    ) -> None:
        if not isinstance(root, Path) or not root.is_absolute() or root.is_symlink():
            raise CuratedRegistryError("registry root must be an explicit non-symlink Path")
        if trust is None:
            trust = CuratedRegistryTrustV1.deny_all()
        if type(trust) is not CuratedRegistryTrustV1:
            raise TypeError("trust must be exact CuratedRegistryTrustV1")
        self._trust = CuratedRegistryTrustV1.from_dict(trust.to_dict())
        try:
            resolved = root.resolve(strict=True)
            root_stat = root.stat()
            entries = root / "entries"
            entries_stat = entries.stat()
            lock_stat = (root / _LOCK).stat()
        except OSError as exc:
            raise CuratedRegistryError("registry layout is unavailable") from exc
        if resolved != root or not stat.S_ISDIR(root_stat.st_mode):
            raise CuratedRegistryError("registry root must be a canonical directory")
        if entries.is_symlink() or not stat.S_ISDIR(entries_stat.st_mode):
            raise CuratedRegistryError("registry entries must be a real directory")
        if entries.resolve(strict=True).parent != root:
            raise CuratedRegistryError("registry entries escape their root")
        if (root / _LOCK).is_symlink() or not stat.S_ISREG(lock_stat.st_mode):
            raise CuratedRegistryError("registry lock must be a regular non-symlink file")
        self.root = root
        self._root_identity = (root_stat.st_dev, root_stat.st_ino)
        self._entries_identity = (entries_stat.st_dev, entries_stat.st_ino)
        self._lock_identity = (lock_stat.st_dev, lock_stat.st_ino)
        with self._held_layout() as (root_descriptor, _entries_descriptor):
            if _read_regular_at(root_descriptor, _MARKER, label="registry marker") != _MARKER_BYTES:
                raise CuratedRegistryError("registry marker is invalid")
            self._load_head_at(root_descriptor)

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        trust: CuratedRegistryTrustV1 | None = None,
    ) -> CuratedVirtualCellRegistry:
        if trust is not None and type(trust) is not CuratedRegistryTrustV1:
            raise TypeError("trust must be exact CuratedRegistryTrustV1")
        if trust is not None and trust.checkpoint.entry_count:
            raise CuratedRegistryError("a write-new registry cannot start from a non-empty checkpoint")
        path = Path(root)
        if not path.is_absolute():
            raise CuratedRegistryError("registry root must be an explicit absolute path")
        parent = path.parent
        try:
            if (
                parent.is_symlink()
                or parent.resolve(strict=True) != parent
                or not parent.is_dir()
                or path.resolve(strict=False) != path
                or path.exists()
                or path.is_symlink()
            ):
                raise CuratedRegistryError("registry requires a canonical write-new root")
        except CuratedRegistryError:
            raise
        except OSError as exc:
            raise CuratedRegistryError("registry parent is unavailable") from exc
        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            directory_flags |= os.O_NOFOLLOW
        try:
            parent_descriptor = os.open(parent, directory_flags)
        except OSError as exc:
            raise CuratedRegistryError("registry parent cannot be held safely") from exc
        staging_descriptor = None
        staging_identity = None
        try:
            staging = Path(tempfile.mkdtemp(prefix=f".{path.name}.curated-registry-", dir=parent))
            os.chmod(staging, 0o700)
            created = staging.lstat()
            staging_identity = (created.st_dev, created.st_ino)
            staging_descriptor = os.open(staging, directory_flags)
            held = os.fstat(staging_descriptor)
            named = os.stat(staging.name, dir_fd=parent_descriptor, follow_symlinks=False)
            if (
                not stat.S_ISDIR(created.st_mode)
                or (held.st_dev, held.st_ino) != staging_identity
                or (named.st_dev, named.st_ino) != staging_identity
            ):
                raise CuratedRegistryError("registry staging identity is unstable")
            os.mkdir("entries", mode=0o700, dir_fd=staging_descriptor)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            for name, payload in (
                (_MARKER, _MARKER_BYTES),
                (
                    _HEAD,
                    _canonical_bytes(
                        CuratedRegistryHeadV1(
                            schema_version="vc.curated-registry-head.v1",
                            entry_count=0,
                            last_entry_fingerprint=None,
                        ).to_dict()
                    )
                    + b"\n",
                ),
                (_LOCK, b""),
            ):
                descriptor = os.open(name, flags, 0o600, dir_fd=staging_descriptor)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
            entries_descriptor = os.open("entries", directory_flags, dir_fd=staging_descriptor)
            try:
                os.fsync(entries_descriptor)
            finally:
                os.close(entries_descriptor)
            os.fsync(staging_descriptor)
            os.fsync(parent_descriptor)
            _atomic_publish_directory(
                staging,
                path,
                parent_descriptor=parent_descriptor,
                source_descriptor=staging_descriptor,
                source_identity=staging_identity,
            )
            os.fsync(parent_descriptor)
        except CuratedRegistryError:
            raise
        except OSError as exc:
            raise CuratedRegistryError("cannot initialize curated registry") from exc
        finally:
            if staging_descriptor is not None:
                os.close(staging_descriptor)
            os.close(parent_descriptor)
        registry = cls(path.resolve(strict=True), trust=trust)
        if staging_identity is None or registry._root_identity != staging_identity:
            raise CuratedRegistryError("published registry root identity changed")
        return registry

    @classmethod
    def open(
        cls,
        root: str | Path,
        *,
        trust: CuratedRegistryTrustV1 | None = None,
    ) -> CuratedVirtualCellRegistry:
        path = Path(root)
        if not path.is_absolute() or path.is_symlink():
            raise CuratedRegistryError("registry root must be an absolute non-symlink path")
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise CuratedRegistryError("registry root does not exist") from exc
        return cls(resolved, trust=trust)

    @property
    def _entries(self) -> Path:
        return self.root / "entries"

    @contextmanager
    def _held_layout(self):
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            root_descriptor = os.open(self.root, flags)
        except OSError as exc:
            raise CuratedRegistryError("registry root cannot be held safely") from exc
        entries_descriptor = None
        try:
            root_stat = os.fstat(root_descriptor)
            if (root_stat.st_dev, root_stat.st_ino) != self._root_identity:
                raise CuratedRegistryError("registry root identity changed")
            entries_descriptor = os.open("entries", flags, dir_fd=root_descriptor)
            entries_stat = os.fstat(entries_descriptor)
            if (entries_stat.st_dev, entries_stat.st_ino) != self._entries_identity:
                raise CuratedRegistryError("registry entries identity changed")
            if _read_regular_at(root_descriptor, _MARKER, label="registry marker") != _MARKER_BYTES:
                raise CuratedRegistryError("registry marker changed")
            yield root_descriptor, entries_descriptor
        finally:
            if entries_descriptor is not None:
                os.close(entries_descriptor)
            os.close(root_descriptor)

    @contextmanager
    def _held_lock(self, root_descriptor: int, *, exclusive: bool):
        flags = os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(_LOCK, flags, dir_fd=root_descriptor)
        except OSError as exc:
            raise CuratedRegistryError("registry lock is unavailable") from exc
        try:
            held = os.fstat(descriptor)
            if (
                not stat.S_ISREG(held.st_mode)
                or (
                    held.st_dev,
                    held.st_ino,
                )
                != self._lock_identity
            ):
                raise CuratedRegistryError("registry lock identity changed")
            fcntl.flock(
                descriptor,
                fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH,
            )
            try:
                named = os.stat(_LOCK, dir_fd=root_descriptor, follow_symlinks=False)
            except OSError as exc:
                raise CuratedRegistryError("registry lock pathname changed") from exc
            if (
                not stat.S_ISREG(named.st_mode)
                or (
                    named.st_dev,
                    named.st_ino,
                )
                != self._lock_identity
            ):
                raise CuratedRegistryError("registry lock identity changed")
            yield
        finally:
            os.close(descriptor)

    def _load_head_at(self, root_descriptor: int) -> CuratedRegistryHeadV1:
        payload = _read_regular_at(root_descriptor, _HEAD, label="registry head")
        head = CuratedRegistryHeadV1.from_dict(_json_object_bytes(payload, "registry head"))
        if payload != _canonical_bytes(head.to_dict()) + b"\n":
            raise CuratedRegistryError("registry head is not canonical")
        return head

    def _write_head_at(
        self,
        root_descriptor: int,
        head: CuratedRegistryHeadV1,
    ) -> None:
        head = CuratedRegistryHeadV1.from_dict(head.to_dict())
        payload = _canonical_bytes(head.to_dict()) + b"\n"
        temporary_name = f".head-staging-{os.urandom(16).hex()}.tmp"
        if not _HEAD_STAGING_NAME.fullmatch(temporary_name):  # pragma: no cover
            raise CuratedRegistryError("registry head staging name is invalid")
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = None
        try:
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=root_descriptor)
            with os.fdopen(os.dup(descriptor), "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            held = os.fstat(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            if _read_descriptor(descriptor, max_bytes=_MAX_FILE_BYTES) != payload:
                raise CuratedRegistryError("staged registry head changed")
            named = os.stat(temporary_name, dir_fd=root_descriptor, follow_symlinks=False)
            if not stat.S_ISREG(held.st_mode) or (
                named.st_dev,
                named.st_ino,
                named.st_size,
            ) != (held.st_dev, held.st_ino, held.st_size):
                raise CuratedRegistryError("staged registry head identity changed")
            os.replace(
                temporary_name,
                _HEAD,
                src_dir_fd=root_descriptor,
                dst_dir_fd=root_descriptor,
            )
            if self._load_head_at(root_descriptor) != head:
                raise CuratedRegistryError("published registry head changed")
            os.fsync(root_descriptor)
        except CuratedRegistryError:
            raise
        except OSError as exc:
            raise CuratedRegistryError("cannot update registry head") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(temporary_name, dir_fd=root_descriptor)
            except FileNotFoundError:
                pass

    def _load_entry_at(
        self,
        entries_descriptor: int,
        name: str,
    ) -> StoredCuratedRegistryEntry:
        payload = _read_regular_at(entries_descriptor, name, label="registry entry")
        entry = CuratedRegistryEntryV1.from_dict(_json_object_bytes(payload, "registry entry"))
        if payload != _canonical_bytes(entry.to_dict()) + b"\n":
            raise CuratedRegistryError("registry entry bytes are not canonical")
        expected = f"{entry.sequence:08d}-{entry.fingerprint()}.json"
        if name != expected:
            raise CuratedRegistryError("registry entry filename and content disagree")
        return StoredCuratedRegistryEntry(entry=entry, path=self._entries / name)

    def _verify_held(
        self,
        root_descriptor: int,
        entries_descriptor: int,
        *,
        recover_unanchored_record_fingerprint: str | None = None,
        recover_unanchored_authorization_fingerprint: str | None = None,
    ) -> tuple[StoredCuratedRegistryEntry, ...]:
        names = []
        for name in os.listdir(entries_descriptor):
            metadata = os.stat(name, dir_fd=entries_descriptor, follow_symlinks=False)
            if name.startswith(".staging-"):
                if not _STAGING_NAME.fullmatch(name) or not stat.S_ISREG(metadata.st_mode):
                    raise CuratedRegistryError("registry contains an invalid staging path")
                continue
            if not name.endswith(".json") or not stat.S_ISREG(metadata.st_mode):
                raise CuratedRegistryError("registry entries contain an unexpected path")
            names.append(name)
        stored = tuple(self._load_entry_at(entries_descriptor, name) for name in sorted(names))
        _validate_log(stored)
        checkpoint = self._trust.checkpoint
        if checkpoint.entry_count and (
            len(stored) < checkpoint.entry_count
            or stored[checkpoint.entry_count - 1].entry_fingerprint != checkpoint.last_entry_fingerprint
        ):
            raise CuratedRegistryError("registry violates the trusted monotonic checkpoint")
        for item in stored[checkpoint.entry_count :]:
            kind, fingerprint = _authorization_subject(item.entry.record)
            expected_authorization = self._trust.authorization_fingerprint(
                kind,
                fingerprint,
            )
            if item.entry.authorization_fingerprint != expected_authorization:
                raise CuratedRegistryError(
                    "registry entry authorization provenance does not match the configured authority"
                )
        head = self._load_head_at(root_descriptor)
        tail = stored[-1].entry_fingerprint if stored else None
        if head.entry_count != len(stored) or head.last_entry_fingerprint != tail:
            prior_tail = stored[-2].entry_fingerprint if len(stored) > 1 else None
            if not (
                recover_unanchored_record_fingerprint is not None
                and head.entry_count == len(stored) - 1
                and head.last_entry_fingerprint == prior_tail
                and stored[-1].record_fingerprint == recover_unanchored_record_fingerprint
                and stored[-1].entry.authorization_fingerprint == recover_unanchored_authorization_fingerprint
            ):
                raise CuratedRegistryError("registry head detects truncation or an unanchored tail")
            try:
                os.fsync(entries_descriptor)
            except OSError as exc:
                raise CuratedRegistryError("cannot make the recoverable registry tail durable") from exc
            self._write_head_at(
                root_descriptor,
                CuratedRegistryHeadV1(
                    schema_version="vc.curated-registry-head.v1",
                    entry_count=len(stored),
                    last_entry_fingerprint=tail,
                ),
            )
        return stored

    def verify(self) -> tuple[StoredCuratedRegistryEntry, ...]:
        with self._held_layout() as (root_descriptor, entries_descriptor):
            with self._held_lock(root_descriptor, exclusive=False):
                return self._verify_held(root_descriptor, entries_descriptor)

    def checkpoint(self) -> CuratedRegistryHeadV1:
        """Return the verified tail for persistence in an independent trust domain."""

        stored = self.verify()
        return CuratedRegistryHeadV1(
            schema_version="vc.curated-registry-head.v1",
            entry_count=len(stored),
            last_entry_fingerprint=(stored[-1].entry_fingerprint if stored else None),
        )

    def _append(
        self,
        record: VirtualCellReleaseV1 | CuratedRegistryDecisionV1,
        *,
        authorization_fingerprint: str,
    ) -> StoredCuratedRegistryEntry:
        if type(record) is VirtualCellReleaseV1:
            record = VirtualCellReleaseV1.from_dict(record.to_dict())
        elif type(record) is CuratedRegistryDecisionV1:
            record = CuratedRegistryDecisionV1.from_dict(record.to_dict())
        else:
            raise TypeError("record must be an exact release or curator decision")
        fingerprint = record.fingerprint()
        authorization_fingerprint = _fingerprint(
            authorization_fingerprint,
            "authorization_fingerprint",
        )
        with self._held_layout() as (root_descriptor, entries_descriptor):
            with self._held_lock(root_descriptor, exclusive=True):
                stored = self._verify_held(
                    root_descriptor,
                    entries_descriptor,
                    recover_unanchored_record_fingerprint=fingerprint,
                    recover_unanchored_authorization_fingerprint=(authorization_fingerprint),
                )
                for item in stored:
                    existing = item.entry.record
                    if item.record_fingerprint == fingerprint:
                        return item
                    if type(record) is VirtualCellReleaseV1 and type(existing) is VirtualCellReleaseV1:
                        if (
                            existing.virtual_cell_id,
                            existing.release_version,
                        ) == (record.virtual_cell_id, record.release_version):
                            raise CuratedRegistryError("Virtual Cell ID/version already binds different bytes")
                    if type(record) is CuratedRegistryDecisionV1 and type(existing) is CuratedRegistryDecisionV1:
                        if existing.decision_id == record.decision_id:
                            raise CuratedRegistryError("curator decision ID already binds different bytes")
                previous = stored[-1].entry_fingerprint if stored else None
                entry = CuratedRegistryEntryV1(
                    schema_version="vc.curated-registry-entry.v1",
                    sequence=len(stored) + 1,
                    previous_entry_fingerprint=previous,
                    authorization_fingerprint=authorization_fingerprint,
                    record_fingerprint=fingerprint,
                    record=record,
                )
                candidate = (
                    *stored,
                    StoredCuratedRegistryEntry(entry=entry, path=Path("<staged>")),
                )
                _validate_log(candidate)
                payload = _canonical_bytes(entry.to_dict()) + b"\n"
                target_name = f"{entry.sequence:08d}-{entry.fingerprint()}.json"
                temporary_name = f".staging-{os.urandom(16).hex()}.tmp"
                temporary_flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
                if hasattr(os, "O_NOFOLLOW"):
                    temporary_flags |= os.O_NOFOLLOW
                temporary_descriptor = None
                try:
                    temporary_descriptor = os.open(
                        temporary_name,
                        temporary_flags,
                        0o600,
                        dir_fd=entries_descriptor,
                    )
                    with os.fdopen(os.dup(temporary_descriptor), "wb") as stream:
                        stream.write(payload)
                        stream.flush()
                        os.fsync(stream.fileno())
                    held = os.fstat(temporary_descriptor)
                    os.lseek(temporary_descriptor, 0, os.SEEK_SET)
                    if _read_descriptor(temporary_descriptor, max_bytes=_MAX_FILE_BYTES) != payload:
                        raise CuratedRegistryError("staged registry entry changed")
                    named = os.stat(
                        temporary_name,
                        dir_fd=entries_descriptor,
                        follow_symlinks=False,
                    )
                    if not stat.S_ISREG(held.st_mode) or (
                        named.st_dev,
                        named.st_ino,
                        named.st_size,
                    ) != (held.st_dev, held.st_ino, held.st_size):
                        raise CuratedRegistryError("staged registry entry identity changed")
                    try:
                        os.link(
                            temporary_name,
                            target_name,
                            src_dir_fd=entries_descriptor,
                            dst_dir_fd=entries_descriptor,
                            follow_symlinks=False,
                        )
                    except FileExistsError as exc:
                        raise CuratedRegistryError("registry destination collision was not overwritten") from exc
                    except OSError as exc:
                        raise CuratedRegistryError("cannot append curated registry entry") from exc
                    published = os.stat(
                        target_name,
                        dir_fd=entries_descriptor,
                        follow_symlinks=False,
                    )
                    if not stat.S_ISREG(published.st_mode) or (
                        published.st_dev,
                        published.st_ino,
                        published.st_size,
                    ) != (held.st_dev, held.st_ino, held.st_size):
                        raise CuratedRegistryError("published registry entry changed")
                    try:
                        os.fsync(entries_descriptor)
                    except OSError as exc:
                        raise CuratedRegistryError(
                            "registry entry committed but directory durability is uncertain"
                        ) from exc
                    self._write_head_at(
                        root_descriptor,
                        CuratedRegistryHeadV1(
                            schema_version="vc.curated-registry-head.v1",
                            entry_count=entry.sequence,
                            last_entry_fingerprint=entry.fingerprint(),
                        ),
                    )
                finally:
                    if temporary_descriptor is not None:
                        os.close(temporary_descriptor)
                    try:
                        os.unlink(temporary_name, dir_fd=entries_descriptor)
                    except FileNotFoundError:
                        pass
                loaded = self._load_entry_at(entries_descriptor, target_name)
                if loaded.entry_fingerprint != entry.fingerprint():
                    raise CuratedRegistryError("published registry entry identity changed")
                return loaded

    def import_release(
        self,
        release: VirtualCellReleaseV1,
    ) -> StoredCuratedRegistryEntry:
        """Import one closure present in the configured operator-owned allowlist."""

        if type(release) is not VirtualCellReleaseV1:
            raise TypeError("release must be exact VirtualCellReleaseV1")
        release = VirtualCellReleaseV1.from_dict(release.to_dict())
        authorization_fingerprint = self._trust.authorization_fingerprint(
            "import",
            compute_curated_import_fingerprint(release),
        )
        return self._append(
            release,
            authorization_fingerprint=authorization_fingerprint,
        )

    def record_decision(
        self,
        decision: CuratedRegistryDecisionV1,
    ) -> StoredCuratedRegistryEntry:
        """Append a catalog-only decision present in the configured allowlist."""

        if type(decision) is not CuratedRegistryDecisionV1:
            raise TypeError("decision must be exact CuratedRegistryDecisionV1")
        decision = CuratedRegistryDecisionV1.from_dict(decision.to_dict())
        authorization_fingerprint = self._trust.authorization_fingerprint(
            "decision",
            decision.fingerprint(),
        )
        return self._append(
            decision,
            authorization_fingerprint=authorization_fingerprint,
        )

    def _release_maps(
        self,
    ) -> tuple[dict[str, VirtualCellReleaseV1], dict[str, CuratedReleaseStateV1]]:
        return _validate_log(self.verify())

    def release(self, release_fingerprint: str) -> VirtualCellReleaseV1:
        release_fingerprint = _fingerprint(release_fingerprint, "release_fingerprint")
        releases, _states = self._release_maps()
        try:
            return releases[release_fingerprint]
        except KeyError as exc:
            raise KeyError(f"unknown Virtual Cell release: {release_fingerprint}") from exc

    def state(self, release_fingerprint: str) -> CuratedReleaseStateV1:
        release_fingerprint = _fingerprint(release_fingerprint, "release_fingerprint")
        _releases, states = self._release_maps()
        try:
            return states[release_fingerprint]
        except KeyError as exc:
            raise KeyError(f"unknown Virtual Cell release: {release_fingerprint}") from exc

    @staticmethod
    def _public_release(
        release: VirtualCellReleaseV1,
        state: CuratedReleaseStateV1,
    ) -> dict[str, Any]:
        model_release = release.source_registry.release(release.model_release_fingerprint)
        evidence = release.source_registry.evidence(release.validation_evidence_fingerprint)
        policy = release.source_registry.policy(release.policy_fingerprint)
        return {
            "virtual_cell_id": release.virtual_cell_id,
            "release_version": release.release_version,
            "release_fingerprint": release.fingerprint(),
            "context_id": release.context.context_id,
            "context_fingerprint": release.context.fingerprint(),
            "organism": release.context.organism,
            "cell_type": release.context.cell_type,
            "intervention": release.context.intervention,
            "endpoint": release.context.endpoint,
            "capability_scope_fingerprint": release.capability_scope_fingerprint,
            "pack_id": release.pack_registration.pack_id,
            "pack_version": release.pack_registration.pack_version,
            "pack_fingerprint": release.pack_registration.pack_fingerprint,
            "model_release_fingerprint": release.model_release_fingerprint,
            "model_fingerprint": model_release.model_fingerprint,
            "environment_fingerprint": model_release.environment_fingerprint,
            "adapter_fingerprints": list(model_release.adapter_fingerprints),
            "validation_evidence_fingerprint": release.validation_evidence_fingerprint,
            "policy_fingerprint": release.policy_fingerprint,
            "ood_policy_fingerprints": list(release.ood_policy_fingerprints),
            "abstain_policy_fingerprint": release.abstain_policy_fingerprint,
            "cataloged": state.cataloged,
            "quarantined": state.quarantined,
            "revoked": state.revoked,
            "superseded_by": state.superseded_by,
            "installed": None,
            "model_compatible": None,
            "environment_compatible": None,
            "adapter_compatible": None,
            "benchmark_passed": evidence.benchmark_passed,
            "scientifically_validated": evidence.scientifically_validated,
            "promotion_eligible": evidence.promotion_eligible,
            "production_promoted": policy.production_promoted,
            "executable": False,
        }

    def public_catalog(self, *, include_inactive: bool = False) -> dict[str, Any]:
        stored = self.verify()
        releases, states = _validate_log(stored)
        public = [
            self._public_release(release, states[fingerprint])
            for fingerprint, release in releases.items()
            if include_inactive or states[fingerprint].cataloged
        ]
        return {
            "schema_version": "vc.curated-virtual-cell-catalog.v1",
            "registry_fingerprint": _canonical_fingerprint([item.entry.to_dict() for item in stored]),
            "revocation_checkpointed": (
                bool(stored)
                and self._trust.checkpoint.entry_count == len(stored)
                and self._trust.checkpoint.last_entry_fingerprint == stored[-1].entry_fingerprint
            ),
            "write_api_enabled": False,
            "releases": sorted(
                public,
                key=lambda item: (
                    item["virtual_cell_id"],
                    item["release_version"],
                ),
            ),
        }

    def query(
        self,
        *,
        virtual_cell_id: str | None = None,
        organism: str | None = None,
        cell_type: str | None = None,
        include_inactive: bool = False,
    ) -> tuple[dict[str, Any], ...]:
        if virtual_cell_id is not None:
            virtual_cell_id = _public_id(virtual_cell_id, "virtual_cell_id")
        if organism is not None:
            organism = _text(organism, "organism")
        if cell_type is not None:
            cell_type = _text(cell_type, "cell_type")
        values = self.public_catalog(include_inactive=include_inactive)["releases"]
        return tuple(
            item
            for item in values
            if (virtual_cell_id is None or item["virtual_cell_id"] == virtual_cell_id)
            and (organism is None or item["organism"] == organism)
            and (cell_type is None or item["cell_type"] == cell_type)
        )

    def dependency_graph(self, release_fingerprint: str) -> dict[str, Any]:
        release = self.release(release_fingerprint)
        return {
            "schema_version": "vc.curated-release-dependency-graph.v1",
            "release_fingerprint": release.fingerprint(),
            "dependencies": list(release.dependency_fingerprints),
        }
