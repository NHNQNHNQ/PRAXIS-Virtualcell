"""kegg-fetcher — resolve a compound name or KEGG ID via KEGG REST.

Used by:
  - QA layer 3 (target_compound_kegg) at scripts/distill/qa.py
  - retrieval target_compound channel (when SMILES needed)
  - heterologous_pathway_design for compound validation

Cache: data/kegg/<safe_name>.json
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_KEGG = PROJECT_ROOT / "data" / "kegg"
USER_AGENT = "PRAXIS-Synth-kegg-fetcher/0.1"


def _safe_key(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", str(s))[:80]


def fetch(name_or_id: str, cache_only: bool = False) -> dict:
    """Resolve a compound name or KEGG ID to (kegg_id, name, formula?, smiles?).

    First checks the local cache. If not cached and cache_only is False, calls
    KEGG REST. Returns a dict with `kegg_id`, `name`, `query`, `tool_provenance`.
    """
    t0 = time.time()
    DATA_KEGG.mkdir(parents=True, exist_ok=True)
    cache_file = DATA_KEGG / f"{_safe_key(name_or_id)}.json"

    if cache_file.exists():
        try:
            d = json.loads(cache_file.read_text(encoding="utf-8"))
            if d.get("kegg_id"):
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

    base = "https://rest.kegg.jp"
    try:
        if re.match(r"^C\d{5}$", name_or_id):
            url = f"{base}/get/cpd:{name_or_id}"
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
            if r.status_code != 200 or not r.text.strip():
                return {"passed_qc": False, "error": f"KEGG status {r.status_code}",
                        "tool_provenance": {"simulated": True, "partial": False, "full": False}}
            # Parse the FLAT-file response for NAME and FORMULA
            text = r.text
            name_line = re.search(r"^NAME\s+(.+?)(?:;|\n)", text, re.M)
            formula_line = re.search(r"^FORMULA\s+(\S+)", text, re.M)
            d = {
                "kegg_id": name_or_id,
                "name": (name_line.group(1).strip() if name_line else ""),
                "formula": (formula_line.group(1).strip() if formula_line else ""),
                "query": name_or_id,
            }
        else:
            q = name_or_id.split("(")[0].split(",")[0].strip()
            url = f"{base}/find/compound/{q}"
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
            if r.status_code != 200 or not r.text.strip():
                return {"passed_qc": False, "error": f"KEGG no hit",
                        "tool_provenance": {"simulated": True, "partial": False, "full": False}}
            first = r.text.strip().splitlines()[0]
            parts = first.split("\t")
            d = {
                "kegg_id": parts[0].split(":")[-1],
                "name": parts[1] if len(parts) > 1 else "",
                "query": name_or_id,
            }
    except Exception as e:
        return {"passed_qc": False, "error": f"network error: {e}",
                "tool_provenance": {"simulated": True, "partial": False, "full": False}}

    cache_file.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    d["from_cache"] = False
    d["tool_provenance"] = {
        "simulated": False, "partial": False, "full": True,
        "backend": "kegg_rest",
        "version": _versions(),
        "wallclock_seconds": round(time.time() - t0, 4),
    }
    d["passed_qc"] = True
    return d


def run(query: str, cache_only: bool = False) -> dict:
    """Skill entry-point — alias of fetch()."""
    return fetch(query, cache_only=cache_only)


def _versions() -> dict:
    return {"python": platform.python_version()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--cache-only", action="store_true")
    args = ap.parse_args()
    print(json.dumps(run(args.query, cache_only=args.cache_only), ensure_ascii=False, indent=2))
