"""ncbi-taxon-fetcher — resolve organism name to NCBI Taxonomy ID via E-utilities.

Used by:
  - QA layer 4 (host_taxon_ncbi) at scripts/distill/qa.py
  - host_organism channel (taxonomy lineage for cross-species queries)

Cache: data/ncbi_taxonomy/<safe_name>.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_NCBI = PROJECT_ROOT / "data" / "ncbi_taxonomy"
USER_AGENT = "PRAXIS-Synth-ncbi-taxon-fetcher/0.1"

# Species → genus expansion for abbreviated names like "S. cerevisiae"
_SPECIES_TO_GENUS = {
    "cerevisiae": "Saccharomyces",
    "coli": "Escherichia",
    "glutamicum": "Corynebacterium",
    "subtilis": "Bacillus",
    "pastoris": "Pichia",
    "phaffii": "Komagataella",
    "coelicolor": "Streptomyces",
    "avermitilis": "Streptomyces",
    "thermophilus": "Geobacillus",
}


def _safe_key(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", str(s))[:80]


def _expand_abbrev(host: str) -> str:
    parts = host.split()
    if not parts:
        return host
    first = parts[0].lower().rstrip(".")
    if len(first) <= 2 and len(parts) >= 2:
        species = parts[1].lower()
        if species in _SPECIES_TO_GENUS:
            return _SPECIES_TO_GENUS[species] + " " + " ".join(parts[1:])
    return host


def fetch(host: str, cache_only: bool = False) -> dict:
    t0 = time.time()
    DATA_NCBI.mkdir(parents=True, exist_ok=True)
    cache_file = DATA_NCBI / f"{_safe_key(host)}.json"

    if cache_file.exists():
        try:
            d = json.loads(cache_file.read_text(encoding="utf-8"))
            if d.get("taxon_id"):
                d["from_cache"] = True
                d["tool_provenance"] = {
                    "simulated": False, "partial": True, "full": False,
                    "version": _versions(),
                    "wallclock_seconds": round(time.time() - t0, 4),
                }
                d["passed_qc"] = True
                return d
        except Exception:
            pass

    if cache_only:
        return {"passed_qc": False, "error": "not in cache and cache_only=True",
                "tool_provenance": {"simulated": True, "partial": False, "full": False}}

    try:
        import requests
    except ImportError:
        return {"passed_qc": False, "error": "requests not installed",
                "tool_provenance": {"simulated": True, "partial": False, "full": False}}

    q = re.sub(r"\([^)]*\)", "", host).strip()
    q = _expand_abbrev(q)
    parts = q.split()
    q_short = " ".join(parts[:2]) if len(parts) >= 2 else q

    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    params = {"db": "taxonomy", "term": q_short, "retmode": "json"}
    if os.environ.get("NCBI_EMAIL"):
        params["email"] = os.environ["NCBI_EMAIL"]
    if os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ["NCBI_API_KEY"]
    try:
        r = requests.get(f"{base}/esearch.fcgi", params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=15)
    except Exception as e:
        return {"passed_qc": False, "error": f"network error: {e}",
                "tool_provenance": {"simulated": True, "partial": False, "full": False}}

    if r.status_code != 200:
        return {"passed_qc": False, "error": f"NCBI esearch status {r.status_code}",
                "tool_provenance": {"simulated": True, "partial": False, "full": False}}
    try:
        idlist = r.json().get("esearchresult", {}).get("idlist", [])
    except Exception:
        return {"passed_qc": False, "error": "could not parse NCBI esearch response",
                "tool_provenance": {"simulated": True, "partial": False, "full": False}}
    if not idlist:
        return {"passed_qc": False, "error": f"no NCBI taxonomy hit for {q_short!r}",
                "tool_provenance": {"simulated": True, "partial": False, "full": False}}

    taxon_id = idlist[0]
    d = {"taxon_id": taxon_id, "scientific_name": q_short, "query": host}
    cache_file.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    d["from_cache"] = False
    d["tool_provenance"] = {
        "simulated": False, "partial": False, "full": True,
        "backend": "ncbi_eutils",
        "version": _versions(),
        "wallclock_seconds": round(time.time() - t0, 4),
    }
    d["passed_qc"] = True
    return d


def run(query: str, cache_only: bool = False) -> dict:
    return fetch(query, cache_only=cache_only)


def _versions() -> dict:
    return {"python": platform.python_version()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--cache-only", action="store_true")
    args = ap.parse_args()
    print(json.dumps(run(args.query, cache_only=args.cache_only), ensure_ascii=False, indent=2))
