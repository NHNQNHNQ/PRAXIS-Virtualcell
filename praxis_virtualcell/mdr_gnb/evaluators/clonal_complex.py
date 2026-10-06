"""克隆复合体(clonal complex, CC)派生:从 7 位点等位谱用 goeBURST 单连锁(SLV)聚 CC。

Phase 17 修两处「克隆群泄漏」病灶的共同前置:ST 不是独立谱系单元,克隆复合体
(如 KP 的 CC258={ST258,ST11,ST340,ST437,ST512})成员彼此是单/双位点变异体,带
不同 ST 标签。按精确 ST 分组会把一个 CC 切成多组 → 切分跨折泄漏 + 聚合伪重复。

本模块从等位谱推 ST→CC:两 ST 共享 ≥(位点数-max_diff) 个「都非 0 且相等」的等位号
即视为同一 CC 的近邻(max_diff=1 = SLV 单位点变异体)。单连锁并查集把 SLV 邻接关系
的连通分量聚成一个 CC。

🔴 确定性红线:CC id **必须**确定性,不能用并查集的任意 rep(rep 依赖 union 顺序)。
CC id = 该连通分量里**最小 ST 号**对应的规范名(如分量含 ST11/258/340/437/512 → CC11)。
同一 profiles 输入(无论 dict 顺序)→ 逐字相同的 {ST: CC_id} 输出。
"""
from __future__ import annotations

import re
from pathlib import Path

_ALLELE_RE = re.compile(r"\((\d+)\)")  # 从 locus(NN) 抽 NN;缺失/多等位/无括号 → 无匹配
_NO_NUMBER = 2**63  # 无数字 ST 的排序哨兵(实际数据 ST 恒为数字)


def parse_mlst_alleles(path: str | Path) -> dict[str, tuple[int, ...]]:
    """读 mlst 完整输出 tsv,返回 {ST: 7 位点等位号 tuple}。

    行格式:FILE<tab>SCHEME<tab>ST<tab>locus1(allele1)<tab>...,例如
        data/.../GCA_000401195.1.fna\tklebsiella\t258\tgapA(3)\tinfB(3)\t...\ttonB(79)

    - 每个 locus(NN) 用正则 `\\((\\d+)\\)` 抽 NN;缺失/多等位(~/?/逗号/无括号)→ 该位点记 0
      (0 不参与相邻判定)。
    - ST 列 `258` → key `ST258`;ST 非数字/为 `-`/`0` → 跳过该行。
    - 同一 ST 取首见等位谱(后续重复行不覆盖)。
    """
    path = Path(path)
    profiles: dict[str, tuple[int, ...]] = {}
    if not path.exists():
        return profiles
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 4:  # 至少 FILE、SCHEME、ST、1 个位点
            continue
        st_raw = cols[2].strip()
        if not st_raw.isdigit() or st_raw == "0":  # 非数字 / '-' / '' / '0' → 跳过
            continue
        key = f"ST{st_raw}"
        if key in profiles:  # 同 ST 取首见
            continue
        alleles = []
        for col in cols[3:]:
            m = _ALLELE_RE.search(col)
            alleles.append(int(m.group(1)) if m else 0)
        profiles[key] = tuple(alleles)
    return profiles


def _st_number(st: str) -> int:
    """抽 ST 标签里的首个数字串用于规范化排序;无数字返回哨兵。"""
    m = re.search(r"(\d+)", st)
    return int(m.group(1)) if m else _NO_NUMBER


def derive_cc_slv(profiles: dict[str, tuple[int, ...]], max_diff: int = 1) -> dict[str, str]:
    """goeBURST 单连锁并查集派生 ST→CC。

    两 ST 共享 ≥(位点数-max_diff) 个「都非 0 且相等」的等位号 → 同一 CC 的近邻。
    max_diff=1 即 SLV(单位点变异体);单连锁 = 邻接关系的连通分量聚成一个 CC。

    CC id = 连通分量内最小 ST 号的规范名(确定性,不用并查集 rep)。单例 ST → 自成一 CC。
    """
    sts = list(profiles)
    if not sts:
        return {}
    # 位点数取全体最长(标准 7 位点 MLST 恒等长);zip 比较自然截到较短者。
    n_loci = max(len(profiles[s]) for s in sts)
    threshold = n_loci - max_diff

    parent = {s: s for s in sts}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # 路径压缩
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra  # rep 依赖顺序 → 后续按最小 ST 号规范化,不直接用 rep

    for i in range(len(sts)):
        pa = profiles[sts[i]]
        for j in range(i + 1, len(sts)):
            pb = profiles[sts[j]]
            shared = sum(
                1 for a, b in zip(pa, pb, strict=False) if a != 0 and b != 0 and a == b
            )
            if shared >= threshold:
                union(sts[i], sts[j])

    # 按连通分量归组(分量本身与 union 顺序无关),再取最小 ST 号做确定性规范名。
    comps: dict[str, list[str]] = {}
    for s in sts:
        comps.setdefault(find(s), []).append(s)

    cc_map: dict[str, str] = {}
    for members in comps.values():
        canon = min(members, key=lambda s: (_st_number(s), s))
        num = _st_number(canon)
        cc_id = f"CC{num}" if num != _NO_NUMBER else f"CC{canon}"
        for m in members:
            cc_map[m] = cc_id
    return cc_map


def load_cc_map(species: str, data_root: str | Path) -> dict[str, str]:
    """便捷封装:读 raw/<species>/mlst_raw.tsv → parse → derive → {ST: CC_id}。

    文件不存在 → 返回 {}(fail-soft,调用方回退按 ST 分组)。
    """
    path = Path(data_root) / "raw" / species / "mlst_raw.tsv"
    if not path.exists():
        return {}
    return derive_cc_slv(parse_mlst_alleles(path))
