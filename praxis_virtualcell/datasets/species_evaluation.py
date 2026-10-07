"""Globally grouped species-reference evaluation with private answer pointers."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
from typing import Literal

from .evaluation import _compound_key, _keys
from .labels import ExperimentRecord
from .species_registry import _digest, _json
from praxis_virtualcell.omics import load_profile

Grouping = Literal["compound", "scaffold", "study", "scaffold_study"]
SCHEMA = "praxis.species-frozen-evaluation.v1"


def _snapshot(path: Path, expected: str | None = None) -> dict:
    digest = _digest(path)
    if expected is not None and digest != expected:
        raise ValueError("frozen_source_changed")
    return {"path": str(path.resolve()), "sha256": digest}


def _verify(snapshot: dict) -> None:
    path = Path(snapshot["path"])
    if not path.is_file() or _digest(path) != snapshot["sha256"]:
        raise ValueError("frozen_source_changed: " + str(path))
    if "size_bytes" in snapshot and path.stat().st_size != snapshot["size_bytes"]:
        raise ValueError("frozen_source_changed: " + str(path))


def _input_identity(request: dict) -> str:
    return hashlib.sha256(_json({"smiles": request["candidate"]["smiles"], "organism": request["organism"],
                                "profile_id": request["profile_id"]}).encode()).hexdigest()


def validate_species_evaluation(manifest_path: str | Path) -> dict:
    """Validate every frozen source before supervision, view generation or scoring."""
    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("invalid_species_evaluation_manifest")
    for source in [manifest["database"], *manifest["label_sources"]]:
        _verify(source)
    for reference in manifest["references"]:
        _verify(reference["manifest"])
        for asset in reference["assets"]:
            _verify(asset)
    for collection in manifest["collections"]:
        _verify(collection["manifest"])
    for filename, fingerprint in manifest["files"].items():
        _verify({"path": str(path.parent / filename), **fingerprint})
    return manifest


def _reference_versions(connection) -> tuple[list[dict], list[dict]]:
    references, collections = [], []
    by_species = defaultdict(dict)
    for taxon, modality, profile_id, _, source_manifest, _ in connection.execute(
        "SELECT * FROM reference_modalities ORDER BY taxon_id,modality"
    ):
        path = Path(source_manifest)
        root = path.parent.parent
        source = load_profile(profile_id, root).select_modalities([modality]).overview()
        if int(source["species"]["taxonomy_id"].removeprefix("NCBITaxon:")) != taxon:
            raise ValueError("reference_species_mismatch")
        native = json.loads(path.read_text(encoding="utf-8"))
        assets = ([native["expression"], native["annotations"]] if native["schema_version"] == "praxis.organism-profile.v1"
                  else [native["modalities"][modality]["features"]])
        references.append({"taxon_id": taxon, "modality": modality, "profile_id": profile_id,
                           "manifest": _snapshot(path), "assets": [
                               {"path": str((path.parent / asset["path"]).resolve()),
                                "size_bytes": asset["size_bytes"], "sha256": asset["sha256"]} for asset in assets]})
        by_species[taxon][modality] = (profile_id, root)
    for taxon, _, profile_id in connection.execute("SELECT * FROM species ORDER BY taxon_id"):
        if profile_id is None:
            continue
        selected = by_species[taxon]
        roots = {root for _, root in selected.values()}
        if len(roots) != 1:
            raise ValueError("inconsistent_reference_roots")
        path = next(iter(roots)) / profile_id / "manifest.json"
        collection = json.loads(path.read_text(encoding="utf-8"))
        expected = {modality: value[0] for modality, value in selected.items()}
        if (collection.get("schema_version") != "praxis.species-reference.v1"
                or collection.get("reference_profiles") != expected):
            raise ValueError("database_reference_collection_changed")
        collections.append({"taxon_id": taxon, "profile_id": profile_id, "manifest": _snapshot(path),
                            "available_modalities": [name for name in ("genome", "transcriptome", "proteome") if name in selected]})
    return references, collections


def _components(chosen: list[dict], seed: int, test_fraction: float, validation_fraction: float) -> list[tuple]:
    parents = list(range(len(chosen)))
    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    first = {}
    for index, item in enumerate(chosen):
        for key in item["keys"]:
            if key in first:
                parents[find(index)] = find(first[key])
            else:
                first[key] = index
    groups = defaultdict(list)
    for index, item in enumerate(chosen):
        groups[find(index)].append(item)
    components = []
    for members in groups.values():
        identity = "\n".join(sorted(item["case_id"] for item in members))
        group_id = hashlib.sha256(identity.encode()).hexdigest()[:20]
        components.append((hashlib.sha256(f"{seed}:{group_id}".encode()).hexdigest(), group_id, members))
    components.sort(key=lambda item: item[0])
    count = len(components)
    test_count = max(1, round(count * test_fraction)) if count >= 3 else 0
    validation_count = max(1, round(count * validation_fraction)) if count >= 3 else 0
    while count >= 3 and test_count + validation_count >= count:
        if test_count > validation_count:
            test_count -= 1
        else:
            validation_count -= 1
    return [(group_id, members, "unassigned" if count < 3 else "test" if index < test_count else
             "validation" if index < test_count + validation_count else "train")
            for index, (_, group_id, members) in enumerate(components)]


def freeze_species_evaluation(
    database: str | Path, output_dir: str | Path, *, grouping: Grouping = "scaffold", seed: int = 20261007,
    test_fraction: float = 0.2, validation_fraction: float = 0.1,
) -> dict:
    """Freeze global groups and existing answer locations, never duplicate MICs."""
    if (isinstance(seed, bool) or not isinstance(seed, int) or grouping not in {"compound", "scaffold", "study", "scaffold_study"}
            or isinstance(test_fraction, bool) or isinstance(validation_fraction, bool)
            or not 0 < test_fraction < 1 or not 0 < validation_fraction < 1
            or test_fraction + validation_fraction >= 1):
        raise ValueError("invalid_split_parameters")
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("frozen_evaluation_destination_exists")
    db = Path(database).resolve()
    database_version = _snapshot(db)
    chosen, excluded = [], []
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as connection, ExitStack() as stack:
        version = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        if version != ("praxis.species-database.v1",):
            raise ValueError("invalid_species_database")
        label_sources = [{"id": file_id, **_snapshot(Path(path), digest)}
                         for file_id, path, digest in connection.execute("SELECT * FROM label_files ORDER BY id")]
        streams = {source["id"]: stack.enter_context(Path(source["path"]).open("rb")) for source in label_sources}
        references, collections = _reference_versions(connection)
        species = [{"taxon_id": taxon, "scientific_name": name} for taxon, name in connection.execute(
            "SELECT taxon_id,scientific_name FROM species ORDER BY taxon_id")]
        connection.row_factory = sqlite3.Row
        for row in connection.execute(
            "SELECT e.case_id,e.record_id,e.taxon_id,e.label_file_id,e.byte_offset,e.line_number,"
            "s.scientific_name,s.profile_id,c.canonical_smiles FROM experiments e "
            "JOIN species s ON s.taxon_id=e.taxon_id JOIN compounds c ON c.identity_key=e.compound_id ORDER BY e.case_id"
        ):
            item = dict(row)
            if item["profile_id"] is None:
                excluded.append({"record_id": item["record_id"], "reason": "species_reference_unavailable"})
                continue
            stream = streams[item["label_file_id"]]
            stream.seek(item["byte_offset"])
            record = ExperimentRecord.model_validate_json(stream.readline())
            if record.record_id != item["record_id"] or record.molecule.canonical_smiles != item["canonical_smiles"]:
                raise ValueError("database_answer_reference_mismatch")
            try:
                keys = (_keys(record, "scaffold") + _keys(record, "study") if grouping == "scaffold_study"
                        else _keys(record, grouping))
                compound = _compound_key(record)
            except ValueError as exc:
                excluded.append({"record_id": item["record_id"], "reason": str(exc)})
                continue
            chosen.append(item | {"keys": keys, "compound": compound})
    components = _components(chosen, seed, test_fraction, validation_fraction)
    inputs, answers, split_summary = [], [], {}
    for group_id, members, split in components:
        for item in sorted(members, key=lambda value: value["case_id"]):
            inputs.append({"case_id": item["case_id"], "split": split, "group_id": group_id, "input": {
                "candidate": {"id": item["case_id"], "smiles": item["canonical_smiles"]},
                "organism": {"species": item["scientific_name"], "taxon_id": item["taxon_id"]},
                "profile_id": item["profile_id"], "prediction_scope": "species_reference"}})
            answers.append({"case_id": item["case_id"], "split": split, "group_id": group_id,
                            **{key: item[key] for key in ("record_id", "label_file_id", "byte_offset", "line_number")}})
    for split in ("train", "validation", "test", "unassigned"):
        members = [(group_id, item) for group_id, group, assignment in components if assignment == split for item in group]
        per_species = []
        for identity in species:
            matched = [(group_id, item) for group_id, item in members if item["taxon_id"] == identity["taxon_id"]]
            per_species.append({**identity, "records": len(matched), "independent_molecules": len({item["compound"] for _, item in matched}),
                                "groups": len({group_id for group_id, _ in matched})})
        split_summary[split] = {"records": len(members), "independent_molecules": len({item["compound"] for _, item in members}),
                                "unique_input_count": len({(item["canonical_smiles"], item["taxon_id"], item["profile_id"]) for _, item in members}),
                                "groups": len({group_id for group_id, _ in members}), "species": per_species,
                                "absent_species": [item["taxon_id"] for item in per_species if item["records"] == 0]}
    manifest = {"schema_version": SCHEMA, "status": "ready" if len(components) >= 3 else "insufficient_groups",
                "prediction_scope": "species_reference", "grouping": grouping, "seed": seed,
                "database": database_version, "label_sources": label_sources, "references": references, "collections": collections,
                "records": len(inputs), "unique_input_count": len({_input_identity(item["input"]) for item in inputs}),
                "independent_groups": len(components), "excluded_records": len(excluded),
                "largest_group_records": max((len(members) for _, members, _ in components), default=0),
                "largest_group_fraction": max((len(members) / len(chosen) for _, members, _ in components), default=0),
                "requested_group_fractions": {"test": test_fraction, "validation": validation_fraction}, "splits": split_summary,
                "limitations": [
                    "Groups are global across species; fractions apply to groups, not records, and no species balance is guaranteed.",
                    "Large transitive components can dominate a split; fewer than three groups are left unassigned.",
                    "Compound/scaffold splitting does not hold out shared studies; study splitting does not establish chemical novelty.",
                    "Empty Murcko scaffolds form one ACYCLIC group; scaffold_study joins shared scaffolds and studies transitively.",
                    "Repeated MICs remain separate observations, not independent molecules; modality views reuse the same cases and splits.",
                    "Fixed species references do not identify individual experimental strains or current states.",
                ], "files": {}}
    # Recheck source versions before publishing the immutable manifest.
    for source in [database_version, *label_sources]:
        _verify(source)
    destination.mkdir(parents=True, exist_ok=True)
    for filename, rows in (("inputs.jsonl", inputs), ("answers.index.jsonl", answers), ("excluded.jsonl", excluded)):
        path = destination / filename
        path.write_text("".join(_json(row) + "\n" for row in rows), encoding="utf-8")
        manifest["files"][filename] = {"sha256": _digest(path)}
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return manifest


def _metrics(details: list[dict]) -> dict:
    eligible = [item for item in details if item.get("eligible_mic")]
    answered = [item for item in eligible if item["scored"]]
    errors = [item["absolute_log2_error"] for item in answered if "absolute_log2_error" in item]
    censored = [item["censored_interval_consistent"] for item in answered if "censored_interval_consistent" in item]
    return {"cases": len(details), "unique_input_count": len({item["input_identity"] for item in details}),
            "eligible_mic_cases": len(eligible), "answered_mic_cases": len(answered),
            "numeric_answer_coverage": len(answered) / len(eligible) if eligible else None,
            "exact_answered_cases": len(errors), "mean_absolute_log2_error": sum(errors) / len(errors) if errors else None,
            "within_one_twofold_step": sum(error <= 1 for error in errors) / len(errors) if errors else None,
            "censored_answered_cases": len(censored), "censored_interval_consistency": sum(censored) / len(censored) if censored else None}


def score_species_evaluation(manifest_path: str | Path, predictions_path: str | Path, *, split: str = "test") -> dict:
    """Read private canonical MICs only after predictions have been saved."""
    manifest_file = Path(manifest_path)
    manifest = validate_species_evaluation(manifest_file)
    if manifest["status"] != "ready":
        raise ValueError("evaluation_not_ready")
    if split not in {"train", "validation", "test"}:
        raise ValueError("invalid_evaluation_split")
    indexed = [json.loads(line) for line in (manifest_file.parent / "answers.index.jsonl").read_text().splitlines() if line]
    cases = {row["case_id"]: row for row in indexed if row["split"] == split}
    inputs = {row["case_id"]: row["input"] for row in (
        json.loads(line) for line in (manifest_file.parent / "inputs.jsonl").read_text().splitlines() if line) if row["split"] == split}
    predictions = {}
    for line in Path(predictions_path).read_text().splitlines():
        if not line.strip():
            continue
        prediction = json.loads(line)
        case_id = prediction.get("case_id") or prediction.get("candidate", {}).get("id")
        if case_id in predictions:
            raise ValueError("duplicate_prediction_case")
        if case_id not in cases:
            raise ValueError("prediction_case_outside_requested_split")
        predictions[case_id] = prediction
    details = []
    with ExitStack() as stack:
        streams = {source["id"]: stack.enter_context(Path(source["path"]).open("rb")) for source in manifest["label_sources"]}
        for case_id, reference in cases.items():
            stream = streams[reference["label_file_id"]]
            stream.seek(reference["byte_offset"])
            record = ExperimentRecord.model_validate_json(stream.readline())
            if record.record_id != reference["record_id"]:
                raise ValueError("frozen_answer_reference_mismatch")
            label = record.endpoint
            detail = {"case_id": case_id, "record_id": record.record_id,
                      "input_identity": _input_identity(inputs[case_id]),
                      "taxon_id": inputs[case_id]["organism"]["taxon_id"], "scored": False,
                      "eligible_mic": label.kind == "MIC" and label.unit == "ug/mL"}
            if not detail["eligible_mic"]:
                detail["reason"] = "endpoint_not_mic_mass_concentration"
                details.append(detail)
                continue
            prediction = predictions.get(case_id, {})
            assessment = prediction.get("assessment")
            estimate = assessment.get("mic_estimate") if isinstance(assessment, dict) else None
            estimate = estimate if isinstance(estimate, dict) else {}
            value = estimate.get("value")
            if (prediction.get("status") != "completed" or isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value <= 0 or estimate.get("unit") != "ug/mL" or estimate.get("basis") != "llm_estimate"):
                detail["reason"] = "unanswered_or_invalid_estimate"
            else:
                detail["scored"] = True
                if label.relation == "=":
                    detail["absolute_log2_error"] = abs(math.log2(value / label.value))
                else:
                    detail["censored_interval_consistent"] = (
                        (label.lower is None or value > label.lower or label.lower_closed and value == label.lower)
                        and (label.upper is None or value < label.upper or label.upper_closed and value == label.upper))
            details.append(detail)
    by_species = [{"taxon_id": item["taxon_id"], "scientific_name": item["scientific_name"],
                   **_metrics([detail for detail in details if detail["taxon_id"] == item["taxon_id"]])}
                  for item in manifest["splits"][split]["species"]]
    macro, macro_counts = {}, {}
    for name in ("numeric_answer_coverage", "mean_absolute_log2_error", "within_one_twofold_step", "censored_interval_consistency"):
        available = [item[name] for item in by_species if item[name] is not None]
        macro[name] = sum(available) / len(available) if available else None
        macro_counts[name] = len(available)
    return {"schema_version": "praxis.species-evaluation-score.v1", "split": split, **_metrics(details),
            "per_species": by_species, "macro": macro, "macro_species_counts": macro_counts, "details": details,
            "limitations": ["Errors apply only to numeric answers; coverage includes unanswered eligible cases.",
                            "Censored interval consistency does not measure precise potency accuracy.",
                            "Macro metrics average only species with defined denominators; counts are reported for each metric.",
                            "Multiple MICs for one molecule/species remain heterogeneous observations, not independent molecules."]}
