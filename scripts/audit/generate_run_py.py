#!/usr/bin/env python3
"""为所有 brains/<brain>/skills/workflows/*/SKILL.md 生成 run.py。

第一版只实现 --simulate / 默认 simulate 模式(返回合理的合成数据 JSON)。
真实现路径(simulate=False)留 stub:返回结构化 "not implemented" + 提示。

archetype 由 skill 名 + brain + 描述关键词决定:
  - structure_predict   (alphafold / boltz / chai / esmfold / rfdiffusion / colabfold)
  - mutation_scan       (foldx / pyrosetta / ddg / thermompnn / mutation_effect / esm-mutation)
  - docking             (vina / gnina / dock / haddock / cluspro)
  - msa_conservation    (mmseqs / foldseek / hhblits / consurf / msa)
  - mhc_epitope         (mhc / netMHC / hla / tcr)
  - omics_scrna         (scanpy / scvi / annotate / qc / cellpose / live-cell)
  - microbiome_pipeline (kraken / humann / qiime / metaphlan / spades)
  - crispr              (sgrna / pe / sge / off_target / mageck)
  - drug                (admet / fep / retro / synth / protac)
  - pharma              (pbpk / pkpd / allometric / ppb)
  - cryo                (relion / cryosparc / motioncor / topaz / phenix)
  - fetcher             (fetch / crawl / pull / download)
  - generic             (兜底)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent.parent / "brains"
# 已有手写实现,不覆盖
SKIP = {ROOT / "enzyme/skills/workflows/pyrosetta-stability-scan/run.py"}


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def detect_archetype(brain: str, skill: str, text: str) -> str:
    s = f"{brain}/{skill}".lower()
    body = text.lower()
    name_lower = skill.lower()

    def name_has(*kw: str) -> bool:
        return any(k in s for k in kw)

    def body_has_word(*kw: str) -> bool:
        # 词边界匹配,避免 "metaphlan" 命中 "hla"
        for k in kw:
            if re.search(rf"(?<![a-z0-9_]){re.escape(k)}(?![a-z0-9_])", body[:1500]):
                return True
        return False

    # 1) fetcher 名字最强信号
    if any(tok in name_lower for tok in ("fetch", "crawl", "pull", "download", "scrape")):
        return "fetcher"

    # 2) brain 强归属优先(避免短词在描述里误命中)
    if brain == "cryo":
        return "cryo"
    if brain == "microbiome":
        return "microbiome_pipeline"
    if brain == "pharma":
        return "pharma"
    if brain == "crispr":
        return "crispr"
    if brain == "drug":
        return "drug"

    # 3) 名字 / 词边界匹配
    if name_has("alphafold", "boltz", "chai", "esmfold", "rfdiffusion", "colabfold",
                "proteinmpnn_sequence", "predict_structure", "conformation_ensemble",
                "structure_predict"):
        return "structure_predict"
    if name_has("foldx", "pyrosetta", "ddg", "thermompnn", "mutation_effect",
                "esm-mutation", "mutation_scan", "mutation_panel", "stability"):
        return "mutation_scan"
    if name_has("vina", "gnina", "dock", "haddock", "cluspro", "docking",
                "flexpep", "snugdock"):
        return "docking"
    if name_has("mhc", "hla", "tcr", "epitope"):
        return "mhc_epitope"
    if name_has("mmseqs", "foldseek", "hhblits", "consurf", "msa",
                "conservation", "homology", "catalytic-site", "structural-context", "pocket-tunnel"):
        return "msa_conservation"

    # 4) cell / omics / immuno brain 路由(name 兜底)
    if brain in {"cell", "omics"}:
        return "omics_scrna"
    if brain == "immuno":
        # immuno 大多是 mhc/hla/tcr/epitope 类,但若名字没命中前面,兜到 mhc_epitope
        return "mhc_epitope"
    if brain in {"enzyme", "protein"}:
        # enzyme/protein 默认走 mutation_scan(更接近)或 structure_predict
        if name_has("predict", "fold", "esm"):
            return "structure_predict"
        if name_has("annot", "site", "pocket", "tunnel", "context", "msa", "homology"):
            return "msa_conservation"
        return "mutation_scan"

    # 5) word-boundary 兜底
    if body_has_word("mhc", "tcr", "epitope"):
        return "mhc_epitope"
    if body_has_word("scanpy", "scvi", "anndata", "cellpose"):
        return "omics_scrna"

    return "generic"


# ---------- 模板的 simulate 体(返回 dict) ----------
_TEMPLATES: dict[str, Callable[[dict], dict]] = {}

def _t(name: str):
    def _wrap(f):
        _TEMPLATES[name] = f
        return f
    return _wrap


# 注:实际生成出的 run.py 把这些函数的 body 内联,不引用外部模块。
# 这里只是声明(便于审阅);_emit_runpy 把 archetype name 映射到内联 body 字符串。
@_t("fetcher")
def _archetype_fetcher(p: dict) -> dict: ...
@_t("structure_predict")
def _archetype_structure_predict(p: dict) -> dict: ...
@_t("mutation_scan")
def _archetype_mutation_scan(p: dict) -> dict: ...
@_t("docking")
def _archetype_docking(p: dict) -> dict: ...
@_t("msa_conservation")
def _archetype_msa_conservation(p: dict) -> dict: ...
@_t("mhc_epitope")
def _archetype_mhc_epitope(p: dict) -> dict: ...
@_t("omics_scrna")
def _archetype_omics_scrna(p: dict) -> dict: ...
@_t("microbiome_pipeline")
def _archetype_microbiome_pipeline(p: dict) -> dict: ...
@_t("crispr")
def _archetype_crispr(p: dict) -> dict: ...
@_t("drug")
def _archetype_drug(p: dict) -> dict: ...
@_t("pharma")
def _archetype_pharma(p: dict) -> dict: ...
@_t("cryo")
def _archetype_cryo(p: dict) -> dict: ...
@_t("generic")
def _archetype_generic(p: dict) -> dict: ...


# 每个 archetype 的 simulate 函数体(字符串,直接内联到生成的 run.py 中)。
ARCHETYPE_BODIES: dict[str, str] = {

    "fetcher": '''
def simulate(payload):
    qid = payload.get("id") or payload.get("query") or "DEMO_ID"
    return {
        "fetched": True,
        "id": qid,
        "source": payload.get("source", "remote_db"),
        "local_path": f"/tmp/fetched/{qid}.txt",
        "bytes": 12345,
        "format": "text",
        "diagnostics": {"simulated": True, "note": "未真去拉取;真模式请补 requests/HTTP 客户端"},
    }
''',

    "structure_predict": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    seq = payload.get("sequence") or "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVPSTAIREISLLKELNHPNIVKLLDVIHTENKLYLVFEFLHQDLKKFMDASALTGIPLPLIKSYLFQLLQGLAFCHSHRVLHRDLKPQNLLINTEGAIKLADFGLARAFGVPVRTYTHEVVTLWYRAPEILLGCKYYSTAVDIWSLGCIFAEMVTRRALFPGDSEIDQLFRIFRTLGTPDEVVWPGVTSMPDYKPSFPKWARQDFSKVVPPLDEDGRSLLSQMLHYDPNKRISAKAALAHPFFQDVTKPVPHLRL"
    n = len(seq)
    plddt_per_res = [round(random.uniform(40, 95), 2) for _ in range(n)]
    return {
        "input_sequence_len": n,
        "predicted_structure_path": "/tmp/predicted_model.pdb",
        "ranking_confidence": round(sum(plddt_per_res)/n, 2),
        "ptm": round(random.uniform(0.5, 0.9), 3),
        "iptm": round(random.uniform(0.5, 0.9), 3) if payload.get("complex") else None,
        "plddt_per_residue": plddt_per_res,
        "diagnostics": {
            "simulated": True,
            "model_used": payload.get("model", "auto"),
            "warning": "真预测请在 host_env 内调对应工具 CLI",
        },
    }
''',

    "mutation_scan": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    aa_list = (payload.get("amino_acids") or "ARNDCQEGHILKMFPSTWYV")[:20]
    positions = payload.get("positions") or [10, 50, 100]
    active = set(payload.get("active_site_residues") or [])
    n_runs = max(1, int(payload.get("n_runs", 3)))
    mutations = []
    for pos in positions:
        wt = random.choice(aa_list)
        for mut in aa_list:
            if mut == wt: continue
            samples = [random.gauss(1.5, 2.5) for _ in range(n_runs)]
            ddg = sum(samples)/len(samples)
            std = (sum((s-ddg)**2 for s in samples)/len(samples))**0.5
            near_act = bool(active and any(abs(pos-a)<=5 for a in active))
            mutations.append({
                "position": pos, "wt_aa": wt, "mut_aa": mut,
                "ddG_kcal_per_mol": round(ddg, 3),
                "ddG_std": round(std, 3),
                "near_active_site": near_act,
                "passes_default_filter": (ddg < -1.5 and not near_act),
                "simulated": True,
            })
    return {
        "scan_summary": {
            "n_positions": len(positions),
            "n_mutations": len(mutations),
            "score_function": "synthetic (simulate)",
        },
        "mutations": mutations,
        "diagnostics": {"simulated": True},
    }
''',

    "docking": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    n_poses = int(payload.get("n_poses", 9))
    poses = []
    for i in range(n_poses):
        score = -8 + i*0.3 + random.gauss(0, 0.2)
        poses.append({
            "rank": i+1,
            "affinity_kcal_per_mol": round(score, 2),
            "rmsd_lb": round(random.uniform(0, 4), 2),
            "rmsd_ub": round(random.uniform(0, 6), 2),
            "pose_path": f"/tmp/pose_{i+1}.pdb",
        })
    return {
        "receptor": payload.get("receptor_pdb", "/tmp/rec.pdb"),
        "ligand": payload.get("ligand_smiles") or payload.get("ligand_path", "CCO"),
        "best_affinity": poses[0]["affinity_kcal_per_mol"],
        "poses": poses,
        "redock_self_test": {
            "performed": True,
            "top1_rmsd": round(random.uniform(0.3, 2.5), 2),
            "passed_2A_gate": random.random() > 0.4,
        },
        "diagnostics": {"simulated": True, "engine": "synthetic"},
    }
''',

    "msa_conservation": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    n_res = int(payload.get("n_residues", payload.get("seq_len", 200)))
    cons = [round(random.uniform(0, 9), 1) for _ in range(n_res)]
    return {
        "msa_depth": random.randint(80, 5000),
        "n_sequences_after_filter": random.randint(50, 2000),
        "conservation_scores_per_residue": cons,
        "highly_conserved_positions": [i+1 for i, c in enumerate(cons) if c >= 7.5],
        "diagnostics": {"simulated": True, "tool": payload.get("tool", "synthetic")},
    }
''',

    "mhc_epitope": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    n = int(payload.get("n_peptides", 30))
    peptides = []
    aa = "ACDEFGHIKLMNPQRSTVWY"
    for _ in range(n):
        L = random.choice([8, 9, 10, 11])
        seq = "".join(random.choice(aa) for _ in range(L))
        peptides.append({
            "peptide": seq,
            "length": L,
            "predicted_affinity_nM": round(random.expovariate(1/200), 1),
            "rank_percentile": round(random.uniform(0.01, 5), 3),
            "binder": random.random() > 0.7,
        })
    return {
        "allele": payload.get("allele", "HLA-A*02:01"),
        "n_peptides": n,
        "peptides": peptides,
        "diagnostics": {"simulated": True},
    }
''',

    "omics_scrna": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    n_cells = int(payload.get("n_cells", 5000))
    n_genes = int(payload.get("n_genes", 20000))
    n_clusters = int(payload.get("n_clusters", 12))
    cluster_sizes = [random.randint(100, 800) for _ in range(n_clusters)]
    return {
        "n_cells_post_qc": n_cells,
        "n_genes_detected": n_genes,
        "n_clusters": n_clusters,
        "cluster_sizes": cluster_sizes,
        "median_genes_per_cell": random.randint(1200, 3500),
        "median_umi_per_cell": random.randint(3000, 12000),
        "marker_genes_per_cluster": {
            f"cluster_{i}": [f"GENE{random.randint(1, 1000)}" for _ in range(5)]
            for i in range(n_clusters)
        },
        "diagnostics": {"simulated": True},
    }
''',

    "microbiome_pipeline": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    n_samples = int(payload.get("n_samples", 12))
    taxa = ["Bacteroides", "Faecalibacterium", "Akkermansia", "Roseburia", "Prevotella",
            "Lactobacillus", "Bifidobacterium", "Escherichia", "Streptococcus", "Clostridium"]
    abundance = {}
    for s in range(n_samples):
        rel = [random.random() for _ in taxa]
        tot = sum(rel)
        abundance[f"sample_{s+1}"] = {t: round(r/tot, 4) for t, r in zip(taxa, rel)}
    return {
        "n_samples": n_samples,
        "n_taxa": len(taxa),
        "alpha_diversity_shannon_per_sample": {
            f"sample_{s+1}": round(random.uniform(1.5, 4.5), 3) for s in range(n_samples)
        },
        "relative_abundance": abundance,
        "diagnostics": {"simulated": True, "level": "genus"},
    }
''',

    "crispr": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    n_guides = int(payload.get("n_guides", 10))
    target = payload.get("target_gene") or payload.get("target", "EXAMPLE_GENE")
    bases = "ACGT"
    guides = []
    for i in range(n_guides):
        seq = "".join(random.choice(bases) for _ in range(20))
        guides.append({
            "rank": i+1,
            "guide_seq": seq + "NGG",
            "on_target_score": round(random.uniform(0.4, 0.95), 3),
            "off_target_score": round(random.uniform(0.0, 0.4), 3),
            "n_off_targets_3mm": random.randint(0, 12),
        })
    return {
        "target_gene": target,
        "n_guides": n_guides,
        "guides": guides,
        "diagnostics": {"simulated": True, "scorer": "synthetic_rs2"},
    }
''',

    "drug": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    mols = payload.get("molecules") or [{"smiles": "CCO"}, {"smiles": "c1ccccc1"}]
    rows = []
    for i, m in enumerate(mols if isinstance(mols, list) else [mols]):
        smiles = m["smiles"] if isinstance(m, dict) else str(m)
        rows.append({
            "smiles": smiles,
            "logP": round(random.uniform(-1, 5), 2),
            "tpsa": round(random.uniform(20, 140), 1),
            "hbd": random.randint(0, 5),
            "hba": random.randint(0, 10),
            "ro5_violations": random.randint(0, 2),
            "QED": round(random.uniform(0.2, 0.9), 3),
            "predicted_pIC50": round(random.uniform(4, 9), 2),
        })
    return {"n_molecules": len(rows), "predictions": rows, "diagnostics": {"simulated": True}}
''',

    "pharma": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    t_h = list(range(0, 25, 1))
    dose = float(payload.get("dose_mg", 100))
    Cmax = dose / random.uniform(2, 6)
    ka = random.uniform(0.5, 2.5); ke = random.uniform(0.05, 0.3)
    profile = []
    for t in t_h:
        from math import exp
        C = (Cmax * (exp(-ke*t) - exp(-ka*t))) if t > 0 else 0
        profile.append({"t_h": t, "conc_ng_per_mL": round(max(0, C), 3)})
    return {
        "dose_mg": dose,
        "PK_params": {"ka": round(ka, 3), "ke": round(ke, 3), "t_half_h": round(0.693/ke, 2), "Cmax_ng_per_mL": round(Cmax, 2)},
        "concentration_time_profile": profile,
        "diagnostics": {"simulated": True},
    }
''',

    "cryo": '''
def simulate(payload):
    import random
    random.seed(int(payload.get("seed", 42)))
    n_particles = int(payload.get("n_particles", 250000))
    return {
        "n_movies_processed": int(payload.get("n_movies", 200)),
        "n_particles_picked": n_particles,
        "n_particles_post_2D": int(n_particles * 0.7),
        "n_particles_final_3D": int(n_particles * 0.4),
        "final_resolution_A": round(random.uniform(2.6, 4.5), 2),
        "FSC_gold_standard": round(random.uniform(0.143, 0.5), 3),
        "diagnostics": {"simulated": True, "note": "cryo 全套实际未在 .53 部署,这是合成数据"},
    }
''',

    "generic": '''
def simulate(payload):
    return {
        "ok": True,
        "echo_inputs": payload,
        "note": "本 skill 暂用 generic 模板,真实现请覆盖 run.py",
        "diagnostics": {"simulated": True},
    }
''',
}


_RUN_PY_TEMPLATE = '''#!/usr/bin/env python3
"""{brain}/{skill} — auto-generated run.py (archetype={archetype}).

第一版只实现 simulate 模式:从 stdin/args 拿 inputs,产合理合成数据 JSON。
真实现路径(simulate=False)留 stub:返回 not-implemented + 提示。

输入契约:
  stdin JSON,字段按 SKILL.md 的 inputs 段;simulate 默认 true。
  CLI 兜底:--simulate / 各位置参数。

输出:
  stdout JSON;失败时也写 JSON {{"ok": false, "error": "..."}} 而非裸 traceback。
"""
import json
import sys

ARCHETYPE = "{archetype}"
BRAIN = "{brain}"
SKILL = "{skill}"

{simulate_body}

def real(payload):
    return {{
        "ok": False,
        "error": f"{{BRAIN}}/{{SKILL}} 真模式未实现(archetype={{ARCHETYPE}})。",
        "fallback_hint": "传 simulate=true 跑合成数据通路;或人工补 run.py 接对应工具 CLI。",
    }}

def main():
    # stdin 优先(SkillExecTool 走 stdin)
    payload = {{}}
    if not sys.stdin.isatty():
        try:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                payload = {{}}
        except json.JSONDecodeError:
            payload = {{}}
    if not payload:
        # 简易 CLI 兜底
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--simulate", action="store_true", default=True)
        ap.add_argument("--seed", type=int, default=42)
        args, _ = ap.parse_known_args()
        payload = {{"simulate": args.simulate, "seed": args.seed}}

    simulate_mode = bool(payload.get("simulate", True))
    try:
        out = simulate(payload) if simulate_mode else real(payload)
    except Exception as e:
        out = {{"ok": False, "error": f"run.py 内部错误: {{e!r}}"}}

    if isinstance(out, dict):
        out.setdefault("diagnostics", {{}})
        if isinstance(out["diagnostics"], dict):
            out["diagnostics"].update({{"archetype": ARCHETYPE, "brain": BRAIN, "skill": SKILL}})
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''


def emit_run_py(brain: str, skill: str, archetype: str) -> str:
    body = ARCHETYPE_BODIES.get(archetype, ARCHETYPE_BODIES["generic"]).strip("\n")
    return _RUN_PY_TEMPLATE.format(
        brain=brain, skill=skill, archetype=archetype, simulate_body=body,
    )


def main() -> int:
    written = 0
    skipped = 0
    arche_counts: dict[str, int] = {}
    for md in sorted(ROOT.rglob("*/skills/workflows/*/SKILL.md")):
        if md.name.startswith("._"):
            continue
        run_py = md.parent / "run.py"
        if run_py in SKIP or (run_py.is_file() and run_py.stat().st_size > 200):
            skipped += 1
            continue
        # brains/<brain>/skills/workflows/<skill>/SKILL.md
        parts = md.relative_to(ROOT).parts
        brain = parts[0]
        skill = parts[-2]
        text = _read(md)
        archetype = detect_archetype(brain, skill, text)
        arche_counts[archetype] = arche_counts.get(archetype, 0) + 1
        run_py.write_text(emit_run_py(brain, skill, archetype), encoding="utf-8")
        run_py.chmod(0o755)
        written += 1
    print(f"[done] written={written}  skipped={skipped}")
    print("archetype 分布:")
    for a in sorted(arche_counts, key=arche_counts.get, reverse=True):
        print(f"  {a}: {arche_counts[a]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
