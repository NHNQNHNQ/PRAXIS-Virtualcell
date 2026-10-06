"""MCP stdio server — 生物数据库实时查询(PubMed/UniProt/PDB/ChEMBL/PubChem)。

让 agent 实时核实真实文献/序列/结构/化合物,补强反幻觉(不编 DOI、能查真实
UniProt 序列/PDB 结构/ChEMBL 化合物元数据)。纯 urllib 标准库,不依赖 npx,规避 .53
node 约束。

启动(praxis2 env python,有 mcp lib):
  python -m praxis2.mcp.servers.biodb_server

6 个 tool:
  search_pubmed       — 文献检索(esearch+esummary,返 PMID/标题/DOI/期刊)
  get_pubmed_abstract — 取摘要全文(efetch)
  get_uniprot         — 蛋白(序列/功能/物种)
  get_pdb             — 结构(标题/方法/分辨率)
  search_chembl       — 化合物检索(ChEMBL ID/SMILES/临床阶段)
  get_pubchem         — 化合物属性(分子式/MW/SMILES/IUPAC)

纯逻辑 _impl 函数不依赖 mcp,可单测(mock _http_get_*)。
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_TIMEOUT_S = 20.0
_TOOL = "praxis-biodb"
_EMAIL = os.environ.get("PRAXIS_NCBI_EMAIL", "")

_NCBI = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_UNIPROT = "https://rest.uniprot.org/uniprotkb"
_RCSB = "https://data.rcsb.org/rest/v1/core/entry"
_CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"
_PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"


# ---- HTTP 辅助(urllib,零依赖) ----

def _http_get_text(url: str, params: dict | None = None) -> str:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": _TOOL})
    with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def _http_get_json(url: str, params: dict | None = None) -> dict:
    return json.loads(_http_get_text(url, params))


def _ncbi_params(extra: dict) -> dict:
    p = {"tool": _TOOL}
    if _EMAIL:
        p["email"] = _EMAIL
    p.update(extra)
    return p


# ---- search_pubmed ----

def search_pubmed_impl(query: str, retmax: int = 5) -> dict:
    try:
        es = _http_get_json(f"{_NCBI}/esearch.fcgi", _ncbi_params(
            {"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"}))
        res = es.get("esearchresult", {})
        count = int(res.get("count", 0))
        idlist = res.get("idlist", [])
        if not idlist:
            return {"ok": True, "count": count, "articles": []}
        su = _http_get_json(f"{_NCBI}/esummary.fcgi", _ncbi_params(
            {"db": "pubmed", "id": ",".join(idlist), "retmode": "json"}))
        result = su.get("result", {})
        articles = []
        for pmid in result.get("uids", []):
            a = result.get(pmid, {})
            doi = ""
            for aid in a.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = aid.get("value", "")
                    break
            articles.append({
                "pmid": pmid,
                "title": a.get("title", ""),
                "journal": a.get("fulljournalname", ""),
                "year": (a.get("pubdate", "") or "")[:4],
                "doi": doi,
            })
        return {"ok": True, "count": count, "articles": articles}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- get_pubmed_abstract ----

def get_pubmed_abstract_impl(pmid: str) -> dict:
    try:
        xml = _http_get_text(f"{_NCBI}/efetch.fcgi", _ncbi_params(
            {"db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "xml"}))
        root = ET.fromstring(xml)  # noqa: S314 — NCBI 可信源
        title = "".join("".join(t.itertext()) for t in root.iter("ArticleTitle"))
        parts = ["".join(t.itertext()) for t in root.iter("AbstractText")]
        abstract = "\n".join(p for p in parts if p)
        if not abstract:
            return {"ok": False, "error": "无摘要(可能是综述/无 abstract)", "pmid": pmid}
        return {"ok": True, "pmid": pmid, "title": title, "abstract": abstract}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- get_uniprot ----

def get_uniprot_impl(accession: str) -> dict:
    try:
        d = _http_get_json(f"{_UNIPROT}/{accession}.json")
        name = (d.get("proteinDescription", {}).get("recommendedName", {})
                .get("fullName", {}).get("value", ""))
        func = ""
        for c in d.get("comments", []):
            if c.get("commentType") == "FUNCTION":
                texts = c.get("texts", [])
                if texts:
                    func = texts[0].get("value", "")
                break
        seq = d.get("sequence", {})
        return {
            "ok": True, "accession": d.get("primaryAccession", accession),
            "name": name, "length": seq.get("length", 0),
            "sequence": seq.get("value", ""),
            "organism": d.get("organism", {}).get("scientificName", ""),
            "function": func,
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- get_pdb ----

def get_pdb_impl(pdb_id: str) -> dict:
    try:
        d = _http_get_json(f"{_RCSB}/{pdb_id.upper()}")
        return {
            "ok": True, "pdb_id": pdb_id.upper(),
            "title": d.get("struct", {}).get("title", ""),
            "method": [e.get("method") for e in d.get("exptl", [])],
            "resolution": d.get("rcsb_entry_info", {}).get("resolution_combined"),
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- search_chembl ----

def search_chembl_impl(query: str, limit: int = 5) -> dict:
    try:
        d = _http_get_json(f"{_CHEMBL}/molecule/search",
                           {"q": query, "limit": limit, "format": "json"})
        mols = []
        for m in d.get("molecules", [])[:limit]:
            struct = m.get("molecule_structures") or {}
            mols.append({
                "chembl_id": m.get("molecule_chembl_id", ""),
                "name": m.get("pref_name") or "",
                "smiles": struct.get("canonical_smiles", ""),
                "max_phase": m.get("max_phase"),
            })
        return {"ok": True, "molecules": mols}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- get_pubchem ----

def get_pubchem_impl(identifier: str, namespace: str = "cid") -> dict:
    try:
        props = "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName"
        d = _http_get_json(
            f"{_PUBCHEM}/{namespace}/{urllib.parse.quote(identifier)}/property/{props}/JSON")
        rows = d.get("PropertyTable", {}).get("Properties", [])
        if not rows:
            return {"ok": False, "error": "无匹配化合物"}
        p = rows[0]
        return {
            "ok": True, "cid": p.get("CID"),
            "formula": p.get("MolecularFormula", ""),
            "mw": p.get("MolecularWeight", ""),
            "smiles": p.get("CanonicalSMILES", ""),
            "iupac_name": p.get("IUPACName", ""),
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- MCP 绑定(仅 __main__) ----

if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP  # noqa: PLC0415

    mcp = FastMCP("praxis-biodb")

    @mcp.tool()
    def search_pubmed(query: str, retmax: int = 5) -> dict:
        """【核实文献首选】检索 PubMed 权威文献库,返结构化 PMID/标题/期刊/真实DOI。
        引用文献、核实 DOI 时优先用此(权威 API,结构化准确),不要用 WebFetch 抓网页,
        更不要凭记忆编 DOI。"""
        return search_pubmed_impl(query, retmax)

    @mcp.tool()
    def get_pubmed_abstract(pmid: str) -> dict:
        """取 PubMed 文献摘要全文(efetch,权威来源)。读某篇文献内容用此而非网页抓取。"""
        return get_pubmed_abstract_impl(pmid)

    @mcp.tool()
    def get_uniprot(accession: str) -> dict:
        """【核实蛋白首选】查 UniProt 权威蛋白库,返真实序列/功能/物种。
        需要蛋白真实序列、功能注释、物种时优先用此(结构化 API),不要用 WebFetch 抓网页。"""
        return get_uniprot_impl(accession)

    @mcp.tool()
    def get_pdb(pdb_id: str) -> dict:
        """【核实结构首选】查 RCSB PDB 权威结构库,返标题/实验方法/分辨率。
        需要 PDB 结构元数据时优先用此(结构化 API),不要用 WebFetch 抓网页。"""
        return get_pdb_impl(pdb_id)

    @mcp.tool()
    def search_chembl(query: str, limit: int = 5) -> dict:
        """【核实化合物首选】检索 ChEMBL 权威生物活性库,返 ChEMBL ID/SMILES/临床阶段。
        需要药物/化合物活性、SMILES、临床阶段时优先用此,不要用 WebFetch 抓网页。"""
        return search_chembl_impl(query, limit)

    @mcp.tool()
    def get_pubchem(identifier: str, namespace: str = "cid") -> dict:
        """【核实化合物属性首选】查 PubChem 权威化学库,返分子式/MW/SMILES/IUPAC。
        namespace=cid|name|smiles。需要化合物属性时优先用此,不要用 WebFetch 抓网页。"""
        return get_pubchem_impl(identifier, namespace)

    mcp.run("stdio")
