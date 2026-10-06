"""S3.2 富集:从 NCBI BioSample efetch 采样年份(collection_date),缓存供 temporal holdout。

现实约束(探针已确认):NCBI Pathogen Detection 数据 vintage 为 2011-2016,无 ≥2020 样本;
故 temporal holdout 只能在窗口内切(非现代 ≥2022)。~部分 isolate 无 collection_date(尤其 KP),
无年份的诚实丢弃(temporal 只用有年份子集)。

缓存:data/mdr_gnb/raw/<species>/biosample_year.tsv(biosample_acc \t year)。幂等(跳过已缓存)。
用法:python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.enrich_biosample --species escherichia_coli
"""
from __future__ import annotations

import argparse
import csv
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path("data/mdr_gnb")
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
BATCH = 200
SLEEP = 0.4                      # 无 API key 限 3/sec,留余量
_YEAR = re.compile(r'attribute_name="collection[_ ]date"[^>]*>([^<]+)<')
_Y4 = re.compile(r"(19|20)\d{2}")


def _biosamples_for(species: str, drugs: set[str] | None) -> dict[str, str]:
    """读物种 phenotype,返回 {biosample_acc: 空}(去重)。drugs 给定则只取这些药的 isolate。"""
    tsv = DATA / "raw" / species / "ncbi_amr_phenotypes.tsv"
    out: dict[str, str] = {}
    with tsv.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if drugs and r.get("antibiotic") not in drugs:
                continue
            acc = (r.get("ncbi_biosample_acc") or "").strip()
            if acc:
                out[acc] = ""
    return out


def _load_cache(species: str) -> dict[str, str]:
    p = DATA / "raw" / species / "biosample_year.tsv"
    cache: dict[str, str] = {}
    if p.exists():
        with p.open() as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 2:
                    cache[parts[0]] = parts[1]
    return cache


def _write_cache(species: str, cache: dict[str, str]) -> Path:
    p = DATA / "raw" / species / "biosample_year.tsv"
    with p.open("w") as f:
        for a in sorted(cache):
            f.write(f"{a}\t{cache[a]}\n")
    return p


def _efetch_block(batch: list[str]) -> dict[str, int]:
    """一批 efetch biosample full,按 <BioSample accession=> 切块对齐 collection_date 年份。"""
    out: dict[str, int] = {}
    data = urllib.parse.urlencode({"db": "biosample", "id": ",".join(batch),
                                   "rettype": "full"}).encode()
    xml = None
    for attempt in range(2):
        try:
            xml = urllib.request.urlopen(EFETCH, data=data, timeout=90).read().decode("utf-8", "ignore")
            break
        except Exception:
            time.sleep(2.0)
    if xml is None:
        return out
    for block in re.split(r"<BioSample\b", xml)[1:]:
        acc_m = re.search(r'accession="([^"]+)"', block)
        date_m = _YEAR.search(block)
        if acc_m and date_m:
            y = _Y4.search(date_m.group(1))
            if y:
                out[acc_m.group(1)] = int(y.group())
    return out


def enrich(species: str, drugs: set[str] | None, batch: int = BATCH) -> dict:
    """增量 + 可续:每批抓完即写缓存;已缓存(含 NA)跳过。中断可重跑续抓。"""
    accs = _biosamples_for(species, drugs)
    cache = _load_cache(species)
    todo = [a for a in accs if a not in cache]
    print(f"{species}: 目标 biosample {len(accs)}(已缓存 {len(accs)-len(todo)},待抓 {len(todo)})", flush=True)
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        got = _efetch_block(chunk)
        for a in chunk:
            cache[a] = str(got.get(a, "NA"))       # 无年份标 NA,避免重复抓
        _write_cache(species, cache)               # 增量落盘(每批)
        have = sum(1 for v in cache.values() if v not in ("NA", ""))
        print(f"  [{min(i+batch,len(todo))}/{len(todo)}] 累计有年份 {have}", flush=True)
        time.sleep(SLEEP)
    p = _write_cache(species, cache)
    have = sum(1 for v in cache.values() if v not in ("NA", ""))
    print(f"  → 缓存 {len(cache)},有年份 {have}({have*100//max(1,len(cache))}%)→ {p}", flush=True)
    return {"species": species, "n_biosample": len(cache), "n_with_year": have}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="S3.2 BioSample 采样年份富集(缓存)")
    ap.add_argument("--species", default="escherichia_coli", help="逗号分隔物种")
    ap.add_argument("--drugs", default="", help="逗号分隔药物(空=全部;建议只富集 anchor 药省时)")
    args = ap.parse_args()
    drugs = {d.strip() for d in args.drugs.split(",") if d.strip()} or None
    for sp in [s.strip() for s in args.species.split(",") if s.strip()]:
        enrich(sp, drugs)
