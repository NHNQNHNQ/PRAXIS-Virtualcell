# praxis_virtualcell/mdr_gnb/databases/ncbi_loader.py
"""从 NCBI Pathogen Detection 下载 基因型(AMRFinderPlus)+ 表型(S/I/R)+ 基因组链接。

数据源(已从 53 实测可达,HTTP 200):
  https://ftp.ncbi.nlm.nih.gov/pathogen/Results/<Organism>/<PDGxxxx.N>/Metadata/<PDGxxxx.N>.metadata.tsv
每行含(按表头动态定位列,不硬编码列号):
  asm_acc(GCA/GCF assembly)、biosample_acc(SAMN)、target_acc(PDT)、scientific_name、
  AST_phenotypes(逗号分隔 drug=SIR)、AMR_genotypes(AMRFinderPlus 基因型)。

**重要限制**:此源只有 S/I/R,无定量 MIC(实测 grep 无数字/mg-L)。故用于 genotype→SIR 分类;
定量 MIC 训练仍依赖 BV-BRC genome_amr 的 measurement 列。输出字段与 bvbrc_loader.AMR_FIELDS
前 8 列对齐(measurement/sign/unit 留空、laboratory_typing_method=SIR),便于两库 concat。

只用公开数据(契约 D3)。属级混合目录(Klebsiella/Salmonella)按 scientific_name 前缀过滤到目标种。
"""
from __future__ import annotations

import csv
import re
import urllib.request
from pathlib import Path

from .species_registry import get_species

NCBI_PD = "https://ftp.ncbi.nlm.nih.gov/pathogen/Results"
NCBI_GENOMES = "https://ftp.ncbi.nlm.nih.gov/genomes/all"

# species_registry.dir_name -> NCBI Pathogen Detection organism 目录名(实测存在)
# 固有耐药:S. maltophilia 与 Morganella 在 NCBI PD 有独立组(2026-07-04 实测补);
# P. mirabilis 在 NCBI PD 无独立 organism 组(实测无 Proteus),G1 诚实标注无数据。
NCBI_ORGANISM: dict[str, str] = {
    "escherichia_coli": "Escherichia_coli_Shigella",
    "klebsiella_pneumoniae": "Klebsiella",
    "acinetobacter_baumannii": "Acinetobacter",
    "pseudomonas_aeruginosa": "Pseudomonas_aeruginosa",
    "salmonella_enterica": "Salmonella",
    "enterobacter_cloacae": "Enterobacter_cloacae",
    "serratia_marcescens": "Serratia",
    "stenotrophomonas_maltophilia": "Stenotrophomonas_maltophilia",
    "morganella_morganii": "Morganella",
}

# 与 bvbrc_loader.AMR_FIELDS 保持一致(便于两库产物 concat)
AMR_FIELDS = [
    "genome_id", "genome_name", "antibiotic",
    "laboratory_typing_method", "measurement", "measurement_unit",
    "measurement_sign", "resistant_phenotype",
]
EXTRA_FIELDS = ["ncbi_target_acc", "ncbi_biosample_acc", "ncbi_amr_genotypes"]
OUTPUT_FIELDS = AMR_FIELDS + EXTRA_FIELDS

_KEEP_SIR = {"S", "I", "R"}
_PDG_RE = re.compile(r"PDG\d+\.\d+")


def _pdg_sort_key(pdg: str) -> tuple[int, int]:
    """PDG 版本按数值排序(不能字典序:PDG...012.2454 比 .836 新,但字典序反了)。"""
    m = re.match(r"PDG0*(\d+)\.(\d+)", pdg)
    if not m:
        return (-1, -1)
    return (int(m.group(1)), int(m.group(2)))


def flatten_metadata_rows(header, rows, scientific_prefix: str | None) -> list[dict]:
    """把 NCBI metadata 行按 AST_phenotypes 展平为契约对齐的 (isolate×drug) 记录。

    - header/rows:表头与数据行(list[str]);按列名定位,容忍列缺失/顺序不同。
    - scientific_prefix:目标种学名前缀(属级混合目录用于过滤),None 则不过滤。
    - 丢弃 AST 为 NULL/空、以及 ND/DD/NS 等非 S/I/R 判定。
    """
    idx = {h: i for i, h in enumerate(header)}
    i_ast = idx.get("AST_phenotypes")
    if i_ast is None:
        return []  # 无表型列,无可展平
    i_sci = idx.get("scientific_name")
    i_asm = idx.get("asm_acc")
    i_bios = idx.get("biosample_acc")
    i_tgt = idx.get("target_acc")
    i_geno = idx.get("AMR_genotypes")

    out: list[dict] = []
    for row in rows:
        if i_ast >= len(row):
            continue
        sci = row[i_sci] if (i_sci is not None and i_sci < len(row)) else ""
        if scientific_prefix and not sci.lower().startswith(scientific_prefix.lower()):
            continue
        ast = (row[i_ast] or "").strip()
        if not ast or ast.upper() == "NULL":
            continue
        asm = row[i_asm] if (i_asm is not None and i_asm < len(row)) else ""
        bios = row[i_bios] if (i_bios is not None and i_bios < len(row)) else ""
        tgt = row[i_tgt] if (i_tgt is not None and i_tgt < len(row)) else ""
        geno = row[i_geno] if (i_geno is not None and i_geno < len(row)) else ""
        for tok in ast.split(","):
            tok = tok.strip()
            if "=" not in tok:
                continue
            drug, sir = tok.split("=", 1)
            sir = sir.strip().upper()
            if sir not in _KEEP_SIR:
                continue
            out.append({
                "genome_id": asm,
                "genome_name": sci,
                "antibiotic": drug.strip().lower(),
                "laboratory_typing_method": "SIR",
                "measurement": "",
                "measurement_unit": "",
                "measurement_sign": "",
                "resistant_phenotype": sir,
                "ncbi_target_acc": tgt,
                "ncbi_biosample_acc": bios,
                "ncbi_amr_genotypes": geno,
            })
    return out


def _list_dir(url: str) -> list[str]:
    """拉取 FTP over HTTPS 的目录 HTML,返回 href 名列表。"""
    req = urllib.request.Request(url, headers={"User-Agent": "PRAXIS-MDR-GNB"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        html = resp.read().decode("utf-8", "replace")
    return re.findall(r'href="([^"?/][^"]*)"', html)


def resolve_latest_snapshot(organism: str) -> tuple[str, str]:
    """列 Results/<organism>/,取最新且含 Metadata/ 的 PDG 快照。

    返回 (pdg_version, metadata_url)。无 latest/ 软链,按版本号排序取尾;
    最新快照若缺 Metadata/ 则回退上一版本。
    """
    base = f"{NCBI_PD}/{organism}"
    pdgs = sorted(
        {m for name in _list_dir(f"{base}/") for m in _PDG_RE.findall(name)},
        key=_pdg_sort_key,
    )
    if not pdgs:
        raise RuntimeError(f"NCBI PD 未找到 {organism} 的 PDG 快照:{base}/")
    for pdg in reversed(pdgs):  # 从最新往旧回退
        meta_url = f"{base}/{pdg}/Metadata/{pdg}.metadata.tsv"
        try:
            req = urllib.request.Request(
                meta_url, method="HEAD", headers={"User-Agent": "PRAXIS-MDR-GNB"}
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.status == 200:
                    return pdg, meta_url
        except Exception:
            continue
    raise RuntimeError(f"{organism} 所有 PDG 快照均无可用 Metadata/{organism}")


def download_species(species_key: str, out_root: Path) -> dict:
    """下载单物种 NCBI metadata,展平为 SIR 表型 → raw/<dir_name>/ncbi_amr_phenotypes.tsv。

    大文件流式逐行解析(csv.reader over 文件句柄),不整表读内存。
    返回 {pdg, n_meta_rows, n_amr_rows, meta_path, amr_path}。
    """
    spec = get_species(species_key)
    organism = NCBI_ORGANISM.get(spec.dir_name)
    if organism is None:
        raise KeyError(f"{spec.dir_name} 无 NCBI organism 映射(NCBI PD 可能无此组)")

    raw_dir = out_root / "raw" / spec.dir_name
    raw_dir.mkdir(parents=True, exist_ok=True)
    pdg, meta_url = resolve_latest_snapshot(organism)

    # 整份 metadata.tsv 落盘(禁止管道 head,避免 curl(23)/内存爆)
    meta_path = raw_dir / "ncbi_metadata.tsv"
    urllib.request.urlretrieve(meta_url, meta_path)

    # 流式解析 + 展平 + 按 scientific_name 过滤到目标种
    amr_path = raw_dir / "ncbi_amr_phenotypes.tsv"
    n_meta = 0
    n_amr = 0
    with meta_path.open(encoding="utf-8", errors="replace", newline="") as fh, \
            amr_path.open("w", encoding="utf-8", newline="") as out_fh:
        reader = csv.reader(fh, delimiter="\t")
        header = next(reader, None)
        w = csv.DictWriter(out_fh, fieldnames=OUTPUT_FIELDS, delimiter="\t",
                           extrasaction="ignore")
        w.writeheader()
        if header is None:
            return {"pdg": pdg, "n_meta_rows": 0, "n_amr_rows": 0,
                    "meta_path": meta_path, "amr_path": amr_path}
        for row in reader:
            n_meta += 1
            for rec in flatten_metadata_rows(header, [row], spec.scientific_name):
                w.writerow(rec)
                n_amr += 1
    return {"pdg": pdg, "n_meta_rows": n_meta, "n_amr_rows": n_amr,
            "meta_path": meta_path, "amr_path": amr_path}


def extract_unique_asm_accs(amr_tsv_path: Path) -> list[str]:
    """从 ncbi_amr_phenotypes.tsv 提取唯一 genome_id(即 asm_acc),保持首次出现顺序。

    供 ST 分型编排:仅需对每个不同菌株下一次 FASTA、跑一次 mlst。
    """
    seen: dict[str, None] = {}
    with amr_tsv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            acc = (row.get("genome_id") or "").strip()
            if acc:
                seen[acc] = None
    return list(seen.keys())


def download_genome_fasta(asm_acc: str, dest_dir: Path) -> Path:
    """由 assembly accession(GCA/GCF_XXXXXXXXX.v)拆三段路径下 .fna。

    如 GCA_000417105.1 -> genomes/all/GCA/000/417/105/GCA_000417105.1_*/*.fna
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    # 已存在则先跳过(断点续下时避免对已下文件白做一次 _list_dir HTTP)
    dest = dest_dir / f"{asm_acc}.fna.gz"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    m = re.match(r"(GC[AF])_(\d{3})(\d{3})(\d{3})", asm_acc)
    if not m:
        raise ValueError(f"非法 assembly accession:{asm_acc!r}")
    prefix, a, b, c = m.groups()
    base = f"{NCBI_GENOMES}/{prefix}/{a}/{b}/{c}/"
    # 该目录下有版本化子目录 <asm_acc>_<name>/,取匹配 asm_acc 的
    subdirs = [d for d in _list_dir(base) if d.startswith(asm_acc)]
    if not subdirs:
        raise RuntimeError(f"{asm_acc} 在 {base} 无匹配 assembly 子目录")
    sub = subdirs[0].rstrip("/")
    fna_url = f"{base}{sub}/{sub}_genomic.fna.gz"
    urllib.request.urlretrieve(fna_url, dest)
    return dest


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="NCBI Pathogen Detection 单物种下载(genotype→SIR)")
    ap.add_argument("--species", required=True, help="dir_name/学名/别名")
    ap.add_argument("--out-root", required=True, type=Path, help="data/mdr_gnb 根")
    a = ap.parse_args()
    r = download_species(a.species, a.out_root)
    print(f"[OK] {a.species}: pdg={r['pdg']} meta_rows={r['n_meta_rows']} amr_rows={r['n_amr_rows']}")
    print(f"     {r['amr_path']}")
