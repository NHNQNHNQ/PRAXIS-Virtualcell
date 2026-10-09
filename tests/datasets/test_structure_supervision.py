"""Additive structure supervision preserves frozen labels and uses source tools."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from praxis_virtualcell.cell_structure import cell_structure_overview, query_cell_structure
from praxis_virtualcell.datasets import structure_supervision as export
from praxis_virtualcell.datasets.species_registry import _digest
from praxis_virtualcell.llm_prediction.schemas import Assessment, empty_assessment


def _write(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def _row(identifier, profile_id):
    target = empty_assessment("Conservative inherited train supervision.")
    target["mic_estimate"]["value"] = 2.0
    target["mic_observations"] = [{"relation": "=", "value": 2.0, "lower": 2.0, "upper": 2.0,
                                   "lower_closed": True, "upper_closed": True}]
    request = {"candidate": {"smiles": "CCO"}, "organism": {"species": "Escherichia coli", "taxon_id": 562,
               "strain_id": "strain-A", "namespace": "study:A", "label": "A"}, "profile_id": profile_id,
               "conditions": {"medium": None}, "available_modalities": ["genome"] if profile_id else []}
    return {"record_id": identifier, "source_record_id": identifier, "target_contract": export.CONTRACT,
            "task_scope": "strain_reference_Assessment_mechanism" if profile_id else "strain_conditioned_Assessment_auxiliary",
            "messages": [{"role": "system", "content": "Original Assessment rules."},
                         {"role": "user", "content": json.dumps(request)},
                         {"role": "assistant", "content": json.dumps(target)}], "tools": []}


@pytest.fixture
def sealed_base(tmp_path):
    base = tmp_path / "qwen_joint_sft_v3"
    base.mkdir()
    rows = [_row("joint:omics", "A-REFERENCE"), _row("mic:auxiliary", None)]
    _write(base / "train.jsonl", rows)
    _write(base / "joint.train.jsonl", rows[:1])
    _write(base / "source_refs.jsonl", [{"record_id": row["record_id"], "split": "train"} for row in rows])
    _write(base / "omics.train.index.jsonl", [{"record_id": rows[0]["record_id"], "file": "train.jsonl",
                                              "byte_offset": 0, "line_number": 1}])
    for split in ("validation", "test"):
        heldout = deepcopy(rows[0])
        heldout.pop("source_record_id")
        heldout.pop("task_scope")
        heldout.update(record_id=f"{split}:heldout", split=split, case_ids=["frozen-case"], cohorts=["frozen_scaffold"])
        heldout["messages"].pop()
        _write(base / f"{split}.inputs.jsonl", [heldout])
        # Export must not open or materialize these frozen answer locators.
        _write(base / f"{split}.answers.index.jsonl", [{"private_answer": "777", "raw_label": "/must/not/read/raw"}])
    counts = {"train.jsonl": 2, "joint.train.jsonl": 1, "source_refs.jsonl": 2, "omics.train.index.jsonl": 1}
    counts.update({f"{split}.{kind}.jsonl": 1 for split in ("validation", "test") for kind in ("inputs", "answers.index")})
    manifest = {"schema_version": "praxis.qwen-MIC-mechanism-chat.v1", "assessment_supervision": True,
                "training_record_count": 2, "training_with_omics_records": 1, "training_MIC_measurement_count": 2,
                "joint_training_record_ids": ["joint:omics"], "mechanism_training_records": 1,
                "files": {name: {"sha256": _digest(base / name), "records": count} for name, count in counts.items()}}
    (base / "manifest.json").write_text(json.dumps(manifest))
    fact = {"structure_id": "reference:562:inner_membrane", "kind": "compartment", "compartment": "inner_membrane",
            "adjacent_to": None, "protein_id": None, "protein_namespace": None,
            "statement": "The species reference has an inner membrane.", "evidence_scope": "species_prior",
            "scope": {"taxonomy_id": "NCBITaxon:562", "strain": None, "strain_namespace": None,
                      "genotype": None, "genotype_scope": "not_reported"},
            "evidence_type": "reference_knowledge", "source_id": "paper:fixture:inner_membrane",
            "source_url": "https://example.org/paper", "source_locator": {"figure": "1"},
            "source_context": {"source_strains": ["Source strain B"], "method": "source reference",
                               "interpretation": "Reference topology only; no current state."}, "condition": None}
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"schema_version": "praxis.cell-structure-catalog.v1",
                                    "catalog_id": "fixture", "structures": [fact]}))
    return base, catalog, rows


def _teacher(catalog, contexts, structure_view="compartment_nodes"):
    def execute(context):
        contexts.append(deepcopy(context))
        overview = {"profile_id": context["profile_id"],
             "species": {"taxonomy_id": "NCBITaxon:562"}, "strain": "A", "strain_namespace": "study:A",
             "genotype": None, "input_role": "strain_reference"}
        full = cell_structure_overview(overview, catalog_path=catalog)
        if structure_view == "full":
            return full
        ids = [row["structure_id"] for row in full["structures"] if row["kind"] == "compartment"]
        return query_cell_structure(overview, structure_ids=ids, limit=len(ids), catalog_path=catalog)
    return execute


def test_additive_export_executes_real_structure_tool_and_never_opens_heldout_answers(sealed_base, tmp_path, monkeypatch):
    base, catalog, old = sealed_base
    before = {path.name: path.read_bytes() for path in base.iterdir()}
    contexts = []
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        if path.name.endswith("answers.index.jsonl") or "must/not/read" in str(path):
            pytest.fail("structure exporter opened heldout answers or raw labels")
        return original_open(path, *args, **kwargs)
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", guarded_open)
        report = export.prepare_structure_sft(base, tmp_path / "qwen_joint_sft_v4", catalog_path=catalog,
            execute=_teacher(catalog, contexts), expected_base_manifest_sha256=_digest(base / "manifest.json"))
        checked = export.validate_structure_sft(tmp_path / "qwen_joint_sft_v4")
    assert before == {path.name: path.read_bytes() for path in base.iterdir()}
    assert len(contexts) == 1 and set(contexts[0]) == {"profile_id", "organism"}
    assert checked == {"status": "passed", "records": 2, "augmented": 1, "auxiliary": 1,
                       "heldout_answers_opened": 0, "existing_MIC_and_mechanism_unchanged": True}
    output = tmp_path / "qwen_joint_sft_v4"
    new = [json.loads(line) for line in (output / "train.jsonl").read_text().splitlines()]
    assert new[1] == old[1]
    assert (output / "train.jsonl").read_bytes().splitlines()[1] == (base / "train.jsonl").read_bytes().splitlines()[1]
    target = Assessment.model_validate_json(new[0]["messages"][-1]["content"])
    assert target.mic_estimate.value == 2.0
    assert target.structure_analysis.accessibility_barriers[0].accessibility == "unknown"
    assert target.structure_analysis.compartment_hypotheses[0].evidence_scope == "species_prior"
    assert target.structure_analysis.compartment_hypotheses[0].protein_id is None
    assert all(item.evidence_type == "reference_knowledge" for item in target.structure_analysis.compartment_hypotheses)
    assert report["structure_supervision"]["human_gold_records"] == 0
    assert report["structure_supervision"]["new_MIC_values"] == 0
    assert report["shared_files"]["source_refs.jsonl"] == {"path": "../qwen_joint_sft_v3/source_refs.jsonl"}
    assert not (output / "source_refs.jsonl").exists()
    assert not (output / "validation.answers.index.jsonl").exists()
    assert report["files"]["validation.answers.index.jsonl"] == json.loads((base / "manifest.json").read_text())["files"]["validation.answers.index.jsonl"]
    assert export.resolve_shared_file(output, "source_refs.jsonl") == base / "source_refs.jsonl"
    for split in ("validation", "test"):
        heldout = json.loads((output / f"{split}.inputs.jsonl").read_text())
        assert heldout["record_id"] == f"{split}:heldout" and heldout["case_ids"] == ["frozen-case"]
        assert [message["role"] for message in heldout["messages"]] == ["system", "user"]
        assert "777" not in json.dumps(heldout)
    # The ordinary training preflight consumes the derivative without private fields.
    import importlib.util
    script = Path(__file__).resolve().parents[2] / "scripts/finetuning/preflight_qwen.py"
    spec = importlib.util.spec_from_file_location("structure_preflight_qwen", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for row in new:
        module.validate_record(row)


def test_relative_shared_receipts_and_derivation_work_after_relocation(sealed_base, tmp_path):
    base, catalog, _ = sealed_base
    output = tmp_path / "qwen_joint_sft_v4"
    export.prepare_structure_sft(base, output, catalog_path=catalog, execute=_teacher(catalog, []))
    relocated = tmp_path / "relocated"
    relocated.mkdir()
    shutil.copytree(base, relocated / base.name)
    shutil.copytree(output, relocated / output.name)
    shutil.copyfile(catalog, relocated / catalog.name)
    assert export.validate_structure_sft(relocated / output.name)["status"] == "passed"
    assert export.resolve_shared_file(relocated / output.name, "source_refs.jsonl") == relocated / base.name / "source_refs.jsonl"


@pytest.mark.parametrize("mutation", ["MIC", "original_observation", "heldout_identity", "tool_binding", "native_structure"])
def test_validator_rejects_label_context_or_assignment_mutations(sealed_base, tmp_path, mutation):
    base, catalog, _ = sealed_base
    output = tmp_path / "qwen_joint_sft_v4"
    export.prepare_structure_sft(base, output, catalog_path=catalog, execute=_teacher(catalog, []))
    name = "validation.inputs.jsonl" if mutation == "heldout_identity" else "train.jsonl"
    rows = [json.loads(line) for line in (output / name).read_text().splitlines()]
    if mutation == "MIC":
        target = json.loads(rows[0]["messages"][-1]["content"])
        target["mic_estimate"]["value"] = 999
        rows[0]["messages"][-1]["content"] = json.dumps(target)
        match = "existing_MIC"
    elif mutation == "original_observation":
        request = json.loads(rows[0]["messages"][1]["content"])
        request["conditions"]["medium"] = "invented"
        rows[0]["messages"][1]["content"] = json.dumps(request)
        match = "original_request"
    elif mutation == "tool_binding":
        rows[0]["messages"][-3]["tool_calls"][0]["id"] = "unbound"
        match = "tool_binding"
    elif mutation == "native_structure":
        call = json.loads(rows[0]["messages"][-2]["content"])
        call["data"]["structures"][0]["source_locator"] = {"figure": "invented"}
        rows[0]["messages"][-2]["content"] = json.dumps(call)
        match = "native_catalog"
    else:
        rows[0]["case_ids"] = ["reassigned"]
        match = "heldout_assignment"
    _write(output / name, rows)
    manifest = json.loads((output / "manifest.json").read_text())
    manifest["files"][name]["sha256"] = _digest(output / name)
    (output / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match=match):
        export.validate_structure_sft(output)


def test_sealed_manifest_and_nonempty_output_guards(sealed_base, tmp_path):
    base, catalog, _ = sealed_base
    with pytest.raises(ValueError, match="manifest_changed"):
        export.prepare_structure_sft(base, tmp_path / "v4", catalog_path=catalog,
                                     expected_base_manifest_sha256="0" * 64)
    with pytest.raises(ValueError, match="separate"):
        export.prepare_structure_sft(base, base / "v4", catalog_path=catalog)
    output = tmp_path / "v4"
    output.mkdir()
    (output / "existing").write_text("preserve")
    with pytest.raises(FileExistsError, match="nonempty"):
        export.prepare_structure_sft(base, output, catalog_path=catalog)


def test_existing_heldout_omics_trajectory_is_retained_without_new_teacher_results(sealed_base, tmp_path):
    base, catalog, _ = sealed_base
    name = "validation.inputs.jsonl"
    row = json.loads((base / name).read_text())
    call = {"tool_call_id": "observed-omics", "name": "overview", "arguments": {}, "ok": True,
            "data": {"source_id": "profile:A", "species": {"taxonomy_id": "NCBITaxon:562"}}}
    row["messages"].extend([
        {"role": "assistant", "content": "", "tool_calls": [{"id": "observed-omics", "type": "function",
            "function": {"name": "overview", "arguments": {}}}]},
        {"role": "tool", "tool_call_id": "observed-omics", "content": json.dumps(call)}])
    _write(base / name, [row])
    manifest = json.loads((base / "manifest.json").read_text())
    manifest["files"][name]["sha256"] = _digest(base / name)
    (base / "manifest.json").write_text(json.dumps(manifest))
    output = tmp_path / "qwen_joint_sft_v4"
    export.prepare_structure_sft(base, output, catalog_path=catalog, execute=_teacher(catalog, []))
    prepared = json.loads((output / name).read_text())
    assert prepared["messages"][1:] == row["messages"][1:]
    assert not any("structure" in message.get("tool_call_id", "") for message in prepared["messages"])


def test_derived_offsets_bind_new_training_rows(sealed_base, tmp_path):
    base, catalog, _ = sealed_base
    output = tmp_path / "qwen_joint_sft_v4"
    export.prepare_structure_sft(base, output, catalog_path=catalog, execute=_teacher(catalog, []))
    item = json.loads((output / "structure.train.index.jsonl").read_text())
    with (output / item["file"]).open("rb") as source:
        source.seek(item["byte_offset"])
        line = source.readline()
    assert hashlib.sha256(line).hexdigest() == item["derived_row_sha256"]
    omics = json.loads((output / "omics.train.index.jsonl").read_text())
    assert omics["byte_offset"] == item["byte_offset"] and omics["record_id"] == item["record_id"]


def test_initial_teacher_rejects_unproved_strain_state_and_localization(sealed_base):
    _, catalog, _ = sealed_base
    data = _teacher(catalog, [])({"profile_id": "A-REFERENCE"})
    call = {"name": "cell_structure_overview", "tool_call_id": "c1", "ok": True, "data": data}
    data["coverage"]["current_state_supported"] = True
    with pytest.raises(ValueError, match="unknown_strain_state"):
        export.structure_analysis(call)
    data["coverage"]["current_state_supported"] = False
    data["structures"][0]["protein_id"] = "not_measured"
    with pytest.raises(ValueError, match="without_protein_localization"):
        export.structure_analysis(call)


def test_compartment_view_queries_all_nodes_and_retains_full_topology_as_explicit_option(sealed_base, tmp_path):
    base, catalog, _ = sealed_base
    source = json.loads(catalog.read_text())
    inner = source["structures"][0]
    outer = {**deepcopy(inner), "structure_id": "reference:562:outer_membrane", "compartment": "outer_membrane",
             "statement": "The reference includes an outer membrane."}
    edge = {**deepcopy(inner), "structure_id": "reference:562:membrane_adjacency", "kind": "adjacency",
            "adjacent_to": "outer_membrane", "statement": "Two reference compartments are adjacent."}
    source["structures"].extend([outer, edge])
    catalog.write_text(json.dumps(source))
    for view, expected_count in (("compartment_nodes", 2), ("full", 3)):
        output = tmp_path / view
        report = export.prepare_structure_sft(base, output, catalog_path=catalog, structure_view=view,
                                               execute=_teacher(catalog, [], structure_view=view))
        row = json.loads((output / "joint.train.jsonl").read_text())
        call = json.loads(row["messages"][-2]["content"])
        target = Assessment.model_validate_json(row["messages"][-1]["content"])
        assert len(call["data"]["structures"]) == expected_count
        assert len(target.structure_analysis.compartment_hypotheses) == expected_count
        assert all(item.accessibility == "unknown" for item in target.structure_analysis.accessibility_barriers)
        if view == "compartment_nodes":
            assert call["name"] == "query_cell_structure"
            assert call["arguments"] == {"structure_ids": [inner["structure_id"], outer["structure_id"]], "limit": 2}
            assert report["structure_derivation"]["retrieval_policy"] == "all_compartment_nodes"
        else:
            assert call["name"] == "cell_structure_overview" and call["arguments"] == {}
            assert report["structure_derivation"]["retrieval_policy"] == "full_topology"
