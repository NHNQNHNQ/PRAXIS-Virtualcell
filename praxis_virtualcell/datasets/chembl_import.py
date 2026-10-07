"""Admit source-linked, single-agent MIC measurements from native ChEMBL records.

The bounded downloader retains native responses and receipts. Importing never
joins legacy MIC rows by SMILES/value, guesses structures, strips salts, or
infers an omics pairing. Species-level supervision is valid when strain is unknown.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .curation import canonical_identity, conditions_from_assay, organism_from_assay
from .labels import Admission, EndpointLabel, ExperimentRecord, MoleculeIdentity, RawMeasurement, SourceEvidence

SPECIES = {470: "Acinetobacter baumannii", 562: "Escherichia coli",
           573: "Klebsiella pneumoniae", 287: "Pseudomonas aeruginosa"}
BASE_URL = "https://www.ebi.ac.uk/chembl/api/data/"
LICENSE = "CC BY-SA 3.0"
_MASS_FACTORS = {
    "ug/mL": 1, "ug/ml": 1, "µg/mL": 1, "μg/mL": 1,
    "ug.mL-1": 1, "ug.ml-1": 1, "ug ml-1": 1, "ug ml^-1": 1,
    "ug ml(-1)": 1, "ug/mL-1": 1, "mg/L": 1, "mg/l": 1,
    "mg l-1": 1, "mg/mL": 1000, "mg/ml": 1000,
    "ng/mL": 0.001, "ng/ml": 0.001, "g/L": 1000,
}
_NONINDEPENDENT = re.compile(
    r"\b(?:MIC\s*[-_]?\s*(?:50|90)|potentiat\w*|adjuvant|checkerboard|FICI?|"
    r"combination|combined|synerg\w*|predicted|calculated|in\s+silico)\b|"
    r"\bin (?:the )?presence of\b|\b(?:with|plus)\s+(?:colistin|SPR741|polymyxin|"
    r"clavulan\w*|avibactam|tazobactam|sulbactam)\b", re.IGNORECASE,
)
_NAMED_SPECIES = re.compile(
    r"\b(?:Acinetobacter|Escherichia|Klebsiella|Pseudomonas|Enterobacter|Staphylococcus|"
    r"Bacillus|Streptococcus|Salmonella|Proteus|Serratia|Morganella|Enterococcus|"
    r"Mycobacterium|Candida)\s+[a-z][a-z-]+\b", re.IGNORECASE,
)


class AdmissionError(ValueError):
    """A native record was excluded with machine-readable reasons."""

    def __init__(self, *reasons: str):
        self.reasons = list(reasons)
        super().__init__(";".join(reasons))


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _experiment_signature(record: ExperimentRecord) -> str:
    return _dump({"molecule": record.molecule.model_dump(), "organism": record.organism.model_dump(),
                  "conditions": record.conditions.model_dump(), "endpoint": record.endpoint.model_dump(),
                  "assay_id": record.source.assay_id, "document_id": record.source.document_id})


def _native_text(value: Any) -> str:
    if value is None or isinstance(value, bool):
        raise AdmissionError("missing_or_invalid_native_measurement")
    return str(value)


def mic_endpoint(activity: Mapping[str, Any]) -> EndpointLabel:
    """Preserve native raw value/unit/relation; convert verified mass units only."""
    if activity.get("standard_type") != "MIC" or activity.get("type", "MIC") != "MIC":
        raise AdmissionError("not_single_MIC_endpoint")
    if activity.get("upper_value") is not None or activity.get("standard_upper_value") is not None:
        raise AdmissionError("unsupported_native_interval_requires_explicit_bound_import")
    native_present = activity.get("value") is not None and activity.get("units") is not None
    fields = ("value", "units", "relation") if native_present else ("standard_value", "standard_units", "standard_relation")
    raw_value, raw_unit, relation = (_native_text(activity.get(k)) for k in fields)
    relation = relation.replace("≤", "<=").replace("≥", ">=")
    if relation not in {"=", "<", "<=", ">", ">="}:
        raise AdmissionError("unsupported_or_missing_relation")
    factor = _MASS_FACTORS.get(raw_unit)
    if factor is None:
        raise AdmissionError("unsupported_or_unverified_mass_unit")
    match = re.fullmatch(r"\s*(<=|>=|<|>|=)?\s*([0-9]+(?:\.[0-9]*)?|\.[0-9]+)([eE][-+]?\d+)?\s*", raw_value)
    if not match or match[1] is not None and match[1] != relation:
        raise AdmissionError("invalid_or_conflicting_native_measurement")
    value = float(match[2] + (match[3] or "")) * factor
    if not math.isfinite(value) or value <= 0:
        raise AdmissionError("nonpositive_or_nonfinite_measurement")
    standard_relation = activity.get("standard_relation")
    if standard_relation is not None and standard_relation != relation:
        raise AdmissionError("native_standard_relation_mismatch")
    # Cross-check standardized mass concentrations when ChEMBL supplies both.
    standard_factor = _MASS_FACTORS.get(activity.get("standard_units"))
    if native_present and standard_factor is not None and activity.get("standard_value") is not None:
        try:
            standardized = float(activity["standard_value"]) * standard_factor
        except (ValueError, TypeError):
            raise AdmissionError("invalid_standard_measurement") from None
        if not math.isclose(standardized, value, rel_tol=1e-5, abs_tol=1e-10):
            raise AdmissionError("native_standard_value_mismatch")
    return EndpointLabel(kind="MIC", relation=relation, unit="ug/mL", value=value,
                         raw=RawMeasurement(value=raw_value, unit=raw_unit, relation=relation),
                         conversion=f"verified_mass_unit_factor:{factor}; {raw_unit} -> ug/mL; fields:{','.join(fields)}")


def curate_activity(activity: Mapping[str, Any], assay: Mapping[str, Any], document: Mapping[str, Any],
                    molecule: Mapping[str, Any], *, taxon_id: int, native_locator: Mapping[str, Any],
                    source_version: str = "chembl-live") -> ExperimentRecord:
    """Require an exact activity→assay→document/molecule chain, without label guesses."""
    if taxon_id not in SPECIES:
        raise AdmissionError("unsupported_taxon")
    activity_id = activity.get("activity_id")
    if (not isinstance(activity_id, (int, str)) or isinstance(activity_id, bool)
            or not str(activity_id).isdigit() or int(activity_id) <= 0):
        raise AdmissionError("missing_native_activity_id")
    pairs = (("assay_chembl_id", assay), ("document_chembl_id", document), ("molecule_chembl_id", molecule))
    for key, metadata in pairs:
        if not metadata or not activity.get(key) or metadata.get(key) != activity[key]:
            raise AdmissionError("missing_or_mismatched_" + key)
    if assay.get("document_chembl_id") != activity["document_chembl_id"]:
        raise AdmissionError("assay_document_identity_mismatch")
    if not activity.get("target_chembl_id") or assay.get("target_chembl_id") != activity["target_chembl_id"]:
        raise AdmissionError("assay_target_identity_mismatch")
    if assay.get("assay_tax_id") != taxon_id or assay.get("assay_organism") != SPECIES[taxon_id]:
        raise AdmissionError("assay_species_taxon_not_exact")
    if (activity.get("target_tax_id") is not None and str(activity["target_tax_id"]) != str(taxon_id)
            or activity.get("target_organism") is not None and activity["target_organism"] != SPECIES[taxon_id]):
        raise AdmissionError("activity_species_taxon_conflict")
    if document.get("doc_type") not in {"PUBLICATION", "PATENT"} or activity.get("src_id") != 1:
        raise AdmissionError("not_source_linked_primary_report")
    if activity.get("data_validity_comment"):
        raise AdmissionError("source_data_validity_flag")
    description = assay.get("description")
    if not isinstance(description, str) or not description.strip():
        raise AdmissionError("missing_assay_description")
    if any(name.lower() != SPECIES[taxon_id].lower() for name in _NAMED_SPECIES.findall(description)):
        raise AdmissionError("assay_description_species_conflict")
    if _NONINDEPENDENT.search(description) or _NONINDEPENDENT.search(str(activity.get("activity_comment") or "")):
        raise AdmissionError("aggregate_combination_potentiation_or_nonexperimental_context")
    endpoint = mic_endpoint(activity)
    structures = molecule.get("molecule_structures") or {}
    smiles = structures.get("canonical_smiles")
    if not isinstance(smiles, str) or not smiles:
        raise AdmissionError("missing_native_molecule_structure")
    try:
        canonical, key = canonical_identity(smiles)
        if activity.get("canonical_smiles") and canonical_identity(activity["canonical_smiles"])[0] != canonical:
            raise AdmissionError("activity_molecule_structure_mismatch")
    except ValueError as exc:
        if isinstance(exc, AdmissionError):
            raise
        raise AdmissionError(str(exc)) from None
    organism = organism_from_assay(dict(assay), {"assay_description": description,
                                               "study": activity["document_chembl_id"],
                                               "assay": activity["assay_chembl_id"]})
    hierarchy = molecule.get("molecule_hierarchy") or {}
    reasons = ["single_agent_source_linked_experimental_MIC", "no_verified_same_isolate_and_condition_omics_pair"]
    if organism.strain is None:
        reasons.append("species_level_supervision_strain_unknown")
    source_id = f"{source_version}:activity:{activity_id}"
    return ExperimentRecord(
        record_id=source_id,
        molecule=MoleculeIdentity(source_molecule_id=activity["molecule_chembl_id"],
                                  source_parent_id=hierarchy.get("parent_chembl_id"),
                                  canonical_smiles=canonical, identity_key=key),
        organism=organism, conditions=conditions_from_assay(dict(assay), description), endpoint=endpoint,
        source=SourceEvidence(source_id=source_id, origin="experimental_database", reported_as_measured=True,
                              measured_qualifier="ChEMBL native MIC activity with exact assay, publication/patent and molecule links; database report, not an independent repeat measurement.",
                              native_locator=dict(native_locator), activity_id=str(activity_id),
                              assay_id=activity["assay_chembl_id"], document_id=activity["document_chembl_id"],
                              doi=document.get("doi"), license=LICENSE),
        admission=Admission(label_eligible=True, paired_omics_eligible=False, reasons=reasons),
    )


class NativeCache:
    """Cache public official responses once, with URL, hash, time and pagination receipts."""

    def __init__(self, root: str | Path, *, reuse_roots: tuple[str | Path, ...] = ()):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.reuse_roots = tuple(Path(path).resolve() for path in reuse_roots)
        self.source_version: str | None = None

    @staticmethod
    def _read(path: Path, receipt_path: Path, expected_url: str | None = None) -> tuple[dict, dict]:
        body = path.read_bytes()
        receipt = json.loads(receipt_path.read_text())
        if (expected_url is not None and receipt.get("url") != expected_url
                or receipt.get("sha256") != hashlib.sha256(body).hexdigest()
                or Path(receipt.get("file", path)).resolve() != path.resolve()):
            raise ValueError("native_cache_integrity_mismatch")
        return json.loads(body), receipt

    def verified_paths(self) -> list[Path]:
        """Verify only native receipts in the supplied cache roots; never copy them."""
        paths = []
        for root in (self.root, *self.reuse_roots):
            for receipt_path in sorted(root.glob("*.receipt.json")):
                if receipt_path.name.startswith("._"):
                    continue
                path = receipt_path.with_name(receipt_path.name.replace(".receipt.json", ".json"))
                _, receipt = self._read(path, receipt_path)
                if receipt.get("chembl_db_version") and self.source_version and receipt["chembl_db_version"] != self.source_version:
                    raise ValueError("native_cache_source_version_mismatch")
                paths.append(path)
        return paths

    def fetch(self, resource: str, params: Mapping[str, Any] | None = None) -> tuple[dict, dict]:
        if not re.fullmatch(r"(?:status|target|activity|assay|document|molecule)(?:/CHEMBL\d+)?", resource):
            raise ValueError("unsupported_public_chembl_resource")
        url = BASE_URL + resource + ".json" + ("?" + urlencode(sorted(params.items())) if params else "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "www.ebi.ac.uk":
            raise ValueError("official_chembl_urls_only")
        key = hashlib.sha256(url.encode()).hexdigest()[:24]
        for root in (self.root, *self.reuse_roots):
            path, receipt_path = root / f"{key}.json", root / f"{key}.receipt.json"
            if path.exists() and receipt_path.exists():
                data, receipt = self._read(path, receipt_path, url)
                if receipt.get("chembl_db_version") and self.source_version and receipt["chembl_db_version"] != self.source_version:
                    raise ValueError("native_cache_source_version_mismatch")
                return data, receipt
            if path.exists() or receipt_path.exists():
                raise ValueError("incomplete_native_cache_requires_explicit_repair")
        path, receipt_path = self.root / f"{key}.json", self.root / f"{key}.receipt.json"
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers={"User-Agent": "PRAXIS-virtualcell-public-data-curation/1.0",
                                                    "Accept": "application/json"}), timeout=45) as response:
                    if urlparse(response.url).hostname != "www.ebi.ac.uk":
                        raise ValueError("unexpected_chembl_redirect")
                    body = response.read()
                    data = json.loads(body)
                    receipt = {"schema_version": "praxis.native-download-receipt.v1", "url": url,
                               "retrieved_at": datetime.now(timezone.utc).isoformat(), "http_status": response.status,
                               "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "file": str(path.resolve()),
                               "page_meta": data.get("page_meta"), "license": LICENSE,
                               "chembl_db_version": self.source_version,
                               "license_url": "https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/general-questions"}
                break
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                if attempt == 2 or isinstance(exc, HTTPError) and exc.code not in {408, 429, 500, 502, 503, 504}:
                    raise
                time.sleep(2 ** attempt)
        path.write_bytes(body)
        receipt_path.write_text(_dump(receipt) + "\n")
        return data, receipt


def metadata_index(paths: list[Path], *, kind: str) -> dict[str, tuple[dict, dict]]:
    """Exact IDs only; do not duplicate source files or resolve aliases by names."""
    id_key = {"assays": "assay_chembl_id", "documents": "document_chembl_id",
              "molecules": "molecule_chembl_id"}[kind]
    result: dict[str, tuple[dict, dict]] = {}
    for path in paths:
        data = json.loads(path.read_text())
        rows = data if isinstance(data, list) else data.get(kind, [])
        for index, row in enumerate(rows):
            if isinstance(row, dict) and isinstance(row.get(id_key), str):
                result.setdefault(row[id_key], (row, {"file": str(path.resolve()),
                                                     "pointer": f"/{index}" if isinstance(data, list) else f"/{kind}/{index}"}))
    return result


def _validate_activity_page(data: Mapping[str, Any], *, offset: int, limit: int, total: int | None,
                            target_ids: list[str], seen_ids: set[str]) -> int:
    """Reject inconsistent pagination before constructing experimental records."""
    rows, page = data.get("activities"), data.get("page_meta")
    if not isinstance(rows, list) or not isinstance(page, dict):
        raise ValueError("invalid_native_activity_page")
    reported_total = page.get("total_count")
    if (page.get("offset") != offset or page.get("limit") != limit or not isinstance(reported_total, int)
            or isinstance(reported_total, bool) or reported_total < offset + len(rows) or len(rows) > limit):
        raise ValueError("native_activity_pagination_mismatch")
    if total is not None and reported_total != total:
        raise ValueError("native_activity_total_count_changed")
    for row in rows:
        native_id = row.get("activity_id")
        if (isinstance(native_id, bool) or not str(native_id).isdigit() or int(native_id) <= 0
                or str(native_id) in seen_ids):
            raise ValueError("native_activity_page_duplicate_or_invalid_id")
        if row.get("target_chembl_id") not in target_ids or row.get("standard_type") != "MIC":
            raise ValueError("native_activity_page_filter_mismatch")
        seen_ids.add(str(native_id))
    following = page.get("next")
    if following:
        parsed = urlparse(following)
        params = parse_qs(parsed.query)
        if (parsed.scheme and (parsed.scheme != "https" or parsed.hostname != "www.ebi.ac.uk")
                or parsed.path != "/chembl/api/data/activity.json"
                or params.get("offset") != [str(offset + len(rows))]
                or params.get("limit") != [str(limit)] or params.get("standard_type") != ["MIC"]
                or params.get("target_chembl_id__in") != [",".join(target_ids)] or not rows):
            raise ValueError("native_activity_next_page_identity_mismatch")
    elif offset + len(rows) != reported_total:
        raise ValueError("native_activity_missing_next_page")
    return reported_total


def write_import(records: list[ExperimentRecord], exclusions: list[dict], output: str | Path,
                 *, reused_existing_labels: list[dict] | None = None, acquisition: list[dict] | None = None,
                 inventory: dict | None = None) -> dict:
    """Write admission and exclusion artifacts; conflicting native IDs never enter labels."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[ExperimentRecord]] = {}
    for record in records:
        grouped.setdefault(str(record.source.activity_id), []).append(record)
    admitted = []
    duplicates = 0
    for activity_id, rows in grouped.items():
        # Provenance location and live version can differ, experimental identities cannot.
        signatures = {_experiment_signature(record) for record in rows}
        if len(signatures) != 1:
            exclusions.append({"native_activity_id": activity_id, "reasons": ["conflicting_native_activity_id"],
                               "source_locators": [r.source.native_locator for r in rows]})
            continue
        duplicates += len(rows) - 1
        admitted.append(rows[0])
    label_files = []
    for taxon_id in SPECIES:
        selected = sorted((r for r in admitted if r.organism.taxon_id == taxon_id), key=lambda r: r.record_id)
        path = output / f"taxon_{taxon_id}.experiments.jsonl"
        if not selected:
            # Clear only this importer's named derivative, never a native source.
            path.unlink(missing_ok=True)
            continue
        path.write_text("".join(r.model_dump_json() + "\n" for r in selected))
        label_files.append({"path": str(path.resolve()), "record_count": len(selected), "taxon_id": taxon_id,
                            "scientific_name": SPECIES[taxon_id], "source_type": "native_chembl_linked_MIC",
                            "paired_omics_eligible_count": 0})
    for existing in reused_existing_labels or []:
        label_files.append(dict(existing))
    excluded_path = output / "exclusions.jsonl"
    excluded_path.write_text("".join(_dump(row) + "\n" for row in exclusions))
    summary = {"schema_version": "praxis.species-mic-import.v1", "label_files": label_files,
               "reused_existing_labels": [row["path"] for row in reused_existing_labels or []],
               "new_label_count": len(admitted), "excluded_count": len(exclusions),
               "excluded_activity_count": sum("record_id" in row or "native_activity_id" in row for row in exclusions),
               "excluded_legacy_source_rows": sum(row.get("source_rows", 0) for row in exclusions),
               "identical_native_activity_duplicates_removed": duplicates,
               "new_taxon_counts": dict(Counter(str(r.organism.taxon_id) for r in admitted)),
               "new_censoring": dict(Counter(r.endpoint.censoring for r in admitted)),
               "exclusion_reason_counts": dict(Counter(reason for row in exclusions for reason in row["reasons"])),
               "source_acquisition": acquisition or [], "local_source_inventory": inventory or {},
               "coverage": "Bounded first pages and existing local records only; not a complete ChEMBL export.",
               "same_isolate_and_condition_omics_pairs": 0, "exclusions_path": str(excluded_path.resolve()),
               "license": LICENSE, "license_boundary": "ChEMBL database attribution and share-alike apply; primary papers retain their own terms."}
    (output / "summary.json").write_text(_dump(summary) + "\n")
    return summary


def acquire_species_mic(repo_root: str | Path, output: str | Path, *,
                        taxon_ids: tuple[int, ...] = (562, 573, 287), per_species_limit: int = 300,
                        archive_root: str | Path | None = None,
                        reused_label_paths: tuple[str | Path, ...] = (),
                        reuse_cache_roots: tuple[str | Path, ...] = (), page_size: int = 1000,
                        progress: Callable[[dict], None] | None = None) -> dict:
    """Fetch bounded continuous activity pages and only missing linked metadata.

    This callable is intentionally separate from any inference or training path.
    Existing native caches are reused with hash verification. No broad organism
    aliases, activity value joins or primary-paper text mining are performed.
    """
    if (not 1 <= per_species_limit <= 50000 or not 1 <= page_size <= 1000
            or len(set(taxon_ids)) != len(taxon_ids)):
        raise ValueError("unique_species_limit_1_to_50000_and_page_size_1_to_1000_required")
    if any(taxon_id not in SPECIES for taxon_id in taxon_ids):
        raise ValueError("unsupported_taxon")
    root, output = Path(repo_root).resolve(), Path(output).resolve()
    cache = NativeCache(output / "nativecache", reuse_roots=reuse_cache_roots)
    # A new snapshot checks the live release in its own cache, rather than
    # treating a prior snapshot's cached status as today's release assertion.
    status, status_receipt = NativeCache(output / "nativecache").fetch("status")
    db_version = status.get("chembl_db_version")
    if not isinstance(db_version, str) or not db_version:
        raise ValueError("missing_official_chembl_version")
    cache.source_version = db_version
    native_paths = cache.verified_paths()
    for path in native_paths:
        data = json.loads(path.read_text())
        if data.get("chembl_db_version") and data["chembl_db_version"] != db_version:
            raise ValueError("native_cache_source_version_mismatch")
    indexes = {}
    for kind in ("assays", "documents", "molecules"):
        paths = [root / "data/antibacterial/abaumannii/curated" / f"chembl_{kind}.json"]
        if archive_root is not None and kind == "molecules":
            paths += sorted((Path(archive_root) / "pan_bacterial_phase1_review/raw").glob("chembl_*.json"))
        indexes[kind] = metadata_index([path for path in paths if path.exists()] + native_paths, kind=kind)
    version = str(status.get("chembl_db_version", "chembl-live")).lower().replace("_", "")
    acquisition = [{"resource": "status", "receipt": status_receipt, "status": status}]
    inventory = {"exact_metadata_ids_available_before_download": {k: len(v) for k, v in indexes.items()},
                 "archive_root": str(Path(archive_root).resolve()) if archive_root is not None else None,
                 "reused_native_cache_roots": [str(Path(path).resolve()) for path in reuse_cache_roots],
                 "chembl_db_version": db_version, "cumulative_activity_limit_per_species": per_species_limit,
                 "legacy_ec_activity_file": {"path": str(root / "data/mdr_gnb/raw/compound_activity/escherichia_coli_mic_raw.jsonl"),
                                             "qualification": "Missing activity/assay/document IDs; not matched by SMILES or MIC value."}}
    records, exclusions = [], []
    legacy_ec = root / "data/mdr_gnb/raw/compound_activity/escherichia_coli_mic_raw.jsonl"
    if legacy_ec.exists():
        with legacy_ec.open() as stream:
            first = stream.readline()
            native_keys = sorted(json.loads(first)) if first else []
            source_rows = int(bool(first)) + sum(1 for line in stream if line.strip())
        inventory["legacy_ec_activity_file"].update(source_rows=source_rows, native_fields=native_keys)
        if not {"activity_id", "assay_chembl_id", "document_chembl_id"} <= set(native_keys):
            exclusions.append({"taxon_id": 562, "scope": "whole_legacy_source", "source_rows": source_rows,
                               "source_locator": {"file": str(legacy_ec)},
                               "reasons": ["legacy_rows_missing_native_activity_assay_document_ids"]})
    for taxon_id in taxon_ids:
        targets, receipt = cache.fetch("target", {"tax_id": taxon_id, "target_type": "ORGANISM", "limit": 20})
        selected_targets = [row["target_chembl_id"] for row in targets.get("targets", [])
                            if row.get("tax_id") == taxon_id and row.get("organism") == SPECIES[taxon_id]
                            and row.get("target_type") == "ORGANISM"]
        acquisition.append({"resource": "targets", "taxon_id": taxon_id, "receipt": receipt,
                            "target_ids": selected_targets, "complete": targets.get("page_meta", {}).get("next") is None})
        if not selected_targets:
            exclusions.append({"taxon_id": taxon_id, "reasons": ["no_exact_official_organism_target"]})
            continue
        native_items, seen_ids = [], set()
        offset, total = 0, None
        while offset < per_species_limit:
            limit = min(300 if offset == 0 else page_size, per_species_limit - offset)
            params = {"target_chembl_id__in": ",".join(selected_targets), "standard_type": "MIC", "limit": limit}
            if offset:
                params["offset"] = offset
            data, activity_receipt = cache.fetch("activity", params)
            total = _validate_activity_page(data, offset=offset, limit=limit, total=total,
                                            target_ids=selected_targets, seen_ids=seen_ids)
            activities = data["activities"]
            native_items.extend((activity, activity_receipt, index) for index, activity in enumerate(activities))
            acquisition.append({"resource": "MIC_activities", "taxon_id": taxon_id, "offset": offset,
                                "retrieved_rows": len(activities), "reported_total_count": total,
                                "complete": data["page_meta"].get("next") is None, "receipt": activity_receipt,
                                "reused_external_cache": Path(activity_receipt["file"]).parent.resolve() != cache.root.resolve()})
            offset += len(activities)
            if progress:
                progress({"stage": "activity_page", "taxon_id": taxon_id, "cumulative_rows": offset,
                          "target_rows": per_species_limit, "reported_total_count": total})
            if not data["page_meta"].get("next"):
                break
        activities = [item[0] for item in native_items]
        for kind, resource, id_key in (("assays", "assay", "assay_chembl_id"),
                                        ("documents", "document", "document_chembl_id"),
                                        ("molecules", "molecule", "molecule_chembl_id")):
            wanted = sorted({row[id_key] for row in activities if row.get(id_key)} - indexes[kind].keys())
            for start in range(0, len(wanted), 100):
                batch = wanted[start:start + 100]
                metadata, metadata_receipt = cache.fetch(resource, {id_key + "__in": ",".join(batch), "limit": 100})
                returned = metadata.get(kind, [])
                ids = [row.get(id_key) for row in returned]
                if len(set(ids)) != len(ids) or set(ids) - set(batch):
                    raise ValueError("native_metadata_batch_identity_mismatch")
                acquisition.append({"resource": kind, "taxon_id": taxon_id, "requested_ids": len(batch),
                                    "returned_rows": len(returned), "receipt": metadata_receipt,
                                    "complete": metadata.get("page_meta", {}).get("next") is None,
                                    "missing_ids": sorted(set(batch) - set(ids))})
                for index, row in enumerate(returned):
                    indexes[kind][row[id_key]] = (row, {"file": metadata_receipt["file"],
                                                       "pointer": f"/{kind}/{index}"})
                if progress:
                    progress({"stage": "metadata_batch", "taxon_id": taxon_id, "resource": kind,
                              "processed_missing_ids": min(start + 100, len(wanted)), "total_missing_ids": len(wanted)})
        for activity, activity_receipt, index in native_items:
            linked = {}
            locator = {"file": activity_receipt["file"], "pointer": f"/activities/{index}",
                       "download_sha256": activity_receipt["sha256"], "native_activity_id": activity.get("activity_id"),
                       "native_activity_taxon": activity.get("target_tax_id"), "native_api_url": activity_receipt["url"]}
            for kind, singular, key in (("assays", "assay", "assay_chembl_id"),
                                        ("documents", "document", "document_chembl_id"),
                                        ("molecules", "molecule", "molecule_chembl_id")):
                row, source_locator = indexes[kind].get(activity.get(key), ({}, {}))
                linked[singular] = row
                locator[singular + "_metadata"] = source_locator
            locator["native_assay_taxon"] = linked["assay"].get("assay_tax_id")
            try:
                record = curate_activity(activity, **linked, taxon_id=taxon_id,
                                         native_locator=locator, source_version=version)
            except (AdmissionError, ValueError, TypeError, OverflowError) as exc:
                reasons = exc.reasons if isinstance(exc, AdmissionError) else ["invalid_native_record:" + type(exc).__name__]
                exclusions.append({"record_id": f"{version}:activity:{activity.get('activity_id')}",
                                   "taxon_id": taxon_id, "source_locator": locator, "reasons": reasons})
            else:
                records.append(record)
    reused = []
    canonical_activities: dict[str, list[ExperimentRecord]] = {}
    for path in reused_label_paths:
        path = Path(path).resolve()
        counts = Counter()
        with path.open() as stream:
            for line in stream:
                record = ExperimentRecord.model_validate_json(line)
                counts[record.organism.taxon_id] += 1
                if record.source.source_id.startswith("chembl") and record.source.activity_id:
                    canonical_activities.setdefault(record.source.activity_id, []).append(record)
        reused.append({"path": str(path), "record_count": sum(counts.values()), "taxon_counts": dict(counts),
                       "source_type": "existing_source_linked_experimental_labels", "copied": False})
        if len(counts) == 1:
            taxon_id = next(iter(counts))
            reused[-1].update(taxon_id=taxon_id, scientific_name=SPECIES.get(taxon_id))
    unique_records = []
    reused_duplicates = 0
    for record in records:
        canonical_records = canonical_activities.get(str(record.source.activity_id), [])
        if canonical_records:
            if any(_experiment_signature(existing) != _experiment_signature(record) for existing in canonical_records):
                exclusions.append({"record_id": record.record_id, "native_activity_id": record.source.activity_id,
                                   "source_locator": record.source.native_locator,
                                   "reasons": ["native_activity_conflicts_with_existing_canonical_label"]})
            else:
                reused_duplicates += 1
        else:
            unique_records.append(record)
    inventory["new_activities_already_present_in_canonical_labels"] = reused_duplicates
    summary = write_import(unique_records, exclusions, output, reused_existing_labels=reused,
                           acquisition=acquisition, inventory=inventory)
    summary["coverage"] = "Bounded continuous pages with verified offsets, unique native activity IDs and stable source totals; not a complete ChEMBL export."
    summary["source_issues"] = [{"resource": row["resource"], "taxon_id": row.get("taxon_id"),
                                "missing_ids": row["missing_ids"], "receipt_file": row["receipt"]["file"]}
                               for row in acquisition if row.get("missing_ids")]
    summary["cumulative_activity_counts"] = dict(Counter({str(taxon_id): sum(row["retrieved_rows"] for row in acquisition
                                                                             if row["resource"] == "MIC_activities" and row["taxon_id"] == taxon_id)
                                                          for taxon_id in taxon_ids}))
    (output / "summary.json").write_text(_dump(summary) + "\n")
    return summary
