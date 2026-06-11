#!/usr/bin/env python3
"""microbiome/phage_host_link — iPHoP + CRISPR spacer 双证据 phage-host 边推断。

archetype = microbiome_pipeline。stdin JSON 优先,CLI 兜底。
simulate 默认 True(Mac 可调);real() 需远端 iphop + blastn 二进制。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from itertools import product
from pathlib import Path

ARCHETYPE = "microbiome_pipeline"
BRAIN = "microbiome"
SKILL = "phage_host_link"


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


# ─── simulate:典型肠道 phage-host 对,sanity baseline 用 ─────────────────
def simulate(payload: dict) -> dict:
    import random
    random.seed(int(payload.get("seed", 42)))

    # (phage_id, host_id, iphop_score, spacer_hit, edge_class)
    demo_edges = [
        # 双证据强对(GPD 经典)
        ("epsilon15_like",     "Escherichia_coli_K12",       96.4, True,  "dual_evidence"),
        ("crAss_like_p001",    "Bacteroides_fragilis_9343",  94.1, True,  "dual_evidence"),
        # iPHoP 强但 host 没留 CRISPR 记录(可能 phage 进化绕过)
        ("Lj928_prophage",     "Lactobacillus_reuteri",      92.7, False, "iphop_only"),
        # CRISPR 有 hit 但 iPHoP 不达标(历史感染、当前 phage 序列变多)
        ("phage_X_novel",      "Escherichia_coli_K12",       72.5, True,  "crispr_only"),
        # 弱 iPHoP only(边界情况)
        ("crAss_like_p007",    "Bacteroides_fragilis_9343",  90.2, False, "iphop_only"),
    ]
    edges = [
        {
            "phage_id": p, "host_id": h,
            "iphop_score": s, "spacer_hit": bool(hit),
            "edge_class": cls,
        }
        for (p, h, s, hit, cls) in demo_edges
    ]

    n_dual = sum(1 for e in edges if e["edge_class"] == "dual_evidence")
    phages = sorted({e["phage_id"] for e in edges})
    hosts = sorted({e["host_id"] for e in edges})
    return {
        "ok": True,
        "skill_id": SKILL,
        "n_samples": 0,
        "taxonomy_table": "",
        "diversity_metrics": {"shannon": 0.0, "observed_otus": len(edges)},
        "diagnostics": {
            "simulated": True,
            "brain": BRAIN, "archetype": ARCHETYPE, "skill": SKILL,
            "n_phages": len(phages),
            "n_hosts": len(hosts),
            "n_pairs_tested": len(phages) * len(hosts),
            "n_significant_edges": len(edges),
            "n_dual_evidence": n_dual,
            "edges_preview": edges,
        },
    }


# ─── 解析输入 ────────────────────────────────────────────────────────────
def _read_manifest(path: str) -> list[dict]:
    """通用 TSV manifest 读取(首行 header)。"""
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
            rows.append(dict(zip(header, cols)))
    return rows


def _read_spacer_db(path: str) -> list[dict]:
    """CRISPR spacer DB:spacer_id<TAB>sequence<TAB>host_genome_id"""
    return _read_manifest(path)


def _write_spacers_fasta(spacers: list[dict], host_id: str, out_fa: str) -> int:
    """把属于 host_id 的 spacer 写成 fasta;返回写入的 spacer 数。"""
    n = 0
    with open(out_fa, "w", encoding="utf-8") as f:
        for s in spacers:
            if s.get("host_genome_id") != host_id:
                continue
            seq = (s.get("sequence") or "").strip()
            sid = s.get("spacer_id") or f"spacer_{n}"
            if not seq:
                continue
            f.write(f">{sid}\n{seq}\n")
            n += 1
    return n


# ─── iPHoP 单 contig 预测 ─────────────────────────────────────────────────
def _iphop_predict(viral_fa: str, out_dir: str, db_dir: str, run_tool, timeout: int) -> dict:
    """iphop predict --fa_file <contig> --out_dir <out> --db_dir <db>。

    输出主文件:<out_dir>/Host_prediction_to_genus_m<score>.csv
    + Host_prediction_to_genome_m<score>.csv
    我们读 genome-level(精度更高)。
    """
    args = [
        "iphop", "predict",
        "--fa_file", viral_fa,
        "--out_dir", out_dir,
        "--db_dir", db_dir,
    ]
    return run_tool(args, timeout=timeout)


def _parse_iphop_csv(out_dir: str, score_min: float) -> list[dict]:
    """扫 out_dir 找 Host_prediction_to_genome_*.csv,返回 [{Virus, Host_genome, Confidence_score, ...}]。

    iPHoP 输出列(genome 级,2023+ 版本):
      Virus, AAI_to_closest_RaFAH_reference, Confidence_score,
      List_of_methods, Host_genome, Host_taxonomy
    """
    rows: list[dict] = []
    out_path = Path(out_dir)
    if not out_path.is_dir():
        return rows
    candidates = list(out_path.glob("Host_prediction_to_genome*.csv"))
    if not candidates:
        # 兜底找任何 genome-level CSV
        candidates = [p for p in out_path.glob("*.csv") if "genome" in p.name.lower()]
    for csv_path in candidates:
        with open(csv_path, encoding="utf-8") as f:
            header = None
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                # iPHoP 输出是 CSV,有些字段含逗号会带引号 — 这里做最简单的 split,
                # 如需更严谨改 csv.reader。
                cols = [c.strip().strip('"') for c in line.split(",")]
                if header is None:
                    header = [c.lower() for c in cols]
                    continue
                row = dict(zip(header, cols))
                try:
                    score = float(row.get("confidence_score", "0") or 0)
                except ValueError:
                    score = 0.0
                if score < score_min:
                    continue
                rows.append({
                    "phage_id": row.get("virus", ""),
                    "host_id": row.get("host_genome", ""),
                    "iphop_score": score,
                    "host_taxonomy": row.get("host_taxonomy", ""),
                })
    return rows


# ─── CRISPR spacer blastn ────────────────────────────────────────────────
def _blastn_spacer_vs_contig(
    spacer_fa: str, contig_fa: str, out_tsv: str, run_tool, timeout: int,
) -> dict:
    """blastn-short:spacer(20-40 nt)对 viral contig。

    输出格式 6:qseqid sseqid pident length qlen qstart qend sstart send evalue
    """
    args = [
        "blastn",
        "-task", "blastn-short",
        "-query", spacer_fa,
        "-subject", contig_fa,
        "-outfmt", "6 qseqid sseqid pident length qlen qstart qend sstart send evalue",
        "-evalue", "1e-3",
        "-out", out_tsv,
    ]
    return run_tool(args, timeout=timeout)


def _parse_blastn_hits(
    tsv_path: str, min_identity: float, min_coverage: float,
) -> list[dict]:
    """返回 [{spacer_id, contig_id, pident, qcov}],过滤后只留达标 hit。"""
    hits = []
    if not os.path.isfile(tsv_path):
        return hits
    with open(tsv_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 10:
                continue
            try:
                pident = float(cols[2]) / 100.0
                length = float(cols[3])
                qlen = float(cols[4])
                qcov = length / qlen if qlen > 0 else 0.0
            except ValueError:
                continue
            if pident < min_identity or qcov < min_coverage:
                continue
            hits.append({
                "spacer_id": cols[0], "contig_id": cols[1],
                "pident": pident, "qcov": qcov,
            })
    return hits


# ─── real() 主流程 ──────────────────────────────────────────────────────
def real(payload: dict) -> dict:
    diag: dict = {"brain": BRAIN, "skill": SKILL, "archetype": ARCHETYPE}

    # 干跑短路:给 SkillExecTool 用,不真起 subprocess
    if os.environ.get("PRAXIS_SKILL_DRY_HOST") == "1":
        return {
            "ok": True, "skill_id": SKILL, "n_samples": 0,
            "taxonomy_table": "",
            "diversity_metrics": {"shannon": 0.0, "observed_otus": 0},
            "diagnostics": {**diag, "dry": True},
        }

    run_tool = _load_run_tool()

    host_manifest = payload.get("host_manifest")
    viral_manifest = payload.get("viral_manifest")
    if not host_manifest or not os.path.isfile(host_manifest):
        return {"ok": False, "error": "需要 host_manifest TSV", "diagnostics": diag}
    if not viral_manifest or not os.path.isfile(viral_manifest):
        return {"ok": False, "error": "需要 viral_manifest TSV", "diagnostics": diag}

    # 早 fail:iphop 二进制
    if not shutil.which("iphop"):
        return {
            "ok": False,
            "error": "iphop 二进制不在 PATH(远端 env: praxis-microbiome-phage)",
            "diagnostics": diag,
        }
    # blastn 只在有 spacer DB 时强制
    spacer_db_path = payload.get("crispr_spacer_db") or ""
    has_spacers = bool(spacer_db_path) and os.path.isfile(spacer_db_path)
    if has_spacers and not shutil.which("blastn"):
        return {
            "ok": False,
            "error": "blastn 二进制不在 PATH,但传了 crispr_spacer_db",
            "diagnostics": diag,
        }

    out_subpath = payload.get("out_subpath") or tempfile.mkdtemp(prefix="phage_host_")
    out_dir = os.path.abspath(out_subpath)
    os.makedirs(out_dir, exist_ok=True)
    diag["out_dir"] = out_dir

    iphop_db = payload.get("iphop_db") or "/data/db/iphop_db"
    iphop_score_min = float(payload.get("iphop_score_min", 90))
    spacer_min_identity = float(payload.get("spacer_min_identity", 0.95))
    spacer_min_coverage = float(payload.get("spacer_min_coverage", 0.95))
    timeout = int(payload.get("timeout_s", 7200))

    # 1. 读 manifest
    hosts = _read_manifest(host_manifest)
    virals = _read_manifest(viral_manifest)
    diag["n_hosts"] = len(hosts)
    diag["n_phages"] = len(virals)
    if not hosts or not virals:
        return {"ok": False, "error": "host 或 viral manifest 为空", "diagnostics": diag}

    spacers = _read_spacer_db(spacer_db_path) if has_spacers else []
    diag["n_spacers"] = len(spacers)

    # 2. iPHoP:对每个 viral contig 跑一次(iPHoP 也支持 batch,但单 fasta 更稳)
    iphop_dir = os.path.join(out_dir, "iphop")
    os.makedirs(iphop_dir, exist_ok=True)
    iphop_hits: list[dict] = []
    for v in virals:
        cid = v.get("contig_id") or ""
        fa = (v.get("fasta_path") or "").strip()
        if not (cid and fa and os.path.isfile(fa)):
            diag.setdefault("skipped_phages", []).append(
                {"contig_id": cid, "reason": "no fasta"}
            )
            continue
        sub = os.path.join(iphop_dir, cid)
        os.makedirs(sub, exist_ok=True)
        rc = _iphop_predict(fa, sub, iphop_db, run_tool, timeout)
        if not rc["ok"]:
            diag.setdefault("iphop_failed", []).append(
                {"contig_id": cid, "error": rc.get("error"),
                 "stderr": (rc.get("stderr") or "")[-200:]}
            )
            continue
        hits = _parse_iphop_csv(sub, iphop_score_min)
        # 用 manifest 的 contig_id 覆盖 iPHoP 内部 Virus 字段(它有时改名)
        for h in hits:
            h["phage_id"] = cid
        iphop_hits.extend(hits)
    diag["n_iphop_hits"] = len(iphop_hits)

    # 3. CRISPR spacer blastn:对每个 (host, viral_contig) 跑
    spacer_dir = os.path.join(out_dir, "spacer_blast")
    os.makedirs(spacer_dir, exist_ok=True)
    # spacer_hits[(phage_id, host_id)] = [...]
    spacer_hits: dict[tuple[str, str], list[dict]] = {}
    if has_spacers:
        # 预写每个 host 的 spacer fasta(避免重复扫 DB)
        spacer_fa_by_host: dict[str, str] = {}
        for h in hosts:
            hid = h.get("genome_id") or ""
            if not hid:
                continue
            sfa = os.path.join(spacer_dir, f"{hid}.spacers.fa")
            n = _write_spacers_fasta(spacers, hid, sfa)
            if n > 0:
                spacer_fa_by_host[hid] = sfa
        diag["n_hosts_with_spacers"] = len(spacer_fa_by_host)

        for h, v in product(hosts, virals):
            hid = h.get("genome_id") or ""
            cid = v.get("contig_id") or ""
            vfa = (v.get("fasta_path") or "").strip()
            sfa = spacer_fa_by_host.get(hid)
            if not (hid and cid and sfa and vfa and os.path.isfile(vfa)):
                continue
            out_tsv = os.path.join(spacer_dir, f"{hid}__{cid}.blastn.tsv")
            rc = _blastn_spacer_vs_contig(sfa, vfa, out_tsv, run_tool, timeout)
            if not rc["ok"]:
                diag.setdefault("blastn_failed", []).append(
                    {"host_id": hid, "contig_id": cid, "error": rc.get("error")}
                )
                continue
            hh = _parse_blastn_hits(out_tsv, spacer_min_identity, spacer_min_coverage)
            if hh:
                spacer_hits[(cid, hid)] = hh
    diag["n_spacer_pairs"] = len(spacer_hits)

    # 4. 合并两路证据
    # 索引 iphop hits 到 (phage_id, host_id)
    iphop_by_pair: dict[tuple[str, str], dict] = {}
    for hit in iphop_hits:
        key = (hit["phage_id"], hit["host_id"])
        # 同对取最高 score
        if key not in iphop_by_pair or hit["iphop_score"] > iphop_by_pair[key]["iphop_score"]:
            iphop_by_pair[key] = hit

    pair_keys = set(iphop_by_pair) | set(spacer_hits)
    edges: list[dict] = []
    for (phage_id, host_id) in pair_keys:
        iphop_hit = iphop_by_pair.get((phage_id, host_id))
        spacer_hh = spacer_hits.get((phage_id, host_id), [])
        has_iphop = iphop_hit is not None
        has_spacer = len(spacer_hh) > 0
        if has_iphop and has_spacer:
            cls = "dual_evidence"
        elif has_iphop:
            cls = "iphop_only"
        else:
            cls = "crispr_only"
        edges.append({
            "phage_id": phage_id,
            "host_id": host_id,
            "iphop_score": iphop_hit["iphop_score"] if has_iphop else 0.0,
            "spacer_hit": has_spacer,
            "n_spacer_hits": len(spacer_hh),
            "edge_class": cls,
        })

    # 5. 写出
    edges_tsv = os.path.join(out_dir, "edges.tsv")
    cols = ["phage_id", "host_id", "iphop_score", "spacer_hit", "n_spacer_hits", "edge_class"]
    with open(edges_tsv, "w", encoding="utf-8") as f:
        f.write("\t".join(cols) + "\n")
        for e in edges:
            f.write("\t".join(str(e.get(c, "")) for c in cols) + "\n")

    n_dual = sum(1 for e in edges if e["edge_class"] == "dual_evidence")
    n_iphop_only = sum(1 for e in edges if e["edge_class"] == "iphop_only")
    n_crispr_only = sum(1 for e in edges if e["edge_class"] == "crispr_only")
    n_pairs_tested = len(hosts) * len(virals)

    summary = {
        "n_phages": len(virals),
        "n_hosts": len(hosts),
        "n_pairs_tested": n_pairs_tested,
        "n_significant_edges": len(edges),
        "n_dual_evidence": n_dual,
        "n_iphop_only": n_iphop_only,
        "n_crispr_only": n_crispr_only,
        "params": {
            "iphop_score_min": iphop_score_min,
            "spacer_min_identity": spacer_min_identity,
            "spacer_min_coverage": spacer_min_coverage,
            "iphop_db": iphop_db,
        },
    }
    summary_json = os.path.join(out_dir, "summary.json")
    Path(summary_json).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    diag.update({
        "n_phages": len(virals),
        "n_hosts": len(hosts),
        "n_pairs_tested": n_pairs_tested,
        "n_significant_edges": len(edges),
        "n_dual_evidence": n_dual,
        "n_iphop_only": n_iphop_only,
        "n_crispr_only": n_crispr_only,
        "edges_tsv": edges_tsv,
        "summary_json": summary_json,
        "edges_preview": edges[:10],
        "tool_versions": {
            "iphop": shutil.which("iphop") or "",
            "blastn": shutil.which("blastn") or "",
        },
    })
    return {
        "ok": True,
        "skill_id": SKILL,
        "n_samples": 0,
        "taxonomy_table": edges_tsv,
        "diversity_metrics": {"shannon": 0.0, "observed_otus": len(edges)},
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
