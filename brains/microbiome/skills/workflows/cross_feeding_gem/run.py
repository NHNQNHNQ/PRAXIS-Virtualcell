#!/usr/bin/env python3
"""microbiome/cross_feeding_gem — CarveMe + SMETANA + KEGG MODULE 互喂边推断。

archetype = microbiome_pipeline。stdin JSON 优先,CLI 兜底。
simulate 默认 True(Mac 可调);real() 需远端 carve + smetana 二进制。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from itertools import combinations
from pathlib import Path

ARCHETYPE = "microbiome_pipeline"
BRAIN = "microbiome"
SKILL = "cross_feeding_gem"


# ─── run_tool shim:跨 (本地 Mac / 远端 zkyd) 路径自适应 ───────────────────
def _load_run_tool():
    try:
        from brains._common.lib.run_tool import run_tool  # type: ignore
        return run_tool
    except ImportError:
        for cand in (
            "/home/zkyd/data1/mzy/praxis2-brains",
            "/Volumes/T7/clade-learn/PRAXIS-2/brains",
        ):
            if os.path.isdir(cand):
                sys.path.insert(0, cand)
                try:
                    from _common.lib.run_tool import run_tool  # type: ignore
                    return run_tool
                except ImportError:
                    continue
        raise ImportError("找不到 _common.lib.run_tool")


# ─── simulate:生成示例 edges,符合 sanity baseline 经典链条 ────────────
def simulate(payload: dict) -> dict:
    import random
    random.seed(int(payload.get("seed", 42)))

    # 经典肠道 fiber → acetate/lactate → butyrate 三级链
    demo_edges = [
        # (donor, receiver, metabolite, smetana_prob, smetana_global, kegg_support)
        ("Bacteroides_thetaiotaomicron", "Eubacterium_rectale",
         "acetate",  0.82, 0.34, True),
        ("Bacteroides_thetaiotaomicron", "Faecalibacterium_prausnitzii",
         "acetate",  0.71, 0.28, True),
        ("Eubacterium_rectale",          "Faecalibacterium_prausnitzii",
         "lactate",  0.65, 0.22, True),
        ("Bacteroides_thetaiotaomicron", "Faecalibacterium_prausnitzii",
         "succinate", 0.58, 0.19, False),
    ]
    edges = [
        {
            "donor": d, "receiver": r, "metabolite": m,
            "smetana_prob": p, "smetana_global": g,
            "kegg_module_support": k,
            "edge_class": "metabolic_cross_feeding" + ("_kegg_supported" if k else ""),
        }
        for (d, r, m, p, g, k) in demo_edges
    ]
    return {
        "ok": True,
        "skill_id": SKILL,
        "n_samples": 0,
        "taxonomy_table": "",
        "diversity_metrics": {"shannon": 0.0, "observed_otus": len(edges)},
        "diagnostics": {
            "simulated": True,
            "brain": BRAIN, "archetype": ARCHETYPE, "skill": SKILL,
            "n_genomes": 3, "n_pairs_tested": 3,
            "n_significant_edges": len(edges),
            "edges_preview": edges,
        },
    }


# ─── 解析输入 ────────────────────────────────────────────────────────────
def _read_manifest(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if header is None:
                header = cols
                continue
            row = dict(zip(header, cols))
            rows.append(row)
    return rows


def _read_kegg_modules(path: str) -> dict[str, dict[str, float]]:
    """genome_id -> {module_id: completeness}"""
    out: dict[str, dict[str, float]] = {}
    with open(path, encoding="utf-8") as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if header is None:
                header = cols
                continue
            row = dict(zip(header, cols))
            gid = row["genome_id"]
            try:
                comp = float(row.get("completeness", "0") or 0)
            except ValueError:
                comp = 0.0
            out.setdefault(gid, {})[row["module_id"]] = comp
    return out


def _file_sha256(path: str, n_bytes: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(n_bytes):
            h.update(chunk)
    return h.hexdigest()[:16]


# ─── 候选 pair:KEGG MODULE 互补 ─────────────────────────────────────────
def _kegg_complementarity_pairs(
    modules_by_genome: dict[str, dict[str, float]],
    *,
    complete_thr: float = 0.8,
    incomplete_thr: float = 0.6,
) -> list[tuple[str, str, list[str]]]:
    """互补对:A 完整(≥0.8)而 B 缺失(<0.6)的同一 module → A 可能给 B 供货。
    返回 (donor_gid, receiver_gid, modules)。"""
    gids = list(modules_by_genome)
    pairs: list[tuple[str, str, list[str]]] = []
    for a, b in combinations(gids, 2):
        for (donor, receiver) in [(a, b), (b, a)]:
            shared_modules: list[str] = []
            for mod_id, comp in modules_by_genome[donor].items():
                if comp < complete_thr:
                    continue
                comp_b = modules_by_genome[receiver].get(mod_id, 0.0)
                if comp_b < incomplete_thr:
                    shared_modules.append(mod_id)
            if shared_modules:
                pairs.append((donor, receiver, shared_modules))
    return pairs


# ─── CarveMe 单基因组建模 ───────────────────────────────────────────────
def _carve(fasta: str, sbml_out: str, template: str, run_tool, timeout: int) -> dict:
    args = ["carve", "--fbc2", "-o", sbml_out, fasta]
    if template != "auto":
        args[1:1] = ["-u", template]
    return run_tool(args, timeout=timeout)


# ─── SMETANA detailed 解析 ──────────────────────────────────────────────
def _smetana_pair(
    sbml_a: str, sbml_b: str, media: str, out_dir: str, run_tool, timeout: int,
    mode: str = "detailed",   # detailed | global
    mediadb: str | None = None,
) -> dict:
    """跑 smetana detailed 或 global,返回 dict(含输出 tsv 路径)。"""
    out_prefix = os.path.join(out_dir, f"smetana_{mode}")
    suffix = "_detailed.tsv" if mode == "detailed" else "_global.tsv"
    out_tsv = out_prefix + suffix
    args = [
        "smetana",
        f"--{mode}",
        "--flavor", "fbc2",
        "--molweight",
        "-m", media,
        "-o", out_prefix,
        sbml_a, sbml_b,
    ]
    if mediadb:
        args[7:7] = ["--mediadb", mediadb]
    r = run_tool(args, timeout=timeout)
    r["out_tsv"] = out_tsv
    r["mode"] = mode
    return r


def _parse_smetana_global(tsv_path: str) -> dict:
    """global 输出:community medium size mip mro"""
    if not os.path.isfile(tsv_path):
        return {}
    with open(tsv_path, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f if l.strip()]
    if len(lines) < 2:
        return {}
    header = [c.strip().lower() for c in lines[0].split("\t")]
    row = dict(zip(header, lines[1].split("\t")))
    out = {"medium": row.get("medium", ""), "size": row.get("size", "")}
    for k in ("mip", "mro"):
        try:
            out[k] = float(row.get(k, "nan"))
        except ValueError:
            out[k] = None
    return out


def _parse_smetana_tsv(tsv_path: str, prob_min: float) -> list[dict]:
    """SMETANA detailed 输出列(2.x):community  medium  receiver  donor  compound  scs  mus  mps  smetana"""
    rows = []
    if not os.path.isfile(tsv_path):
        return rows
    with open(tsv_path, encoding="utf-8") as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if header is None:
                header = [c.strip().lower() for c in cols]
                continue
            row = dict(zip(header, cols))
            try:
                prob = float(row.get("smetana", "0") or 0)
            except ValueError:
                prob = 0.0
            if prob < prob_min:
                continue
            rows.append({
                "donor": row.get("donor", ""),
                "receiver": row.get("receiver", ""),
                "metabolite": row.get("compound", ""),
                "smetana_prob": prob,
            })
    return rows


# ─── real() 主流程 ──────────────────────────────────────────────────────
def real(payload: dict) -> dict:
    run_tool = _load_run_tool()
    diag: dict = {"brain": BRAIN, "skill": SKILL, "archetype": ARCHETYPE}

    manifest_path = payload.get("genome_manifest")
    if not manifest_path or not os.path.isfile(manifest_path):
        return {"ok": False, "error": "需要 genome_manifest TSV", "diagnostics": diag}

    out_subpath = payload.get("out_subpath") or tempfile.mkdtemp(prefix="cross_feed_")
    out_dir = os.path.abspath(out_subpath)
    os.makedirs(out_dir, exist_ok=True)
    diag["out_dir"] = out_dir

    smetana_score_min = float(payload.get("smetana_score_min", 0.1))
    metab_prob_min = float(payload.get("metab_prob_min", 0.5))
    pair_filter = payload.get("candidate_pair_filter", "kegg_module")
    template = payload.get("carveme_template", "auto")
    # 默认 LB[-O2](anaerobic LB)— 对肠道菌通用;M9 太贫瘠,大多 GEM 长不出来
    media = payload.get("community_media", "LB[-O2]")
    # SMETANA 需要 mediadb;默认用 carveme 自带的
    mediadb = payload.get("smetana_mediadb")
    if not mediadb:
        try:
            import carveme as _cm
            mediadb = os.path.join(
                os.path.dirname(_cm.__file__), "data", "input", "media_db.tsv"
            )
            if not os.path.isfile(mediadb):
                mediadb = None
        except ImportError:
            mediadb = None
    timeout = int(payload.get("timeout_s", 7200))

    # 1. 读 manifest
    rows = _read_manifest(manifest_path)
    diag["n_genomes"] = len(rows)
    if not rows:
        return {"ok": False, "error": "manifest 为空", "diagnostics": diag}

    # 2. CarveMe(没 sbml 的现造)
    gem_manifest: dict[str, dict] = {}
    gem_dir = os.path.join(out_dir, "gems")
    os.makedirs(gem_dir, exist_ok=True)
    for r in rows:
        gid = r["genome_id"]
        sbml = r.get("gem_sbml_path", "").strip()
        if sbml and os.path.isfile(sbml):
            gem_manifest[gid] = {"sbml": sbml, "checksum": _file_sha256(sbml), "carved": False}
            continue
        fasta = r.get("fasta_path", "").strip()
        if not (fasta and os.path.isfile(fasta)):
            diag.setdefault("skipped", []).append({"genome_id": gid, "reason": "no fasta and no sbml"})
            continue
        target = os.path.join(gem_dir, f"{gid}.xml")
        rc = _carve(fasta, target, template, run_tool, timeout)
        if not rc["ok"] or not os.path.isfile(target):
            diag.setdefault("carve_failed", []).append(
                {"genome_id": gid, "error": rc.get("error"), "stderr": (rc.get("stderr") or "")[-200:]}
            )
            continue
        gem_manifest[gid] = {"sbml": target, "checksum": _file_sha256(target), "carved": True}

    if len(gem_manifest) < 2:
        return {
            "ok": False, "error": f"GEM < 2 ({len(gem_manifest)}),无法两两模拟",
            "diagnostics": {**diag, "gem_manifest": gem_manifest},
        }

    # 3. 候选 pair
    kegg_path = payload.get("kegg_module_table") or ""
    modules = _read_kegg_modules(kegg_path) if kegg_path and os.path.isfile(kegg_path) else {}
    if pair_filter == "kegg_module" and modules:
        candidate_pairs = _kegg_complementarity_pairs(
            {g: modules.get(g, {}) for g in gem_manifest}
        )
        # 同一个 (donor, receiver) 可能重复,这里只去重 pair-of-gids 集合
        seen = set()
        pairs_unique = []
        for d, r, _ in candidate_pairs:
            key = (d, r)
            if key in seen:
                continue
            seen.add(key)
            pairs_unique.append(key)
    else:
        gids = list(gem_manifest)
        pairs_unique = [(a, b) for a, b in combinations(gids, 2)]
    diag["n_pairs_tested"] = len(pairs_unique)

    # 4. SMETANA pair-wise:每对按 modes 跑 global(快,MIP/MRO)+ detailed(慢,metabolite-level)
    # modes:["global"] / ["detailed"] / ["global","detailed"](默认两个都跑)
    modes = payload.get("smetana_modes") or ["global", "detailed"]
    pair_out = os.path.join(out_dir, "smetana")
    os.makedirs(pair_out, exist_ok=True)
    all_edges: list[dict] = []
    global_summaries: list[dict] = []   # community-level MIP/MRO 汇总
    for (gid_a, gid_b) in pairs_unique:
        sub = os.path.join(pair_out, f"{gid_a}__{gid_b}")
        os.makedirs(sub, exist_ok=True)

        # 4a. global:即便 detailed 没结果也保留 MIP/MRO 信号
        if "global" in modes:
            rg = _smetana_pair(
                gem_manifest[gid_a]["sbml"], gem_manifest[gid_b]["sbml"],
                media, sub, run_tool, timeout, mode="global", mediadb=mediadb,
            )
            if rg["ok"]:
                g = _parse_smetana_global(rg["out_tsv"])
                if g:
                    g.update({"organism_a": gid_a, "organism_b": gid_b})
                    global_summaries.append(g)

        # 4b. detailed
        if "detailed" not in modes:
            continue
        rc = _smetana_pair(
            gem_manifest[gid_a]["sbml"], gem_manifest[gid_b]["sbml"],
            media, sub, run_tool, timeout, mode="detailed", mediadb=mediadb,
        )
        if not rc["ok"]:
            diag.setdefault("smetana_failed", []).append(
                {"pair": f"{gid_a},{gid_b}", "error": rc.get("error")}
            )
            continue
        for edge in _parse_smetana_tsv(rc["out_tsv"], metab_prob_min):
            # KEGG MODULE evidence:donor 完整 ∧ receiver 缺失 同一类代谢途径
            d_gid = edge.get("donor") or gid_a
            r_gid = edge.get("receiver") or gid_b
            kegg_support = False
            if modules:
                donor_complete = any(
                    c >= 0.8 for c in modules.get(d_gid, {}).values()
                )
                recv_incomplete = any(
                    c < 0.6 for c in modules.get(r_gid, {}).values()
                )
                kegg_support = donor_complete and recv_incomplete
            edge["smetana_global"] = max(edge["smetana_prob"], smetana_score_min)
            edge["kegg_module_support"] = kegg_support
            edge["edge_class"] = "metabolic_cross_feeding" + ("_kegg_supported" if kegg_support else "")
            all_edges.append(edge)

    # 5. 写出
    edges_tsv = os.path.join(out_dir, "edges.tsv")
    cols = ["donor", "receiver", "metabolite", "smetana_prob",
            "smetana_global", "kegg_module_support", "edge_class"]
    with open(edges_tsv, "w", encoding="utf-8") as f:
        f.write("\t".join(cols) + "\n")
        for e in all_edges:
            f.write("\t".join(str(e.get(c, "")) for c in cols) + "\n")

    gem_manifest_json = os.path.join(out_dir, "gem_manifest.json")
    Path(gem_manifest_json).write_text(json.dumps(gem_manifest, indent=2), encoding="utf-8")

    # 写 community-level MIP/MRO 汇总
    global_tsv = os.path.join(out_dir, "global_summaries.tsv")
    if global_summaries:
        gcols = ["organism_a", "organism_b", "medium", "size", "mip", "mro"]
        with open(global_tsv, "w", encoding="utf-8") as f:
            f.write("\t".join(gcols) + "\n")
            for g in global_summaries:
                f.write("\t".join(str(g.get(c, "")) for c in gcols) + "\n")

    summary = {
        "n_genomes": len(gem_manifest),
        "n_pairs_tested": len(pairs_unique),
        "n_significant_edges": len(all_edges),
        "n_global_summaries": len(global_summaries),
        "params": {
            "smetana_score_min": smetana_score_min,
            "metab_prob_min": metab_prob_min,
            "candidate_pair_filter": pair_filter,
            "carveme_template": template,
            "community_media": media,
        },
    }
    summary_json = os.path.join(out_dir, "summary.json")
    Path(summary_json).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    diag.update({
        "n_genomes": len(gem_manifest),
        "n_pairs_tested": len(pairs_unique),
        "n_significant_edges": len(all_edges),
        "n_global_summaries": len(global_summaries),
        "edges_tsv": edges_tsv,
        "global_tsv": global_tsv if global_summaries else "",
        "global_preview": global_summaries[:5],
        "gem_manifest_json": gem_manifest_json,
        "summary_json": summary_json,
        "tool_versions": {
            "carve": shutil.which("carve") or "",
            "smetana": shutil.which("smetana") or "",
        },
    })
    return {
        "ok": True,
        "skill_id": SKILL,
        "n_samples": 0,
        "taxonomy_table": edges_tsv,
        "diversity_metrics": {"shannon": 0.0, "observed_otus": len(all_edges)},
        "diagnostics": diag,
    }


# ─── 入口 ────────────────────────────────────────────────────────────────
def main() -> int:
    payload: dict = {}
    if not sys.stdin.isatty():
        try:
            data = json.load(sys.stdin)
            if isinstance(data, dict):
                payload = data
        except json.JSONDecodeError:
            pass
    if not payload:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--simulate", action="store_true", default=True)
        ap.add_argument("--seed", type=int, default=42)
        args, _ = ap.parse_known_args()
        payload = {"simulate": args.simulate, "seed": args.seed}

    simulate_mode = bool(payload.get("simulate", True))
    try:
        out = simulate(payload) if simulate_mode else real(payload)
    except Exception as e:
        out = {"ok": False, "error": f"run.py 内部错误: {e!r}",
               "diagnostics": {"brain": BRAIN, "skill": SKILL}}

    if isinstance(out, dict):
        out.setdefault("diagnostics", {})
        if isinstance(out["diagnostics"], dict):
            out["diagnostics"].update({"archetype": ARCHETYPE, "brain": BRAIN, "skill": SKILL})

    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
