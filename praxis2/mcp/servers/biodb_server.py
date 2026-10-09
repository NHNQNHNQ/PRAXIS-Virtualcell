"""Query PubMed, UniProt, PDB, ChEMBL, and PubChem through their public APIs."""

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
        es = _http_get_json(
            f"{_NCBI}/esearch.fcgi", _ncbi_params({"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"})
        )
        res = es.get("esearchresult", {})
        count = int(res.get("count", 0))
        idlist = res.get("idlist", [])
        if not idlist:
            return {"ok": True, "count": count, "articles": []}
        su = _http_get_json(
            f"{_NCBI}/esummary.fcgi", _ncbi_params({"db": "pubmed", "id": ",".join(idlist), "retmode": "json"})
        )
        result = su.get("result", {})
        articles = []
        for pmid in result.get("uids", []):
            a = result.get(pmid, {})
            doi = ""
            for aid in a.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = aid.get("value", "")
                    break
            articles.append(
                {
                    "pmid": pmid,
                    "title": a.get("title", ""),
                    "journal": a.get("fulljournalname", ""),
                    "year": (a.get("pubdate", "") or "")[:4],
                    "doi": doi,
                }
            )
        return {"ok": True, "count": count, "articles": articles}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- get_pubmed_abstract ----


def get_pubmed_abstract_impl(pmid: str) -> dict:
    try:
        xml = _http_get_text(
            f"{_NCBI}/efetch.fcgi", _ncbi_params({"db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "xml"})
        )
        root = ET.fromstring(xml)  # noqa: S314
        title = "".join("".join(t.itertext()) for t in root.iter("ArticleTitle"))
        parts = ["".join(t.itertext()) for t in root.iter("AbstractText")]
        abstract = "\n".join(p for p in parts if p)
        if not abstract:
            return {"ok": False, "error": "No abstract is available", "pmid": pmid}
        return {"ok": True, "pmid": pmid, "title": title, "abstract": abstract}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- get_uniprot ----


def get_uniprot_impl(accession: str) -> dict:
    try:
        d = _http_get_json(f"{_UNIPROT}/{accession}.json")
        name = d.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "")
        func = ""
        for c in d.get("comments", []):
            if c.get("commentType") == "FUNCTION":
                texts = c.get("texts", [])
                if texts:
                    func = texts[0].get("value", "")
                break
        seq = d.get("sequence", {})
        return {
            "ok": True,
            "accession": d.get("primaryAccession", accession),
            "name": name,
            "length": seq.get("length", 0),
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
            "ok": True,
            "pdb_id": pdb_id.upper(),
            "title": d.get("struct", {}).get("title", ""),
            "method": [e.get("method") for e in d.get("exptl", [])],
            "resolution": d.get("rcsb_entry_info", {}).get("resolution_combined"),
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- search_chembl ----


def search_chembl_impl(query: str, limit: int = 5) -> dict:
    try:
        d = _http_get_json(f"{_CHEMBL}/molecule/search", {"q": query, "limit": limit, "format": "json"})
        mols = []
        for m in d.get("molecules", [])[:limit]:
            struct = m.get("molecule_structures") or {}
            mols.append(
                {
                    "chembl_id": m.get("molecule_chembl_id", ""),
                    "name": m.get("pref_name") or "",
                    "smiles": struct.get("canonical_smiles", ""),
                    "max_phase": m.get("max_phase"),
                }
            )
        return {"ok": True, "molecules": mols}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


# ---- get_pubchem ----


def get_pubchem_impl(identifier: str, namespace: str = "cid") -> dict:
    try:
        props = "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName"
        d = _http_get_json(f"{_PUBCHEM}/{namespace}/{urllib.parse.quote(identifier)}/property/{props}/JSON")
        rows = d.get("PropertyTable", {}).get("Properties", [])
        if not rows:
            return {"ok": False, "error": "No matching compound"}
        p = rows[0]
        return {
            "ok": True,
            "cid": p.get("CID"),
            "formula": p.get("MolecularFormula", ""),
            "mw": p.get("MolecularWeight", ""),
            "smiles": p.get("CanonicalSMILES", ""),
            "iupac_name": p.get("IUPACName", ""),
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP  # noqa: PLC0415

    mcp = FastMCP("praxis-biodb")

    @mcp.tool()
    def search_pubmed(query: str, retmax: int = 5) -> dict:

        return search_pubmed_impl(query, retmax)

    @mcp.tool()
    def get_pubmed_abstract(pmid: str) -> dict:

        return get_pubmed_abstract_impl(pmid)

    @mcp.tool()
    def get_uniprot(accession: str) -> dict:

        return get_uniprot_impl(accession)

    @mcp.tool()
    def get_pdb(pdb_id: str) -> dict:

        return get_pdb_impl(pdb_id)

    @mcp.tool()
    def search_chembl(query: str, limit: int = 5) -> dict:

        return search_chembl_impl(query, limit)

    @mcp.tool()
    def get_pubchem(identifier: str, namespace: str = "cid") -> dict:

        return get_pubchem_impl(identifier, namespace)

    mcp.run("stdio")
