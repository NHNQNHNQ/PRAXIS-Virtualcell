"""Index measured labels against one reference per species and modality.

MIC answers stay in their existing canonical JSONL files. The inference export
uses an explicit whitelist and never reads those files or their assay metadata.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from praxis_virtualcell.datasets.labels import ExperimentRecord
from praxis_virtualcell.omics.profiles import load_profile

SPECIES = {
    470: ("Acinetobacter baumannii", "AB-SPECIES-REFERENCE"),
    562: ("Escherichia coli", "EC-SPECIES-REFERENCE"),
    573: ("Klebsiella pneumoniae", "KP-SPECIES-REFERENCE"),
    287: ("Pseudomonas aeruginosa", "PA-SPECIES-REFERENCE"),
}
_MODALITIES = ("genome", "transcriptome", "proteome")


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _taxon(value) -> int:
    return int(str(value).removeprefix("NCBITaxon:"))


def register_references(selection_path, profile_root) -> dict:
    """Validate selected native profiles before writing species collection manifests."""
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    root = Path(profile_root).resolve()
    references = {taxon: {} for taxon in SPECIES}
    for item in selection["references"]:
        if item["status"] != "ready":
            continue
        taxon = _taxon(item["taxon_id"])
        if taxon not in SPECIES or item["modality"] not in _MODALITIES:
            raise ValueError("unsupported species or modality in reference selection")
        modality = item["modality"]
        if modality in references[taxon]:
            raise ValueError("only one selected reference per species and modality is allowed")
        profile = load_profile(item["profile_id"], root).select_modalities([modality])
        overview = profile.overview()
        identity = overview["species"]
        if (_taxon(identity["taxonomy_id"]) != taxon
                or identity["scientific_name"] != SPECIES[taxon][0]):
            raise ValueError("selected reference species identity mismatch")
        if overview.get("prediction_scope") == "species_reference":
            raise ValueError("reference collections must point directly to native profiles")
        references[taxon][modality] = {
            "profile_id": item["profile_id"],
            "reference_strain": overview["strain"],
            "selection_reason": item["selection_reason"],
            "source_manifest": str(root / item["profile_id"] / "manifest.json"),
        }
    registry = {"schema_version": "praxis.species-registry.v1", "prediction_scope": "species_reference",
                "profile_root": str(root), "species": [], "gaps": selection.get("gaps", [])}
    for taxon, (name, collection_id) in SPECIES.items():
        native = references[taxon]
        entry = {"taxon_id": taxon, "scientific_name": name,
                 "profile_id": collection_id if native else None,
                 "reference_profiles": native,
                 "available_modalities": [m for m in _MODALITIES if m in native],
                 "missing_modalities": [m for m in _MODALITIES if m not in native]}
        if native:
            manifest = {
                "schema_version": "praxis.species-reference.v1", "profile_id": collection_id,
                "species": {"scientific_name": name, "taxonomy_id": f"NCBITaxon:{taxon}"},
                "reference_profiles": {m: data["profile_id"] for m, data in native.items()},
                "input_role": "species_reference", "relation": "species_level_reference",
                "prediction_scope": "species_reference",
                "selection_reasons": {m: data["selection_reason"] for m, data in native.items()},
            }
            destination = root / collection_id / "manifest.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(_json(manifest) + "\n", encoding="utf-8")
            load_profile(collection_id, root)
        registry["species"].append(entry)
    return registry


_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE species(taxon_id INTEGER PRIMARY KEY, scientific_name TEXT UNIQUE NOT NULL,
                     profile_id TEXT UNIQUE);
CREATE TABLE reference_modalities(
    taxon_id INTEGER NOT NULL REFERENCES species, modality TEXT NOT NULL,
    profile_id TEXT NOT NULL, reference_strain TEXT, source_manifest TEXT NOT NULL,
    selection_reason TEXT NOT NULL, PRIMARY KEY(taxon_id, modality));
CREATE TABLE label_files(id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, sha256 TEXT NOT NULL);
CREATE TABLE compounds(identity_key TEXT PRIMARY KEY, canonical_smiles TEXT NOT NULL);
CREATE TABLE experiments(
    record_id TEXT PRIMARY KEY, case_id TEXT UNIQUE NOT NULL, native_key TEXT UNIQUE NOT NULL,
    taxon_id INTEGER NOT NULL REFERENCES species,
    compound_id TEXT NOT NULL REFERENCES compounds(identity_key),
    source_molecule_id TEXT NOT NULL, experimental_strain TEXT, strain_namespace TEXT,
    isolate_id TEXT, source_id TEXT NOT NULL, activity_id TEXT, assay_id TEXT,
    document_id TEXT, doi TEXT, endpoint_kind TEXT NOT NULL, censoring TEXT NOT NULL,
    label_file_id INTEGER NOT NULL REFERENCES label_files(id), byte_offset INTEGER NOT NULL,
    line_number INTEGER NOT NULL);
CREATE INDEX species_compound ON experiments(taxon_id, compound_id);
CREATE INDEX source_study ON experiments(document_id);
"""


def _native_key(record: ExperimentRecord) -> str:
    source = record.source
    if source.activity_id and source.origin == "experimental_database" and "chembl" in source.source_id.lower():
        return "chembl:activity:" + source.activity_id
    return source.source_id


def build_species_database(selection_path, label_paths, output_dir, *, profile_root) -> dict:
    """Build a derived SQLite index; no MIC values or original omics are copied."""
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    db_path = destination / "praxis_species_reference.sqlite3"
    if db_path.exists():
        raise ValueError("database output already exists; select a new version directory")
    registry = register_references(selection_path, profile_root)
    excluded, duplicates = Counter(), 0
    paths = list(dict.fromkeys(Path(path).resolve() for path in label_paths))
    staging = db_path.with_suffix(".building")
    try:
        with sqlite3.connect(staging) as connection:
            connection.executescript(_SCHEMA)
            connection.execute("INSERT INTO metadata VALUES (?,?)", ("schema_version", "praxis.species-database.v1"))
            connection.execute("INSERT INTO metadata VALUES (?,?)", ("prediction_scope", "species_reference"))
            for entry in registry["species"]:
                connection.execute("INSERT INTO species VALUES (?,?,?)",
                                   (entry["taxon_id"], entry["scientific_name"], entry["profile_id"]))
                for modality, item in entry["reference_profiles"].items():
                    connection.execute("INSERT INTO reference_modalities VALUES (?,?,?,?,?,?)", (
                        entry["taxon_id"], modality, item["profile_id"], item["reference_strain"],
                        item["source_manifest"], item["selection_reason"]))
            names = {name.casefold(): taxon for taxon, (name, _) in SPECIES.items()}
            for path in paths:
                cursor = connection.execute("INSERT INTO label_files(path,sha256) VALUES (?,?)", (str(path), _digest(path)))
                file_id = cursor.lastrowid
                with path.open("rb") as stream:
                    for line_number in range(1, 10**10):
                        offset = stream.tell()
                        line = stream.readline()
                        if not line:
                            break
                        if not line.strip():
                            continue
                        record = ExperimentRecord.model_validate_json(line)
                        taxon = names.get(record.organism.species.strip().casefold())
                        if taxon is None:
                            excluded["outside_selected_species"] += 1
                            continue
                        if record.organism.taxon_id is not None and record.organism.taxon_id != taxon:
                            excluded["conflicting_species_taxonomy"] += 1
                            continue
                        if not record.admission.label_eligible or record.endpoint.kind != "MIC":
                            excluded["not_admitted_measured_MIC"] += 1
                            continue
                        native_key = _native_key(record)
                        prior = connection.execute(
                            "SELECT e.compound_id,e.taxon_id,f.path,e.byte_offset FROM experiments e "
                            "JOIN label_files f ON f.id=e.label_file_id WHERE e.native_key=? OR e.record_id=?",
                            (native_key, record.record_id)).fetchone()
                        if prior:
                            with Path(prior[2]).open("rb") as previous:
                                previous.seek(prior[3])
                                original = ExperimentRecord.model_validate_json(previous.readline())
                            endpoint_fields = {"kind", "relation", "unit", "value", "lower", "upper", "lower_closed", "upper_closed"}
                            if (prior[:2] != (record.molecule.identity_key, taxon)
                                    or original.endpoint.model_dump(include=endpoint_fields) != record.endpoint.model_dump(include=endpoint_fields)
                                    or original.organism.model_dump() != record.organism.model_dump()
                                    or original.conditions.model_dump() != record.conditions.model_dump()
                                    or (original.source.assay_id, original.source.document_id) != (record.source.assay_id, record.source.document_id)):
                                raise ValueError("conflicting native experiment identity across label files")
                            duplicates += 1
                            continue
                        molecule = record.molecule
                        prior_smiles = connection.execute("SELECT canonical_smiles FROM compounds WHERE identity_key=?",
                                                          (molecule.identity_key,)).fetchone()
                        if prior_smiles and prior_smiles[0] != molecule.canonical_smiles:
                            raise ValueError("compound identity key has conflicting canonical structures")
                        connection.execute("INSERT OR IGNORE INTO compounds VALUES (?,?)",
                                           (molecule.identity_key, molecule.canonical_smiles))
                        source, organism = record.source, record.organism
                        case_id = "case-" + hashlib.sha256(record.record_id.encode()).hexdigest()[:24]
                        connection.execute("INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                            record.record_id, case_id, native_key, taxon, molecule.identity_key, molecule.source_molecule_id,
                            organism.strain, organism.strain_namespace, organism.isolate_id, source.source_id,
                            source.activity_id, source.assay_id, source.document_id, source.doi, record.endpoint.kind,
                            record.endpoint.censoring, file_id, offset, line_number,
                        ))
        staging.replace(db_path)
    except Exception:
        staging.unlink(missing_ok=True)
        raise
    summary = database_coverage(db_path)
    summary.update(excluded=dict(excluded), duplicate_native_experiments_skipped=duplicates,
                   raw_assets_copied=False, MIC_values_copied=False,
                   pairing_relation="species_level_reference", label_files=[str(path) for path in paths])
    (destination / "registry.json").write_text(_json(registry) + "\n", encoding="utf-8")
    (destination / "coverage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def database_coverage(db_path) -> dict:
    with sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True) as connection:
        species = []
        for taxon, name, profile in connection.execute("SELECT * FROM species ORDER BY taxon_id"):
            total, compounds, studies = connection.execute(
                "SELECT COUNT(*),COUNT(DISTINCT compound_id),COUNT(DISTINCT document_id) FROM experiments WHERE taxon_id=?",
                (taxon,)).fetchone()
            modalities = [row[0] for row in connection.execute(
                "SELECT modality FROM reference_modalities WHERE taxon_id=? ORDER BY modality", (taxon,))]
            censoring = dict(connection.execute("SELECT censoring,COUNT(*) FROM experiments WHERE taxon_id=? GROUP BY censoring", (taxon,)))
            species.append({"taxon_id": taxon, "scientific_name": name, "profile_id": profile,
                            "MIC_records": total, "unique_compounds": compounds, "studies": studies,
                            "available_modalities": modalities,
                            "missing_modalities": [m for m in _MODALITIES if m not in modalities],
                            "species_reference_input_records": total if profile else 0, "censoring": censoring})
        return {"schema_version": "praxis.species-database-coverage.v1", "database": str(Path(db_path).resolve()),
                "prediction_scope": "species_reference", "species": species,
                "MIC_records": connection.execute("SELECT COUNT(*) FROM experiments").fetchone()[0],
                "unique_compounds": connection.execute("SELECT COUNT(*) FROM compounds").fetchone()[0]}


def export_species_inputs(db_path, output_path) -> int:
    """Read only species/reference/structure index fields, never canonical labels."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True) as connection, destination.open("w", encoding="utf-8") as stream:
        for case_id, smiles, taxon, species, profile in connection.execute(
            "SELECT e.case_id,c.canonical_smiles,s.taxon_id,s.scientific_name,s.profile_id "
            "FROM experiments e JOIN compounds c ON c.identity_key=e.compound_id "
            "JOIN species s ON s.taxon_id=e.taxon_id WHERE s.profile_id IS NOT NULL ORDER BY e.record_id"
        ):
            input_data = {"candidate": {"id": case_id, "smiles": smiles},
                          "organism": {"species": species, "taxon_id": taxon},
                          "profile_id": profile, "prediction_scope": "species_reference"}
            stream.write(_json({"case_id": case_id, "input": input_data}) + "\n")
            count += 1
    return count


def read_experimental_answer(db_path, record_id: str) -> ExperimentRecord:
    """Explicit private label access for curation/supervision/evaluation only."""
    with sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True) as connection:
        item = connection.execute(
            "SELECT f.path,e.byte_offset,f.sha256,e.record_id FROM experiments e JOIN label_files f ON f.id=e.label_file_id "
            "WHERE e.record_id=? OR e.case_id=?",
            (record_id, record_id)).fetchone()
    if item is None:
        raise KeyError(record_id)
    if _digest(Path(item[0])) != item[2]:
        raise ValueError("canonical label file changed; rebuild the derived index")
    with Path(item[0]).open("rb") as stream:
        stream.seek(item[1])
        record = ExperimentRecord.model_validate_json(stream.readline())
    if record.record_id != item[3]:
        raise ValueError("canonical label file changed; rebuild the derived index")
    return record
