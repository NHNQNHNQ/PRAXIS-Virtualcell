"""每 species×drug 数据漏斗表(NCBI-only 适配,G1)。

决策变更(2026-07-03):项目 NCBI-only。NCBI Pathogen Detection 只有 S/I/R、无定量 MIC,
故不再有 has_quantitative_mic / breakpoint_harmonized 级。逐级 N(单调不增):
  total                       该物种全部 SIR 记录(全药,展示药物覆盖占比)
  has_ast                     指定药、有表型字符串的记录
  valid_sir                   表型 ∈ {S,I,R}(排除 ND/DD/NS/空等非判定)
  dedup_isolate_drug          去重 isolate×drug(同株同药多次提交取一)
  declonalized                按 ST 去克隆(唯一 ST;unknown ST 每株单列不合并)
  single_species_single_drug  最终建模候选集(= declonalized)

契约 FunnelRow:stage/n_records/n_strains/note。产出 reports/funnel/<species>_<drug>.md,
数据不足在 note 与 Go/No-Go 里诚实标注(不假装能建模)。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# 漏斗阶段(锁定顺序)
STAGES = [
    "total",
    "has_ast",
    "valid_sir",
    "dedup_isolate_drug",
    "declonalized",
    "single_species_single_drug",
]

# 视作有效 S/I/R 判定的表型串(单字母 + BV-BRC 全称;排除 ND/DD/NS/空)
_VALID_SIR = {
    "S", "I", "R",
    "SUSCEPTIBLE", "INTERMEDIATE", "RESISTANT",
}


@dataclass
class FunnelRow:
    """漏斗一级。"""

    stage: str
    n_records: int
    n_strains: int
    note: str = ""


def _is_valid_sir(phenotype) -> bool:
    """表型是否为有效 S/I/R 判定(排除 NCBI 的 ND/DD/NS 等非判定)。"""
    return str(phenotype).strip().upper() in _VALID_SIR


def _unique_strains(genome_ids, st_map) -> int:
    """按 ST 去克隆计唯一株数。

    - 空/NULL genome_id 无 assembly 标识,不计为株(NCBI 有大量无 asm_acc 的 SIR 行);
    - 未定型(unknown ST)按 genome_id 去重计株(不按行膨胀,否则同株多药会虚高);
    - 已定型按 ST 去克隆合并。
    """
    seen_st: set[str] = set()
    unknown_gids: set[str] = set()
    for gid in genome_ids:
        g = (gid or "").strip()
        if not g or g.upper() == "NULL":
            continue  # 无 assembly 标识,不计为株
        st = st_map.get(g)
        if st is None or st == "" or str(st).lower() == "unknown":
            unknown_gids.add(g)
        else:
            seen_st.add(st)
    return len(seen_st) + len(unknown_gids)


def build_funnel(
    species_dir: str,
    drug: str,
    amr_rows: list[dict],
    st_map: dict[str, str],
) -> list[FunnelRow]:
    """构建单 species×drug 漏斗(NCBI genotype→SIR 现实)。

    amr_rows 为该物种全部 SIR 记录(会按 drug 过滤);st_map: genome_id(asm_acc)->ST。
    """
    # total:该物种所有 SIR 记录(全药),用于展示药物覆盖占比
    total_records = len(amr_rows)

    # has_ast:指定药、有表型字符串的记录
    drug_rows = [r for r in amr_rows if r.get("antibiotic", "") == drug]
    has_ast = [r for r in drug_rows if str(r.get("resistant_phenotype", "")).strip()]

    # valid_sir:表型 ∈ {S,I,R}(排除 ND/DD/NS/空)
    valid = [r for r in has_ast if _is_valid_sir(r.get("resistant_phenotype", ""))]

    # dedup_isolate_drug:去重 isolate×drug(drug 已固定,即按 genome_id 去重,保留首条)
    seen_ids: set[str] = set()
    dedup: list[dict] = []
    for r in valid:
        gid = (r.get("genome_id") or "").strip()
        if gid and gid not in seen_ids:
            seen_ids.add(gid)
            dedup.append(r)
    dedup_ids = [r.get("genome_id", "") for r in dedup]

    # declonalized:按 ST 去克隆
    n_declon = _unique_strains(dedup_ids, st_map)
    # unknown ST 计数(供 note 诚实标注去克隆完备性)
    n_unknown = sum(
        1 for g in dedup_ids
        if not st_map.get(g) or str(st_map[g]).lower() == "unknown"
    )
    unknown_note = (
        f"其中 {n_unknown} 株无 ST(单列不合并)" if n_unknown else "全部有 ST"
    )

    rows = [
        FunnelRow(
            "total", total_records,
            _unique_strains([r.get("genome_id", "") for r in amr_rows], st_map),
            note=f"{species_dir} 全部 SIR 记录(全药)",
        ),
        FunnelRow(
            "has_ast", len(has_ast),
            _unique_strains([r.get("genome_id", "") for r in has_ast], st_map),
            note=f"药={drug} 有表型字符串",
        ),
        FunnelRow(
            "valid_sir", len(valid),
            _unique_strains([r.get("genome_id", "") for r in valid], st_map),
            note="表型 ∈ {S,I,R}(ND/DD/NS/空已弃)",
        ),
        FunnelRow(
            "dedup_isolate_drug", len(dedup),
            _unique_strains(dedup_ids, st_map),
            note="同株同药多次提交去重(按 asm_acc)",
        ),
        FunnelRow(
            "declonalized", n_declon, n_declon,
            note=f"按 ST 去克隆;{unknown_note}",
        ),
        FunnelRow(
            "single_species_single_drug", n_declon, n_declon,
            note="最终建模候选集(单物种单药)",
        ),
    ]
    return rows


def write_funnel_md(
    species_dir: str,
    drug: str,
    rows: list[FunnelRow],
    out_root: Path,
    min_strains_for_model: int = 100,
) -> Path:
    """写 reports/funnel/<species>_<drug>.md;数据不足给诚实降级建议(NCBI 走 SIR 分类)。"""
    out_dir = out_root / "reports" / "funnel"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_dir}_{drug}.md"

    final = rows[-1]
    if final.n_strains >= min_strains_for_model:
        verdict = (
            f"**可进入 genotype→SIR 分类建模候选**"
            f"(去克隆株数 {final.n_strains} ≥ {min_strains_for_model})"
        )
    elif final.n_strains >= 20:
        verdict = (
            f"**样本偏少,SIR 分类需谨慎(小样本/迁移学习)**"
            f"(去克隆株数 {final.n_strains} < {min_strains_for_model})"
        )
    else:
        verdict = (
            f"**数据不足,弃权/仅规则法**"
            f"(去克隆株数 {final.n_strains} < 20;诚实标注不假装建模)"
        )

    lines = [
        f"# 漏斗表:{species_dir} × {drug}",
        "",
        "> 仅科研筛选,非临床用药决策。数据源:NCBI Pathogen Detection(genotype→SIR,无定量 MIC)。",
        "",
        "| 阶段 | 记录数 n_records | 去克隆株数 n_strains | 说明 |",
        "| --- | ---: | ---: | --- |",
    ]
    for r in rows:
        lines.append(f"| {r.stage} | {r.n_records} | {r.n_strains} | {r.note} |")
    lines += ["", "## Go/No-Go 判定", "", verdict, ""]
    # ST 完备性 caveat:declonalized 按 ST 去克隆,unknown 株单列不合并。
    # 按 unknown 占比分级:高占比=分型可能未完成(临时值,需重生成);低占比=分型已完成、
    # 少量 mlst 真未定型(novel/不完整等位谱),declon 为真实值。
    declon = next((r for r in rows if r.stage == "declonalized"), None)
    dedup = next((r for r in rows if r.stage == "dedup_isolate_drug"), None)
    if declon is not None and dedup is not None:
        import re as _re
        m = _re.search(r"(\d+)\s*株无 ST", declon.note)
        n_unknown = int(m.group(1)) if m else 0
        frac = (n_unknown / dedup.n_records) if dedup.n_records else 0.0
        if frac >= 0.5:
            lines += [
                f"> ⚠️ {n_unknown}/{dedup.n_records} 株未定型(占 {frac:.0%}):**ST 分型可能未完成**,"
                "declonalized 为临时值(unknown 单列不折叠克隆,此列虚高);全量 mlst 完成后需重生成本报告。",
                "",
            ]
        elif n_unknown > 0:
            lines += [
                f"> 注:{n_unknown}/{dedup.n_records} 株经 mlst 未定型(novel/不完整等位谱),"
                "按 unknown 单列不折叠克隆;declonalized 为真实值(ST 分型已完成)。",
                "",
            ]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
