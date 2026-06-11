"""praxis2.mcp.servers.biodb_server 单元测试。

测 6 个 _impl 工具的解析逻辑(mock _http_get_json,不真调 API)。
真实 API 往返见 e2e。
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from praxis2.mcp.servers import biodb_server as bd


# ---- search_pubmed(esearch + esummary 两步) ----

def test_search_pubmed_parses_articles():
    esearch = {"esearchresult": {"count": "39330", "idlist": ["42268489", "42268478"]}}
    esummary = {"result": {
        "uids": ["42268489", "42268478"],
        "42268489": {"title": "CRISPR review", "fulljournalname": "Nature",
                     "articleids": [{"idtype": "doi", "value": "10.1/abc"}]},
        "42268478": {"title": "Cas9 study", "fulljournalname": "Cell",
                     "articleids": [{"idtype": "doi", "value": "10.2/def"}]},
    }}
    with patch.object(bd, "_http_get_json", side_effect=[esearch, esummary]):
        r = bd.search_pubmed_impl("CRISPR", retmax=2)
    assert r["ok"] is True
    assert r["count"] == 39330
    assert len(r["articles"]) == 2
    assert r["articles"][0]["pmid"] == "42268489"
    assert r["articles"][0]["doi"] == "10.1/abc"
    assert r["articles"][0]["title"] == "CRISPR review"


def test_search_pubmed_empty():
    esearch = {"esearchresult": {"count": "0", "idlist": []}}
    with patch.object(bd, "_http_get_json", side_effect=[esearch]):
        r = bd.search_pubmed_impl("zzznonexistent", retmax=5)
    assert r["ok"] is True
    assert r["count"] == 0
    assert r["articles"] == []


# ---- get_pubmed_abstract(efetch) ----

def test_get_pubmed_abstract():
    xml = ("<PubmedArticleSet><PubmedArticle><MedlineCitation>"
           "<Article><ArticleTitle>T</ArticleTitle>"
           "<Abstract><AbstractText>This is the abstract body.</AbstractText></Abstract>"
           "</Article></MedlineCitation></PubmedArticle></PubmedArticleSet>")
    with patch.object(bd, "_http_get_text", return_value=xml):
        r = bd.get_pubmed_abstract_impl("42268489")
    assert r["ok"] is True
    assert "abstract body" in r["abstract"]


# ---- get_uniprot ----

def test_get_uniprot_parses():
    resp = {
        "primaryAccession": "P00698",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "Lysozyme C"}}},
        "sequence": {"value": "KVFGRCEL", "length": 147},
        "organism": {"scientificName": "Gallus gallus"},
        "comments": [{"commentType": "FUNCTION", "texts": [{"value": "Hydrolyzes peptidoglycan."}]}],
    }
    with patch.object(bd, "_http_get_json", return_value=resp):
        r = bd.get_uniprot_impl("P00698")
    assert r["ok"] is True
    assert r["accession"] == "P00698"
    assert r["name"] == "Lysozyme C"
    assert r["length"] == 147
    assert r["sequence"] == "KVFGRCEL"
    assert r["organism"] == "Gallus gallus"
    assert "peptidoglycan" in r["function"]


# ---- get_pdb ----

def test_get_pdb_parses():
    resp = {
        "struct": {"title": "HEN EGG WHITE LYSOZYME"},
        "exptl": [{"method": "X-RAY DIFFRACTION"}],
        "rcsb_entry_info": {"resolution_combined": [1.5]},
    }
    with patch.object(bd, "_http_get_json", return_value=resp):
        r = bd.get_pdb_impl("1AKI")
    assert r["ok"] is True
    assert r["pdb_id"] == "1AKI"
    assert "LYSOZYME" in r["title"]
    assert r["method"] == ["X-RAY DIFFRACTION"]
    assert r["resolution"] == [1.5]


# ---- search_chembl ----

def test_search_chembl_parses():
    resp = {"molecules": [{
        "molecule_chembl_id": "CHEMBL25",
        "pref_name": "ASPIRIN",
        "molecule_structures": {"canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O"},
        "max_phase": 4,
    }]}
    with patch.object(bd, "_http_get_json", return_value=resp):
        r = bd.search_chembl_impl("aspirin", limit=1)
    assert r["ok"] is True
    assert r["molecules"][0]["chembl_id"] == "CHEMBL25"
    assert r["molecules"][0]["smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert r["molecules"][0]["max_phase"] == 4


# ---- get_pubchem ----

def test_get_pubchem_parses():
    resp = {"PropertyTable": {"Properties": [{
        "CID": 2244, "MolecularFormula": "C9H8O4", "MolecularWeight": "180.16",
        "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O", "IUPACName": "2-acetyloxybenzoic acid",
    }]}}
    with patch.object(bd, "_http_get_json", return_value=resp):
        r = bd.get_pubchem_impl("2244", namespace="cid")
    assert r["ok"] is True
    assert r["cid"] == 2244
    assert r["formula"] == "C9H8O4"
    assert r["smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"


# ---- 错误处理 ----

def test_http_error_returns_ok_false():
    with patch.object(bd, "_http_get_json", side_effect=RuntimeError("503 timeout")):
        r = bd.get_uniprot_impl("BADACC")
    assert r["ok"] is False
    assert "error" in r
