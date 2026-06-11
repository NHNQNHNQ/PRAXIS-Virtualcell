#!/usr/bin/env python3
"""Validate candidate cases against external sources.

Six checks per case (PRAXIS-Synth):
  1. schema                  — frontmatter parses; required fields present
  2. doi_crossref            — DOI resolvable on CrossRef
  3. target_compound_kegg    — target_compound resolvable in KEGG (or SMILES parseable)
  4. host_taxon_ncbi         — host_organism resolvable to an NCBI taxonomy ID
  5. enzyme_uniprot_ec       — if frontmatter lists enzymes, every one has UniProt + EC
  6. plasmid_part_registry   — if frontmatter cites parts, registry IDs resolvable
  7. mandatory_body          — '★ 排除' + '★ 失败' sections present, non-empty

Layer 5 + 6 are conditional (only fire when relevant frontmatter fields exist).

Usage:
  python scripts/distill/qa.py --case memory/cases/synth-001-fba-ecoli-iml1515.md
  python scripts/distill/qa.py --all                   # all active memory/cases/
  python scripts/distill/qa.py --all-proposed          # all _proposed/
  python scripts/distill/qa.py --strict                # exit non-zero on any FAIL
  python scripts/distill/qa.py --no-network            # skip CrossRef + KEGG + NCBI calls
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CASES_DIR = PROJECT_ROOT / "memory" / "cases"
PROPOSED_DIR = CASES_DIR / "_proposed"
DATA_KEGG = PROJECT_ROOT / "data" / "kegg"
DATA_NCBI = PROJECT_ROOT / "data" / "ncbi_taxonomy"
DATA_IGEM = PROJECT_ROOT / "data" / "igem"
DATA_UNIPROT = PROJECT_ROOT / "data" / "uniprot"
USER_AGENT = "PRAXIS-Synth-research/0.1.0"

logger = logging.getLogger("distill.qa")

REQUIRED_FRONTMATTER_PATHS = [
    ("case_id",),
    ("task",),
    ("status",),
    ("key_paper_doi",),
]

SOFT_REQUIRED_HOST_FIELDS = ("host_organism", "target_host", "system")

SOFT_REQUIRED_OBJECTIVE_FIELDS = (
    "target_compound", "target_construct", "target_protein", "target_data",
    "input_protein", "target_analyte", "circuit_type", "model",
)

# Synth task enum (from synthesis §VII)
SYNTH_TASK_ENUM = {
    # Frontmatter `task` field uses richer descriptors; map to canonical synth_task here
    "flux_balance_analysis": "fba",
    "heterologous_pathway_design": "pathway_design",
    "plasmid_construction": "plasmid_assembly",
    "plasmid_assembly": "plasmid_assembly",
    "codon_optimization": "codon_opt",
    "codon_opt": "codon_opt",
    "genetic_circuit_design": "circuit",
    "circuit": "circuit",
    "dna_constraint_optimization": "codon_opt",  # often co-applied with codon-opt
    "cell_free_protein_synthesis_design": "cell_free",
    "cell_free": "cell_free",
    "biosensor_circuit_design": "biosensor",
    "biosensor": "biosensor",
    "strain_engineering_for_production": "strain_engineering",
    "strain_engineering": "strain_engineering",
    "biosynthetic_gene_cluster_mining": "bgc_mining",
    "bgc_mining": "bgc_mining",
    "fba": "fba",
}


# ---------- helpers ----------

def _normalize_organism(s: str) -> str:
    """Lower, strip parens content, collapse whitespace."""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^a-z\s.]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _organism_compatible(a: str, b: str) -> tuple[bool, str]:
    """Fuzzy organism match with synth-domain synonyms (E. coli strains, yeast, etc.)."""
    SYNONYMS = [
        {"escherichia coli", "e. coli", "ecoli"},
        {"saccharomyces cerevisiae", "s. cerevisiae", "scerevisiae", "yeast"},
        {"corynebacterium glutamicum", "c. glutamicum", "cglutamicum"},
        {"streptomyces coelicolor", "streptomyces avermitilis", "streptomyces sp"},
        {"bacillus subtilis", "b. subtilis"},
        {"pichia pastoris", "p. pastoris", "komagataella phaffii"},
    ]
    na, nb = _normalize_organism(a), _normalize_organism(b)
    if not na or not nb:
        return False, "empty after normalization"
    if na == nb:
        return True, "exact match"
    for grp in SYNONYMS:
        if any(syn in na for syn in grp) and any(syn in nb for syn in grp):
            return True, f"synonym match ({sorted(grp)[0]})"
    ta, tb = na.split(), nb.split()
    if len(ta) >= 2 and len(tb) >= 2 and ta[0] == tb[0] and ta[1] == tb[1]:
        return True, "genus+species match"
    if na in nb or nb in na:
        return True, "substring match"
    return False, f"no match: {na!r} vs {nb!r}"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    import yaml
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end < 0:
        return {}, text
    fm_text = text[3:end]
    body = text[end + 3:]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        logger.warning(f"YAML parse error: {e}")
        return {}, body
    if not isinstance(fm, dict):
        return {}, body
    return fm, body


def _get(fm: dict, *keys, default=None):
    cur = fm
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


# ---------- 1. schema ----------

def check_schema(fm: dict, body: str) -> dict:
    missing = [".".join(p) for p in REQUIRED_FRONTMATTER_PATHS if _get(fm, *p) in (None, "", "null")]

    # Soft: synth_task in canonical enum
    task = (fm.get("task") or "").strip()
    if task and task not in SYNTH_TASK_ENUM:
        missing.append(f"task={task!r} not in canonical synth_task enum")

    # Soft: at least one host-like or objective-like field
    has_host = any(fm.get(f) for f in SOFT_REQUIRED_HOST_FIELDS)
    has_obj = any(fm.get(f) for f in SOFT_REQUIRED_OBJECTIVE_FIELDS)
    if not (has_host or has_obj):
        missing.append("must have ≥1 of host_organism/target_host/system OR target_compound/target_protein/...")

    # Soft: tools list non-empty
    tools = fm.get("tools") or []
    if not isinstance(tools, list) or not tools:
        missing.append("tools (non-empty list)")

    if missing:
        return {"name": "schema", "status": "fail", "message": f"missing: {missing}"}
    return {"name": "schema", "status": "pass", "message": "all required + soft fields present"}


# ---------- 2. doi_crossref (100% reuse) ----------

def check_doi_crossref(fm: dict) -> dict:
    doi = fm.get("key_paper_doi") or _get(fm, "provenance", "doi")
    if not doi or doi in {"null", "None"}:
        return {"name": "doi_crossref", "status": "warn", "message": "no DOI provided"}
    doi = str(doi).strip().strip('"').lstrip("https://doi.org/").lstrip("doi:")
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": USER_AGENT}
    if os.environ.get("CROSSREF_MAILTO"):
        headers["User-Agent"] += f" (mailto:{os.environ['CROSSREF_MAILTO']})"
    try:
        r = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as e:
        return {"name": "doi_crossref", "status": "warn", "message": f"network error: {e}"}
    if r.status_code == 404:
        return {"name": "doi_crossref", "status": "fail", "message": f"DOI not in CrossRef: {doi}"}
    if r.status_code != 200:
        return {"name": "doi_crossref", "status": "warn", "message": f"CrossRef status {r.status_code}"}
    try:
        msg = r.json()["message"]
    except Exception:
        return {"name": "doi_crossref", "status": "warn", "message": "could not parse CrossRef response"}
    title = (msg.get("title") or [""])[0]
    year = (msg.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0]
    journal = (msg.get("container-title") or [""])[0]
    return {
        "name": "doi_crossref",
        "status": "pass",
        "message": f"verified: {title[:60]}... ({year}, {journal[:30]})",
        "data": {"title": title, "year": year, "journal": journal},
    }


# ---------- 3. target_compound_kegg (NEW) ----------

def _kegg_compound_lookup(name_or_id: str) -> tuple[bool, str]:
    """Resolve a compound to a KEGG ID via local cache or REST find."""
    # local cache: data/kegg/<NAME_OR_ID>.json
    DATA_KEGG.mkdir(parents=True, exist_ok=True)
    cache_key = re.sub(r"[^A-Za-z0-9_]", "_", str(name_or_id))[:80]
    cache_file = DATA_KEGG / f"{cache_key}.json"
    if cache_file.exists():
        try:
            d = json.loads(cache_file.read_text(encoding="utf-8"))
            if d.get("kegg_id"):
                return True, f"cached: {d['kegg_id']} ({d.get('name', '?')})"
        except Exception:
            pass

    # KEGG REST: find compound by name
    base = "https://rest.kegg.jp"
    try:
        if re.match(r"^C\d{5}$", name_or_id):
            r = requests.get(f"{base}/get/cpd:{name_or_id}", headers={"User-Agent": USER_AGENT}, timeout=15)
        else:
            # Strip parenthetical context, take first comma-separated token
            q = name_or_id.split("(")[0].split(",")[0].strip()
            r = requests.get(f"{base}/find/compound/{q}", headers={"User-Agent": USER_AGENT}, timeout=15)
    except requests.RequestException as e:
        return False, f"network error: {e}"

    if r.status_code != 200:
        return False, f"KEGG status {r.status_code}"
    text = r.text.strip()
    if not text:
        return False, "no KEGG hit"
    # Parse first line: "cpd:C00031\tD-Glucose; ..."
    first = text.splitlines()[0]
    parts = first.split("\t")
    kegg_id = parts[0].split(":")[-1]
    name = parts[1] if len(parts) > 1 else ""
    cache_file.write_text(json.dumps({"kegg_id": kegg_id, "name": name, "query": name_or_id}, ensure_ascii=False), encoding="utf-8")
    return True, f"resolved {kegg_id} ({name[:50]})"


def check_target_compound_kegg(fm: dict, network: bool) -> dict:
    """Resolve `target_compound` (or `target_analyte`) against KEGG. Pass if KEGG ID
    resolves OR a SMILES string is parseable."""
    candidate = (
        fm.get("target_compound") or fm.get("target_analyte") or fm.get("target_protein") or fm.get("input_protein")
    )
    if not candidate:
        return {"name": "target_compound_kegg", "status": "skip", "message": "no compound/analyte field"}
    candidate = str(candidate)

    # If looks like a SMILES (no spaces, has typical SMILES chars), validate via RDKit
    if " " not in candidate and re.search(r"[=#@]", candidate):
        try:
            from rdkit import Chem
            mol = Chem.MolFromSmiles(candidate)
            if mol is not None:
                return {"name": "target_compound_kegg", "status": "pass", "message": f"SMILES parseable ({Chem.MolToSmiles(mol)[:40]}...)"}
        except Exception as e:
            logger.debug(f"rdkit parse failed: {e}")

    # If candidate is a protein (has 'human IL-2' style or 'GFP'), KEGG won't help — pass with warn
    if any(p in candidate.lower() for p in ("protein", "antibody", "gfp", "il-", "p450", "cyp", "cas9", "membrane")):
        return {"name": "target_compound_kegg", "status": "skip", "message": f"protein target {candidate!r} — KEGG compound lookup not applicable"}

    if not network:
        return {"name": "target_compound_kegg", "status": "skip", "message": "network disabled"}

    ok, msg = _kegg_compound_lookup(candidate)
    if ok:
        return {"name": "target_compound_kegg", "status": "pass", "message": msg}
    return {"name": "target_compound_kegg", "status": "warn", "message": f"could not resolve {candidate!r} in KEGG: {msg}"}


# ---------- 4. host_taxon_ncbi (NEW) ----------

_GENUS_ABBREV_EXPAND = {
    "e.": "Escherichia",
    "s.": None,  # ambiguous — could be Saccharomyces, Streptomyces, etc.; resolve by next token
    "c.": None,
    "b.": None,
    "p.": None,
    "k.": None,
    "h.": None,
    "t.": None,
}

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


def _expand_abbreviated_genus(host: str) -> str:
    """E.g. 'S. cerevisiae' -> 'Saccharomyces cerevisiae' using a known species->genus table."""
    parts = host.split()
    if not parts:
        return host
    first = parts[0].lower().rstrip(".")
    if len(first) <= 2 and len(parts) >= 2:
        species = parts[1].lower()
        if species in _SPECIES_TO_GENUS:
            return _SPECIES_TO_GENUS[species] + " " + " ".join(parts[1:])
    return host


def _ncbi_taxon_lookup(host: str) -> tuple[bool, str]:
    """Resolve organism name to an NCBI Taxonomy ID via E-utilities."""
    DATA_NCBI.mkdir(parents=True, exist_ok=True)
    cache_key = re.sub(r"[^A-Za-z0-9_]", "_", host)[:80]
    cache_file = DATA_NCBI / f"{cache_key}.json"
    if cache_file.exists():
        try:
            d = json.loads(cache_file.read_text(encoding="utf-8"))
            if d.get("taxon_id"):
                return True, f"cached: {d['taxon_id']} ({d.get('scientific_name', '?')})"
        except Exception:
            pass

    # Strip "(strain ...)" tails for easier search
    q = re.sub(r"\([^)]*\)", "", host).strip()
    # Expand abbreviated genus (S. cerevisiae -> Saccharomyces cerevisiae)
    q = _expand_abbreviated_genus(q)
    # Strip strain qualifiers like "K-12 MG1655" → use just genus + species
    parts = q.split()
    if len(parts) >= 2:
        q_short = " ".join(parts[:2])
    else:
        q_short = q

    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    params = {"db": "taxonomy", "term": q_short, "retmode": "json"}
    if os.environ.get("NCBI_EMAIL"):
        params["email"] = os.environ["NCBI_EMAIL"]
    if os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ["NCBI_API_KEY"]
    try:
        r = requests.get(f"{base}/esearch.fcgi", params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
    except requests.RequestException as e:
        return False, f"network error: {e}"
    if r.status_code != 200:
        return False, f"NCBI esearch status {r.status_code}"
    try:
        idlist = r.json().get("esearchresult", {}).get("idlist", [])
    except Exception:
        return False, "could not parse NCBI esearch response"
    if not idlist:
        return False, f"no NCBI taxonomy hit for {q_short!r}"
    taxon_id = idlist[0]
    cache_file.write_text(
        json.dumps({"taxon_id": taxon_id, "scientific_name": q_short, "query": host}, ensure_ascii=False),
        encoding="utf-8",
    )
    return True, f"resolved {taxon_id} ({q_short})"


def check_host_taxon_ncbi(fm: dict, network: bool) -> dict:
    host = fm.get("host_organism") or fm.get("target_host")
    if not host:
        return {"name": "host_taxon_ncbi", "status": "skip", "message": "no host field"}
    host = str(host)
    if host.lower() in ("cell_free", "cell free", "in vitro", "tx-tl", "pure"):
        return {"name": "host_taxon_ncbi", "status": "skip", "message": f"cell-free system ({host}) — no taxon lookup"}
    if not network:
        return {"name": "host_taxon_ncbi", "status": "skip", "message": "network disabled"}
    ok, msg = _ncbi_taxon_lookup(host)
    return {"name": "host_taxon_ncbi", "status": "pass" if ok else "warn", "message": msg}


# ---------- 5. enzyme_uniprot_ec (CONDITIONAL REUSE) ----------

def check_enzyme_uniprot_ec(fm: dict) -> dict:
    """Only fires when frontmatter has an `enzymes` list with uniprot+ec entries."""
    enzymes = fm.get("enzymes")
    if not enzymes or not isinstance(enzymes, list):
        return {"name": "enzyme_uniprot_ec", "status": "skip", "message": "no enzymes list"}

    issues = []
    for e in enzymes:
        if not isinstance(e, dict):
            issues.append(f"enzyme entry is not a dict: {e!r}")
            continue
        acc = e.get("uniprot")
        ec = e.get("ec")
        name = e.get("name", "?")
        if not acc:
            issues.append(f"{name}: no uniprot accession")
        if not ec:
            issues.append(f"{name}: no EC")
    if issues:
        return {"name": "enzyme_uniprot_ec", "status": "warn", "message": "; ".join(issues)}
    return {"name": "enzyme_uniprot_ec", "status": "pass", "message": f"{len(enzymes)} enzyme(s) all have uniprot+EC"}


# ---------- 6. plasmid_part_registry (NEW) ----------

def _load_igem_parts() -> set[str]:
    """Load iGEM/Addgene part-name set from local snapshot. Returns lowercased names."""
    DATA_IGEM.mkdir(parents=True, exist_ok=True)
    snap = DATA_IGEM / "parts.json"
    if not snap.exists():
        # Bootstrap minimal known parts (BioBricks + MoClo)
        bootstrap = {
            "parts": [
                "BBa_B0034", "BBa_B0030", "BBa_B0010", "BBa_B0012",  # RBS, terminators
                "BBa_R0010", "BBa_R0040", "BBa_R0011",                # promoters lacI, tetR, lacI-derived
                "BBa_E0040", "BBa_E1010",                              # GFP, mRFP
                "BBa_J23100", "BBa_J23119",                            # Anderson
                "pTet", "pBAD", "pLac", "pTrc", "pT7",
                "RBS_B0034", "RBS_strong", "RBS_medium", "RBS_weak",
                "Term_T1", "Term_T7",
                "MoClo_AATG", "MoClo_GCTT",                            # canonical MoClo overhangs
                "pSB1A3", "pSB1C3", "pSB1K3", "pSB3K3",                # iGEM backbones
            ],
            "source": "bootstrap_2026-04-29",
        }
        snap.write_text(json.dumps(bootstrap, indent=2), encoding="utf-8")
    try:
        d = json.loads(snap.read_text(encoding="utf-8"))
        return {p.lower() for p in d.get("parts", [])}
    except Exception:
        return set()


def check_plasmid_part_registry(fm: dict) -> dict:
    parts = fm.get("parts") or fm.get("biobricks") or fm.get("registry_parts")
    if not parts:
        return {"name": "plasmid_part_registry", "status": "skip", "message": "no parts list"}
    if not isinstance(parts, list):
        return {"name": "plasmid_part_registry", "status": "warn", "message": "parts is not a list"}
    known = _load_igem_parts()
    missing = [p for p in parts if str(p).lower() not in known]
    if not missing:
        return {"name": "plasmid_part_registry", "status": "pass", "message": f"{len(parts)} part(s) all in registry"}
    if fm.get("parts_validated") is True:
        return {"name": "plasmid_part_registry", "status": "fail", "message": f"missing from registry: {missing}"}
    return {"name": "plasmid_part_registry", "status": "warn", "message": f"not in local registry (may be custom): {missing}"}


# ---------- 7. mandatory_body ----------

def check_mandatory_body(body: str) -> dict:
    """Look for ## ★ 排除... and ## ★ 失败... sections, each non-empty after the heading."""
    excl_match = re.search(r"##\s*★\s*排除[^\n]*\n+([\s\S]*?)(?=\n##|\Z)", body)
    fail_match = re.search(r"##\s*★\s*失败[^\n]*\n+([\s\S]*?)(?=\n##|\Z)", body)
    issues = []
    if not excl_match:
        issues.append("missing '## ★ 排除' section")
    elif not excl_match.group(1).strip() or excl_match.group(1).strip() in {"-", "无", "未报道"}:
        issues.append("'## ★ 排除' section is empty")
    if not fail_match:
        issues.append("missing '## ★ 失败' section")
    elif not fail_match.group(1).strip() or fail_match.group(1).strip() in {"-", "无", "未报道"}:
        issues.append("'## ★ 失败' section is empty")
    if issues:
        return {"name": "mandatory_body", "status": "fail", "message": "; ".join(issues)}
    return {"name": "mandatory_body", "status": "pass", "message": "both ★ sections present and non-empty"}


# ---------- runner ----------

def run_qa(case_path: Path, network: bool = True) -> dict:
    text = case_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    checks = [check_schema(fm, body)]
    if network:
        checks.append(check_doi_crossref(fm))
    else:
        checks.append({"name": "doi_crossref", "status": "skip", "message": "network disabled"})
    checks.append(check_target_compound_kegg(fm, network))
    checks.append(check_host_taxon_ncbi(fm, network))
    checks.append(check_enzyme_uniprot_ec(fm))
    checks.append(check_plasmid_part_registry(fm))
    checks.append(check_mandatory_body(body))

    statuses = [c["status"] for c in checks]
    if "fail" in statuses:
        overall = "fail"
    elif "warn" in statuses:
        overall = "pass_with_warnings"
    else:
        overall = "pass"

    return {
        "case_id": fm.get("case_id") or case_path.stem,
        "case_path": str(case_path.relative_to(PROJECT_ROOT)),
        "overall": overall,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PRAXIS-Synth cases")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--case", type=Path, help="single case path (relative or absolute)")
    src.add_argument("--all", action="store_true", help="check all active memory/cases/")
    src.add_argument("--all-proposed", action="store_true", help="check all _proposed/")
    parser.add_argument("--no-network", action="store_true", help="skip CrossRef + KEGG + NCBI")
    parser.add_argument("--report-dir", type=Path, help="save per-case JSON reports")
    parser.add_argument("--strict", action="store_true", help="exit non-zero if any FAIL")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    case_paths: list[Path] = []
    if args.case:
        p = args.case if args.case.is_absolute() else (PROJECT_ROOT / args.case)
        case_paths = [p]
    elif args.all:
        case_paths = [p for p in CASES_DIR.glob("synth-*.md") if not p.name.startswith(("_", "."))]
    elif args.all_proposed:
        if PROPOSED_DIR.exists():
            case_paths = [p for p in PROPOSED_DIR.glob("*.md") if not p.name.startswith(".")]

    if not case_paths:
        print("No cases to check.")
        return 0

    if args.report_dir:
        args.report_dir.mkdir(parents=True, exist_ok=True)

    any_fail = False
    n_pass = n_warn = n_fail = 0
    for cp in sorted(case_paths):
        rep = run_qa(cp, network=not args.no_network)
        if rep["overall"] == "fail":
            any_fail = True
            n_fail += 1
        elif rep["overall"] == "pass_with_warnings":
            n_warn += 1
        else:
            n_pass += 1
        print(f"\n=== {rep['case_id']} ({rep['overall'].upper()}) ===")
        for c in rep["checks"]:
            mark = {"pass": "OK", "warn": "WARN", "fail": "FAIL", "skip": "..."}[c["status"]]
            print(f"  [{mark:4}] {c['name']:25} {c['message']}")
        if args.report_dir:
            (args.report_dir / f"{rep['case_id']}.json").write_text(
                json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    print(f"\n--- Summary: {n_pass} pass, {n_warn} pass-with-warnings, {n_fail} fail ---")
    return 1 if (args.strict and any_fail) else 0


if __name__ == "__main__":
    sys.exit(main())
