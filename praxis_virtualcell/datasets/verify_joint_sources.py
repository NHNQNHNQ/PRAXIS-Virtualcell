"""Independently check exported training supervision against relocated sources.

A path map changes only the file opened, never the native article locator or
passage identity. This verifier reads approved training MIC rows and private
review spans; it opens no validation/test answers and performs no LLM or training.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from .joint_qwen_sft import SCHEMA, TARGET_CONTRACT
from .joint_supervision import Annotation
from .labels import ExperimentRecord
from .literature import normalize_doi, parse_article_source
from .qwen_sft import qwen_messages
from .species_registry import _digest
from .strain_supervision import _rows

_OBSERVATION_FIELDS = ("relation", "value", "lower", "upper", "lower_closed", "upper_closed")


def _strain_label(value: str | None) -> str | None:
    if value is None:
        return None
    atcc = re.fullmatch(r"ATCC\s*[-:]?\s*(\d+)", value.strip(), re.I)
    if atcc:
        return "ATCC " + atcc[1]
    return "AB5075" if value.strip().casefold() == "ab5075" else value.strip()


def _taxon(value) -> int | None:
    if value is None:
        return None
    return int(str(value).removeprefix("NCBITaxon:"))


def _check_tool_strain_boundaries(record: dict, organism: dict, profile_id: str | None) -> None:
    def check(value):
        if isinstance(value, list):
            for item in value:
                check(item)
        elif isinstance(value, dict):
            species = value.get("source_species", value.get("species"))
            if isinstance(species, dict):
                if (species.get("scientific_name") not in {None, organism["species"]}
                        or _taxon(species.get("taxonomy_id")) not in {None, organism["taxon_id"]}):
                    raise ValueError("verified_omics_tool_crosses_species_boundary")
            label = value.get("source_strain", value.get("strain"))
            if isinstance(label, str) and _strain_label(label) != _strain_label(organism.get("label")):
                raise ValueError("verified_omics_tool_crosses_strain_boundary")
            for item in value.values():
                check(item)
    overview = None
    for message in record["messages"]:
        if message["role"] != "tool":
            continue
        reply = json.loads(message["content"])
        data = reply["data"]
        if data.get("profile_id") != profile_id:
            raise ValueError("verified_omics_tool_profile_mismatch")
        check(data)
        if reply["name"] == "overview":
            overview = data
    if profile_id and overview is None:
        raise ValueError("verified_strain_reference_requires_actual_overview")
    if overview is not None:
        if (overview.get("species", {}).get("scientific_name") != organism["species"]
                or _taxon(overview.get("species", {}).get("taxonomy_id")) != organism["taxon_id"]
                or _strain_label(overview.get("strain")) != _strain_label(organism.get("label"))):
            raise ValueError("verified_reference_identity_missing_or_mismatched")


def _pointer(value, pointer: str):
    if not pointer:
        return value
    if not pointer.startswith("/"):
        raise ValueError("compound_mapping_pointer_must_be_JSON_pointer")
    for part in pointer[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def verify_joint_sources(dataset_dir: str | Path, source_path_map: dict[str, str] | str | Path,
                          *, report_path: str | Path | None = None) -> dict:
    """Verify train MIC and native reviewed mechanisms without legacy databases."""
    root = Path(dataset_dir).resolve()
    mapping = (dict(source_path_map) if isinstance(source_path_map, dict)
               else json.loads(Path(source_path_map).read_text()))
    if not isinstance(mapping, dict) or any(not isinstance(old, str) or not isinstance(new, str)
                                            for old, new in mapping.items()):
        raise ValueError("source_path_map_must_map_paths_to_paths")
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("source_verifier_requires_joint_Qwen_dataset")
    required = ("train.jsonl", "joint.train.jsonl", "source_refs.jsonl", "quarantined_components.index.jsonl")
    for name in required:
        if _digest(root / name) != manifest["files"][name]["sha256"]:
            raise ValueError("exported_training_source_changed")
    train = _rows(root / "train.jsonl")
    references = _rows(root / "source_refs.jsonl")
    sources = {row["record_id"]: row for row in references}
    if len(sources) != len(references) or len({row["record_id"] for row in train}) != len(train):
        raise ValueError("duplicate_exported_training_source")
    if set(sources) != {row["record_id"] for row in train}:
        raise ValueError("training_source_reference_set_mismatch")
    if len(train) != manifest["training_record_count"]:
        raise ValueError("exported_training_count_mismatch")
    verified_files, native_articles, native_mappings = {}, {}, {}
    components, case_ids = set(), set()
    measurement_count = joint_count = claim_count = quote_count = mechanism_case_count = 0
    grades = Counter()

    def native_file(original: str, digest: str) -> Path:
        # No /Volumes fallback is needed on 53. Every source must have an
        # explicit map entry; two original paths may share the same bytes.
        if original not in mapping:
            raise ValueError("native_source_missing_from_path_map:" + original)
        actual = Path(mapping[original]).resolve()
        if actual not in verified_files:
            verified_files[actual] = _digest(actual)
        if verified_files[actual] != digest:
            raise ValueError("native_source_bytes_changed:" + original)
        return actual

    for record in train:
        qwen_messages(record["messages"])
        private = sources[record["record_id"]]
        component_id = record["source_record_id"]
        if (private.get("split") != "train" or private.get("component_id") != component_id
                or component_id in components):
            raise ValueError("source_verifier_only_accepts_distinct_train_components")
        components.add(component_id)
        request = json.loads(record["messages"][1]["content"])
        target = json.loads(record["messages"][-1]["content"])
        if record["messages"][-1]["role"] != "assistant" or target.get("endpoint") != "MIC" or target.get("unit") != "ug/mL":
            raise ValueError("source_verifier_requires_MIC_assistant_target")
        _check_tool_strain_boundaries(record, request["organism"], request.get("profile_id"))
        native_answers, observations = {}, []
        for source in private["source_refs"]:
            case_id, locator = source["case_id"], source["locator"]
            if case_id in case_ids:
                raise ValueError("training_MIC_case_is_counted_twice")
            case_ids.add(case_id)
            path = native_file(locator["path"], locator["sha256"])
            with path.open("rb") as stream:
                stream.seek(locator["byte_offset"])
                answer = ExperimentRecord.model_validate_json(stream.readline())
            organism = request["organism"]
            if (answer.record_id != locator["record_id"] or answer.molecule.canonical_smiles != request["candidate"]["smiles"]
                    or answer.organism.species != organism["species"] or answer.organism.taxon_id != organism["taxon_id"]
                    or answer.endpoint.kind != "MIC" or answer.endpoint.unit != "ug/mL" or not answer.admission.label_eligible):
                raise ValueError("native_MIC_identity_structure_or_endpoint_mismatch")
            # Only formatting already supported by the source strain registry
            # is normalized; a same-species strain is never silently substituted.
            if _strain_label(answer.organism.strain) != _strain_label(organism.get("label")):
                raise ValueError("native_MIC_strain_differs_from_public_input")
            native_answers[case_id] = answer
            observations.append({field: getattr(answer.endpoint, field) for field in _OBSERVATION_FIELDS})
        if observations != target["observations"]:
            raise ValueError("exported_MIC_observations_differ_from_native_answers")
        measurement_count += len(observations)
        if record["target_contract"] != TARGET_CONTRACT:
            if "literature_review" in private:
                raise ValueError("numeric_component_has_unbound_mechanism_review")
            continue
        joint_count += 1
        if private.get("mechanism_admission") != "agent_source_reviewed" or private.get("human_gold") is not False:
            raise ValueError("joint_mechanism_review_quality_mismatch")
        review = private["literature_review"]
        annotation = Annotation.model_validate(review["annotation"])
        if (review.get("record_id") != record["record_id"] or review.get("inference_eligible") is not False
                or annotation.component_record_id != component_id or set(annotation.case_ids) != set(native_answers)):
            raise ValueError("joint_mechanism_case_binding_mismatch")
        mechanism_cases = annotation.case_ids if annotation.mechanism_case_ids is None else annotation.mechanism_case_ids
        if not mechanism_cases or len(set(mechanism_cases)) != len(mechanism_cases) or not set(mechanism_cases).issubset(native_answers):
            raise ValueError("joint_mechanism_case_subset_invalid")
        mechanism_case_count += len(mechanism_cases)
        compound = annotation.compound_mapping
        mapping_path = native_file(compound.file, compound.sha256)
        if mapping_path not in native_mappings:
            native_mappings[mapping_path] = json.loads(mapping_path.read_text())
        mapped = _pointer(native_mappings[mapping_path], compound.pointer)
        if mapped["compound_key"] != annotation.compound_paper_name:
            raise ValueError("paper_compound_name_differs_from_native_mapping")
        for case_id in mechanism_cases:
            answer = native_answers[case_id]
            if (mapped["molecule_chembl_id"] != answer.molecule.source_molecule_id
                    or mapped["document_chembl_id"] != answer.source.document_id):
                raise ValueError("paper_compound_or_document_differs_from_mechanism_source_subset")
        quotes = [*annotation.binding_quotes, *(quote for claim in annotation.claims for quote in claim.quotes)]
        paper_ids = {quote.passage_id.rsplit(":passage:", 1)[0] for quote in quotes}
        if len(paper_ids) != 1:
            raise ValueError("joint_review_contains_multiple_unbound_papers")
        article_source = review["paper_source"]
        article_url = urlparse(article_source.get("url", ""))
        if (article_url.scheme != "https" or article_url.hostname not in
                {"www.ebi.ac.uk", "europepmc.org", "www.europepmc.org", "pmc.ncbi.nlm.nih.gov"}):
            raise ValueError("native_article_requires_recorded_official_source_URL")
        article_path = native_file(article_source["file"], article_source["sha256"])
        article_key = (article_path, next(iter(paper_ids)), article_source["file"])
        if article_key not in native_articles:
            # Preserve old source.file so native locators/passages remain exact.
            native_articles[article_key] = parse_article_source(article_path.read_bytes(),
                                                               paper_id=next(iter(paper_ids)), source=article_source)
        parsed = native_articles[article_key]
        expected_doi = normalize_doi(annotation.doi)
        if expected_doi is None or normalize_doi(parsed["identifiers"].get("doi")) != expected_doi:
            raise ValueError("native_article_DOI_differs_from_annotation")
        passages = {passage["passage_id"]: passage for passage in parsed["passages"]}
        for quote in quotes:
            passage = passages.get(quote.passage_id)
            if (passage is None or quote.end <= quote.start or quote.end > len(passage["text"])
                    or quote.text != passage["text"][quote.start:quote.end]):
                raise ValueError("reviewed_quote_differs_from_native_article_span")
            quote_count += 1
        binding_evidence = review["binding_evidence"]
        if len(binding_evidence) != len(annotation.binding_quotes):
            raise ValueError("native_binding_evidence_count_mismatch")
        for quote, evidence in zip(annotation.binding_quotes, binding_evidence, strict=True):
            if (any(evidence.get(key) != value for key, value in quote.model_dump().items())
                    or evidence.get("source_locator") != passages[quote.passage_id]["locator"]
                    or normalize_doi(evidence.get("doi")) != normalize_doi(annotation.doi)):
                raise ValueError("native_binding_locator_or_DOI_mismatch")
        claims = target["mechanism_claims"]
        if len(claims) != len(annotation.claims):
            raise ValueError("public_mechanism_claim_count_mismatch")
        for claim, checked in zip(claims, annotation.claims, strict=True):
            if (any(claim.get(key) != getattr(checked, key) for key in
                    ("statement", "evidence_grade", "experiment_type", "target_names"))
                    or claim.get("scope") != annotation.claim_scope
                    or claim.get("mechanism_role", "unresolved") != checked.mechanism_role):
                raise ValueError("public_mechanism_claim_differs_from_reviewed_annotation")
            expected_sources = {(normalize_doi(annotation.doi), quote.passage_id) for quote in checked.quotes}
            if {(normalize_doi(source["doi"]), source["locator_id"]) for source in claim["sources"]} != expected_sources:
                raise ValueError("public_mechanism_DOI_or_locator_differs_from_native_quotes")
            claim_count += 1
            grades[checked.evidence_grade] += 1
    subset = _rows(root / "joint.train.jsonl")
    joint_train = {row["record_id"]: row for row in train if row["target_contract"] == TARGET_CONTRACT}
    if (len(subset) != len(joint_train) or len({row["record_id"] for row in subset}) != len(subset)
            or any(row != joint_train.get(row["record_id"]) for row in subset)):
        raise ValueError("independently_verified_joint_subset_mismatch")
    quarantine = _rows(root / "quarantined_components.index.jsonl")
    for row in quarantine:
        if row["component_id"] in components or row.get("training_eligible") is not False or not row.get("reason"):
            raise ValueError("quarantined_component_is_not_isolated_from_training")
    if (measurement_count != manifest["training_MIC_measurement_count"] or joint_count != manifest["mechanism_training_records"]
            or len(quarantine) != manifest["quarantined_component_count"]):
        raise ValueError("independently_verified_source_counts_differ_from_manifest")
    report = {"schema_version": "praxis.joint-native-source-verification.v1", "status": "passed",
              "training_records_checked": len(train), "training_MIC_measurements_checked": measurement_count,
              "joint_records_checked": joint_count, "mechanism_source_subset_cases_checked": mechanism_case_count,
              "mechanism_claims_checked": claim_count, "native_quotes_checked": quote_count,
              "mechanism_claim_grades": dict(grades), "native_source_files_checked": len(verified_files),
              "native_articles_checked": len(native_articles), "quarantined_components_checked": len(quarantine),
              "human_gold_mechanism_records": 0, "heldout_MIC_answers_opened": 0,
              "raw_omics_or_legacy_SQLite_required": False, "path_map_changes_bytes": False,
              "original_article_locators_preserved": True, "LLM_calls": 0, "training_runs": 0,
              "dataset_manifest": {"path": str(root / "manifest.json"), "sha256": _digest(root / "manifest.json")}}
    if report_path is not None:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--source-path-map", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    print(json.dumps(verify_joint_sources(args.dataset_dir, args.source_path_map, report_path=args.report),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
