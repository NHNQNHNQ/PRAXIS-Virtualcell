"""Compile explicitly reviewed, record-bound literature annotation targets.

The paper is supervision only. Public messages reuse the label-isolated numeric
component and actual strain tools; neither source passages nor MIC lookup are
inserted into inference inputs. A reviewed author hypothesis stays a hypothesis.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .species_registry import _digest, _json
from .strain_supervision import _rows


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Quote(_Strict):
    passage_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)


class Claim(_Strict):
    statement: str = Field(min_length=1)
    evidence_grade: Literal["experimental", "genetic", "author_proposed", "class_background", "unresolved"]
    experiment_type: Literal["phenotypic_rescue", "time_kill", "target_binding", "genetic", "author_hypothesis", "class_background", "not_identified"]
    target_names: list[str]
    quotes: list[Quote] = Field(min_length=1)

    @model_validator(mode="after")
    def preserve_experiment_grade(self):
        expected = {"phenotypic_rescue": "experimental", "time_kill": "experimental", "target_binding": "experimental",
                    "genetic": "genetic", "author_hypothesis": "author_proposed",
                    "class_background": "class_background", "not_identified": "unresolved"}
        if self.evidence_grade != expected[self.experiment_type]:
            raise ValueError("mechanism_experiment_and_grade_conflict")
        if self.experiment_type == "target_binding" and not self.target_names:
            raise ValueError("target_binding_requires_identified_target")
        if self.experiment_type == "not_identified" and self.target_names:
            raise ValueError("unresolved_mechanism_cannot_supply_verified_target")
        return self


class CompoundMapping(_Strict):
    file: str
    sha256: str
    pointer: str


class Annotation(_Strict):
    component_record_id: str
    case_ids: list[str] = Field(min_length=1)
    doi: str
    compound_paper_name: str = Field(min_length=1)
    compound_mapping: CompoundMapping
    compound_binding_basis: str = Field(min_length=1)
    strain_binding_basis: str = Field(min_length=1)
    binding_quotes: list[Quote] = Field(min_length=1)
    claims: list[Claim] = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    review_status: Literal["source_reviewed"]
    # A paper-level annotation cannot be silently represented as a direct
    # strain-specific target experiment.
    claim_scope: Literal["exact_compound_exact_strain", "exact_compound_general_mechanism", "unresolved_mechanism"]


class Reviews(_Strict):
    schema_version: Literal["praxis.literature-reviews.v1"]
    annotations: list[Annotation]


def prepare_joint_supervision(supervision_dir, literature_dir, reviews_path, output_dir) -> dict:
    source, literature = Path(supervision_dir).resolve(), Path(literature_dir).resolve()
    destination = Path(output_dir).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("joint_supervision_destination_exists")
    summary = json.loads((source / "summary.json").read_text())
    if _digest(Path(summary["dataset_summary"])) != summary["dataset_summary_sha256"]:
        raise ValueError("joint_supervision_dataset_snapshot_changed")
    names = {"mic_sft.jsonl", "private_training_sources.jsonl", "observation_views.jsonl", "joint_review_queue.jsonl"}
    if set(summary.get("files", {})) != names:
        raise ValueError("joint_supervision_requires_frozen_component_files")
    for name in names:
        if _digest(source / name) != summary["files"][name]["sha256"]:
            raise ValueError("joint_supervision_component_changed")
    from .strain_dataset import validate_strain_dataset
    validate_strain_dataset(summary["dataset_summary"])
    components = {row["record_id"]: row for row in _rows(source / "mic_sft.jsonl")}
    private_sources = {row["record_id"]: row["private_sources"] for row in _rows(source / "private_training_sources.jsonl")}
    queue = {row["MIC_training_record_id"]: row for row in _rows(source / "joint_review_queue.jsonl")}
    papers = {row["doi"]: row for row in _rows(literature / "papers.jsonl")}
    passages = {row["passage_id"]: row for row in _rows(literature / "passages.jsonl")}
    reviews = Reviews.model_validate_json(Path(reviews_path).read_text())
    seen, native_passages = set(), {}

    def verify(quote: Quote, paper: dict) -> dict:
        passage = passages[quote.passage_id]
        locator = passage["locator"]
        if passage["paper_id"] != paper["paper_id"] or quote.text != passage["text"][quote.start:quote.end]:
            raise ValueError("literature_quote_or_paper_mismatch")
        if quote.end > len(passage["text"]) or quote.end <= quote.start:
            raise ValueError("invalid_literature_span")
        asset = (locator["file"], locator["sha256"])
        if asset not in native_passages:
            if _digest(Path(asset[0])) != asset[1]:
                raise ValueError("reviewed_literature_source_changed")
            from .literature import parse_jats
            parsed = parse_jats(Path(asset[0]).read_bytes(), paper_id=paper["paper_id"], source=locator)
            native_passages[asset] = {item["passage_id"]: item for item in parsed["passages"]}
        if native_passages[asset].get(quote.passage_id) != passage:
            raise ValueError("reviewed_passage_does_not_match_native_article")
        return {**quote.model_dump(), "source_locator": locator, "doi": paper["doi"]}

    records, provenance = [], []
    for annotation in reviews.annotations:
        key = annotation.component_record_id
        if key in seen:
            raise ValueError("duplicate_joint_component_review")
        seen.add(key)
        component, pending = components[key], queue[key]
        if component["split"] != "train" or not component["trainable"]:
            raise ValueError("joint_supervision_requires_train_component")
        if set(annotation.case_ids) != set(component["case_ids"]):
            raise ValueError("joint_annotation_must_cover_all_grouped_cases")
        paper = papers[annotation.doi]
        if not set(annotation.case_ids).issubset(paper["case_ids"]):
            raise ValueError("joint_review_case_not_bound_to_paper")
        if paper["status"] != "open_fulltext_parsed":
            raise ValueError("joint_review_requires_verified_fulltext")
        mapping = annotation.compound_mapping
        if _digest(Path(mapping.file)) != mapping.sha256:
            raise ValueError("joint_compound_mapping_source_changed")
        native = json.loads(Path(mapping.file).read_text())
        for part in mapping.pointer.strip("/").split("/"):
            native = native[int(part)] if isinstance(native, list) else native[part]
        if native["compound_key"] != annotation.compound_paper_name:
            raise ValueError("joint_paper_compound_name_mismatch")
        for member in private_sources[key]:
            locator = member["locator"]
            if _digest(Path(locator["path"])) != locator["sha256"]:
                raise ValueError("joint_MIC_source_changed")
            with Path(locator["path"]).open("rb") as stream:
                stream.seek(locator["byte_offset"])
                answer = json.loads(stream.readline())
            if (answer["record_id"] != locator["record_id"]
                    or native["molecule_chembl_id"] != answer["molecule"]["source_molecule_id"]
                    or native["document_chembl_id"] != answer["source"]["document_id"]
                    or answer["molecule"]["canonical_smiles"] != pending["input"]["candidate"]["smiles"]):
                raise ValueError("joint_compound_structure_or_document_mismatch")
        bindings = [verify(quote, paper) for quote in annotation.binding_quotes]
        claims = []
        for claim in annotation.claims:
            claims.append({**claim.model_dump(exclude={"quotes"}),
                           "evidence": [verify(quote, paper) for quote in claim.quotes],
                           "direct_target_binding_supported": claim.experiment_type == "target_binding",
                           "strain_specific_experiment": annotation.claim_scope == "exact_compound_exact_strain"
                           and claim.evidence_grade in {"experimental", "genetic"}})
        # The actual tool messages already present in the component are the
        # only biological observations shown before the answer.
        record = deepcopy(component)
        target = json.loads(record["messages"][-1]["content"])
        target["literature_mechanisms"] = claims
        target["mechanism_scope"] = annotation.claim_scope
        target["mechanism_limitations"] = [
            "Literature annotations are supervision, not candidate-time evidence lookup.",
            "Reference expression/presence does not prove the proposed target causes this MIC.",
        ]
        record["messages"][0]["content"] += (
            "\n此联合组件还监督 literature_mechanisms、mechanism_scope 和 mechanism_limitations。"
            "保留原文证据等级；通用机制不能升级为该菌株的靶点结合实验证据。"
            "原文引用属于训练答案，不是可用的推理工具。")
        record["messages"][-1]["content"] = _json(target)
        record.update(record_id="joint:" + key.removeprefix("mic:"), task="MIC_and_literature_annotation",
                      task_scope="strain_reference_joint_component", mechanism_supervision="source_reviewed_literature",
                      target_contract="praxis.strain-joint-component.v1", reviewed_by=annotation.reviewer,
                      literature_claim_scope=annotation.claim_scope, complete_agent_report=False,
                      source_review_is_experimental_validation=False, model_generated_target=True,
                      target_origins={"MIC": "source_verified_experimental", "literature_quotes": "verbatim_source",
                                      "literature_statements": "agent_source_reviewed_paraphrase"},
                      human_reviewed=False)
        if pending["input"]["profile_id"] != record["observation_view_id"]:
            raise ValueError("joint_strain_view_mismatch")
        records.append(record)
        provenance.append({"record_id": record["record_id"], "annotation": annotation.model_dump(),
                           "binding_evidence": bindings, "paper_source": paper["article"],
                           "inference_eligible": False})
    validate_strain_dataset(summary["dataset_summary"])
    report = {"schema_version": "praxis.joint-supervision.v1", "record_count": len(records),
              "MIC_measurement_count": sum(row["source_case_count"] for row in records),
              "claim_count": sum(len(row.claims) for row in reviews.annotations),
              "source_reviewed": True, "model_generated_literature_paraphrases": True,
              "model_generated_MIC_targets": False, "human_reviewed": False,
              "complete_agent_report_count": 0, "training_runs": 0,
              "input_files": {str(path): _digest(path) for path in
                              [source / "mic_sft.jsonl", source / "joint_review_queue.jsonl",
                               literature / "papers.jsonl", literature / "passages.jsonl", Path(reviews_path)]}}
    destination.mkdir(parents=True, exist_ok=True)
    for name, rows in (("joint_sft.jsonl", records), ("private_literature_reviews.jsonl", provenance)):
        (destination / name).write_text("".join(_json(row) + "\n" for row in rows))
    (destination / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report
