"""The pilot uses frozen public identities and actual scoped structure context."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from praxis_virtualcell.datasets import validation_pilot as pilot
from praxis_virtualcell.datasets.species_registry import _digest
from praxis_virtualcell.datasets.structure_supervision import _add_tools, _tool_definitions
from praxis_virtualcell.llm_prediction.schemas import Assessment


def _write(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def _row(taxon, reference, index):
    profile = f"REF-{taxon}" if reference else None
    request = {"candidate": {"smiles": "CCO"}, "organism": {"taxon_id": taxon, "label": f"strain-{index}",
        "namespace": "fixture", "strain_id": f"strain-{taxon}-{index}", "species": f"species-{taxon}"},
        "conditions": {"medium": None}, "profile_id": profile,
        "available_modalities": ["genome"] if reference else [],
        "prediction_scope": "strain_reference" if reference else "strain_conditioned_auxiliary"}
    messages = [{"role": "system", "content": "Return an Assessment from public data only."},
                {"role": "user", "content": json.dumps(request)}]
    tools = []
    if reference:
        tools = [{"type": "function", "function": {"name": name, "parameters": {}}}
                 for name in ("overview", "search_features", "query_features")]
        for identifier, name, data in (("seed-overview", "overview", {"selected_modalities": ["genome"]}),
                                       ("seed-feature", "query_features", {"features": [{"gene_id": "G1"}]})):
            call = {"id": identifier, "type": "function", "function": {"name": name, "arguments": {}}}
            reply = {"tool_call_id": identifier, "name": name, "arguments": {}, "ok": True,
                     "data": {"profile_id": profile, **data}}
            messages.extend([{"role": "assistant", "content": "", "tool_calls": [call]},
                             {"role": "tool", "tool_call_id": identifier, "content": json.dumps(reply)}])
    return {"record_id": f"validation:{taxon}-{reference}-{index}", "split": "validation",
            "case_ids": [f"case-{taxon}-{reference}-{index}"], "cohorts": ["frozen_scaffold"],
            "target_contract": "praxis.assessment-supervision.v1", "messages": messages, "tools": tools}


@pytest.fixture
def public_dataset(tmp_path):
    base, derivative = tmp_path / "v3", tmp_path / "v4"
    base.mkdir()
    derivative.mkdir()
    rows = [_row(taxon, reference, index) for taxon in (470, 562, 287, 573)
            for reference in (False, True) for index in range(3)]
    _write(base / "validation.inputs.jsonl", rows)
    base_manifest = {"files": {"validation.inputs.jsonl": {
        "sha256": _digest(base / "validation.inputs.jsonl"), "records": len(rows)},
        "validation.answers.index.jsonl": {"sha256": "do-not-open", "records": len(rows)}}}
    (base / "manifest.json").write_text(json.dumps(base_manifest))
    tools, system = _tool_definitions()
    _write(derivative / "validation.inputs.jsonl", [_add_tools(row, tools, system) for row in rows])
    manifest = {"structure_derivation": {"base_dataset": {"path": "../v3",
        "manifest": {"sha256": _digest(base / "manifest.json")}}}, "files": {"validation.inputs.jsonl": {
        "sha256": _digest(derivative / "validation.inputs.jsonl"), "records": len(rows)}}}
    (derivative / "manifest.json").write_text(json.dumps(manifest))
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps({"status": "reviewed", "split": "validation",
        "dataset_manifest_sha256": _digest(base / "manifest.json"), "record_count": len(rows),
        "excluded_record_ids": [rows[0]["record_id"]], "eligible_record_count": len(rows) - 1,
        "decisions": [{"native_description": "This description must not participate in sampling."}]}))
    return base, derivative, audit_path, rows


def _executor(context):
    assert set(context) == {"profile_id", "organism"}
    organism = context["organism"]
    return {"profile_id": context["profile_id"], "structures": [{"structure_id": "reference:membrane",
            "compartment": "inner_membrane", "evidence_scope": "species_prior"}],
            "request_scope": {"taxonomy_id": "NCBITaxon:" + str(organism["taxon_id"]),
                              "strain": organism["label"], "strain_namespace": organism["namespace"]}}


def test_public_selection_is_balanced_and_independent_of_input_order(public_dataset):
    _, _, _, rows = public_dataset
    eligible = {row["record_id"] for row in rows} - {rows[0]["record_id"]}
    one = pilot.select_public_rows(rows, eligible, count=16)
    two = pilot.select_public_rows(list(reversed(rows)), eligible, count=16)
    assert one == two
    counts = {}
    for row in one:
        request = pilot._request(row)
        key = (request["organism"]["taxon_id"], bool(request["profile_id"]))
        counts[key] = counts.get(key, 0) + 1
    assert len(counts) == 8 and set(counts.values()) == {2}
    assert rows[0]["record_id"] not in {row["record_id"] for row in one}


def test_preparation_preserves_sealed_sources_and_never_opens_answers(public_dataset, tmp_path, monkeypatch):
    base, derivative, audit, _ = public_dataset
    before = {str(path): path.read_bytes() for directory in (base, derivative) for path in directory.iterdir()}
    original_open = Path.open
    def boundary(path, *args, **kwargs):
        if "answers" in path.name or path.name == "train.jsonl" or "MIC" in path.name:
            pytest.fail("Public pilot opened private answers, training targets or MIC labels")
        return original_open(path, *args, **kwargs)
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", boundary)
        output = tmp_path / "pilot"
        report = pilot.prepare_validation_pilot(derivative, audit, output, count=16, execute=_executor)
    assert all(Path(path).read_bytes() == content for path, content in before.items())
    assert report["private_answers_opened"] == 0 and report["MIC_labels_opened"] == 0
    assert report["paired_ablation_record_count"] == 8
    assert (output / report["scoring_dataset_manifest"]["path"]).resolve() == base / "manifest.json"
    original = {row["record_id"]: row for row in pilot._rows(derivative / "validation.inputs.jsonl")}
    main = pilot._rows(output / "validation.inputs.jsonl")
    for row in main:
        old = original[row["record_id"]]
        assert row["record_id"] == old["record_id"]
        request = pilot._request(row)
        assert request["assessment_schema"] == Assessment.model_json_schema()
        assert {k: v for k, v in request.items() if k != "assessment_schema"} == pilot._request(old)
        if pilot._request(row)["profile_id"]:
            assert row["messages"][0] == old["messages"][0]
            assert row["messages"][2:-2] == old["messages"][2:]
            assert json.loads(row["messages"][-1]["content"])["name"] == "cell_structure_overview"
        else:
            assert row["tools"] == [] and [m["role"] for m in row["messages"]] == ["system", "user"]
    for layer in ("omics", "structure"):
        ablation = pilot._rows(output / f"without_{layer}.inputs.jsonl")
        assert [row["record_id"] for row in ablation] == report["paired_ablation_record_ids"]
        for row in ablation:
            request, old_request = pilot._request(row), pilot._request(original[row["record_id"]])
            assert request["assessment_schema"] == Assessment.model_json_schema()
            assert {k: v for k, v in request.items() if k not in {"available_modalities", "assessment_schema"}} == {
                k: v for k, v in old_request.items() if k != "available_modalities"}
            names = {m["function"]["name"] for m in row["tools"]}
            assert not names & (pilot.OMICS_TOOLS if layer == "omics" else pilot.STRUCTURE_TOOLS)
            assert request["available_modalities"] == ([] if layer == "omics" else old_request["available_modalities"])
            pilot.qwen_messages(row["messages"])


@pytest.mark.parametrize("mutation,match", [("answer", "assistant_answer"), ("private", "unrecognized_request"),
                                            ("candidate_name", "SMILES_only"), ("train", "public_validation")])
def test_sampler_rejects_answers_private_fields_and_non_structure_candidates(mutation, match):
    row = _row(562, False, 0)
    if mutation == "answer":
        row["messages"].append({"role": "assistant", "content": '{"mic_estimate": 777}'})
    elif mutation == "train":
        row["split"] = "train"
    else:
        request = json.loads(row["messages"][1]["content"])
        if mutation == "candidate_name":
            request["candidate"]["name"] = "secret"
        else:
            request["mic_value"] = 777
        row["messages"][1]["content"] = json.dumps(request)
    with pytest.raises(ValueError, match=match):
        pilot.select_public_rows([row], {row["record_id"]}, count=1)


def test_structure_bootstrap_checks_actual_strain_scope():
    tools, system = _tool_definitions()
    row = _add_tools(_row(562, True, 0), tools, system)
    def wrong(context):
        result = _executor(context)
        result["request_scope"]["strain"] = "other-strain"
        return result
    with pytest.raises(ValueError, match="strain_identity_mismatch"):
        pilot.add_live_structure_context(row, wrong)


@pytest.mark.parametrize("mutation", ["extra_label", "changed_default"])
def test_schema_accepts_only_actual_public_platform_contract_without_labels(mutation):
    row = pilot.add_assessment_schema(_row(562, False, 0))
    request = pilot._request(row)
    assert request["assessment_schema"] == Assessment.model_json_schema()
    if mutation == "extra_label":
        request["assessment_schema"]["experimental_MIC"] = 777
    else:
        request["assessment_schema"]["$defs"]["MICEstimate"]["properties"]["value"]["default"] = 777
    row["messages"][1]["content"] = json.dumps(request)
    with pytest.raises(ValueError, match="public_platform_contract"):
        pilot._request(row)


def test_sealed_public_change_wrong_audit_and_existing_output_are_rejected(public_dataset, tmp_path):
    _, derivative, audit, _ = public_dataset
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "preserve").write_text("must remain")
    with pytest.raises(FileExistsError, match="nonempty"):
        pilot.prepare_validation_pilot(derivative, audit, existing, count=8, execute=_executor)
    wrong = tmp_path / "wrong_audit.json"
    content = json.loads(audit.read_text())
    content["dataset_manifest_sha256"] = "0" * 64
    wrong.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="reviewed_base_validation_audit"):
        pilot.prepare_validation_pilot(derivative, wrong, tmp_path / "wrong", count=8, execute=_executor)
    original = derivative / "validation.inputs.jsonl"
    rows = pilot._rows(original)
    rows[0]["messages"][1]["content"] += " "
    _write(original, rows)
    with pytest.raises(ValueError, match="sealed_public_input_changed"):
        pilot.prepare_validation_pilot(derivative, audit, tmp_path / "changed", count=8, execute=_executor)


def test_audit_descriptions_do_not_change_selected_IDs(public_dataset, tmp_path):
    _, derivative, audit, _ = public_dataset
    first = pilot.prepare_validation_pilot(derivative, audit, tmp_path / "first", count=8, execute=_executor)
    changed = deepcopy(json.loads(audit.read_text()))
    changed["decisions"] = [{"native_description": "Entirely different", "private_answer": 999}]
    audit.write_text(json.dumps(changed))
    second = pilot.prepare_validation_pilot(derivative, audit, tmp_path / "second", count=8, execute=_executor)
    assert first["record_ids"] == second["record_ids"]
    assert (tmp_path / "first/validation.inputs.jsonl").read_bytes() == (tmp_path / "second/validation.inputs.jsonl").read_bytes()
