import hashlib
import json
from pathlib import Path

import pytest

from praxis_virtualcell.datasets.joint_supervision import prepare_joint_supervision
from praxis_virtualcell.datasets.literature import parse_jats


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    import praxis_virtualcell.datasets.strain_dataset as strain
    monkeypatch.setattr(strain, "validate_strain_dataset", lambda path: {})
    source, literature = tmp_path / "sft", tmp_path / "literature"
    source.mkdir()
    literature.mkdir()
    article = literature / "article.xml"
    article.write_text('<article><front><article-meta><article-id pub-id-type="doi">10.1/pilot</article-id>'
                       '</article-meta></front><body><p id="binding">Drug A was tested against AB5075.</p>'
                       '<p id="claim">Drug A may affect fatty acid metabolism.</p></body></article>')
    sha = hashlib.sha256(article.read_bytes()).hexdigest()
    asset = {"file": str(article), "sha256": sha}
    parsed = parse_jats(article.read_bytes(), paper_id="paper:pilot", source=asset)
    passages = parsed["passages"]
    def write(path, rows):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    component = {"record_id": "mic:one", "case_ids": ["case-one"], "split": "train", "trainable": True,
                 "source_case_count": 1, "observation_view_id": "AB-STRAIN",
                 "messages": [{"role": "system", "content": "MIC task"},
                              {"role": "user", "content": '{"candidate":{"smiles":"CCO"}}'},
                              {"role": "tool", "content": '{"presence":true}'},
                              {"role": "assistant", "content": '{"endpoint":"MIC","observations":[{"value":2}]}'}]}
    write(source / "mic_sft.jsonl", [component])
    write(source / "joint_review_queue.jsonl", [{"MIC_training_record_id": "mic:one", "input": {
        "profile_id": "AB-STRAIN", "candidate": {"smiles": "CCO"}}}])
    dataset_summary = tmp_path / "dataset.json"
    dataset_summary.write_text('{}')
    answer = tmp_path / "answer.jsonl"
    write(answer, [{"record_id": "label-one", "molecule": {"source_molecule_id": "CHEMBL1", "canonical_smiles": "CCO"},
                    "source": {"document_id": "DOC1"}}])
    write(source / "private_training_sources.jsonl", [{"record_id": "mic:one", "private_sources": [{"case_id": "case-one",
        "locator": {"path": str(answer), "sha256": hashlib.sha256(answer.read_bytes()).hexdigest(),
                    "byte_offset": 0, "record_id": "label-one"}}]}])
    write(source / "observation_views.jsonl", [])
    (source / "summary.json").write_text(json.dumps({"dataset_summary": str(dataset_summary),
        "dataset_summary_sha256": hashlib.sha256(dataset_summary.read_bytes()).hexdigest(),
        "files": {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in source.glob('*.jsonl')}}))
    write(literature / "papers.jsonl", [{"doi": "10.1/pilot", "paper_id": "paper:pilot", "case_ids": ["case-one"],
                                       "status": "open_fulltext_parsed", "article": asset}])
    write(literature / "passages.jsonl", passages)
    def quote(p):
        return {"passage_id": p["passage_id"], "start": 0, "end": len(p["text"]), "text": p["text"]}
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({"compound_records": [{"compound_key": "Drug A", "molecule_chembl_id": "CHEMBL1",
                                                        "document_chembl_id": "DOC1"}]}))
    annotation = {"component_record_id": "mic:one", "case_ids": ["case-one"], "doi": "10.1/pilot",
                  "compound_paper_name": "Drug A", "compound_mapping": {"file": str(mapping),
                    "sha256": hashlib.sha256(mapping.read_bytes()).hexdigest(), "pointer": "/compound_records/0"},
                  "compound_binding_basis": "Source mapping reviewed.",
                  "strain_binding_basis": "Exact AB5075 source label.", "binding_quotes": [quote(passages[0])],
                  "claims": [{"statement": "Possible fatty acid metabolism effect; target unknown.",
                              "evidence_grade": "author_proposed", "experiment_type": "author_hypothesis",
                              "target_names": [], "quotes": [quote(passages[1])]}],
                  "reviewer": "software-fixture-review", "review_status": "source_reviewed",
                  "claim_scope": "exact_compound_general_mechanism"}
    reviews = tmp_path / "reviews.json"
    reviews.write_text(json.dumps({"schema_version": "praxis.literature-reviews.v1", "annotations": [annotation]}))
    return source, literature, reviews, tmp_path / "out", annotation, passages, component


def test_joint_targets_preserve_public_tools_and_hypothesis_grade(pilot):
    source, literature, reviews, output, _, _, component = pilot
    report = prepare_joint_supervision(source, literature, reviews, output)
    assert report["record_count"] == 1 and report["complete_agent_report_count"] == 0
    row = json.loads((output / "joint_sft.jsonl").read_text())
    assert row["model_generated_target"] is True and row["human_reviewed"] is False
    assert row["target_origins"]["MIC"] == "source_verified_experimental"
    assert row["messages"][1:-1] == component["messages"][1:-1]
    target = json.loads(row["messages"][-1]["content"])
    assert target["observations"] == [{"value": 2}]
    claim = target["literature_mechanisms"][0]
    assert claim["evidence_grade"] == "author_proposed"
    assert claim["strain_specific_experiment"] is False
    assert claim["direct_target_binding_supported"] is False
    assert claim["target_names"] == []


@pytest.mark.parametrize("mutation", ["quote", "case", "heldout", "source", "forged_passage", "compound", "grade"])
def test_joint_rejects_unbound_answers_or_changed_source(pilot, mutation):
    source, literature, reviews, output, annotation, passages, component = pilot
    if mutation == "quote":
        annotation["claims"][0]["quotes"][0]["text"] = "Invented binding result."
    elif mutation == "case":
        annotation["case_ids"] = ["other-case"]
    elif mutation == "heldout":
        component["split"] = "test"
        (source / "mic_sft.jsonl").write_text(json.dumps(component) + "\n")
    elif mutation == "source":
        (literature / "article.xml").write_text("changed source")
    elif mutation == "compound":
        annotation["compound_paper_name"] = "Drug B"
    elif mutation == "grade":
        annotation["claims"][0]["evidence_grade"] = "experimental"
    else:
        passages[1]["text"] = "Invented binding result."
        annotation["claims"][0]["quotes"][0].update(text=passages[1]["text"], end=len(passages[1]["text"]))
        (literature / "passages.jsonl").write_text("".join(json.dumps(p) + "\n" for p in passages))
    reviews.write_text(json.dumps({"schema_version": "praxis.literature-reviews.v1", "annotations": [annotation]}))
    with pytest.raises(ValueError):
        prepare_joint_supervision(source, literature, reviews, output)
    assert not output.exists()


def test_joint_native_DOI_case_differences_preserve_original_metadata(pilot):
    source, literature, reviews, output, annotation, _, _ = pilot
    article = literature / "article.xml"
    article.write_text(article.read_text().replace("10.1/pilot", "10.1/PILOT"))
    asset = {"file": str(article), "sha256": hashlib.sha256(article.read_bytes()).hexdigest()}
    parsed = parse_jats(article.read_bytes(), paper_id="paper:pilot", source=asset)
    (literature / "passages.jsonl").write_text("".join(json.dumps(row) + "\n" for row in parsed["passages"]))
    paper = json.loads((literature / "papers.jsonl").read_text())
    paper["article"] = asset
    (literature / "papers.jsonl").write_text(json.dumps(paper) + "\n")
    annotation["doi"] = "10.1/Pilot"
    reviews.write_text(json.dumps({"schema_version": "praxis.literature-reviews.v1", "annotations": [annotation]}))
    result = prepare_joint_supervision(source, literature, reviews, output)
    assert result["record_count"] == 1
    private = json.loads((output / "private_literature_reviews.jsonl").read_text())
    assert private["annotation"]["doi"] == "10.1/Pilot"
    assert private["binding_evidence"][0]["doi"] == "10.1/pilot"
    assert parsed["identifiers"]["doi"] == "10.1/PILOT"


def test_joint_groups_MIC_sources_but_binds_mechanism_to_explicit_paper_subset(pilot):
    source, literature, reviews, output, annotation, _, component = pilot
    private_path = source / 'private_training_sources.jsonl'
    private = json.loads(private_path.read_text())
    first = private['private_sources'][0]['locator']
    answer_path = Path(first['path'])
    original = answer_path.read_bytes()
    second = {'record_id': 'label-two', 'molecule': {'source_molecule_id': 'CHEMBL2', 'canonical_smiles': 'CCO'},
              'source': {'document_id': 'DOC2'}}
    answer_path.write_bytes(original + (json.dumps(second) + '\n').encode())
    digest = hashlib.sha256(answer_path.read_bytes()).hexdigest()
    first['sha256'] = digest
    private['private_sources'].append({'case_id': 'case-two', 'locator': {
        'path': str(answer_path), 'sha256': digest, 'byte_offset': len(original), 'record_id': 'label-two'}})
    private_path.write_text(json.dumps(private) + '\n')
    component.update(case_ids=['case-one', 'case-two'], source_case_count=2)
    component['messages'][-1]['content'] = json.dumps({'endpoint': 'MIC', 'observations': [{'value': 2}, {'value': 4}]})
    (source / 'mic_sft.jsonl').write_text(json.dumps(component) + '\n')
    annotation.update(case_ids=['case-one', 'case-two'], mechanism_case_ids=['case-one'])
    reviews.write_text(json.dumps({'schema_version': 'praxis.literature-reviews.v1', 'annotations': [annotation]}))
    summary_path = source / 'summary.json'
    summary = json.loads(summary_path.read_text())
    for name in summary['files']:
        summary['files'][name]['sha256'] = hashlib.sha256((source / name).read_bytes()).hexdigest()
    summary_path.write_text(json.dumps(summary))
    report = prepare_joint_supervision(source, literature, reviews, output)
    assert report['MIC_measurement_count'] == 2
    target = json.loads(json.loads((output / 'joint_sft.jsonl').read_text())['messages'][-1]['content'])
    assert target['observations'] == [{'value': 2}, {'value': 4}]
    # The second MIC publication cannot impersonate the first paper's mechanism.
    annotation['mechanism_case_ids'] = ['case-two']
    reviews.write_text(json.dumps({'schema_version': 'praxis.literature-reviews.v1', 'annotations': [annotation]}))
    with pytest.raises(ValueError, match='bound_to_paper'):
        prepare_joint_supervision(source, literature, reviews, output.parent / 'bad-subset')
