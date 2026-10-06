"""Build the versioned MDR-GNB runtime model catalog from audited source manifests.

The generated catalog is the runtime authority.  It contains one exact SIR unit per
species×drug artifact, the two activity models, the actual iML1515 GEM, and explicit
fail-closed stubs.  The older batch/evidence files remain provenance inputs only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_ZOO_ROOT = REPO_ROOT / "praxis_virtualcell" / "model_zoo"
BATCH_MANIFEST = MODEL_ZOO_ROOT / "registry_mdr_gnb_batch.yaml"
EVIDENCE_TIERS = MODEL_ZOO_ROOT / "evidence_tiers.yaml"
AMRFINDER_SIR_RULES = (
    REPO_ROOT
    / "praxis_virtualcell"
    / "mdr_gnb"
    / "predictors"
    / "rules"
    / "amrfinder_sir_rules.yaml"
)
DEFAULT_OUTPUT = MODEL_ZOO_ROOT / "registry_mdr_gnb.yaml"

# Audit baseline used to produce the locally verified joblib artifacts.  The
# serialization format is known to be sklearn-version sensitive, so this is an
# execution contract rather than a scientific validation claim.
SKLEARN_ARTIFACT_VERSION = "1.9.0"

# RDKit performs the small-molecule model's SMILES parsing and fingerprint
# construction.  Pinning its runtime distribution therefore makes a version
# drift fail closed instead of silently changing the model's feature pipeline.
# This is an execution/reproducibility contract, not a scientific validation
# claim for the QSAR artifact.
RDKIT_ARTIFACT_VERSION = "2026.3.3"

# This is an explicit sidecar execution contract for the bounded iML1515 FBA
# probe.  It deliberately does not make the GEM routeable or scientifically
# validated; it merely prevents a direct load from silently using a different
# solver stack than the one audited locally.
GEM_SIDECAR_DEPENDENCY_VERSIONS = {
    "cobra": "0.31.1",
    "optlang": "1.9.1",
    "swiglpk": "5.0.13",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_drug_id(value: str) -> str:
    """Canonical artifact/query key; never join runtime state on display spelling."""
    return value.strip().lower().replace("/", "_").replace(" ", "_")


def evidence_record_sha256(record: dict[str, Any]) -> str:
    """Return a deterministic digest for one exact evidence-tier record.

    The source YAML file is already SHA-bound at catalog level.  This additional
    digest prevents a hand-edited catalog entry from silently pointing its model
    metadata at another record in that otherwise current source file.
    """
    serialized = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _asset_sha(path: str) -> str:
    return sha256_file(REPO_ROOT / path)


def _catalog_path(path: Path) -> str:
    """Use repository-relative paths when possible; keep test inputs usable too."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _evidence_by_unit(doc: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = doc.get("evidence_tiers") or []
    return {
        (str(row["species"]), canonical_drug_id(str(row["drug"]))): dict(row)
        for row in rows
    }


def _sir_model(
    *,
    batch_name: str,
    entry: dict[str, Any],
    evidence: dict[str, Any] | None,
    evidence_source_path: str,
    evidence_source_sha256: str,
) -> tuple[str, dict[str, Any]]:
    asset = (entry.get("assets") or [])[0]
    species = str((entry.get("species") or [""])[0])
    filename = str(asset["filename"])
    stem = Path(filename).stem.removeprefix("genotype_to_sir__")
    drug_id = canonical_drug_id(stem)
    model_id = f"sir/{species}/{drug_id}"
    return model_id, {
        "id": model_id,
        "execution": "predict",
        "capability": {
            "output_kind": "sir_class",
            "species": species,
            "drug_id": drug_id,
            "scientific_contract": "r_vs_non_r",
        },
        "runtime": {
            "adapter": "genotype_to_sir",
            "dependencies": ["numpy", "joblib", "sklearn"],
            "dependency_versions": {"scikit-learn": SKLEARN_ARTIFACT_VERSION},
            "input_contract_id": "amr_profile_v1",
        },
        "asset": {"path": filename, "sha256": str(asset["sha256"])},
        "validation": {
            "status": "limited",
            "evidence_level": (evidence or {}).get("evidence_level"),
            "evidence_tier": (evidence or {}).get("tier"),
            "evidence_key": (f"{species}:{drug_id}" if evidence else None),
            "evidence_source_path": evidence_source_path if evidence else None,
            "evidence_source_sha256": evidence_source_sha256 if evidence else None,
            "evidence_record_sha256": (
                evidence_record_sha256(evidence) if evidence else None
            ),
            # Binding evidence to the exact artifact avoids an E3/E4 row silently
            # following a replacement joblib.  Limited is deliberately not validated.
            "artifact_sha256": str(asset["sha256"]) if evidence else None,
        },
        "source": {"batch_model_name": batch_name, "batch_version": entry.get("version")},
        "lifecycle": {"declared": True, "routeable_when_ready": True},
    }


def _artifact_model(
    *,
    model_id: str,
    execution: str,
    output_kind: str,
    species: str,
    artifact_path: str,
    dependencies: list[str],
    input_contract_id: str,
    dependency_versions: dict[str, str],
    validation_status: str,
    evidence_source: str | None,
    routeable_when_ready: bool,
) -> tuple[str, dict[str, Any]]:
    return model_id, {
        "id": model_id,
        "execution": execution,
        "capability": {
            "output_kind": output_kind,
            "species": species,
            "drug_id": "*",
            "scientific_contract": (
                "aggregated_ecoli_activity" if output_kind in {"sm_activity", "peptide_activity"}
                else "experimental_mechanism_candidate"
            ),
        },
        "runtime": {
            "adapter": model_id.rsplit("/", 1)[-1],
            "dependencies": dependencies,
            "dependency_versions": dependency_versions,
            "input_contract_id": input_contract_id,
        },
        "asset": {"path": artifact_path, "sha256": _asset_sha(artifact_path)},
        "validation": {
            "status": validation_status,
            "evidence_source": evidence_source,
            "artifact_sha256": _asset_sha(artifact_path) if evidence_source else None,
        },
        "lifecycle": {"declared": True, "routeable_when_ready": routeable_when_ready},
    }


def _stub_model(
    model_id: str,
    output_kind: str,
    species: str,
    reason_code: str,
) -> tuple[str, dict[str, Any]]:
    return model_id, {
        "id": model_id,
        "execution": "fail_closed",
        "capability": {
            "output_kind": output_kind,
            "species": species,
            "drug_id": "*",
            "scientific_contract": "not_an_available_model",
        },
        "runtime": {"adapter": None, "dependencies": [], "input_contract_id": None},
        "asset": None,
        "validation": {"status": "unverified", "evidence_source": None},
        "lifecycle": {
            "declared": True,
            "routeable_when_ready": False,
            "reason_code": reason_code,
        },
    }


def build_catalog(
    *,
    batch_manifest: Path = BATCH_MANIFEST,
    evidence_tiers: Path = EVIDENCE_TIERS,
    output: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    """Build a deterministic runtime catalog; caller decides where to persist it."""
    batch = yaml.safe_load(batch_manifest.read_text(encoding="utf-8")) or {}
    evidence_doc = yaml.safe_load(evidence_tiers.read_text(encoding="utf-8")) or {}
    evidence_by_unit = _evidence_by_unit(evidence_doc)
    evidence_source_path = _catalog_path(evidence_tiers)
    evidence_source_sha256 = sha256_file(evidence_tiers)

    models: dict[str, dict[str, Any]] = {}
    referenced_evidence: set[tuple[str, str]] = set()
    for batch_name, entry in sorted((batch.get("models") or {}).items()):
        assets = entry.get("assets") or []
        if len(assets) != 1 or not entry.get("species"):
            raise ValueError(f"invalid SIR batch entry: {batch_name}")
        species = str(entry["species"][0])
        drug_id = canonical_drug_id(
            Path(str(assets[0]["filename"])).stem.removeprefix("genotype_to_sir__")
        )
        evidence = evidence_by_unit.get((species, drug_id))
        if evidence:
            referenced_evidence.add((species, drug_id))
        model_id, model = _sir_model(
            batch_name=batch_name,
            entry=entry,
            evidence=evidence,
            evidence_source_path=evidence_source_path,
            evidence_source_sha256=evidence_source_sha256,
        )
        models[model_id] = model

    for model_id, model in (
        _artifact_model(
            model_id="activity/escherichia_coli/small_molecule",
            execution="predict",
            output_kind="sm_activity",
            species="escherichia_coli",
            artifact_path="data/mdr_gnb/models/escherichia_coli/sm_activity__mic.joblib",
            dependencies=["numpy", "joblib", "sklearn", "rdkit"],
            input_contract_id="smiles_v1",
            dependency_versions={
                "scikit-learn": SKLEARN_ARTIFACT_VERSION,
                "rdkit": RDKIT_ARTIFACT_VERSION,
            },
            validation_status="limited",
            evidence_source="reports/science_v2/qsar_baseline",
            routeable_when_ready=True,
        ),
        _artifact_model(
            model_id="activity/escherichia_coli/peptide",
            execution="predict",
            output_kind="peptide_activity",
            species="escherichia_coli",
            artifact_path="data/mdr_gnb/models/escherichia_coli/peptide_activity__mic.joblib",
            dependencies=["numpy", "joblib", "sklearn"],
            input_contract_id="peptide_sequence_v1",
            dependency_versions={"scikit-learn": SKLEARN_ARTIFACT_VERSION},
            validation_status="limited",
            evidence_source="reports/science_v2/peptide_baseline",
            routeable_when_ready=True,
        ),
        _artifact_model(
            model_id="mechanism/escherichia_coli/iml1515",
            execution="experimental",
            output_kind="mechanism_state",
            species="escherichia_coli",
            artifact_path="data/mdr_gnb/gems/iML1515.xml.gz",
            dependencies=list(GEM_SIDECAR_DEPENDENCY_VERSIONS),
            input_contract_id="metabolic_target_drug_v1",
            dependency_versions=GEM_SIDECAR_DEPENDENCY_VERSIONS,
            validation_status="unverified",
            evidence_source=None,
            routeable_when_ready=False,
        ),
        _stub_model(
            "stub/mic_regressor", "mic_scalar", "*", "quantitative_mic_model_unavailable"
        ),
        _stub_model(
            "stub/mechanism_state",
            "mechanism_state",
            "*",
            "mechanism_state_model_unavailable",
        ),
        _stub_model("stub/rule_baseline", "sir_class", "*", "rule_baseline_not_runtime_predictor"),
    ):
        models[model_id] = model

    orphaned = [
        {
            "species": species,
            "drug_id": drug_id,
            "evidence_level": row.get("evidence_level"),
            "tier": row.get("tier"),
            "reason_code": "evidence_without_runtime_artifact",
        }
        for (species, drug_id), row in sorted(evidence_by_unit.items())
        if (species, drug_id) not in referenced_evidence
    ]
    catalog = {
        "schema_version": "1.0",
        "catalog_version": "2026-07-18-local",
        "generated_from": {
            "sir_batch_manifest": {
                "path": _catalog_path(batch_manifest),
                "sha256": sha256_file(batch_manifest),
            },
            "evidence_tiers": {
                "path": evidence_source_path,
                "sha256": evidence_source_sha256,
            },
            # Rule-first SIR fusion consumes this source on the production path.
            # Pinning it here makes a rule edit fail closed alongside the artifact
            # manifest and evidence tiers; it does not reclassify any scientific
            # evidence or validation status.
            "amrfinder_sir_rules": {
                "path": _catalog_path(AMRFINDER_SIR_RULES),
                "sha256": sha256_file(AMRFINDER_SIR_RULES),
            },
        },
        "models": dict(sorted(models.items())),
        "orphaned_evidence": orphaned,
    }
    output.write_text(
        yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return catalog


if __name__ == "__main__":
    catalog = build_catalog()
    print(
        f"[CATALOG_DONE] models={len(catalog['models'])} "
        f"orphaned_evidence={len(catalog['orphaned_evidence'])} -> {DEFAULT_OUTPUT}"
    )
