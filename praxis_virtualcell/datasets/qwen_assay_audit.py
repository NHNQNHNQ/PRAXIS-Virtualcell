"""Screen native heldout assay context without exporting MIC answers.

Unencoded combinations, derivatives and history endpoints are isolated pending
source review. A missing plasmid descriptor is never interpreted as wild type.
The frozen assignments stay unchanged; this creates explicit scoring exclusions.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
from .paths import dataset_file
import re

from .qwen_evaluation import _rows
from .species_registry import _digest

PATTERNS = {
    "combination_or_fixed_other_drug_requires_review": r"\b(?:combination|combined with|co[- ]?treatment|synerg\w*|potentiat\w*|adjuvant)\b|in (?:the )?presence of",
    "derived_genetic_background_requires_review": r"\b(?:transform\w*|complement\w*|knockout|knock[- ]?down|overexpress\w*|mutant|gene[- ]?deficient)\b|harboring plasmid|containing plasmid|\bdelta[- ]",
    "exposure_history_requires_review": r"serial passag\w*|after (?:drug |antibiotic )?exposure|subcultur\w*|withdrawal",
    "animal_endpoint_requires_review": r"\bin vivo\b|\bmurine\b|\bmouse\b|\bmice\b|\binfected animals?\b",
}


def _pointer(value, pointer: str):
    for token in pointer.lstrip("/").split("/") if pointer else []:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def audit_qwen_assays(dataset_dir: str | Path, *, split: str,
                      source_path_map: dict[str, str] | None = None,
                      historical_assays: str | Path = "data/antibacterial/abaumannii/curated/chembl_assays.json") -> dict:
    if split not in {"validation", "test"}:
        raise ValueError("heldout_split_required")
    root, mapping = Path(dataset_dir), source_path_map or {}
    manifest = json.loads((root / "manifest.json").read_text())
    inputs = {row["record_id"]: row for row in _rows(root / f"{split}.inputs.jsonl")}
    answers = _rows(dataset_file(root, f"{split}.answers.index.jsonl", manifest))
    cached, decisions = {}, []
    historical = Path(historical_assays)
    historical_rows = json.loads(historical.read_text()) if historical.is_file() else []
    historical_by_id = {row["assay_chembl_id"]: row for row in historical_rows}
    with ExitStack() as stack:
        streams = {}
        for answer in answers:
            descriptions, assays, reasons = [], [], set()
            public = inputs[answer["record_id"]]
            request = json.loads(next(message["content"] for message in public["messages"] if message["role"] == "user"))
            for ref in answer["private_answer_refs"]:
                locator = ref["locator"]
                path = Path(mapping.get(locator["path"], locator["path"]))
                if path not in streams:
                    streams[path] = stack.enter_context(path.open("rb"))
                streams[path].seek(locator["byte_offset"])
                # Parse only source/organism metadata; endpoint values are not
                # used in decisions, returned, or sent to a model.
                native = json.loads(streams[path].readline())
                if native["record_id"] != locator["record_id"]:
                    raise ValueError("native_context_locator_mismatch")
                source = native["source"]
                assay_id = source.get("assay_id")
                assays.append(assay_id)
                location = source["native_locator"].get("assay_metadata")
                assay = None
                if location:
                    metadata = Path(mapping.get(location["file"], location["file"]))
                    if metadata.is_file():
                        if metadata not in cached:
                            cached[metadata] = json.loads(metadata.read_text())
                        assay = _pointer(cached[metadata], location["pointer"])
                if assay is None:
                    assay = historical_by_id.get(assay_id)
                if not assay:
                    reasons.add("native_assay_metadata_unavailable")
                    continue
                description = assay.get("description") or ""
                descriptions.append(description)
                if not description:
                    reasons.add("native_assay_description_missing")
                for reason, pattern in PATTERNS.items():
                    if re.search(pattern, description, re.I):
                        reasons.add(reason)
                native_taxon = assay.get("assay_tax_id")
                if native_taxon is not None and int(native_taxon) != request["organism"]["taxon_id"]:
                    reasons.add("native_assay_taxon_conflict")
            # The public organism does not encode plasmid differences; a group
            # spanning stated and unstated backgrounds remains quarantined.
            if len(set(descriptions)) > 1 and any(re.search(r"plasmid|transform\w*|mutant", value, re.I)
                                                  for value in descriptions):
                reasons.add("merged_background_descriptions_require_source_review")
            decisions.append({"record_id": answer["record_id"], "assay_ids": sorted(set(filter(None, assays))),
                              "native_descriptions": sorted(set(descriptions)),
                              "scoring_eligible": not reasons, "reasons": sorted(reasons),
                              "human_reviewed": False})
    excluded = [row["record_id"] for row in decisions if not row["scoring_eligible"]]
    return {"schema_version": "praxis.qwen-native-assay-audit.v1", "status": "reviewed", "split": split,
            "review_method": "conservative_native_metadata_screen; flagged_contexts_isolated_pending_source_review",
            "human_reviewed": False, "dataset_dir": str(root.resolve()),
            "dataset_manifest_sha256": _digest(root / "manifest.json"),
            "record_count": len(decisions), "eligible_record_count": len(decisions) - len(excluded),
            "excluded_record_ids": excluded,
            "reason_counts": dict(Counter(reason for row in decisions for reason in row["reasons"])),
            "MIC_values_exported": False, "frozen_split_changed": False, "decisions": decisions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--split", required=True, choices=["validation", "test"])
    parser.add_argument("--source-path-map")
    parser.add_argument("--historical-assays", default="data/antibacterial/abaumannii/curated/chembl_assays.json")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    mapping = json.loads(Path(args.source_path_map).read_text()) if args.source_path_map else None
    report = audit_qwen_assays(args.dataset_dir, split=args.split, source_path_map=mapping,
                              historical_assays=args.historical_assays)
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"decisions", "excluded_record_ids"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
