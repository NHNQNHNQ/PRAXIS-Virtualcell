"""Freeze experiment groups and score predictions without giving labels to an LLM."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Literal

from .labels import ExperimentRecord

Grouping = Literal["compound", "scaffold", "strain", "study", "joint"]


def read_experiments(path: str | Path) -> list[ExperimentRecord]:
    records = [ExperimentRecord.model_validate_json(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("duplicate_experiment_record_ids")
    return records


def _compound_key(record: ExperimentRecord) -> str:
    # Remove counterions/neutralize only for split grouping; tested forms stay in
    # the record and are never silently merged into a new measurement.
    from rdkit import Chem
    from rdkit.Chem.MolStandardize import rdMolStandardize
    molecule = Chem.MolFromSmiles(record.molecule.canonical_smiles)
    if molecule is None:
        raise ValueError("invalid_experiment_structure")
    parent = rdMolStandardize.ChargeParent(molecule)
    return Chem.MolToSmiles(parent, isomericSmiles=True)


def _keys(record: ExperimentRecord, grouping: Grouping) -> list[str]:
    compound = _compound_key(record)
    if grouping == "compound":
        return [f"compound:{compound}"]
    if grouping == "scaffold":
        from rdkit import Chem
        from rdkit.Chem.Scaffolds import MurckoScaffold
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=Chem.MolFromSmiles(compound))
        # All acyclic compounds stay together; don't imply scaffold novelty from
        # an arbitrary different molecule identifier on an empty scaffold.
        return [f"scaffold:{scaffold or 'ACYCLIC'}"]
    strain = record.organism.isolate_id or record.organism.strain
    namespace = record.organism.strain_namespace
    study = record.source.document_id or record.source.doi
    if grouping == "strain":
        if not strain or record.organism.identity_evidence in {"unresolved", "conflicting"}:
            raise ValueError("verified_strain_identity_required")
        if not namespace:
            raise ValueError("strain_namespace_required")
        return [f"strain:{record.organism.species}:{namespace}:{strain}"]
    if grouping == "study":
        if not study:
            raise ValueError("study_identity_required")
        return [f"study:{study}"]
    if grouping == "joint":
        if not strain or not namespace or not study or record.organism.identity_evidence in {"unresolved", "conflicting"}:
            raise ValueError("joint_requires_verified_strain_and_study")
        return [f"compound:{compound}", f"strain:{record.organism.species}:{namespace}:{strain}", f"study:{study}"]
    raise ValueError("invalid_split_grouping")


def freeze_evaluation(
    label_path: str | Path, output_dir: str | Path, *, grouping: Grouping = "compound",
    seed: int = 20261007, test_fraction: float = 0.2, validation_fraction: float = 0.1,
    paired_only: bool = False,
) -> dict:
    """Group before generating modality views; preserve the canonical label file.

    Frozen inputs contain no endpoints or assay descriptions. The private answer
    index references source records instead of duplicating experimental labels.
    Joint splitting joins all shared identities transitively, so one large
    component can legitimately make an independent split impossible.
    """
    if (isinstance(seed, bool) or not isinstance(seed, int)
            or not 0 < test_fraction < 1 or not 0 < validation_fraction < 1
            or test_fraction + validation_fraction >= 1):
        raise ValueError("invalid_split_parameters")
    if grouping not in {"compound", "scaffold", "strain", "study", "joint"}:
        raise ValueError("invalid_split_grouping")
    source = Path(label_path).resolve()
    records = read_experiments(source)
    chosen = []
    excluded = []
    for record in records:
        if not record.admission.label_eligible or paired_only and not record.admission.paired_omics_eligible:
            excluded.append({"record_id": record.record_id, "reason": "required_admission_not_met"})
            continue
        try:
            keys = _keys(record, grouping)
        except ValueError as exc:
            excluded.append({"record_id": record.record_id, "reason": str(exc)})
            continue
        chosen.append((record, keys))
    parents = list(range(len(chosen)))
    def find(index):
        while index != parents[index]:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    first = {}
    for index, (_, keys) in enumerate(chosen):
        for key in keys:
            if key in first:
                parents[find(index)] = find(first[key])
            else:
                first[key] = index
    groups = {}
    for index, (record, _) in enumerate(chosen):
        groups.setdefault(find(index), []).append(record)
    components = []
    for members in groups.values():
        identity = "\n".join(sorted(record.record_id for record in members))
        group_id = hashlib.sha256(identity.encode()).hexdigest()[:20]
        order = hashlib.sha256(f"{seed}:{group_id}".encode()).hexdigest()
        components.append((order, group_id, members))
    components.sort()
    count = len(components)
    assignments = {}
    if count >= 3:
        test_count = max(1, round(count * test_fraction))
        validation_count = max(1, round(count * validation_fraction))
        while test_count + validation_count >= count:
            if test_count > validation_count:
                test_count -= 1
            else:
                validation_count -= 1
        for index, (_, group_id, _) in enumerate(components):
            assignments[group_id] = "test" if index < test_count else "validation" if index < test_count + validation_count else "train"
    else:
        assignments = {group_id: "unassigned" for _, group_id, _ in components}
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("frozen_evaluation_destination_exists")
    destination.mkdir(parents=True, exist_ok=True)
    inputs = []
    answers = []
    split_counts = Counter()
    for _, group_id, members in components:
        split = assignments[group_id]
        for record in sorted(members, key=lambda item: item.record_id):
            case_id = f"case-{len(inputs) + 1:06d}"
            request = record.analysis_input()
            request["candidate"]["id"] = case_id
            inputs.append({"case_id": case_id, "split": split, "group_id": group_id, "input": request})
            answers.append({"case_id": case_id, "split": split, "group_id": group_id, "record_id": record.record_id})
            split_counts[split] += 1
    for filename, rows in (("inputs.jsonl", inputs), ("answers.index.jsonl", answers), ("excluded.jsonl", excluded)):
        (destination / filename).write_text("".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows))
    manifest = {
        "schema_version": "praxis.frozen-evaluation.v1", "status": "ready" if count >= 3 else "insufficient_groups",
        "grouping": grouping, "seed": seed, "paired_only": paired_only,
        "label_source": str(source), "label_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "records": len(inputs), "independent_groups": count, "split_counts": dict(split_counts),
        "largest_group_records": max((len(members) for _, _, members in components), default=0),
        "requested_group_fractions": {"test": test_fraction, "validation": validation_fraction},
        "excluded_records": len(excluded), "matched_omics_records": sum(record.admission.paired_omics_eligible for record, _ in chosen),
        "limitations": [
            "Fractions apply to groups; row counts may be imbalanced.",
            "Named strains are not genomic relatedness clusters; strain split does not establish lineage novelty.",
            "Only paired_only=true cohorts qualify for matched-omics effect evaluation.",
            "Censoring remains in the canonical experiment source, never in model-visible inputs.",
            "Sharing an input/group across modality views does not add independent experiments.",
        ],
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def score_evaluation(manifest_path: str | Path, predictions_path: str | Path, *, split: str = "test") -> dict:
    """Score only after inference. No client or inference tool sees this module."""
    manifest_file = Path(manifest_path)
    manifest = json.loads(manifest_file.read_text())
    if manifest.get("schema_version") != "praxis.frozen-evaluation.v1" or manifest.get("status") != "ready":
        raise ValueError("evaluation_not_ready")
    if split not in {"train", "validation", "test"}:
        raise ValueError("invalid_evaluation_split")
    source = Path(manifest["label_source"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["label_source_sha256"]:
        raise ValueError("frozen_label_source_changed")
    experiments = {record.record_id: record for record in read_experiments(source)}
    indexed = [json.loads(line) for line in (manifest_file.parent / "answers.index.jsonl").read_text().splitlines() if line]
    cases = {row["case_id"]: experiments[row["record_id"]] for row in indexed if row["split"] == split}
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
    errors = []
    censored = []
    details = []
    answered = 0
    eligible = sum(record.endpoint.kind == "MIC" and record.endpoint.unit == "ug/mL" for record in cases.values())
    for case_id, record in cases.items():
        label = record.endpoint
        detail = {"case_id": case_id, "record_id": record.record_id, "scored": False}
        if label.kind != "MIC" or label.unit != "ug/mL":
            detail["reason"] = "endpoint_not_mic_mass_concentration"
            details.append(detail)
            continue
        prediction = predictions.get(case_id, {})
        assessment = prediction.get("assessment")
        estimate = assessment.get("mic_estimate") if isinstance(assessment, dict) else None
        estimate = estimate if isinstance(estimate, dict) else {}
        value = estimate.get("value")
        if (prediction.get("status") != "completed" or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value <= 0 or estimate.get("unit") != "ug/mL"
                or estimate.get("basis") != "llm_estimate"):
            detail["reason"] = "unanswered_or_invalid_estimate"
            details.append(detail)
            continue
        answered += 1
        detail["scored"] = True
        if label.relation == "=":
            error = abs(math.log2(value / label.value))
            errors.append(error)
            detail["absolute_log2_error"] = error
        else:
            consistent = ((label.lower is None or value > label.lower or label.lower_closed and value == label.lower)
                          and (label.upper is None or value < label.upper or label.upper_closed and value == label.upper))
            censored.append(consistent)
            detail["censored_interval_consistent"] = consistent
        details.append(detail)
    return {"schema_version": "praxis.evaluation-score.v1", "split": split, "cases": len(cases),
            "eligible_mic_cases": eligible, "answered_mic_cases": answered,
            "numeric_answer_coverage": answered / eligible if eligible else None,
            "exact_answered_cases": len(errors), "mean_absolute_log2_error": sum(errors) / len(errors) if errors else None,
            "within_one_twofold_step": sum(error <= 1 for error in errors) / len(errors) if errors else None,
            "censored_answered_cases": len(censored),
            "censored_interval_consistency": sum(censored) / len(censored) if censored else None,
            "matched_omics_cases": sum(record.admission.paired_omics_eligible for record in cases.values()),
            "limitations": ["Error metrics apply only to answered cases; always report coverage alongside error.",
                            "Interval consistency alone is not a precise potency accuracy metric."], "details": details}
