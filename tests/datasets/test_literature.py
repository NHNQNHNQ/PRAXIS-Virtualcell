"""Open literature remains source material, never automatic training gold."""
import hashlib
import io
import json
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

from praxis_virtualcell.datasets import literature

JATS = b'''<?xml version="1.0" encoding="UTF-8"?>
<article xmlns:xlink="http://www.w3.org/1999/xlink">
 <front><article-meta><article-id pub-id-type="doi">10.1234/example</article-id>
 <article-id pub-id-type="pmid">123</article-id><article-id pub-id-type="pmc">456</article-id>
 <permissions><license license-type="open-access" xlink:href="https://creativecommons.org/licenses/by/4.0/">
 <license-p>Creative Commons Attribution 4.0.</license-p></license></permissions>
 <abstract><p>Abstract says all compounds bind gyrase; do not extract this as gold.</p></abstract></article-meta></front>
 <body><sec id="methods"><title>Materials and methods</title>
 <p id="culture">AB5075 was grown in Mueller-Hinton broth without antibiotics at 37 C.</p>
 <p id="assay">Recombinant gyrase bound compound A with a measured Kd. This may explain growth inhibition.</p>
 <table-wrap id="t1"><label>Table 1</label><caption><p>Isolate conditions</p></caption>
 <table><thead><tr><th>Isolate</th><th>Medium</th></tr></thead>
 <tbody><tr><td>AB5075</td><td>Mueller-Hinton broth</td></tr></tbody></table></table-wrap>
 <fig id="f1"><label>Figure 1</label><caption><p>Deletion mutant showed altered efflux.</p></caption>
 <graphic xlink:href="figure1.jpg"/></fig></sec></body>
 <back><ref-list><ref><mixed-citation><p>A cited paper proposes other mechanisms.</p></mixed-citation></ref></ref-list>
 <supplementary-material id="s1" xlink:href="supp.xlsx"><caption><p>Supplementary Table 1.</p></caption></supplementary-material></back>
</article>'''


def case(*, case_id="case-1", doi="10.1234/example", split="train", strain="AB5075", namespace="stock"):
    return {"case_id": case_id, "split": split,
            "strain": {"strain_id": "strain-1", "species": "Acinetobacter baumannii", "taxon_id": 470,
                       "label": strain, "namespace": namespace, "identity_basis": "native assay"},
            "candidate": {"id": "CHEMBL1", "smiles": "CCO"},
            "private_answer": {"record_id": f"activity:{case_id}", "MIC": 16},
            "literature": {"doi": doi, "document_id": "CHEMBLDOC1"}}


def write_cases(path: Path, records):
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    return path


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def official_fake(monkeypatch, *, xml=JATS, supplementary=True):
    calls = []

    def request(url, *, max_bytes):
        calls.append(url)
        if url.startswith(literature.PMC_IDS):
            dois = parse_qs(urlparse(url).query)["ids"][0].split(",")
            data = {"records": [{"doi": doi, "pmid": "123", "pmcid": "PMC456"} for doi in dois]}
            return json.dumps(data).encode(), {"content-type": "application/json"}
        if "/search?" in url:
            doi = parse_qs(urlparse(url).query)["query"][0].removeprefix('DOI:"').removesuffix('"')
            data = {"resultList": {"result": [{"doi": doi, "source": "MED", "pmid": "123",
                     "pmcid": "PMC456", "isOpenAccess": "Y", "title": "A primary study"}]}}
            return json.dumps(data).encode(), {"content-type": "application/json"}
        if url.endswith("/fullTextXML"):
            return xml, {"content-type": "application/xml"}
        if url.endswith("/supplementaryFiles") and supplementary:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("supp.xlsx", b"opaque original supplementary bytes")
            return buffer.getvalue(), {"content-type": "application/zip"}
        raise HTTPError(url, 404, "unavailable", {}, None)

    monkeypatch.setattr(literature, "_request_bytes", request)
    return calls


def test_parse_jats_native_anchors_table_cells_figure_and_no_abstract():
    source = {"file": "/native/article.xml", "sha256": hashlib.sha256(JATS).hexdigest()}
    result = literature.parse_jats(JATS, paper_id="paper:1", source=source)
    rows = result["passages"]
    assert len(rows) == 8  # 2 paragraphs, caption, 4 cells, figure caption
    assert all("Abstract says" not in row["text"] and "cited paper" not in row["text"] for row in rows)
    culture = next(row for row in rows if row["locator"]["xml_id"] == "culture")
    assert culture["section"] == ["body", "Materials and methods"]
    assert culture["locator"]["xpath"] == "/article/body[1]/sec[1]/p[1]"
    cell = next(row for row in rows if row["kind"] == "table_cell" and row["text"] == "Mueller-Hinton broth")
    assert cell["locator"]["xpath"].endswith("/table[1]/tbody[1]/tr[1]/td[2]")
    assert cell["context"]["header_rows"] == [["Isolate", "Medium"]]
    assert cell["context"]["row_cells"] == ["AB5075", "Mueller-Hinton broth"]
    assert cell["context"]["table_id"] == "t1"
    figure = next(row for row in rows if row["kind"] == "figure_caption")
    assert figure["context"]["graphics"] == ["figure1.jpg"]
    assert result["supplementary_refs"][0]["href"] == "supp.xlsx"
    assert result["licenses"][0]["url"] == "https://creativecommons.org/licenses/by/4.0/"


def test_candidate_quotes_are_exact_and_classifications_are_only_proposals():
    rows = literature.parse_jats(JATS, paper_id="paper:1", source={"file": "a.xml", "sha256": "a" * 64})["passages"]
    candidates = literature.locate_candidates(rows, doi="10.1234/example", record_ids=["record-1"], strain_labels=["AB5075"])
    by_id = {row["passage_id"]: row for row in rows}
    for item in candidates:
        text = by_id[item["passage_id"]]["text"]
        assert text[item["span"]["start"]:item["span"]["end"]] == item["quoted_span"]
        assert item["review_status"] == "needs_review"
        assert not item["gold_eligible"] and not item["inference_eligible"]
        assert item["record_binding_status"] == "paper_only_needs_review"
        assert item["record_ids"] == ["record-1"]
    assert {item["claim_classification"] for item in candidates if item["kind"] == "mechanism"} == {
        "experimental", "genetic"}
    assert any(item["strain_mentions"] == ["AB5075"] for item in candidates)
    assert all(not item["compound_mentions"] for item in candidates)
    hypothetical = {**rows[0], "text": "Docking suggests binding may target another enzyme."}
    candidate = literature.locate_candidates([hypothetical], doi="10.1234/example", record_ids=[])[0]
    assert candidate["claim_classification"] == "author_proposed"


def test_acquire_only_namespaced_train_dois_dedup_and_offline_identical(tmp_path, monkeypatch):
    calls = official_fake(monkeypatch)
    cases = write_cases(tmp_path / "cases.jsonl", [case(), case(case_id="same-paper", doi="https://doi.org/10.1234/EXAMPLE"),
                        case(case_id="held-out", doi="10.1234/heldout", split="test"),
                        case(case_id="unresolved", doi="10.1234/unresolved", namespace=None)])
    output = tmp_path / "literature"
    summary = literature.acquire_literature(cases, output)
    assert summary["paper_count"] == 1 and summary["gold_count"] == 0
    assert summary["selection_counts"]["excluded_not_train"] == 1
    assert summary["selection_counts"]["excluded_unresolved_strain_namespace"] == 1
    paper = read_jsonl(output / "papers.jsonl")[0]
    assert paper["status"] == "open_fulltext_parsed" and paper["pmcid"] == "PMC456"
    assert paper["record_ids"] == ["activity:case-1", "activity:same-paper"]
    assert paper["article"]["sha256"] == hashlib.sha256(JATS).hexdigest()
    assert paper["supplementary_assets"][0]["storage"] == "archive_member_reference_not_extracted"
    assert not list(output.rglob("*.xlsx"))
    assert len(calls) == 4
    files = list(output.rglob("*"))
    before = {path: path.read_bytes() for path in files if path.is_file()}
    monkeypatch.setattr(literature, "_request_bytes", lambda *args, **kwargs: pytest.fail("offline network"))
    assert literature.acquire_literature(cases, output, offline=True) == summary
    assert {path: path.read_bytes() for path in before} == before
    all_output = (output / "extraction_candidates.jsonl").read_text()
    assert '"MIC":16' not in all_output


def test_missing_fulltext_and_supplements_are_reported_not_gold(tmp_path, monkeypatch):
    official_fake(monkeypatch, supplementary=False)
    cases = write_cases(tmp_path / "cases.jsonl", [case()])
    output = tmp_path / "literature"
    summary = literature.acquire_literature(cases, output)
    paper = read_jsonl(output / "papers.jsonl")[0]
    assert paper["status"] == "open_fulltext_parsed"
    assert paper["supplementary_status"] == "unavailable_or_exceeds_pilot_bound"
    assert paper["errors"] == [{"stage": "supplementary", "error": "official_api_http_404"}]
    assert summary["gold_count"] == 0
    before = {name: (output / name).read_bytes() for name in ("papers.jsonl", "passages.jsonl", "extraction_candidates.jsonl")}
    monkeypatch.setattr(literature, "_request_bytes", lambda *args, **kwargs: pytest.fail("offline network"))
    assert literature.acquire_literature(cases, output, offline=True) == summary
    assert {name: (output / name).read_bytes() for name in before} == before


def test_no_pmc_record_keeps_metadata_only_and_no_candidates(tmp_path, monkeypatch):
    def request(url, *, max_bytes):
        data = {"records": []} if url.startswith(literature.PMC_IDS) else {
            "resultList": {"result": [{"doi": "10.1234/example", "source": "MED", "pmid": "123", "isOpenAccess": "N"}]}}
        return json.dumps(data).encode(), {}
    monkeypatch.setattr(literature, "_request_bytes", request)
    output = tmp_path / "literature"
    result = literature.acquire_literature(write_cases(tmp_path / "cases.jsonl", [case()]), output)
    assert result["paper_status_counts"] == {"metadata_only": 1}
    assert result["candidate_count"] == 0
    assert read_jsonl(output / "papers.jsonl")[0]["pmid"] == "123"


def test_pmcid_does_not_imply_open_access_fulltext(tmp_path, monkeypatch):
    calls = []
    def request(url, *, max_bytes):
        calls.append(url)
        assert not url.endswith("fullTextXML") and not url.endswith("supplementaryFiles")
        data = {"records": [{"doi": "10.1234/example", "pmid": "123", "pmcid": "PMC456"}]} if url.startswith(literature.PMC_IDS) else {
            "resultList": {"result": [{"doi": "10.1234/example", "source": "MED", "pmid": "123", "pmcid": "PMC456", "isOpenAccess": "N"}]}}
        return json.dumps(data).encode(), {}
    monkeypatch.setattr(literature, "_request_bytes", request)
    output = tmp_path / "out"
    result = literature.acquire_literature(write_cases(tmp_path / "cases.jsonl", [case()]), output)
    assert result["candidate_count"] == 0 and len(calls) == 2
    assert read_jsonl(output / "papers.jsonl")[0]["fulltext_status"] == "not_open_access_in_official_metadata"


def test_explicit_skip_supplements_retains_source_anchors_without_zip_request(tmp_path, monkeypatch):
    calls = official_fake(monkeypatch)
    output = tmp_path / "out"
    result = literature.acquire_literature(write_cases(tmp_path / "cases.jsonl", [case()]), output, skip_supplements=True)
    assert result["acquisition_policy"]["skip_supplements_current_pilot"]
    assert all(not url.endswith("supplementaryFiles") for url in calls)
    paper = read_jsonl(output / "papers.jsonl")[0]
    assert paper["supplementary_status"] == "skip_supplements_current_pilot"
    assert paper["supplementary_refs"][0]["linked_assets"][0]["href"] == "supp.xlsx"
    assert paper["status"] == "open_fulltext_parsed"


def test_phenotypic_pathway_candidates_do_not_become_protein_binding_gold():
    passage = {"passage_id": "p:1", "paper_id": "paper:1", "kind": "paragraph", "section": ["Results"],
               "text": "Fatty acid supplementation abrogated activity against AB5075 with observed MIC >128 ug/mL.",
               "locator": {"file": "one.xml", "sha256": "a" * 64, "xpath": "/article/body/p[1]"}, "context": {}}
    rows = literature.locate_candidates([passage], doi="10.1234/example", record_ids=["r:1"], strain_labels=["AB5075"])
    mechanism = next(row for row in rows if row["kind"] == "mechanism")
    assert mechanism["claim_classification"] == "experimental"
    assert mechanism["contains_phenotype_labels"]
    assert not mechanism["gold_eligible"] and not mechanism["inference_eligible"]
    assert mechanism["scope_status"] == "compound_strain_target_and_condition_binding_unverified"
    assert mechanism["record_binding_status"] == "paper_only_needs_review"


def test_nested_supplement_media_anchor_is_preserved():
    xml = JATS.replace(b'<supplementary-material id="s1" xlink:href="supp.xlsx">',
                       b'<supplementary-material id="s1"><media xlink:href="supp.xlsx"/>')
    parsed = literature.parse_jats(xml, paper_id="paper:1", source={"file": "one.xml", "sha256": "a" * 64})
    asset = parsed["supplementary_refs"][0]["linked_assets"][0]
    assert asset["href"] == "supp.xlsx"
    assert asset["xpath"].endswith("/supplementary-material[1]/media[1]")


def test_oai_jats_locator_contains_envelope_and_uses_original_source_hash():
    xml = b'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><GetRecord><record><metadata>' + JATS.split(b'?>', 1)[1] + b'</metadata></record></GetRecord></OAI-PMH>'
    digest = hashlib.sha256(xml).hexdigest()
    rows = literature.parse_jats(xml, paper_id="p:1", source={"file": "oai.xml", "sha256": digest})["passages"]
    assert len(rows) == 8
    culture = next(row for row in rows if row["locator"]["xml_id"] == "culture")
    assert culture["locator"]["xpath"] == "/OAI-PMH/GetRecord[1]/record[1]/metadata[1]/article[1]/body[1]/sec[1]/p[1]"
    assert culture["locator"]["sha256"] == digest
    with pytest.raises(ValueError, match="official_PMC_OAI_error"):
        literature.parse_jats(b'<OAI-PMH><error code="cannotDisseminateFormat">reuse not permitted</error></OAI-PMH>',
                              paper_id="p:1", source={"file": "oai.xml", "sha256": "a" * 64})


def test_known_epmc_outage_uses_one_official_pmc_oai_source(tmp_path, monkeypatch):
    calls = []
    xml = b'<OAI-PMH><GetRecord><record><metadata>' + JATS.split(b'?>', 1)[1] + b'</metadata></record></GetRecord></OAI-PMH>'
    def request(url, *, max_bytes):
        calls.append(url)
        if url.startswith(literature.PMC_IDS):
            return json.dumps({"records": [{"doi": "10.1234/example", "pmid": "123", "pmcid": "PMC456"}]}).encode(), {}
        if url.startswith(literature.PMC_OAI):
            return xml, {}
        raise HTTPError(url, 503, "source unavailable", {}, None)
    monkeypatch.setattr(literature, "_request_bytes", request)
    cases = write_cases(tmp_path / "cases.jsonl", [case()])
    output = tmp_path / "out"
    result = literature.acquire_literature(cases, output, skip_supplements=True)
    assert result["paper_status_counts"] == {"open_fulltext_parsed": 1}
    assert sum(url.startswith(literature.PMC_OAI) for url in calls) == 1
    assert sum("/search?" in url for url in calls) == 1
    before = (output / "papers.jsonl").read_bytes()
    assert literature.acquire_literature(cases, output, offline=True, skip_supplements=True) == result
    assert (output / "papers.jsonl").read_bytes() == before
    assert sum("/search?" in url for url in calls) == 1


@pytest.mark.parametrize("xml", [JATS.replace(b"10.1234/example", b"10.1234/different"),
                                    b"<article><front><abstract><p>bind protein</p></abstract></front></article>"])
def test_wrong_article_or_abstract_only_never_creates_candidates(tmp_path, monkeypatch, xml):
    official_fake(monkeypatch, xml=xml)
    result = literature.acquire_literature(write_cases(tmp_path / "cases.jsonl", [case()]), tmp_path / "out")
    assert result["paper_status_counts"] == {"source_error_or_fulltext_unavailable": 1}
    assert result["passage_count"] == 0 and result["candidate_count"] == 0


def test_native_metadata_reused_with_pointer_no_copy_and_conflict_rejected(tmp_path, monkeypatch):
    official_fake(monkeypatch)
    native = tmp_path / "old-documents.json"
    native.write_text(json.dumps({"documents": [{"doi": "10.1234/example", "pubmed_id": 123,
                                             "document_chembl_id": "CHEMBLDOC1"}]}))
    item = case()
    item["literature"]["native_metadata_ref"] = {"file": str(native), "pointer": "/documents/0",
                                               "sha256": hashlib.sha256(native.read_bytes()).hexdigest()}
    output = tmp_path / "out"
    literature.acquire_literature(write_cases(tmp_path / "cases.jsonl", [item]), output)
    paper = read_jsonl(output / "papers.jsonl")[0]
    assert paper["native_metadata_refs"][0]["file"] == str(native)
    assert not any(path.read_bytes() == native.read_bytes() for path in (output / "nativecache").iterdir())
    item["literature"]["native_metadata_ref"]["sha256"] = "0" * 64
    result = literature.acquire_literature(write_cases(tmp_path / "other-cases.jsonl", [item]), tmp_path / "bad")
    assert result["candidate_count"] == 0
    assert result["paper_status_counts"] == {"source_error_or_fulltext_unavailable": 1}


def test_cached_source_tampering_cannot_be_overwritten(tmp_path, monkeypatch):
    calls = official_fake(monkeypatch)
    cache = literature.LiteratureCache(tmp_path)
    url = literature.EUROPE_PMC + "PMC456/fullTextXML"
    _, ref = cache.fetch(url, "xml")
    Path(ref["file"]).write_bytes(b"modified")
    with pytest.raises(ValueError, match="fingerprint"):
        cache.fetch(url, "xml")
    assert len(calls) == 1
    assert Path(ref["file"]).read_bytes() == b"modified"


def test_native_and_official_pmid_conflict_cannot_silently_rebind(tmp_path, monkeypatch):
    official_fake(monkeypatch)
    native = tmp_path / "old.json"
    native.write_text(json.dumps({"doi": "10.1234/example", "pubmed_id": "999"}))
    item = case()
    item["literature"]["native_metadata_ref"] = {"file": str(native), "pointer": ""}
    output = tmp_path / "out"
    summary = literature.acquire_literature(write_cases(tmp_path / "cases.jsonl", [item]), output)
    assert summary["candidate_count"] == 0
    assert "PMID conflict" in read_jsonl(output / "papers.jsonl")[0]["errors"][0]["error"]


def test_selection_cannot_change_within_same_snapshot(tmp_path, monkeypatch):
    official_fake(monkeypatch)
    cases = write_cases(tmp_path / "cases.jsonl", [case()])
    output = tmp_path / "out"
    literature.acquire_literature(cases, output)
    write_cases(cases, [case(case_id="changed")])
    with pytest.raises(ValueError, match="selection cannot be overwritten"):
        literature.acquire_literature(cases, output)


def test_empty_train_selection_and_invalid_limit_fail(tmp_path):
    cases = write_cases(tmp_path / "cases.jsonl", [case(split="validation")])
    with pytest.raises(ValueError, match="no train cases"):
        literature.acquire_literature(cases, tmp_path / "out")
    with pytest.raises(ValueError, match="limit"):
        literature.acquire_literature(cases, tmp_path / "out", limit=True)


def test_singlecopy_supplement_manifest_never_extracts_traversal_member(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../../external.txt", b"source bytes")
    refs = literature._supplement_manifest(buffer.getvalue(), {"file": str(tmp_path / "one.zip"), "sha256": "a" * 64})
    assert refs[0]["member"] == "../../external.txt"
    assert refs[0]["storage"] == "archive_member_reference_not_extracted"
    assert not list(tmp_path.iterdir())


def test_compound_number_mapping_is_source_linked_and_not_protein_binding(tmp_path, monkeypatch):
    source = tmp_path / "original.json"
    source.write_text(json.dumps([{"doi": "10.1234/example", "document_chembl_id": "CHEMBL100", "pubmed_id": 123}]))
    calls = []
    def request(url, *, max_bytes):
        calls.append(url)
        assert "compound_record.json" in url
        return json.dumps({"compound_records": [{"record_id": 15, "compound_key": "5", "compound_name": "paper name",
                  "document_chembl_id": "CHEMBL100", "molecule_chembl_id": "CHEMBL200", "src_id": 1}],
                  "page_meta": {"offset": 0, "total_count": 1, "next": None}}).encode(), {}
    monkeypatch.setattr(literature, "_request_bytes", request)
    output = tmp_path / "out"
    kwargs = {"document_ref": {"file": str(source), "pointer": "/0"}}
    summary = literature.acquire_document_compound_bindings("CHEMBL100", "10.1234/example", output, **kwargs)
    assert summary["complete_for_document"] and summary["record_count"] == 1
    row = read_jsonl(output / "compound_bindings.jsonl")[0]
    assert row["compound_key"] == "5" and row["molecule_chembl_id"] == "CHEMBL200"
    assert row["source"]["pointer"] == "/compound_records/0"
    assert row["document_source"]["file"] == str(source)
    assert not row["protein_binding_supported"] and not row["structure_and_tested_form_confirmed"]
    assert row["review_status"] == "needs_review" and not row["inference_eligible"]
    assert literature.acquire_document_compound_bindings("CHEMBL100", "10.1234/example", output, offline=True, **kwargs) == summary
    assert len(calls) == 1


def test_compound_number_mapping_requires_exact_document_and_reports_partial(tmp_path, monkeypatch):
    def request(url, *, max_bytes):
        if "/document/" in url:
            return json.dumps({"document_chembl_id": "CHEMBL100", "doi": "10.1234/example"}).encode(), {}
        return json.dumps({"compound_records": [{"record_id": 1, "document_chembl_id": "CHEMBL999",
            "molecule_chembl_id": "CHEMBL200"}], "page_meta": {"offset": 0, "total_count": 1, "next": None}}).encode(), {}
    monkeypatch.setattr(literature, "_request_bytes", request)
    with pytest.raises(ValueError, match="different source document"):
        literature.acquire_document_compound_bindings("CHEMBL100", "10.1234/example", tmp_path / "out")
    assert not (tmp_path / "out" / "compound_bindings.jsonl").exists()
