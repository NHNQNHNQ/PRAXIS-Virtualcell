"""确定性重生 golden_compounds.csv(可一键从训练 parquet 重建、可审计)。

用法(从仓库根):
    .venv/bin/python -m \
        praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.build_golden_compounds

取样规则(确定性,固定排序):
  - 候选为 27 个经典抗菌药(硬编码 name→SMILES;结构是公开事实,不算编数据)。
    覆盖氟喹诺酮/青霉素/头孢/磺胺/大环内酯/硝基呋喃/恶唑烷酮/碳青霉烯/单环β-内酰胺/
    四环素/苯并异噁唑/抗结核 等经典类别。
  - **每条候选 build 时经可执行分子式核对**(`_canonical_checked`:RDKit CalcMolFormula 与
    `KNOWN_FORMULA[name]`(该药已知真实分子式,公开事实)逐条 assert 相等,不一致即 raise 停)。
    这道核对当初逮到手打错的利福平/万古霉素/克林霉素/头孢曲松/美罗培南/卡那霉素/多西环素/
    莫西沙星等复杂天然产物/半合成大环骨架(分子式对不上→结构画错),一律不收入本表;现在
    它进了仓库作可执行守卫(build_golden 每次都跑),防止把结构画错的化合物当"公开事实"
    硬编进 golden——以后谁加药画错结构会被当场拦。
  - SMILES 用 RDKit canonical(`Chem.MolToSmiles(Chem.MolFromSmiles(s))`)规范化,
    与训练 parquet(`escherichia_coli_mic_clean.parquet`,已验证其 smiles 列本身即
    RDKit canonical 形式)同口径,按**精确 canonical SMILES 字符串匹配**取真实 MIC:
      - 匹配到 → label_source="chembl_train"、mic_ug_ml=训练集真实值、in_training=true、
        doi_or_source=训练 parquet 相对路径。
      - 匹配不到(且本脚本作者无可靠独立文献值)→ label_source="none"、mic_ug_ml 留空、
        in_training=false、doi_or_source 留空 —— **诚实排除评分,绝不编 MIC**。
  - 环丙沙星(锚点,T1B 面值合理性哨兵)必须在候选表中,且预期匹配到低 MIC 真实值。
  - 行按 name 字母序排序(固定排序,不依赖 dict 迭代顺序)。

局限(诚实标注):候选覆盖以"结构简单、分子式我能高置信度手工核对正确"为筛选标准,
系统性偏向小分子经典抗菌药;复杂天然产物(糖肽/氨基糖苷/利福霉素/大环内酯环系细节)
因手工 SMILES 出错风险高,本轮保守不纳入,宁缺毋编。

红线:纯确定性(固定排序 + 精确匹配,不模糊/不近似)。重跑字节一致(浮点 MIC 直接
取自训练 parquet 的原始值,不做额外舍入)。
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

# 仓库根(本文件 parents:[0]=validation [1]=science_v2 [2]=workflows [3]=mdr_gnb
# [4]=praxis_virtualcell [5]=仓库根;与 build_golden_sir.py 同口径,实测核对)。
_REPO_ROOT = Path(__file__).resolve().parents[5]
DATA = _REPO_ROOT / "data" / "mdr_gnb"
OUT = DATA / "golden" / "golden_compounds.csv"
_TRAIN_PARQUET = DATA / "raw" / "compound_activity" / "escherichia_coli_mic_clean.parquet"
# 从 _TRAIN_PARQUET 派生相对路径(防两处硬编码漂移;golden 的 doi_or_source 写这个)。
_TRAIN_PARQUET_REL = str(_TRAIN_PARQUET.relative_to(_REPO_ROOT))

# 候选:name → 硬编码 SMILES(结构是公开事实,不算编数据;每条已经 RDKit 分子式与该药
# 已知真实分子式手工核对一致,见模块docstring)。
CANDIDATES: dict[str, str] = {
    # 氟喹诺酮
    "ciprofloxacin": "OC(=O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O",  # 锚点
    "levofloxacin": "C[C@@H]1COc2c(N3CCN(C)CC3)c(F)cc3c(=O)c(C(=O)O)cn1c23",
    "norfloxacin": "CCn1cc(C(=O)O)c(=O)c2cc(F)c(N3CCNCC3)cc21",
    "ofloxacin": "CC1COc2c(N3CCN(C)CC3)c(F)cc3c(=O)c(C(=O)O)cn1c23",
    "nalidixic_acid": "CCn1cc(C(=O)O)c(=O)c2ccc(C)nc21",
    # 青霉素类
    "ampicillin": "CC1(C)S[C@@H]2[C@H](NC(=O)[C@H](N)c3ccccc3)C(=O)N2[C@H]1C(=O)O",
    "amoxicillin": "CC1(C)S[C@@H]2[C@H](NC(=O)[C@H](N)c3ccc(O)cc3)C(=O)N2[C@H]1C(=O)O",
    "penicillin_g": "CC1(C)S[C@@H]2[C@H](NC(=O)Cc3ccccc3)C(=O)N2[C@H]1C(=O)O",
    "oxacillin": "Cc1onc(-c2ccccc2)c1C(=O)N[C@@H]1C(=O)N2C(C(=O)O)C(C)(C)S[C@@H]12",
    # 头孢菌素(一代,结构简单)
    "cephalexin": "CC1=C(C(=O)O)N2C(=O)[C@@H](NC(=O)[C@H](N)c3ccccc3)[C@H]2SC1",
    # 碳青霉烯 / 单环β-内酰胺
    "imipenem": "CC(O)[C@@H]1[C@H]2CC(=C(N2C1=O)C(=O)O)SCC/N=C\\N",
    "aztreonam": "CC1C(NC(=O)C(=NOC(C)(C)C(=O)O)c2csc(N)n2)C(=O)N1S(=O)(=O)O",
    # 磺胺类 + 甲氧苄啶(叶酸通路)
    "sulfamethoxazole": "Cc1cc(NS(=O)(=O)c2ccc(N)cc2)no1",
    "sulfadiazine": "Nc1ccc(cc1)S(=O)(=O)Nc1ncccn1",
    "sulfisoxazole": "CC1=C(C)ON=C1NS(=O)(=O)c1ccc(N)cc1",
    "sulfacetamide": "CC(=O)Nc1ccc(S(N)(=O)=O)cc1",
    # 甲氧苄啶:真实结构(3,4,5-三甲氧基苄基-2,4-二氨基嘧啶,C14H18N4O3)。
    # 注:与任务环境说明里给的锚点 SMILES 不同——那条经分子式核对(C14H18N4O3 少 2 个 O)
    # 结构有误,故本表改用经核对无误的真实结构(仍是公开事实,不算编数据),已在报告中说明。
    "trimethoprim": "COc1cc(CC2=CN=C(N)N=C2N)cc(OC)c1OC",
    # 大环内酯 / 硝基呋喃 / 恶唑烷酮 / 硝基咪唑 / 四环素 / 抗结核 / 氯霉素 / 磷霉素 / 砜类
    "erythromycin": ("CC[C@H]1OC(=O)[C@H](C)[C@@H](O[C@H]2C[C@@](C)(OC)[C@@H](O)[C@H](C)O2)"
                      "[C@H](C)[C@@H](O[C@@H]2O[C@H](C)C[C@H](N(C)C)[C@H]2O)[C@](C)(O)C[C@@H](C)"
                      "C(=O)[C@H](C)[C@@H](O)[C@]1(C)O"),
    "nitrofurantoin": "O=C1CN(/N=C/c2ccc([N+](=O)[O-])o2)C(=O)N1",
    "furazolidone": "O=C1OCCN1/N=C/c1ccc([N+](=O)[O-])o1",
    "linezolid": "CC(=O)NC[C@H]1CN(c2ccc(N3CCOCC3)c(F)c2)C(=O)O1",
    "metronidazole": "Cc1ncc([N+](=O)[O-])n1CCO",
    "tetracycline": ("CN(C)[C@H]1C(=O)C(C(N)=O)=C(O)[C@@]2(O)C(=O)C3=C(O)c4c(O)cccc4"
                      "[C@@](C)(O)[C@H]3C[C@@H]12"),
    "isoniazid": "NNC(=O)c1ccncc1",
    "chloramphenicol": "O=C(NC(CO)C(O)c1ccc([N+](=O)[O-])cc1)C(Cl)Cl",
    "fosfomycin": "C[C@H]1O[C@H]1P(=O)(O)O",
    "dapsone": "Nc1ccc(S(=O)(=O)c2ccc(N)cc2)cc1",
}

_ANCHOR = "ciprofloxacin"

# 每个候选的已知真实分子式(公开事实)——build 时 assert RDKit CalcMolFormula 与之逐条相等。
# 这就是当初逮到画错结构(利福平/万古霉素/头孢曲松等)的那道核对,现在进仓库作可执行守卫:
# 以后谁加药 SMILES 画错、分子式对不上真实值,build 会当场 raise 停(防错结构冒充公开事实)。
KNOWN_FORMULA: dict[str, str] = {
    "amoxicillin": "C16H19N3O5S",
    "ampicillin": "C16H19N3O4S",
    "aztreonam": "C13H17N5O8S2",
    "cephalexin": "C16H17N3O4S",
    "chloramphenicol": "C11H12Cl2N2O5",
    "ciprofloxacin": "C17H18FN3O3",
    "dapsone": "C12H12N2O2S",
    "erythromycin": "C37H67NO13",
    "fosfomycin": "C3H7O4P",
    "furazolidone": "C8H7N3O5",
    "imipenem": "C12H17N3O4S",
    "isoniazid": "C6H7N3O",
    "levofloxacin": "C18H20FN3O4",
    "linezolid": "C16H20FN3O4",
    "metronidazole": "C6H9N3O3",
    "nalidixic_acid": "C12H12N2O3",
    "nitrofurantoin": "C8H6N4O5",
    "norfloxacin": "C16H18FN3O3",
    "ofloxacin": "C18H20FN3O4",
    "oxacillin": "C19H19N3O5S",
    "penicillin_g": "C16H18N2O4S",
    "sulfacetamide": "C8H10N2O3S",
    "sulfadiazine": "C10H10N4O2S",
    "sulfamethoxazole": "C10H11N3O3S",
    "sulfisoxazole": "C11H13N3O3S",
    "tetracycline": "C22H24N2O8",
    "trimethoprim": "C14H18N4O3",
}


def _canonical_checked(name: str, smi: str) -> str:
    """解析 SMILES → 分子式核对(与 KNOWN_FORMULA 逐条相等)→ 返回 RDKit canonical。

    分子式对不上=SMILES 画错了(结构非该药),raise 停,绝不让错结构进 golden。
    """
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        raise ValueError(f"{name}: SMILES 解析失败(候选表写错了,应先修正再重跑):{smi}")
    expect = KNOWN_FORMULA.get(name)
    if expect is None:
        raise ValueError(f"{name}: 缺 KNOWN_FORMULA 条目(新加候选须补真实分子式作守卫)")
    got = rdMolDescriptors.CalcMolFormula(mol)
    if got != expect:
        raise ValueError(
            f"{name}: 分子式核对失败 got={got} expect={expect}——SMILES 画错了(结构非该药),"
            f"修正 SMILES 或核对 KNOWN_FORMULA 后再重跑,不得让错结构进 golden")
    return Chem.MolToSmiles(mol)


def build_rows() -> list[dict]:
    """候选 → 按 canonical SMILES 精确匹配训练 parquet 取真实 MIC(确定性,按 name 排序)。"""
    train = pd.read_parquet(_TRAIN_PARQUET)
    train_by_smiles = dict(zip(train["smiles"], train["mic_ug_ml"], strict=True))

    rows: list[dict] = []
    for name in sorted(CANDIDATES):
        can = _canonical_checked(name, CANDIDATES[name])
        if can in train_by_smiles:
            rows.append({
                "name": name,
                "smiles": can,
                "mic_ug_ml": float(train_by_smiles[can]),
                "label_source": "chembl_train",
                "doi_or_source": _TRAIN_PARQUET_REL,
                "in_training": True,
            })
        else:
            rows.append({
                "name": name,
                "smiles": can,
                "mic_ug_ml": "",
                "label_source": "none",
                "doi_or_source": "",
                "in_training": False,
            })
    if _ANCHOR not in CANDIDATES:
        raise ValueError(f"锚点 {_ANCHOR} 缺失于 CANDIDATES")
    return rows


def build(out_path: Path = OUT) -> dict:
    """重生 golden_compounds.csv 并写盘;返回统计。"""
    rows = build_rows()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["name", "smiles", "mic_ug_ml", "label_source", "doi_or_source", "in_training"]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n_matched = sum(1 for r in rows if r["label_source"] == "chembl_train")
    return {
        "path": str(out_path),
        "n_total": len(rows),
        "n_matched": n_matched,
        "n_none": len(rows) - n_matched,
    }


if __name__ == "__main__":
    stat = build()
    print(f"golden_compounds 写入 {stat['path']}")
    print(f"  总 {stat['n_total']} 行:匹配训练集(chembl_train) {stat['n_matched']} / "
          f"未匹配(none,排除评分) {stat['n_none']}")
