"""Capture the mutable governance inputs consumed by one MDR execution.

The model catalog SHA-locks executable artifacts.  Fusion evidence, AMRFinder
rule baselines, and species brains are a separate mutable control plane.  A
plain digest alone is not enough: the files could change between hashing and a
later read.  ``GovernanceExecutionContext`` therefore reads each source once,
derives its public snapshot from those bytes, and retains only parsed private
documents for the rest of that execution.

Only the public source identity is written to cache, trace, report, or
persistence.  Parsed rule/evidence/brain contents never become a new public
API field merely because they were captured here.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from praxis_virtualcell.mdr_gnb.agents.brain_loader import load_species_brain_documents
from praxis_virtualcell.mdr_gnb.coordinator.fusion import evidence_tiers_from_document

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_SCHEMA_VERSION = "mdr-governance-snapshot-v2"

_BRAIN_SPECIES = (
    "acinetobacter_baumannii",
    "enterobacter_cloacae",
    "escherichia_coli",
    "klebsiella_pneumoniae",
    "morganella_morganii",
    "proteus_mirabilis",
    "pseudomonas_aeruginosa",
    "salmonella_enterica",
    "serratia_marcescens",
    "stenotrophomonas_maltophilia",
)
_BRAIN_OVERLAY_KEYS = (
    "resistance_mechanisms",
    "negative_cases",
    "assay_boundaries",
    "species_specific_breakpoints",
)


@dataclass(frozen=True)
class GovernanceExecutionContext:
    """Private parsed governance inputs paired with a public content snapshot.

    The mappings are only for the in-process execution.  Callers must publish
    ``snapshot`` (not these documents) when recording cache/trace/report/DB
    provenance.  Accessors return defensive copies so one pipeline stage cannot
    alter another stage's captured inputs.
    """

    snapshot: dict[str, Any]
    evidence_tiers: dict[tuple[str, str], dict[str, Any]]
    amrfinder_rules_document: dict[str, Any] | None
    brains: dict[str, dict[str, Any]]
    brain_available: dict[str, bool]
    brain_references: dict[str, tuple[str, ...]]

    def brain_for_species(self, species: str) -> dict[str, Any]:
        return deepcopy(self.brains.get(species, load_species_brain_documents(None)))

    def rule_document(self) -> dict[str, Any] | None:
        return (deepcopy(self.amrfinder_rules_document)
                if self.amrfinder_rules_document is not None else None)

    def evidence_for(self, species: str, drug: str) -> dict[str, Any] | None:
        entry = self.evidence_tiers.get((species, drug))
        return deepcopy(entry) if entry is not None else None


def sha256_file(path: Path) -> str:
    """Return an exact digest without loading a mutable governance file as text."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_governance_source_paths() -> dict[str, Path]:
    """Return every production governance source, including future overlays.

    An absent overlay is deliberately recorded as ``present: false``.  Creating
    it later then changes the execution identity *and* makes it available to
    the captured brain instead of silently bypassing the snapshot.
    """
    paths: dict[str, Path] = {
        "evidence_tiers": REPO_ROOT / "praxis_virtualcell/model_zoo/evidence_tiers.yaml",
        "amrfinder_sir_rules": (
            REPO_ROOT / "praxis_virtualcell/mdr_gnb/predictors/rules/amrfinder_sir_rules.yaml"
        ),
    }
    for species in _BRAIN_SPECIES:
        brain_dir = REPO_ROOT / "praxis_virtualcell/mdr_gnb/agents" / species / "brain"
        paths[f"brain/{species}/rules"] = brain_dir / "rules.yaml"
        for key in _BRAIN_OVERLAY_KEYS:
            paths[f"brain/{species}/{key}"] = brain_dir / f"{key}.yaml"
    return dict(sorted(paths.items()))


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def build_governance_execution_context(
    source_paths: Mapping[str, Path] | None = None,
) -> GovernanceExecutionContext:
    """Read governance inputs once and return their execution-scoped context.

    ``source_paths`` remains injectable for isolated tests.  The production
    default includes all ten base brain files and every supported per-key
    overlay path, so both a content change and a newly-created overlay alter the
    cache/provenance namespace.
    """
    paths = dict(source_paths or default_governance_source_paths())
    sources: list[dict[str, Any]] = []
    documents: dict[str, Any] = {}
    for source_id, raw_path in sorted(paths.items()):
        path = Path(raw_path)
        present = path.is_file()
        raw = path.read_bytes() if present else None
        sources.append(
            {
                "id": str(source_id),
                "path": _display_path(path),
                "present": present,
                "sha256": hashlib.sha256(raw).hexdigest() if raw is not None else None,
            }
        )
        documents[str(source_id)] = yaml.safe_load(raw) if raw is not None else None
    snapshot_input = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "sources": sources,
    }
    blob = json.dumps(
        snapshot_input,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    snapshot = {
        **snapshot_input,
        "governance_digest": hashlib.sha256(blob).hexdigest(),
    }
    records = {str(record["id"]): record for record in sources}
    brains: dict[str, dict[str, Any]] = {}
    brain_available: dict[str, bool] = {}
    brain_references: dict[str, tuple[str, ...]] = {}
    for species in _BRAIN_SPECIES:
        prefix = f"brain/{species}/"
        rule_id = f"{prefix}rules"
        brains[species] = load_species_brain_documents(
            documents.get(rule_id),
            {
                key: documents.get(f"{prefix}{key}")
                for key in _BRAIN_OVERLAY_KEYS
            },
        )
        related_paths = [
            Path(path) for source_id, path in paths.items()
            if str(source_id).startswith(prefix)
        ]
        # Capture the directory fact with the source set too; the agent must
        # not call ``is_dir`` again after snapshotting.
        brain_available[species] = any(path.parent.is_dir() for path in related_paths)
        brain_references[species] = tuple(
            str(records[source_id]["path"])
            for source_id in sorted(records)
            if source_id.startswith(prefix) and records[source_id]["present"]
        )

    evidence_doc = documents.get("evidence_tiers")
    evidence_tiers = evidence_tiers_from_document(
        evidence_doc if isinstance(evidence_doc, Mapping) else None
    )
    rules_doc = documents.get("amrfinder_sir_rules")
    return GovernanceExecutionContext(
        snapshot=snapshot,
        evidence_tiers=deepcopy(evidence_tiers),
        amrfinder_rules_document=(deepcopy(dict(rules_doc))
                                  if isinstance(rules_doc, Mapping) else None),
        brains=brains,
        brain_available=brain_available,
        brain_references=brain_references,
    )


def build_governance_snapshot(
    source_paths: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Return only the public identity for compatibility/read-only callers."""
    return build_governance_execution_context(source_paths).snapshot
