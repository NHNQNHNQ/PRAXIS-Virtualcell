"""Source-linked strain training cases; MICs stay in private canonical locations."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from praxis_virtualcell.omics import load_profile
from praxis_virtualcell.omics.strain_reference import _UNKNOWN
from praxis_virtualcell.datasets.labels import AssayConditions, ExperimentRecord
from .species_evaluation import _snapshot, _verify, validate_species_evaluation
from .species_registry import _digest, _json

CONDITION_FIELDS = ("medium", "medium_supplements", "temperature_c", "exposure_hours", "method", "inoculum")
_DERIVATIVE = re.compile(r"Δ|\b(?:mutant|knockout|deleted|deletion|deficient|derivative|delta)\b", re.I)
_ACCESSION = re.compile(r"\b(?:GC[AF]_\d+\.\d+|NC_\d+\.\d+|CP\d+\.\d+)\b")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _Source(_Strict):
    citation: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class _StrainCorrection(_Strict):
    label: str = Field(min_length=1)
    namespace: str | None = None
    identity_basis: str = Field(min_length=1)


class _ConditionsCorrection(_Strict):
    medium: str | None = None
    medium_supplements: list[str] | None = None
    temperature_c: float | None = None
    exposure_hours: float | None = None
    method: str | None = None
    inoculum: str | None = None


class _Enrichment(_Strict):
    record_id: str = Field(min_length=1)
    source: _Source
    strain: _StrainCorrection | None = None
    conditions: _ConditionsCorrection | None = None


class _Enrichments(_Strict):
    schema_version: Literal["praxis.strain-enrichments.v1"]
    enrichments: list[_Enrichment]


def _normalize(label: str | None) -> str | None:
    if not label or not label.strip():
        return None
    label = label.strip()
    atcc = re.fullmatch(r"ATCC\s*[-:]?\s*(\d+)", label, re.I)
    if atcc:
        return "ATCC " + atcc[1]
    return "AB5075" if re.fullmatch("AB5075", label, re.I) else label


def _native_inventory(root: Path) -> tuple[dict, dict, list[dict]]:
    candidates, anchors, snapshots = defaultdict(list), {}, []
    for path in sorted(root.glob("*/manifest.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema_version") not in {"praxis.organism-profile.v1", "praxis.organism-profile.v2"}:
            continue
        profile = load_profile(raw["profile_id"], root)
        overview = profile.overview()
        taxon = int(overview["species"]["taxonomy_id"].removeprefix("NCBITaxon:"))
        label = overview["strain"]
        assets = ([raw["expression"], raw["annotations"]] if raw["schema_version"] == "praxis.organism-profile.v1"
                  else [item["features"] for item in raw["modalities"].values()])
        snapshots.append({"profile_id": profile.profile_id, "manifest": _snapshot(path), "assets": [
            {"path": str((path.parent / asset["path"]).resolve()), "size_bytes": asset["size_bytes"],
             "sha256": asset["sha256"]} for asset in assets]})
        for name in overview["available_modalities"]:
            selected = profile.select_modalities([name]).overview()
            native = selected.get("modalities", {}).get(name, selected)
            provenance = native["provenance"]
            item = {"profile_id": profile.profile_id, "manifest_path": str(path.resolve()),
                    "manifest_sha256": snapshots[-1]["manifest"]["sha256"], "strain": label,
                    "species": overview["species"],
                    "genotype": overview.get("genotype"), "condition": selected["condition"],
                    **{key: native.get(key) for key in ("unit", "scale", "value_semantics", "observation_unit")},
                    "citation": provenance["citation"], "study_id": provenance["study_id"],
                    "source_samples": selected["source_samples"], "modality": name}
            candidates[taxon, label, name].append(item)
            # Only the actual source genome can anchor a stable reference name;
            # an RNA mapping reference/accession does not identify its source strain.
            if name == "genome":
                accessions = sorted(set(_ACCESSION.findall(_json(provenance))))
                if accessions:
                    anchors[taxon, label] = {"profile_id": profile.profile_id,
                                             "manifest_path": str(path.resolve()), "accessions": accessions}
    return candidates, anchors, snapshots


def _identity(organism: dict, taxon: int, species: str, case_id: str, source: dict, anchors: dict,
              corrected: _StrainCorrection | None) -> dict:
    label = _normalize(corrected.label if corrected else organism.get("strain"))
    namespace = corrected.namespace if corrected else organism.get("strain_namespace")
    evidence = organism.get("identity_evidence")
    unknown = (label is None or label.casefold() in _UNKNOWN or label == species
               or not corrected and evidence in {"unresolved", "conflicting"})
    if unknown:
        label, namespace = None, None
        basis = "unresolved_or_conflicting_source_strain"
        key = [taxon, "unknown", case_id]
        anchor = None
    else:
        anchor = anchors.get((taxon, label))
        if label == "AB5075" or re.fullmatch(r"ATCC \d+", label):
            namespace, basis = "strain_reference" if label == "AB5075" else "ATCC", "exact_source_reference_label"
        elif anchor:
            namespace, basis = "strain_reference", "exact_native_reference_label_with_assembly_accession"
        else:
            # Every non-reference name remains restricted to the source study.
            # Equal spelling in another paper is not evidence of isolate equivalence.
            namespace = "study:" + (source.get("document_id") or source.get("doi") or source["source_id"])
            basis = "explicit_study_local_strain_label"
        if corrected:
            if corrected.namespace is not None and corrected.namespace != namespace:
                allowed = {"study:" + value for value in (source.get("document_id"), source.get("doi")) if value}
                if basis != "explicit_study_local_strain_label" or corrected.namespace not in allowed:
                    raise ValueError("unsupported_source_correction_namespace")
                namespace = corrected.namespace
            basis += "; source_correction:" + corrected.identity_basis
        key = [taxon, namespace, label]
    strain_id = "strain-" + hashlib.sha256(_json(key).encode()).hexdigest()[:24]
    return {"strain_id": strain_id, "species": species, "taxon_id": taxon, "label": label,
            "namespace": namespace, "identity_basis": basis, "unknown": bool(unknown),
            "reference_anchor": anchor, "native_strain_label": organism.get("native_strain_label")}


def _references(identity: dict, candidates: dict, *, native_study: str | None = None) -> dict:
    if identity["unknown"] or native_study is None and identity["namespace"] not in {"ATCC", "strain_reference"}:
        return {}
    selected = {}
    genotype = None
    genotype_set = False
    for name in ("genome", "transcriptome", "proteome"):
        options = candidates.get((identity["taxon_id"], identity["label"], name), [])
        if native_study is not None:
            options = [item for item in options if item["study_id"] == native_study]
        # Exact strain spelling is required by the runtime collection contract.
        compatible = [item for item in options if not genotype_set or item["genotype"] == genotype]
        if not compatible:
            continue
        source = sorted(compatible, key=lambda item: item["profile_id"])[0]
        genotype, genotype_set = source["genotype"], True
        selected[name] = {key: value for key, value in source.items() if key != "modality"} | {
            "selection_reason": "Exact confirmed source strain; deterministic first compatible native profile ID. Different source conditions are retained, without matched-sample claims.",
            "alternative_profile_ids": sorted(item["profile_id"] for item in compatible if item != source)}
    return selected


def _collection(root: Path, identity: dict, references: dict) -> dict | None:
    if not references:
        return None
    version = {"strain_id": identity["strain_id"], "identity_basis": identity["identity_basis"],
               "references": {name: (item["profile_id"], item["manifest_sha256"]) for name, item in references.items()}}
    version_id = hashlib.sha256(_json(version).encode()).hexdigest()[:24]
    fixed = {(470, "AB5075"): "AB5075-STRAIN-REFERENCE", (562, "MG1655"): "EC-MG1655-STRAIN-REFERENCE",
             (287, "PAO1"): "PA-PAO1-STRAIN-REFERENCE", (573, "HS11286"): "KP-HS11286-STRAIN-REFERENCE",
             (573, "K26"): "KP-K26-STRAIN-REFERENCE", (573, "NCTC418"): "KP-NCTC418-STRAIN-REFERENCE"}
    label = re.sub(r"[^A-Za-z0-9_.-]+", "-", identity["label"])[:40].strip(".-") or "source"
    profile_id = fixed.get((identity["taxon_id"], identity["label"]),
                           f"STRAIN-{identity['taxon_id']}-{label}-{identity['strain_id'][-12:]}-REFERENCE")
    manifest = {"schema_version": "praxis.strain-reference.v1", "profile_id": profile_id,
                "species": {"scientific_name": identity["species"], "taxonomy_id": f"NCBITaxon:{identity['taxon_id']}"},
                "strain": identity["label"], "label": identity["label"], "strain_namespace": identity["namespace"],
                "identity_basis": identity["identity_basis"], "genotype": next(iter(references.values()))["genotype"],
                "input_role": "strain_reference", "prediction_scope": "strain_reference", "relation": "same_strain_reference",
                "reference_profiles": {name: item["profile_id"] for name, item in references.items()},
                "selection_reasons": {name: item["selection_reason"] for name, item in references.items()}}
    path = root / profile_id / "manifest.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != manifest:
        profile_id += "-" + version_id[:12]
        manifest["profile_id"] = profile_id
        path = root / profile_id / "manifest.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != manifest:
            raise ValueError("strain_reference_destination_exists")
    else:
        path.parent.mkdir(exist_ok=False)
        path.write_text(_json(manifest) + "\n", encoding="utf-8")
    load_profile(profile_id, root)
    return {"profile_id": profile_id, "strain_id": identity["strain_id"], "manifest": _snapshot(path)}


_SCHEMA = """
CREATE TABLE strain_identity(strain_id TEXT PRIMARY KEY,taxon_id INTEGER NOT NULL,canonical_label TEXT,
 namespace TEXT,identity_basis TEXT NOT NULL,unknown INTEGER NOT NULL,metadata_json TEXT NOT NULL);
CREATE TABLE strain_profiles(strain_id TEXT NOT NULL,modality TEXT NOT NULL,profile_id TEXT NOT NULL,
 metadata_json TEXT NOT NULL,PRIMARY KEY(strain_id,modality));
CREATE TABLE cases(case_id TEXT PRIMARY KEY,record_id TEXT UNIQUE NOT NULL,split TEXT NOT NULL,group_id TEXT NOT NULL,
 strain_id TEXT NOT NULL,conditions_json TEXT NOT NULL,doi TEXT,document_id TEXT,private_answer_json TEXT NOT NULL,
 candidate_json TEXT NOT NULL,task_scope TEXT NOT NULL);
"""


def build_strain_dataset(species_database, frozen_manifest, output_dir, *, profile_root, enrichments_path=None) -> dict:
    """Associate exact source strains and keep experimental outcomes as pointers."""
    destination = Path(output_dir).resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("strain_dataset_destination_exists")
    frozen_path = Path(frozen_manifest).resolve()
    frozen = validate_species_evaluation(frozen_path)
    database = Path(species_database).resolve()
    if (frozen["status"] != "ready" or frozen["grouping"] != "scaffold"
            or database != Path(frozen["database"]["path"]).resolve()):
        raise ValueError("ready_scaffold_freeze_for_same_database_required")
    root = Path(profile_root).resolve()
    if not root.is_dir():
        raise ValueError("profile_root_unavailable")
    if destination == root or destination.is_relative_to(root) or destination == frozen_path.parent:
        raise ValueError("strain_dataset_must_be_separate_from_sources")
    enrichments, enrichment_snapshot = {}, None
    if enrichments_path:
        path = Path(enrichments_path).resolve()
        sidecar = _Enrichments.model_validate_json(path.read_text(encoding="utf-8"))
        for item in sidecar.enrichments:
            if item.record_id in enrichments:
                raise ValueError("duplicate_record_enrichment")
            if item.strain is None and item.conditions is None:
                raise ValueError("empty_record_enrichment")
            enrichments[item.record_id] = item
        enrichment_snapshot = _snapshot(path)
    inputs = {row["case_id"]: row for row in (json.loads(line) for line in
        (frozen_path.parent / "inputs.jsonl").read_text().splitlines() if line)}
    index = [json.loads(line) for line in (frozen_path.parent / "answers.index.jsonl").read_text().splitlines() if line]
    if set(enrichments) - {row["record_id"] for row in index}:
        raise ValueError("enrichment_record_outside_frozen_cases")
    candidates, anchors, snapshots = _native_inventory(root)
    identities, references_by_strain, collections, cases = {}, {}, {}, []
    label_sources = {source["id"]: source for source in frozen["label_sources"]}
    with ExitStack() as stack:
        streams = {file_id: stack.enter_context(Path(source["path"]).open("rb")) for file_id, source in label_sources.items()}
        for pointer in index:
            input_row = inputs[pointer["case_id"]]
            if pointer["split"] != input_row["split"] or pointer["group_id"] != input_row["group_id"]:
                raise ValueError("frozen_case_split_mismatch")
            stream = streams[pointer["label_file_id"]]
            stream.seek(pointer["byte_offset"])
            record = ExperimentRecord.model_validate_json(stream.readline())
            if record.record_id != pointer["record_id"]:
                raise ValueError("frozen_answer_reference_mismatch")
            correction = enrichments.get(record.record_id)
            original = record.organism.model_dump()
            if correction and correction.strain and _DERIVATIVE.search(original.get("strain") or original.get("native_strain_label") or ""):
                if not _DERIVATIVE.search(correction.strain.label):
                    raise ValueError("derivative_strain_identity_erasure")
            organism = input_row["input"]["organism"]
            identity = _identity(original, organism["taxon_id"], organism["species"], pointer["case_id"],
                                 record.source.model_dump(), anchors, correction.strain if correction else None)
            strain_id = identity["strain_id"]
            source = label_sources[pointer["label_file_id"]]
            private = {"label_file_id": pointer["label_file_id"], "path": source["path"], "sha256": source["sha256"],
                       **{key: pointer[key] for key in ("byte_offset", "line_number", "record_id")}}
            if strain_id not in identities:
                identities[strain_id] = identity | {"canonical_label": identity["label"], "source_pointers": []}
                refs = _references(identity, candidates)
                references_by_strain[strain_id] = refs
                collection = _collection(root, identity, refs)
                if collection:
                    collections[strain_id] = collection
            identities[strain_id]["source_pointers"].append(private | {"identity_evidence": original["identity_evidence"],
                "enrichment_source": correction.source.model_dump() if correction and correction.strain else None})
            conditions = {name: getattr(record.conditions, name) for name in CONDITION_FIELDS}
            if correction and correction.conditions:
                conditions.update(correction.conditions.model_dump(exclude_unset=True))
            conditions = AssayConditions.model_validate(conditions).model_dump(exclude={"provenance"})
            refs = references_by_strain[strain_id]
            scope = "strain_reference_omics" if refs else "species_auxiliary_strain_unknown" if identity["unknown"] else "strain_without_omics"
            cases.append({"case_id": pointer["case_id"], "split": pointer["split"], "group_id": pointer["group_id"],
                "strain": {key: identity[key] for key in ("strain_id", "species", "taxon_id", "label", "namespace", "identity_basis")},
                "conditions": conditions, "reference_profiles": refs,
                "profile_id": collections[strain_id]["profile_id"] if strain_id in collections else None,
                "candidate": {"id": pointer["case_id"], "smiles": record.molecule.canonical_smiles},
                "private_answer": private, "literature": {"doi": record.source.doi, "document_id": record.source.document_id},
                "condition_sources": {"canonical": record.conditions.provenance,
                    "enrichment": correction.source.model_dump() if correction and correction.conditions else None},
                "task_scope": scope})
    # Platform choices also include source-declared native strains without MIC
    # matches. Their existence never authorizes assigning them to unknown cases.
    native_sources = {item["profile_id"]: (taxon, label, item) for (taxon, label, _), options in candidates.items() for item in options}
    for taxon, label, item in native_sources.values():
        identity = _identity({"strain": label, "identity_evidence": "structured_assay_strain", "native_strain_label": label},
                             taxon, item["species"]["scientific_name"], "native:" + item["profile_id"],
                             {"document_id": item["study_id"], "doi": None, "source_id": item["profile_id"]}, anchors, None)
        if identity["unknown"]:
            continue
        strain_id = identity["strain_id"]
        if strain_id not in identities:
            identities[strain_id] = identity | {"canonical_label": label, "source_pointers": []}
            refs = _references(identity, candidates, native_study=item["study_id"]
                               if identity["namespace"].startswith("study:") else None)
            references_by_strain[strain_id] = refs
            collection = _collection(root, identity, refs)
            if collection:
                collections[strain_id] = collection
        identities[strain_id]["source_pointers"].append({"source_type": "native_profile", "profile_id": item["profile_id"],
            "manifest_path": item["manifest_path"], "manifest_sha256": item["manifest_sha256"]})
    destination.mkdir(parents=True, exist_ok=True)
    db_path = destination / "strain_dataset.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(_SCHEMA)
        for strain_id, identity in identities.items():
            connection.execute("INSERT INTO strain_identity VALUES (?,?,?,?,?,?,?)", (
                strain_id, identity["taxon_id"], identity["canonical_label"], identity["namespace"], identity["identity_basis"],
                identity["unknown"], _json(identity)))
            for name, item in references_by_strain[strain_id].items():
                connection.execute("INSERT INTO strain_profiles VALUES (?,?,?,?)", (strain_id, name, item["profile_id"], _json(item)))
        for case in cases:
            connection.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                case["case_id"], case["private_answer"]["record_id"], case["split"], case["group_id"], case["strain"]["strain_id"],
                _json(case["conditions"]), case["literature"]["doi"], case["literature"]["document_id"],
                _json(case["private_answer"]), _json(case["candidate"]), case["task_scope"]))
    for filename, rows in (("cases.jsonl", cases), ("strain_identities.jsonl", list(identities.values()))):
        (destination / filename).write_text("".join(_json(row) + "\n" for row in rows), encoding="utf-8")
    per_species = []
    for taxon in sorted({case["strain"]["taxon_id"] for case in cases}):
        selected = [case for case in cases if case["strain"]["taxon_id"] == taxon]
        per_species.append({"taxon_id": taxon, "species": selected[0]["strain"]["species"], **_coverage(selected)})
    summary = {"schema_version": "praxis.strain-dataset.v1", "status": "prepared_not_trainable",
               "output_dir": str(destination), "source_database": _snapshot(database), "frozen_manifest": _snapshot(frozen_path),
               "reference_sources": snapshots, "collections": list(collections.values()), "enrichments": enrichment_snapshot,
               "native_collection_count": len(collections),
               "enriched_records": len(enrichments), **_coverage(cases), "per_species": per_species,
               "splits": {split: _coverage([case for case in cases if case["split"] == split]) for split in ("train", "validation", "test")},
               "files": {name: {"sha256": _digest(destination / name)} for name in ("cases.jsonl", "strain_identities.jsonl", "strain_dataset.sqlite3")},
               "MIC_values_copied": False, "omics_assets_copied": False,
               "limitations": ["Study-local identities are not merged across papers; unknown strains do not borrow species references.",
                               "Same-strain sources may have different conditions and are not matched samples or current states.",
                               "Reference strain/genotype labels are preserved; null genotype does not establish wild type.",
                               "DOI and private MIC pointers do not constitute reviewed mechanism evidence or admitted training targets.",
                               "Cases retain the original scaffold splits; no new strain or study holdout is claimed."]}
    (destination / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _coverage(cases: list[dict]) -> dict:
    return {"records": len(cases), "named_strain_records": sum(case["strain"]["label"] is not None for case in cases),
            "strain_identity_count": len({case["strain"]["strain_id"] for case in cases if case["strain"]["label"] is not None}),
            "strain_omics_records": sum(bool(case["reference_profiles"]) for case in cases),
            "strain_omics_identity_count": len({case["strain"]["strain_id"] for case in cases if case["reference_profiles"]}),
            "unknown_strain_auxiliary_records": sum(case["task_scope"] == "species_auxiliary_strain_unknown" for case in cases),
            "strain_doi_records": sum(bool(case["strain"]["label"] and case["literature"]["doi"]) for case in cases),
            "strain_omics_doi_records": sum(bool(case["reference_profiles"] and case["literature"]["doi"]) for case in cases),
            "missing_conditions": {field: sum(case["conditions"][field] in (None, [], "") for case in cases) for field in CONDITION_FIELDS},
            "task_scope_counts": dict(Counter(case["task_scope"] for case in cases))}


def validate_strain_dataset(summary_path: str | Path) -> dict:
    """Reject changed sources or derived cases before target materialization."""
    path = Path(summary_path).resolve()
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("schema_version") != "praxis.strain-dataset.v1":
        raise ValueError("invalid_strain_dataset_summary")
    _verify(summary["frozen_manifest"])
    validate_species_evaluation(summary["frozen_manifest"]["path"])
    _verify(summary["source_database"])
    if summary.get("enrichments"):
        _verify(summary["enrichments"])
    for source in summary["reference_sources"]:
        _verify(source["manifest"])
        for asset in source["assets"]:
            _verify(asset)
    for collection in summary["collections"]:
        _verify(collection["manifest"])
    for filename, fingerprint in summary["files"].items():
        _verify({"path": str(path.parent / filename), **fingerprint})
    return summary
