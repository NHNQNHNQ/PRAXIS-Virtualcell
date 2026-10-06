# praxis_virtualcell/mdr_gnb/databases/bvbrc_loader.py
"""从 BV-BRC 下载基因组元数据 + AMR 表型。

数据源优先级:
  1) BV-BRC Data API(REST):https://www.bvbrc.org/api/  —— 无需安装 CLI,主用。
  2) p3-CLI(p3-all-genomes / p3-get-genome-features)—— 若已装则可回退。

AMR 表型字段(契约锁定):laboratory_typing_method / measurement / measurement_unit /
measurement_sign / resistant_phenotype;另取 antibiotic / genome_id / genome_name。

只用公开数据(契约 D3)。基因组序列(.fna)按 genome_id 从 BV-BRC FTP 拉取。
"""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .species_registry import get_species

BVBRC_API = "https://www.bvbrc.org/api"
BVBRC_FTP_GENOME = "https://ftp.bvbrc.org/genomes"  # /{genome_id}/{genome_id}.fna

# AMR 表型契约字段
AMR_FIELDS = [
    "genome_id", "genome_name", "antibiotic",
    "laboratory_typing_method", "measurement", "measurement_unit",
    "measurement_sign", "resistant_phenotype",
]
GENOME_FIELDS = [
    "genome_id", "genome_name", "taxon_id", "genome_status",
    "collection_year", "geographic_location", "genome_length", "genome_quality",
]


@dataclass
class BvbrcQueryResult:
    n_genomes: int
    n_amr_rows: int
    genome_meta_path: Path
    amr_path: Path


def _api_query(core: str, filt: str, select: list[str], limit: int = 25000) -> list[dict]:
    """调用 BV-BRC Data API(RQL over HTTP)。core 如 'genome' / 'genome_amr'。

    用 POST + application/rqlquery 以规避超长 URL;分页拉全量。
    """
    url = f"{BVBRC_API}/{core}/"
    headers = {
        "Content-Type": "application/rqlquery+x-www-form-urlencoded",
        "Accept": "application/json",
    }
    out: list[dict] = []
    start = 0
    while True:
        rql = (
            f"{filt}"
            f"&select({','.join(select)})"
            f"&limit({limit},{start})"
        )
        req = urllib.request.Request(
            url, data=rql.encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            batch = json.loads(resp.read().decode("utf-8"))
        if not batch:
            break
        out.extend(batch)
        if len(batch) < limit:
            break
        start += limit
        time.sleep(0.5)  # 温和限速
    return out


def download_species(species_key: str, out_root: Path) -> BvbrcQueryResult:
    """下载单物种的基因组元数据 + AMR 表型到 raw/<dir_name>/。"""
    spec = get_species(species_key)
    raw_dir = out_root / "raw" / spec.dir_name
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 1) 基因组元数据:taxon_lineage_ids 命中 species taxon_id
    genome_filt = f"in(taxon_lineage_ids,({spec.taxon_id}))"
    genomes = _api_query("genome", genome_filt, GENOME_FIELDS)
    genome_meta_path = raw_dir / "genome_meta.tsv"
    _write_tsv(genome_meta_path, GENOME_FIELDS, genomes)

    # 2) AMR 表型:同样按 taxon_lineage_ids 过滤(genome_amr core 带 taxon_lineage_ids)
    amr_filt = f"in(taxon_lineage_ids,({spec.taxon_id}))"
    amr_rows = _api_query("genome_amr", amr_filt, AMR_FIELDS)
    amr_path = raw_dir / "amr_phenotypes.tsv"
    _write_tsv(amr_path, AMR_FIELDS, amr_rows)

    return BvbrcQueryResult(
        n_genomes=len(genomes),
        n_amr_rows=len(amr_rows),
        genome_meta_path=genome_meta_path,
        amr_path=amr_path,
    )


def download_genome_fasta(genome_id: str, dest_dir: Path) -> Path:
    """从 BV-BRC FTP 拉取单个基因组 .fna(供 AMRFinder/RGI/mlst 注释)。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{genome_id}.fna"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    url = f"{BVBRC_FTP_GENOME}/{genome_id}/{genome_id}.fna"
    urllib.request.urlretrieve(url, dest)
    return dest


def _write_tsv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="BV-BRC 单物种下载")
    ap.add_argument("--species", required=True, help="dir_name/学名/别名")
    ap.add_argument("--out-root", required=True, type=Path, help="data/mdr_gnb 根")
    a = ap.parse_args()
    r = download_species(a.species, a.out_root)
    print(f"[OK] {a.species}: genomes={r.n_genomes} amr_rows={r.n_amr_rows}")
    print(f"     {r.genome_meta_path}")
    print(f"     {r.amr_path}")
