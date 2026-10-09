"""给 SKILL.md 没'## 输出契约'段的补一个 archetype 合理默认,
   对 json 解析失败的(trailing comma/comment)原地清洗后回写。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.uplift._skills import all_brain_names, find_skill_dirs
from scripts.uplift.parse_skill_outputs import (
    _BARE_ELLIPSIS_RE,
    _DICT_ELLIPSIS_RE,
    _LINE_COMMENT_RE,
    _LIST_ELLIPSIS_RE,
    _SECTION_RE,
    _TRAILING_COMMA_RE,
    parse_skill_md,
)

ARCHETYPE_DEFAULTS: dict[str, dict] = {
    "docking": {
        "skill_id": "",
        "receptor": "",
        "ligand": "",
        "best_affinity": 0.0,
        "poses": [{"rank": 1, "affinity_kcal_per_mol": 0.0, "pose_path": ""}],
        "runtime_sec": 0.0,
        "diagnostics": {},
    },
    "structure_predict": {
        "skill_id": "",
        "sequence": "",
        "model_path": "",
        "plddt_mean": 0.0,
        "ptm": 0.0,
        "n_residues": 0,
        "runtime_sec": 0.0,
        "diagnostics": {},
    },
    "mutation_scan": {
        "skill_id": "",
        "wt_score": 0.0,
        "scan_csv": "",
        "top_mutations": [{"position": 1, "from_aa": "A", "to_aa": "V", "ddg": 0.0}],
        "diagnostics": {},
    },
    "msa_conservation": {
        "skill_id": "",
        "msa_path": "",
        "n_sequences": 0,
        "conservation_csv": "",
        "diagnostics": {},
    },
    "omics_scrna": {
        "skill_id": "",
        "matrix_path": "",
        "n_cells_post_qc": 0,
        "cluster_sizes": {},
        "marker_genes_per_cluster": {},
        "umap_png": "",
        "diagnostics": {},
    },
    "microbiome_pipeline": {
        "skill_id": "",
        "n_samples": 0,
        "taxonomy_table": "",
        "diversity_metrics": {"shannon": 0.0, "observed_otus": 0},
        "diagnostics": {},
    },
    "drug": {
        "skill_id": "",
        "n_compounds": 0,
        "best_score": 0.0,
        "compound_csv": "",
        "diagnostics": {},
    },
    "pharma": {
        "skill_id": "",
        "n_compounds": 0,
        "admet_csv": "",
        "diagnostics": {},
    },
    "cryo": {
        "skill_id": "",
        "n_particles": 0,
        "resolution_a": 0.0,
        "map_path": "",
        "diagnostics": {},
    },
    "crispr": {
        "skill_id": "",
        "n_guides": 0,
        "guides_csv": "",
        "best_guide": {"seq": "", "cfd_score": 0.0, "mit_score": 0.0},
        "diagnostics": {},
    },
    "mhc_epitope": {
        "skill_id": "",
        "n_epitopes": 0,
        "epitopes_csv": "",
        "diagnostics": {},
    },
    "fetcher": {
        "skill_id": "",
        "fetched": [],
        "diagnostics": {},
    },
    "generic": {
        "ok": True,
        "skill_id": "",
        "result": {},
        "diagnostics": {},
    },
}


def default_schema_for_archetype(archetype: str, *, brain: str, skill: str) -> dict:
    base = ARCHETYPE_DEFAULTS.get(archetype, ARCHETYPE_DEFAULTS["generic"])
    out = json.loads(json.dumps(base))  # deep copy
    out["skill_id"] = skill
    out.setdefault("diagnostics", {})["brain"] = brain
    out["diagnostics"]["archetype"] = archetype
    return out


def insert_outputs_section(path: Path, schema: dict) -> dict:
    txt = path.read_text(encoding="utf-8", errors="replace")
    if _SECTION_RE.search(txt):
        return {"path": str(path), "action": "skipped"}
    json_body = json.dumps(schema, indent=2, ensure_ascii=False)
    block = f"\n\n## 输出契约\n\n```json\n{json_body}\n```\n"
    new_txt = txt.rstrip() + block
    path.write_text(new_txt, encoding="utf-8")
    return {"path": str(path), "action": "inserted"}


def clean_existing_json_section(path: Path) -> dict:
    """若 outputs 段存在但 json 块解析失败,清洗 trailing-comma/comment 后回写。"""
    info = parse_skill_md(path)
    if info["verdict"] != "PARSE_ERR":
        return {"path": str(path), "action": "no-op", "verdict": info["verdict"]}
    txt = path.read_text(encoding="utf-8", errors="replace")
    m = _SECTION_RE.search(txt)
    if not m:
        return {"path": str(path), "action": "no-op"}
    body = m.group(1)
    cleaned = _LINE_COMMENT_RE.sub("", body)
    cleaned = _LIST_ELLIPSIS_RE.sub("[]", cleaned)
    cleaned = _DICT_ELLIPSIS_RE.sub("{}", cleaned)
    cleaned = _BARE_ELLIPSIS_RE.sub(": null", cleaned)
    cleaned = _TRAILING_COMMA_RE.sub(r"\1", cleaned)
    try:
        json.loads(cleaned)
    except Exception:
        return {"path": str(path), "action": "still-broken"}
    new_txt = txt[: m.start(1)] + cleaned.strip() + "\n" + txt[m.end(1):]
    path.write_text(new_txt, encoding="utf-8")
    return {"path": str(path), "action": "cleaned"}


def replace_broken_outputs_with_default(path: Path, schema: dict) -> dict:
    """对 still-broken 的 SKILL.md:整段替换 outputs json 块为 archetype default。"""
    info = parse_skill_md(path)
    if info["verdict"] == "OK":
        return {"path": str(path), "action": "no-op", "verdict": "OK"}
    txt = path.read_text(encoding="utf-8", errors="replace")
    m = _SECTION_RE.search(txt)
    if not m:
        return {"path": str(path), "action": "no-op", "verdict": "MISSING_SECTION"}
    json_body = json.dumps(schema, indent=2, ensure_ascii=False)
    new_txt = txt[: m.start(1)] + json_body + "\n" + txt[m.end(1):]
    path.write_text(new_txt, encoding="utf-8")
    return {"path": str(path), "action": "replaced-with-default"}


def _archetype_of(run_py: Path) -> str:
    if not run_py.is_file():
        return "generic"
    txt = run_py.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'ARCHETYPE\s*=\s*"([^"]+)"', txt)
    return m.group(1) if m else "generic"


def fix_one(skill_dir: Path) -> list[dict]:
    md = skill_dir / "SKILL.md"
    run_py = skill_dir / "run.py"
    if not md.is_file():
        return [{"path": str(skill_dir), "action": "no-skill-md"}]
    results = []
    archetype = _archetype_of(run_py)
    # brain 名:skill_dir 路径里第二段
    parts = skill_dir.parts
    try:
        brain = parts[parts.index("brains") + 1]
    except (ValueError, IndexError):
        brain = "?"
    skill = skill_dir.name
    schema = default_schema_for_archetype(archetype, brain=brain, skill=skill)

    r1 = clean_existing_json_section(md)
    results.append(r1)
    if r1.get("action") == "still-broken":
        # 救不了,整段替换为 archetype default
        results.append(replace_broken_outputs_with_default(md, schema))
    results.append(insert_outputs_section(md, schema))
    return results


def fix_brain(brain: str, root: Path = Path("brains")) -> list[dict]:
    out = []
    for sd in find_skill_dirs(brain, root):
        out.extend(fix_one(sd))
    return out


if __name__ == "__main__":
    import sys
    brain = sys.argv[1] if len(sys.argv) > 1 else None
    if brain:
        rows = fix_brain(brain)
    else:
        rows = []
        for bn in all_brain_names():
            rows.extend(fix_brain(bn))
    by_a = {}
    for r in rows:
        by_a[r.get("action")] = by_a.get(r.get("action"), 0) + 1
    print(json.dumps({"total": len(rows), "by_action": by_a}, indent=2, ensure_ascii=False))
