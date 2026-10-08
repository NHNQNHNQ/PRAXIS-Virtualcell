"""Build a small SQLite inspection index over joint training JSONL records.

The conversations, omics and literature remain in their existing files. Only
training rows are indexed; held-out MIC sources are never opened. The SQLite
record locators point to the one canonical joint.train.jsonl and source index.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

from .joint_qwen_sft import SCHEMA as DATASET_SCHEMA, TARGET_CONTRACT
from .species_registry import _digest, _json

SCHEMA = "praxis.joint-inspection-index.v1"


def _positioned_rows(path: Path):
    with path.open("rb") as stream:
        line_number = 0
        while True:
            offset = stream.tell()
            line = stream.readline()
            if not line:
                break
            line_number += 1
            if line.strip():
                yield json.loads(line), {"file": str(path), "byte_offset": offset, "line_number": line_number}


def _key(prefix: str, value) -> str:
    return prefix + hashlib.sha256(_json(value).encode()).hexdigest()[:24]


def _overview(record: dict) -> dict:
    for message in record["messages"]:
        if message["role"] == "tool":
            reply = json.loads(message["content"])
            if reply.get("name") == "overview" and reply.get("ok") is True:
                return reply.get("data", {})
    return {}


def _omics_summary(record: dict, request: dict) -> dict:
    overview = _overview(record)
    available = request["available_modalities"]
    selected = overview.get("selected_modalities", available)
    if set(selected) - set(available):
        raise ValueError("inspection_selected_modality_not_available")
    native_profiles = overview.get("reference_profiles", {})
    native = overview.get("modalities", {})
    modalities = []
    for name in selected:
        item = native.get(name, {})
        modalities.append({"modality": name, "native_profile_id": native_profiles.get(name, item.get("profile_id")),
                           "feature_count": item.get("feature_count"), "source_samples": item.get("source_samples", []),
                           "reference_condition": item.get("condition"),
                           "value_semantics": item.get("value_semantics")})
    return {"profile_id": request["profile_id"], "available_modalities": available,
            "selected_modalities": selected, "modalities": modalities,
            "reference_relation": overview.get("relation", "same_strain_reference"),
            "paired_with_MIC_experiment": False,
            "limitation": "Same-strain reference modalities can have different samples and conditions; they are not a paired MIC culture."}


def _component_cases(component_dir: Path) -> dict[str, dict]:
    summary = json.loads((component_dir / "summary.json").read_text())
    component_path = component_dir / "mic_sft.jsonl"
    if _digest(component_path) != summary["files"]["mic_sft.jsonl"]["sha256"]:
        raise ValueError("inspection_component_source_changed")
    dataset_summary = Path(summary["dataset_summary"])
    if _digest(dataset_summary) != summary["dataset_summary_sha256"]:
        raise ValueError("inspection_strain_dataset_changed")
    cases = {row["case_id"]: row for row, _ in _positioned_rows(dataset_summary.parent / "cases.jsonl")}
    components = {row["record_id"]: row for row, _ in _positioned_rows(component_path)}
    return {"cases": cases, "components": components}


def _select_samples(samples: list[dict], count: int) -> list[dict]:
    selected, identifiers = [], set()
    def choose(candidate):
        if candidate is not None and len(selected) < count and candidate["record_id"] not in identifiers:
            identifiers.add(candidate["record_id"])
            selected.append(candidate)
    for grade in ("experimental", "genetic", "author_proposed", "unresolved", "class_background"):
        choose(next((row for row in samples if any(claim["evidence_grade"] == grade
                                                   for claim in row["mechanism_claims"])), None))
    # Prefer a previously unseen species/strain tuple and real modality selection.
    for row in samples:
        strains = {_json(item["strain"]) for item in selected}
        modalities = {tuple(item["omics"]["selected_modalities"]) for item in selected}
        if _json(row["strain"]) not in strains or tuple(row["omics"]["selected_modalities"]) not in modalities:
            choose(row)
    for row in samples:
        choose(row)
    return selected


def prepare_joint_inspection(dataset_dir: str | Path, output_dir: str | Path, *,
                             component_dir: str | Path | None = None, sample_count: int = 8) -> dict:
    """Index verified joint train rows without opening any native MIC label file."""
    dataset, output = Path(dataset_dir).resolve(), Path(output_dir).resolve()
    if sample_count < 1 or sample_count > 100:
        raise ValueError("inspection_sample_count_must_be_between_1_and_100")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("joint_inspection_output_nonempty")
    if output == dataset or output.is_relative_to(dataset):
        raise ValueError("inspection_output_must_be_separate_from_dataset")
    manifest_path = dataset / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != DATASET_SCHEMA:
        raise ValueError("inspection_requires_joint_Qwen_dataset")
    paths = {name: dataset / name for name in ("train.jsonl", "joint.train.jsonl", "source_refs.jsonl")}
    for name, path in paths.items():
        if _digest(path) != manifest["files"][name]["sha256"]:
            raise ValueError("inspection_training_source_changed")
    mixed = {row["record_id"]: row for row, _ in _positioned_rows(paths["train.jsonl"])}
    sources = {row["record_id"]: (row, locator) for row, locator in _positioned_rows(paths["source_refs.jsonl"])}
    component_snapshot = _component_cases(Path(component_dir).resolve()) if component_dir is not None else None
    rows, samples, used_components = [], [], set()
    for record, record_locator in _positioned_rows(paths["joint.train.jsonl"]):
        if record != mixed.get(record["record_id"]) or record.get("target_contract") != TARGET_CONTRACT:
            raise ValueError("inspection_joint_subset_does_not_match_train")
        source, source_locator = sources[record["record_id"]]
        component_id = record["source_record_id"]
        if (source.get("split") != "train" or source.get("component_id") != component_id
                or source.get("mechanism_admission") != "agent_source_reviewed"
                or source.get("human_gold") is not False or component_id in used_components):
            raise ValueError("inspection_only_admits_distinct_agent_reviewed_train_components")
        used_components.add(component_id)
        members = source["source_refs"]
        annotation = source["literature_review"]["annotation"]
        case_ids = [member["case_id"] for member in members]
        if annotation.get("review_status") != "source_reviewed" or set(annotation["case_ids"]) != set(case_ids):
            raise ValueError("inspection_review_case_binding_mismatch")
        if component_snapshot is not None:
            component = component_snapshot["components"][component_id]
            if component["split"] != "train" or component.get("trainable") is not True or set(component["case_ids"]) != set(case_ids):
                raise ValueError("inspection_cannot_admit_heldout_component")
            for member in members:
                case = component_snapshot["cases"][member["case_id"]]
                if case["split"] != "train" or member["locator"] != case["private_answer"]:
                    raise ValueError("inspection_cannot_admit_heldout_MIC_source")
        request = json.loads(record["messages"][1]["content"])
        target = json.loads(record["messages"][-1]["content"])
        strain = request["organism"]
        if (request.get("prediction_scope") != "strain_reference" or not request.get("profile_id")
                or not request.get("available_modalities") or not strain.get("species") or not strain.get("label")):
            raise ValueError("inspection_requires_explicit_strain_and_real_reference_modalities")
        if target["endpoint"] != "MIC" or target["unit"] != "ug/mL" or len(target["observations"]) != len(members):
            raise ValueError("inspection_MIC_source_count_or_endpoint_mismatch")
        omics = _omics_summary(record, request)
        sample = {"record_id": record["record_id"], "component_id": component_id, "split": "train",
                  "record_locator": record_locator, "source_ref_locator": source_locator, "case_ids": case_ids,
                  "drug": request["candidate"], "strain": strain, "conditions": request["conditions"],
                  "omics": omics, "MIC": {key: target[key] for key in ("endpoint", "unit", "observations")},
                  "MIC_label_origin": "source_verified_experimental_MIC",
                  "mechanism_claims": target["mechanism_claims"],
                  "mechanism_limitations": target["mechanism_limitations"],
                  "mechanism_supervision": "agent_source_reviewed_weak_supervision", "human_gold": False}
        samples.append(sample)
        rows.append((record, source, sample))
    if not rows or len(rows) != manifest["mechanism_training_records"]:
        raise ValueError("inspection_joint_record_count_mismatch")

    output.mkdir(parents=True, exist_ok=True)
    index_path = output / "joint_index.sqlite"
    with sqlite3.connect(index_path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript("""
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE drug (drug_id TEXT PRIMARY KEY, canonical_smiles TEXT NOT NULL);
            CREATE TABLE strain (strain_key TEXT PRIMARY KEY, strain_id TEXT, label TEXT NOT NULL,
                                 species TEXT NOT NULL, taxon_id INTEGER, namespace TEXT, identity_basis TEXT);
            CREATE TABLE profile (profile_key TEXT PRIMARY KEY, profile_id TEXT NOT NULL,
                                  strain_key TEXT NOT NULL REFERENCES strain(strain_key), reference_relation TEXT,
                                  paired_with_MIC_experiment INTEGER NOT NULL CHECK(paired_with_MIC_experiment=0));
            CREATE TABLE profile_modality (profile_key TEXT REFERENCES profile(profile_key), modality TEXT NOT NULL,
                                           native_profile_id TEXT, feature_count INTEGER, source_samples TEXT,
                                           reference_condition TEXT, PRIMARY KEY(profile_key, modality));
            CREATE TABLE paper (doi TEXT PRIMARY KEY, article_url TEXT, private_article_file TEXT);
            CREATE TABLE record (record_id TEXT PRIMARY KEY, component_id TEXT UNIQUE NOT NULL,
                                 drug_id TEXT NOT NULL REFERENCES drug(drug_id),
                                 strain_key TEXT NOT NULL REFERENCES strain(strain_key),
                                 profile_key TEXT NOT NULL REFERENCES profile(profile_key),
                                 split TEXT NOT NULL CHECK(split='train'), target_contract TEXT NOT NULL,
                                 record_file TEXT NOT NULL, record_byte_offset INTEGER NOT NULL, record_line_number INTEGER NOT NULL,
                                 source_ref_file TEXT NOT NULL, source_ref_byte_offset INTEGER NOT NULL,
                                 source_ref_line_number INTEGER NOT NULL, conditions TEXT, MIC_observations TEXT,
                                 MIC_label_origin TEXT NOT NULL, mechanism_supervision TEXT NOT NULL,
                                 human_gold INTEGER NOT NULL CHECK(human_gold=0), evidence_grade_summary TEXT,
                                 experiment_type_summary TEXT, mechanism_scope_summary TEXT);
            CREATE TABLE record_case (record_id TEXT REFERENCES record(record_id), case_id TEXT NOT NULL,
                                      PRIMARY KEY(record_id, case_id));
            CREATE TABLE record_paper (record_id TEXT REFERENCES record(record_id), doi TEXT REFERENCES paper(doi),
                                       PRIMARY KEY(record_id, doi));
            CREATE INDEX record_strain_idx ON record(strain_key);
            CREATE INDEX record_drug_idx ON record(drug_id);
            CREATE INDEX record_profile_idx ON record(profile_key);
        """)
        connection.executemany("INSERT INTO metadata VALUES (?, ?)", [
            ("schema_version", SCHEMA), ("dataset_manifest", str(manifest_path)),
            ("dataset_manifest_sha256", _digest(manifest_path)),
            ("joint_train_sha256", _digest(paths["joint.train.jsonl"])),
            ("source_refs_sha256", _digest(paths["source_refs.jsonl"])),
            ("heldout_MIC_sources_opened", "0"), ("raw_assets_copied", "false")])
        for record, source, sample in rows:
            strain, omics = sample["strain"], sample["omics"]
            drug_id = _key("drug:", sample["drug"]["smiles"])
            strain_key = _key("strain:", strain)
            profile_key = _key("profile:", [omics["profile_id"], strain_key, omics["selected_modalities"]])
            connection.execute("INSERT OR IGNORE INTO drug VALUES (?, ?)", (drug_id, sample["drug"]["smiles"]))
            connection.execute("INSERT OR IGNORE INTO strain VALUES (?, ?, ?, ?, ?, ?, ?)", (
                strain_key, strain.get("strain_id"), strain["label"], strain["species"], strain.get("taxon_id"),
                strain.get("namespace"), strain.get("identity_basis")))
            connection.execute("INSERT OR IGNORE INTO profile VALUES (?, ?, ?, ?, 0)", (
                profile_key, omics["profile_id"], strain_key, omics["reference_relation"]))
            for modality in omics["modalities"]:
                connection.execute("INSERT OR IGNORE INTO profile_modality VALUES (?, ?, ?, ?, ?, ?)", (
                    profile_key, modality["modality"], modality["native_profile_id"], modality["feature_count"],
                    _json(modality["source_samples"]), _json(modality["reference_condition"])))
            record_locator, source_locator = sample["record_locator"], sample["source_ref_locator"]
            connection.execute("INSERT INTO record VALUES (" + ",".join("?" for _ in range(21)) + ")", (
                record["record_id"], sample["component_id"], drug_id, strain_key, profile_key, "train", TARGET_CONTRACT,
                record_locator["file"], record_locator["byte_offset"], record_locator["line_number"],
                source_locator["file"], source_locator["byte_offset"], source_locator["line_number"],
                _json(sample["conditions"]), _json(sample["MIC"]["observations"]), sample["MIC_label_origin"],
                sample["mechanism_supervision"], 0,
                _json(dict(Counter(claim["evidence_grade"] for claim in sample["mechanism_claims"]))),
                _json(dict(Counter(claim["experiment_type"] for claim in sample["mechanism_claims"]))),
                _json(sorted({claim["scope"] for claim in sample["mechanism_claims"]}))))
            connection.executemany("INSERT INTO record_case VALUES (?, ?)", [(record["record_id"], case_id) for case_id in sample["case_ids"]])
            article = source["literature_review"]["paper_source"]
            dois = {evidence["doi"] for claim in sample["mechanism_claims"] for evidence in claim["sources"]}
            for doi in sorted(dois):
                connection.execute("INSERT OR IGNORE INTO paper VALUES (?, ?, ?)", (doi, article.get("url"), article.get("file")))
                connection.execute("INSERT INTO record_paper VALUES (?, ?)", (record["record_id"], doi))
        table_counts = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        for table in ("record", "drug", "strain", "profile", "paper", "record_case")}
    selected = _select_samples(samples, sample_count)
    preview_path = output / "inspection_samples.json"
    preview_path.write_text(json.dumps({"schema_version": SCHEMA, "samples": selected}, ensure_ascii=False, indent=2) + "\n")
    combinations = Counter("+".join(sorted(sample["omics"]["selected_modalities"])) for sample in samples)
    report = {"schema_version": SCHEMA, "record_count": len(rows), "MIC_measurement_count": sum(len(row[2]["case_ids"]) for row in rows),
              "table_counts": table_counts, "modalities": dict(combinations),
              "single_modality_record_count": sum(len(sample["omics"]["selected_modalities"]) == 1 for sample in samples),
              "multiple_modality_record_count": sum(len(sample["omics"]["selected_modalities"]) > 1 for sample in samples),
              "sample_count": len(selected), "MIC_label_origin": "source_verified_experimental_MIC",
              "mechanism_supervision": "agent_source_reviewed_weak_supervision", "human_gold": False,
              "heldout_MIC_sources_opened": 0, "raw_assets_copied": False,
              "full_omics_or_literature_copied_into_SQLite": False,
              "dataset_manifest": {"file": str(manifest_path), "sha256": _digest(manifest_path)},
              "files": {"joint_index.sqlite": {"sha256": _digest(index_path)},
                        "inspection_samples.json": {"sha256": _digest(preview_path)}},
              "limitations": ["SQLite is an inspection index, not a second raw dataset or a training source.",
                               "A known training MIC is supervised experimental data, not an inference lookup tool.",
                               "Mechanism statements remain agent source-reviewed weak supervision, not human gold.",
                               "Only available reference modalities are indexed; no missing modality is synthesized."]}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def load_indexed_record(index_path: str | Path, record_id: str) -> dict:
    """Resolve a SQLite locator into the unchanged JSONL row and its private source."""
    with sqlite3.connect(f"file:{Path(index_path).resolve()}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        indexed = connection.execute("SELECT * FROM record WHERE record_id=?", (record_id,)).fetchone()
        if indexed is None:
            raise KeyError(record_id)
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        for field, receipt in (("record_file", "joint_train_sha256"), ("source_ref_file", "source_refs_sha256")):
            if _digest(Path(indexed[field])) != metadata[receipt]:
                raise ValueError("indexed_joint_source_changed")
        result = {}
        for name, field, offset in (("record", "record_file", "record_byte_offset"),
                                   ("source_ref", "source_ref_file", "source_ref_byte_offset")):
            with Path(indexed[field]).open("rb") as stream:
                stream.seek(indexed[offset])
                row = json.loads(stream.readline())
            if row["record_id"] != record_id:
                raise ValueError("indexed_record_locator_mismatch")
            result[name] = row
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--component-dir")
    parser.add_argument("--sample-count", type=int, default=8)
    args = parser.parse_args()
    result = prepare_joint_inspection(args.dataset_dir, args.output_dir,
                                      component_dir=args.component_dir, sample_count=args.sample_count)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
