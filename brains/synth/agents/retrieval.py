"""Multi-channel retrieval with RRF fusion and (synth_task, host_organism) pool routing.

8 channels:
  1. synth_task        (exact-tag, drives pool routing)
  2. host_organism     (exact-tag with synonyms)
  3. target_compound   (RDKit Morgan FP Tanimoto when SMILES given)
  4. pathway_class     (exact-tag)
  5. assembly_strategy (exact-tag)
  6. scale             (exact-tag)
  7. method_choice     (exact-tag)
  8. text              (BM25 over case markdown)

Pool routing:
  same_task_same_host (5 picks) > same_task (2) > same_host (1) > cross (1)

Cold-start gating:
  n < skip_retrieval_below:         return all cases (mode="cold_start")
  n < same_task_only_below:         only same_task pool (mode="same_task_only")
  n >= full_routing_at:             full pool routing (mode="full")
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.retrieval import task as task_mod
from scripts.retrieval import host as host_mod
from scripts.retrieval import compound as compound_mod
from scripts.retrieval import exact_tag as exact_tag_mod
from scripts.retrieval.text import CaseTextIndex
from scripts.retrieval.fuse import rrf

INDEX_PATH = PROJECT_ROOT / "memory" / "index.json"
CONFIG_PATH = PROJECT_ROOT / "config" / "retrieval.yaml"
CASES_DIR = PROJECT_ROOT / "memory" / "cases"
KEGG_DIR = PROJECT_ROOT / "data" / "kegg"

_text_idx_cache: CaseTextIndex | None = None


def _get_text_index() -> CaseTextIndex:
    global _text_idx_cache
    if _text_idx_cache is None:
        _text_idx_cache = CaseTextIndex(CASES_DIR)
    return _text_idx_cache


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def _rank_pool_cases(
    pool: list[dict],
    query: dict,
    weights: dict[str, float],
    text_idx: CaseTextIndex,
) -> list[tuple[str, float]]:
    """Rank cases within one pool by RRF over up to 8 channels."""
    if not pool:
        return []

    pool_ids_set = {c["case_id"] for c in pool}
    rankings: dict[str, list[str]] = {}

    # 1. synth_task (within-pool: same_task is uniform; useful when pool is mixed)
    qt = query.get("synth_task") or query.get("task") or ""
    if qt:
        rankings["synth_task"] = task_mod.rank_by_task(qt, pool)

    # 2. host_organism
    qh = query.get("host_organism") or query.get("host") or ""
    if qh:
        rankings["host_organism"] = host_mod.rank_by_host(qh, pool, INDEX_PATH)

    # 3. target_compound (only when query has SMILES)
    qsmiles = query.get("target_compound_smiles") or query.get("query_smiles")
    if qsmiles:
        ranked = compound_mod.rank_by_compound(qsmiles, pool, KEGG_DIR)
        if ranked:
            rankings["target_compound"] = [cid for cid in ranked if cid in pool_ids_set]

    # 4-7. exact-tag categorical channels
    for field, channel_name in [
        ("pathway_class", "pathway_class"),
        ("assembly_strategy", "assembly_strategy"),
        ("scale", "scale"),
        ("method_choice", "method_choice"),
    ]:
        qv = query.get(field, "")
        if qv:
            rankings[channel_name] = exact_tag_mod.rank_by_field(qv, pool, field)

    # 8. text (BM25)
    qtext = query.get("free_text") or " ".join(
        str(v) for v in [
            query.get("target_compound"),
            query.get("synth_task"),
            query.get("host_organism"),
            query.get("pathway_class"),
        ]
        if v
    )
    if qtext.strip():
        text_results = text_idx.query(qtext, top_k=50)
        rankings["text"] = [cid for cid, _ in text_results if cid in pool_ids_set]

    return rrf(rankings, weights, k=60)


def _score_rule(rule_meta: dict, query: dict) -> float:
    """Score a rule against the query — synth-domain `applies_to` keys."""
    score = 0.0
    applies = rule_meta.get("applies_to", {})
    qtask = task_mod.canonicalize(query.get("synth_task") or query.get("task") or "")
    qhost = (query.get("host_organism") or "").lower()
    qscale = (query.get("scale") or "").lower()

    ap_tasks = applies.get("synth_tasks", []) or []
    if isinstance(ap_tasks, str):
        ap_tasks = [ap_tasks]
    if qtask and (qtask in ap_tasks or "ALL" in ap_tasks or "all" in ap_tasks):
        score += 2.0

    ap_hosts = applies.get("host_organisms", []) or []
    if isinstance(ap_hosts, str):
        ap_hosts = [ap_hosts]
    if qhost and any(h.lower() in qhost or qhost in h.lower() for h in ap_hosts):
        score += 1.0
    if "ALL" in ap_hosts or "all" in ap_hosts:
        score += 0.3

    ap_scales = applies.get("scale", []) or []
    if isinstance(ap_scales, str):
        ap_scales = [ap_scales]
    if qscale and (qscale in [s.lower() for s in ap_scales] or "ALL" in ap_scales):
        score += 0.5

    return score


def retrieve(query: dict, stage: str = "scoping", top_k: int = 5) -> dict[str, Any]:
    """Multi-channel retrieval.

    Args:
        query: dict with optional fields:
            synth_task              one of: fba | pathway_design | plasmid_assembly | codon_opt |
                                            circuit | cell_free | biosensor | strain_engineering | bgc_mining
            host_organism           e.g. 'E. coli'
            target_compound         free-text or KEGG ID
            target_compound_smiles  SMILES (drives Tanimoto channel)
            pathway_class           e.g. 'terpenoid'
            assembly_strategy       e.g. 'golden_gate'
            scale                   e.g. 'fermenter'
            method_choice           e.g. 'optknock'
            free_text               BM25 fallback
        stage: 'scoping' | 'design' | 'execution' | 'reporting' (affects channel weights)
        top_k: how many cases to return

    Returns:
        {retrieval_mode, n_cases_in_library, cases, rules, channels_used, stage_used, ...}
    """
    if not INDEX_PATH.exists():
        return {"cases": [], "rules": [], "warning": "memory/index.json not found"}

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    cases = index.get("cases", [])
    rules = index.get("rules", [])
    n_cases = len(cases)

    config = _load_config()
    cold = (config.get("cold_start") or {}).get("thresholds") or {}
    skip_below = cold.get("skip_retrieval_below", 5)
    same_task_only_below = cold.get("same_task_only_below", 30)

    has_task_or_host = bool(
        (query.get("synth_task") or query.get("task"))
        or (query.get("host_organism") or query.get("host"))
    )
    if n_cases < skip_below:
        retrieval_mode = "cold_start"
    elif not has_task_or_host:
        # Free-text-only or compound-only query — no pool routing, rank all cases.
        retrieval_mode = "no_pool_routing"
    elif n_cases < same_task_only_below:
        retrieval_mode = "same_task_only"
    else:
        retrieval_mode = "full"

    stage_weights_all = config.get("stage_weights") or {}
    weights = stage_weights_all.get(stage) or stage_weights_all.get("scoping") or {
        "synth_task": 1.5, "host_organism": 1.0, "text": 0.5,
    }
    pool_sizes = config.get("pool_sizes") or {
        "same_task_same_host": 5, "same_task": 2, "same_host": 1, "cross": 1,
    }

    # Build pools
    qt = query.get("synth_task") or query.get("task") or ""
    qh = query.get("host_organism") or query.get("host") or ""
    pools: dict[str, list[dict]] = {
        "same_task_same_host": [],
        "same_task": [],
        "same_host": [],
        "cross": [],
    }
    for c in cases:
        ct = c.get("synth_task") or c.get("task") or ""
        ch = c.get("host_organism") or c.get("target_host") or ""
        label = task_mod.pool_label(qt, qh, ct, ch)
        pools[label].append(c)

    text_idx = _get_text_index()
    final_picks: list[tuple[str, float, str]] = []

    if retrieval_mode in ("cold_start", "no_pool_routing"):
        ranked = _rank_pool_cases(cases, query, weights, text_idx)
        for cid, score in ranked:
            case = next((c for c in cases if c["case_id"] == cid), None)
            if case:
                ct = case.get("synth_task") or case.get("task") or ""
                ch = case.get("host_organism") or ""
                final_picks.append((cid, score, task_mod.pool_label(qt, qh, ct, ch)))
    else:
        # `same_task_only` mode (n < same_task_only_below): pull task-matching pools first,
        # then up to same_host (skip `cross`). `full` mode adds the cross pool.
        pool_order = [
            ("same_task_same_host", pool_sizes.get("same_task_same_host", 5)),
            ("same_task", pool_sizes.get("same_task", 2)),
            ("same_host", pool_sizes.get("same_host", 1)),
        ]
        if retrieval_mode == "full":
            pool_order.append(("cross", pool_sizes.get("cross", 1)))
        for pool_name, max_n in pool_order:
            ranked = _rank_pool_cases(pools[pool_name], query, weights, text_idx)
            for cid, score in ranked[:max_n]:
                final_picks.append((cid, score, pool_name))

    # Build result list (preserving pool order, deduping)
    case_lookup = {c["case_id"]: c for c in cases}
    result_cases = []
    seen = set()
    for cid, score, pool in final_picks:
        if cid in seen:
            continue
        seen.add(cid)
        c = case_lookup.get(cid)
        if not c:
            continue
        result_cases.append({
            "case_id": cid,
            "path": c["path"],
            "similarity": round(score, 4),
            "pool": pool,
            "synth_task": c.get("synth_task"),
            "host_organism": c.get("host_organism"),
            "doi": c.get("key_paper_doi"),
            "status": c.get("status"),
        })
        if len(result_cases) >= top_k:
            break

    # Rules: separate scoring path
    scored_rules: list[dict] = []
    for r in rules:
        if r.get("rule_type") == "cold_start_defaults":
            scored_rules.append({
                "rule_id": r["rule_id"],
                "path": r["path"],
                "rule_type": "cold_start_defaults",
                "applicability_note": "always loaded as fallback",
            })
            continue
        s = _score_rule(r, query)
        if s > 0:
            scored_rules.append({
                "rule_id": r["rule_id"],
                "path": r["path"],
                "rule_type": r.get("rule_type"),
                "score": round(s, 2),
                "evidence_cases": r.get("evidence_cases", []),
                "applies_to": r.get("applies_to"),
            })
    cs = [r for r in scored_rules if r.get("rule_type") == "cold_start_defaults"]
    others = [r for r in scored_rules if r.get("rule_type") != "cold_start_defaults"]
    others.sort(key=lambda x: -x.get("score", 0.0))
    scored_rules = others + cs

    return {
        "retrieval_mode": retrieval_mode,
        "n_cases_in_library": n_cases,
        "cases": result_cases,
        "rules": scored_rules,
        "stage_used": stage,
        "channels_used": [
            "synth_task (pool routing)",
            "host_organism (synonym-aware)",
            "target_compound (Morgan FP Tanimoto, when SMILES given)",
            "pathway_class (tag)",
            "assembly_strategy (tag)",
            "scale (tag)",
            "method_choice (tag)",
            "text (BM25)",
        ],
        "note": f"v0.1: 8-channel synth retrieval, mode={retrieval_mode}, n_cases={n_cases}",
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="run a fixed demo set of queries")
    ap.add_argument("--query-json", help="JSON string with query dict")
    ap.add_argument("--stage", default="scoping")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    if args.demo or not args.query_json:
        queries = [
            ({"synth_task": "pathway_design", "host_organism": "E. coli", "target_compound": "lycopene", "pathway_class": "terpenoid", "scale": "fermenter"},
             "lycopene heterologous pathway in E. coli (fermenter)"),
            ({"synth_task": "fba", "host_organism": "E. coli K-12 MG1655"},
             "iML1515 FBA"),
            ({"synth_task": "plasmid_assembly", "assembly_strategy": "golden_gate"},
             "Golden Gate plasmid construction"),
            ({"synth_task": "strain_engineering", "host_organism": "Corynebacterium glutamicum", "target_compound": "lysine", "scale": "industrial"},
             "Lysine industrial strain in C. glutamicum"),
            ({"synth_task": "bgc_mining", "host_organism": "Streptomyces"},
             "BGC mining in Streptomyces"),
            ({"free_text": "toggle switch bistable circuit"},
             "free-text toggle switch"),
        ]
        for q, label in queries:
            print(f"\n=== {label} ===")
            r = retrieve(q, stage=args.stage, top_k=args.top_k)
            print(f"  mode: {r['retrieval_mode']}  | n_cases_in_lib: {r['n_cases_in_library']}")
            for c in r['cases']:
                print(f"    {c['case_id']:50}  sim={c['similarity']:.4f}  pool={c['pool']}")
            if r.get('rules'):
                print(f"  rules: {[(rr['rule_id'], rr.get('score', 'fallback')) for rr in r['rules']]}")
    else:
        q = json.loads(args.query_json)
        r = retrieve(q, stage=args.stage, top_k=args.top_k)
        print(json.dumps(r, ensure_ascii=False, indent=2))
