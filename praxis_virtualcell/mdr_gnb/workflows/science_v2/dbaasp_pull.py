"""B5-肽 数据门:从 DBAASP 拉抗菌肽序列 + 靶菌 MIC → 清洗集(仿 chembl_pull 的做法)。

DBAASP v3 REST(探针 2026-07-11 确认):
  列表  https://dbaasp.org/peptides?complexity=monomer&offset=&limit=  → {totalCount, data:[{id,...}]}
  详情  https://dbaasp.org/peptides/{id}  → {sequence, targetActivities:[{targetSpecies.name,
        activityMeasureGroup.name=="MIC", activity(float), unit.name(µM/µg/ml)}]}
  探针:24397 monomer,采样外推 ~4879 条 EC-MIC(数值)肽。

清洗(诚实):只留 targetSpecies==<species> 且 MIC 且 activity 数值;单位统一到 µM(µg/ml 经肽 MW
折算 µM = µg/ml / MW * 1000);同序列取中位去噪;序列须全大写标准 AA、长度 [5,60]。
log10(MIC_µM)。**无网/拉取中时清洗集不存在 → baseline gate fail(不伪造)。**

用法:.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.dbaasp_pull --species "Escherichia coli"
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
_OUT = _ROOT / "data" / "mdr_gnb" / "raw" / "peptide_activity"

# 氨基酸平均残基质量(Da),用于 µg/ml → µM 折算(肽 MW = Σ残基 + 水 18.02)
_AA_MASS = {
    "A": 71.08, "R": 156.19, "N": 114.10, "D": 115.09, "C": 103.14, "E": 129.12,
    "Q": 128.13, "G": 57.05, "H": 137.14, "I": 113.16, "L": 113.16, "K": 128.17,
    "M": 131.19, "F": 147.18, "P": 97.12, "S": 87.08, "T": 101.10, "W": 186.21,
    "Y": 163.18, "V": 99.13,
}
_WATER = 18.02
_CANON = frozenset(_AA_MASS)


def peptide_mw(seq: str) -> float:
    """肽平均分子量(Da)= Σ残基质量 + 一分子水。序列须全标准 AA。"""
    return sum(_AA_MASS[c] for c in seq) + _WATER


def _get(url: str, timeout: float = 25.0, retries: int = 3) -> dict:
    """GET JSON,3× 退避重试(仿 chembl_pull:24k 详情长任务抗网络抖动)。全失败才抛。"""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:                          # noqa: BLE001 - 重试兜网络抖动
            last = e
            time.sleep(0.5 * (attempt + 1))
    raise last


def _to_um(activity: float, unit: str, seq: str) -> float | None:
    """MIC 单位统一到 µM。摩尔单位纯因子换算(更确定);质量单位经肽 MW 折算;未知单位丢弃(不臆测)。"""
    u = (unit or "").lower().replace("μ", "µ").strip()
    a = float(activity)
    # 摩尔浓度:纯因子(比质量折算更确定,不依赖 MW)
    if u in ("µm", "um"):
        return a
    if u in ("nm",):
        return a / 1000.0
    if u in ("mm",):
        return a * 1000.0
    # 质量浓度:µM = µg/ml / MW * 1000(µg/ml == mg/l)
    mw = peptide_mw(seq)
    if u in ("µg/ml", "ug/ml", "mg/l"):
        return a / mw * 1000.0
    if u in ("mg/ml", "µg/l", "ug/l", "ng/ml"):          # mg/ml=1e3µg/ml;µg/l=1e-3µg/ml;ng/ml=1e-3µg/ml
        factor = {"mg/ml": 1e3, "µg/l": 1e-3, "ug/l": 1e-3, "ng/ml": 1e-3}[u]
        return a * factor / mw * 1000.0
    return None                                          # 未知单位不折算(诚实)


def clean_records(details, species: str):
    """从详情列表抽 (sequence, mic_um);过滤非标准序列/非 MIC/未知单位/非数值。返回 [(seq, mic_um)]。"""
    out = []
    for d in details:
        seq = (d.get("sequence") or "").strip().upper()
        if not seq or len(seq) < 5 or len(seq) > 60 or any(c not in _CANON for c in seq):
            continue
        for ta in (d.get("targetActivities") or []):
            if (ta.get("targetSpecies") or {}).get("name") != species:
                continue
            if (ta.get("activityMeasureGroup") or {}).get("name") != "MIC":
                continue
            act = ta.get("activity")
            if not isinstance(act, (int, float)) or act <= 0:
                continue
            mic = _to_um(float(act), (ta.get("unit") or {}).get("name"), seq)
            if mic is None or mic <= 0:
                continue
            out.append((seq, mic))
    return out


def pull(species: str, *, page_size: int = 200, sleep: float = 0.05,
         out_dir: Path = _OUT, limit_pages: int | None = None) -> Path:
    """分页拉 monomer + 详情 → 清洗 → 同序列中位 log10-MIC(µM)→ parquet。返回落盘路径。"""
    import numpy as np
    import pandas as pd

    out_dir.mkdir(parents=True, exist_ok=True)
    lst = _get(f"https://dbaasp.org/peptides?complexity=monomer&offset=0&limit=1")
    total = int(lst.get("totalCount", 0))
    print(f"DBAASP monomer 总数 {total};逐页拉详情(page={page_size})…", flush=True)

    records: list[tuple[str, float]] = []
    offset, page = 0, 0
    while offset < total:
        try:
            ids = [d["id"] for d in _get(
                f"https://dbaasp.org/peptides?complexity=monomer&offset={offset}&limit={page_size}"
            ).get("data", [])]
        except Exception as e:                          # 列表页 3× 重试仍失败:跳过本页不中断全任务
            print(f"  page@{offset} 列表拉取失败({e!r}),跳过", flush=True)
            offset += page_size
            page += 1
            continue
        details = []
        for pid in ids:
            try:
                details.append(_get(f"https://dbaasp.org/peptides/{pid}"))
            except Exception:
                pass                                    # 单条失败诚实跳过,不中断
            time.sleep(sleep)
        records.extend(clean_records(details, species))
        offset += page_size
        page += 1
        print(f"  page {page}: 累计 {len(records)} 条 {species} MIC", flush=True)
        if limit_pages and page >= limit_pages:
            break

    if not records:
        raise RuntimeError(f"未拉到任何 {species} 肽 MIC(检查物种名/网络);不产空清洗集")
    df = pd.DataFrame(records, columns=["sequence", "mic_um"])
    # 同序列取中位去噪
    agg = df.groupby("sequence")["mic_um"].agg(["median", "count"]).reset_index()
    agg.columns = ["sequence", "mic_um", "n_meas"]
    agg["log10_mic"] = np.log10(agg["mic_um"].astype(float))
    safe = species.lower().replace(" ", "_")
    path = out_dir / f"{safe}_peptide_mic_clean.parquet"
    agg.to_parquet(path, index=False)
    print(f"清洗集 {len(agg)} 唯一序列 → {path}", flush=True)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="B5-肽 DBAASP 拉取(序列→靶菌 MIC)")
    ap.add_argument("--species", default="Escherichia coli")
    ap.add_argument("--limit-pages", type=int, default=None, help="限页(调试用)")
    args = ap.parse_args()
    pull(args.species, limit_pages=args.limit_pages)
