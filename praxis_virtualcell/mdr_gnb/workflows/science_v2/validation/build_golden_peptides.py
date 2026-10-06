"""确定性重生 golden_peptides.csv(可一键从训练 parquet 重建、可审计)。

用法(从仓库根):
    .venv/bin/python -m \
        praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.build_golden_peptides

取样规则(确定性,固定排序;仿 build_golden_compounds.py 同风格):
  - 候选为 28 条经典抗菌肽(硬编码 name→sequence;序列是公开事实,不算编数据)。
    覆盖两栖类皮肤肽(Magainin/Aurein/Brevinin/Ranalexin/Temporin/Caerin/Gaegurin)、
    蜂毒肽(Melittin)、人源肽(LL-37/HNP-1)、蛙皮素衍生合成肽(Pexiganan/MSI-78)、
    昆虫/甲壳类(Indolicidin/Protegrin-1/Polyphemusin-1)、鱼类(Piscidin-1)、
    蛙脑啡肽衍生(Buforin-2)等经典类别。
  - **每条候选 build 时经序列合法性守卫**(`_validate_sequence`:序列只含 20 种标准氨基酸
    字母 ACDEFGHIKLMNPQRSTVWY,不一致即 raise 停),防乱码/非标准残基进 golden。
  - 按**序列精确字符串匹配**训练 parquet
    (`escherichia_coli_peptide_mic_clean.parquet`,DBAASP EC 子集)取真实 MIC(µM):
      - 匹配到 → label_source="dbaasp_train"、mic_um=训练集真实值、in_training=true、
        doi_or_source=训练 parquet 相对路径。
      - 匹配不到(且本脚本作者无可靠独立文献值可信匹配到同一物种同一测量条件)→
        label_source="none"、mic_um 留空、in_training=false、doi_or_source 留空 ——
        **诚实排除评分,绝不编 MIC**。
  - Magainin-2(锚点,T1C 面值合理性哨兵)必须在候选表中,且预期匹配到真实 MIC。
  - 行按 name 字母序排序(固定排序,不依赖 dict 迭代顺序)。

局限(诚实标注):候选覆盖以"序列是公开发表的经典 AMP、我能高置信度确认残基序列"为
筛选标准;含二硫键的肽(Protegrin-1/HNP-1/Tachyplesin-1 等)按线性一级序列收录,
不建模二硫键连接性(与训练 parquet/部署模型特征化口径一致——后者同样只吃线性序列)。

红线:纯确定性(固定排序 + 精确匹配,不模糊/不近似)。重跑字节一致(浮点 MIC 直接
取自训练 parquet 的原始值,不做额外舍入)。
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

# 仓库根(本文件 parents:[0]=validation [1]=science_v2 [2]=workflows [3]=mdr_gnb
# [4]=praxis_virtualcell [5]=仓库根;与 build_golden_compounds.py 同口径,实测核对)。
_REPO_ROOT = Path(__file__).resolve().parents[5]
DATA = _REPO_ROOT / "data" / "mdr_gnb"
OUT = DATA / "golden" / "golden_peptides.csv"
_TRAIN_PARQUET = DATA / "raw" / "peptide_activity" / "escherichia_coli_peptide_mic_clean.parquet"
# 从 _TRAIN_PARQUET 派生相对路径(防两处硬编码漂移;golden 的 doi_or_source 写这个)。
_TRAIN_PARQUET_REL = str(_TRAIN_PARQUET.relative_to(_REPO_ROOT))

# 20 种标准氨基酸单字母代码(序列合法性守卫用)。
_STANDARD_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")

# 候选:name → 硬编码序列(公开发表的经典 AMP 一级序列,不算编数据)。
CANDIDATES: dict[str, str] = {
    # 两栖类皮肤肽
    "magainin_2": "GIGKFLHSAKKFGKAFVGEIMNS",  # 锚点
    "magainin_1": "GIGKFLHSAGKFGKAFVGEIMKS",
    "aurein_1_2": "GLFDIIKKIAESF",
    "aurein_2_2": "GLFDIVKKVVGALGSL",
    "brevinin_1": "FLPLLAGLAANFLPKIFCKITRKC",
    "ranalexin": "FLGGLIKIVPAMICAVTKKC",
    "temporin_a": "FLPLIGRVLSGIL",
    "temporin_b": "LLPIVGNLLKSLL",
    "caerin_1_1": "GLLSVLGSVAKHVLPHVVPVIAEHL",
    "esculentin_1a": "GIFSKLAGKKIKNLLISGLKNVGKEVGMDVVRTGIDIAGCKIKGEC",
    # 蛙皮素衍生合成肽 / 蜂毒肽
    "pexiganan_msi78": "GIGKFLKKAKKFGKAFVKILKK",
    "melittin": "GIGAVLKVLTTGLPALISWIKRKRQQ",
    # 人源肽
    "ll_37": "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES",
    "hnp_1": "ACYCRIPACIAGERRYGTCIYQGRLWAFCC",
    "lactoferricin_b": "FKCRRWQWRMKKLGAPSITCVRRAF",
    "histatin_5": "DSHAKRHHGYKRKFHEKHHSHRGY",
    # 昆虫 / 甲壳类 / 哺乳动物中性粒细胞肽
    "cecropin_a": "KWKLFKKIEKVGQNIRDGIIKAGPAVAVVGQATQIAK",
    "cecropin_b": "KWKVFKKIEKMGRNIRNGIVKAGPAIAVLGEAKAL",
    "indolicidin": "ILPWKWPWWPWRR",
    "protegrin_1": "RGGRLCYCRRRFCVCVGR",
    "polyphemusin_1": "RRWCFRVCYRGFCYRKCR",
    "tachyplesin_1": "KWCFRVCYRGICYRRCR",
    "bactenecin": "RLCRIVVIRVCR",
    # 鱼类 / 蛙脑啡肽衍生
    "piscidin_1": "FFHHIFRGIVHVGKTIHRLVTG",
    "buforin_2": "TRSSRAGLQFPVGRVHRLLRK",
    "gaegurin_5": "FLGALFKVASKVLPSVFCAITKKC",
    # 其它经典两栖/合成肽
    "dermaseptin_b2": "GLWSKIKEVGKEAAKAAAKAAGKAALGAVSEAV",
    "ovispirin_1": "KNLRRIIRKIIHIIKKYG",
}

_ANCHOR = "magainin_2"


def _validate_sequence(name: str, seq: str) -> str:
    """序列合法性守卫:只含 20 种标准氨基酸字母,不一致即 raise 停(防乱码进 golden)。"""
    bad = sorted(set(seq) - _STANDARD_AA)
    if not seq or bad:
        raise ValueError(
            f"{name}: 序列含非标准氨基酸字符 {bad}(候选表写错了,应先修正再重跑):{seq}")
    return seq


def build_rows() -> list[dict]:
    """候选 → 按精确序列匹配训练 parquet 取真实 MIC(确定性,按 name 排序)。"""
    train = pd.read_parquet(_TRAIN_PARQUET)
    train_by_seq = dict(zip(train["sequence"], train["mic_um"], strict=True))

    rows: list[dict] = []
    for name in sorted(CANDIDATES):
        seq = _validate_sequence(name, CANDIDATES[name])
        if seq in train_by_seq:
            rows.append({
                "name": name,
                "sequence": seq,
                "mic_um": float(train_by_seq[seq]),
                "label_source": "dbaasp_train",
                "doi_or_source": _TRAIN_PARQUET_REL,
                "in_training": True,
            })
        else:
            rows.append({
                "name": name,
                "sequence": seq,
                "mic_um": "",
                "label_source": "none",
                "doi_or_source": "",
                "in_training": False,
            })
    if _ANCHOR not in CANDIDATES:
        raise ValueError(f"锚点 {_ANCHOR} 缺失于 CANDIDATES")
    return rows


def build(out_path: Path = OUT) -> dict:
    """重生 golden_peptides.csv 并写盘;返回统计。"""
    rows = build_rows()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["name", "sequence", "mic_um", "label_source", "doi_or_source", "in_training"]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n_matched = sum(1 for r in rows if r["label_source"] == "dbaasp_train")
    return {
        "path": str(out_path),
        "n_total": len(rows),
        "n_matched": n_matched,
        "n_none": len(rows) - n_matched,
    }


if __name__ == "__main__":
    stat = build()
    print(f"golden_peptides 写入 {stat['path']}")
    print(f"  总 {stat['n_total']} 行:匹配训练集(dbaasp_train) {stat['n_matched']} / "
          f"未匹配(none,排除评分) {stat['n_none']}")
