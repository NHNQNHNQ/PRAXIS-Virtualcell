"""机制聚合特征(G2R 特征工程,本地,不需组装/53)。

问题:NCBI genotype 串已含 porin 失活(ompK35/ompK36 移码)、靶点突变(gyrA/parC)等机制标记,
但 parse_genotypes 打成**逐等位 one-hot**(mut=ompK36_D135DGD 与 mut=ompK36_GD134ins 是两个特征)→
模型学不到"任何 ompK36 失活→通透性↓"这个可泛化机制,也没有规则法没有的**交互项**。

本模块把逐等位标记**聚合成生物学类别 + 关键交互**(启发式基因族折叠,由 G2R eval 经验判定是否有用):
  - porin 失活:ompK35/ompK36(KP)、ompC/ompF(EC)任一 disruption
  - 碳青霉烯酶类:KPC/NDM/VIM/IMP/OXA-48-like
  - ESBL:CTX-M(可靠)+ curated SHV/TEM-ESBL;AmpC:CMY/DHA/ACT/FOX/MIR/MOX/ACC
  - **交互(规则法没有)**:碳青霉烯耐药通路 = 碳青霉烯酶 OR (ESBL/AmpC ∧ porin 失活);
    3GC 耐药通路 = ESBL OR AmpC

诚实:这是启发式聚合,不是金标准注释;是否提升由 ST 分组 locked per-ST VME 经验判定,不预设有效。
"""
from __future__ import annotations

from .features import parse_genotypes

_CARBAPENEMASE = ("blakpc", "blandm", "blavim", "blaimp", "blaoxa-48", "blaoxa-181",
                  "blaoxa-232", "blaoxa-162", "blaoxa-204", "blaoxa-244", "blaoxa-23", "blaoxa-58")
_ESBL_CTXM = ("blactx-m",)
_ESBL_SHV = ("blashv-2", "blashv-5", "blashv-7", "blashv-12", "blashv-30")   # curated ESBL-SHV(非 SHV-1/11 窄谱)
_ESBL_TEM = ("blatem-3", "blatem-10", "blatem-26", "blatem-52")             # curated ESBL-TEM(非 TEM-1/2)
_AMPC = ("blacmy", "bladha", "blaact", "blafox", "blamir", "blamox", "blaacc", "blacit")
_PORIN = ("ompk35", "ompk36", "ompc", "ompf")   # 孔蛋白基因(带具体突变后缀=失活证据)


def _bases(genotype_str: str) -> list[str]:
    """取基名(小写),含突变后缀(如 ompk36_d135dgd、gyra_s83i)。"""
    out = []
    for t in parse_genotypes(genotype_str):        # gene=… / mut=…
        out.append(t.split("=", 1)[1].lower())
    return out


def mechanism_tokens(genotype_str: str) -> set[str]:
    """从 genotype 串派生机制聚合 token(mech=…)。纯确定性。"""
    bases = _bases(genotype_str)
    def any_pref(prefixes):
        return any(b.startswith(p) for b in bases for p in prefixes)
    carba = any_pref(_CARBAPENEMASE)
    esbl = any_pref(_ESBL_CTXM) or any_pref(_ESBL_SHV) or any_pref(_ESBL_TEM)
    ampc = any_pref(_AMPC)
    # porin 失活:基名含孔蛋白基因且带突变后缀(_ 后有内容 = 具体等位突变/移码)
    porin35 = any(b.startswith("ompk35") and "_" in b for b in bases)
    porin36 = any(b.startswith("ompk36") and "_" in b for b in bases)
    porinEC = any((b.startswith("ompc") or b.startswith("ompf")) and "_" in b for b in bases)
    porin_loss = porin35 or porin36 or porinEC

    feats: set[str] = set()
    if carba: feats.add("mech=carbapenemase")
    if esbl: feats.add("mech=esbl")
    if ampc: feats.add("mech=ampc")
    if porin35: feats.add("mech=porin_ompK35_loss")
    if porin36: feats.add("mech=porin_ompK36_loss")
    if porinEC: feats.add("mech=porin_ompCF_loss")
    if porin_loss: feats.add("mech=porin_loss_any")
    # 关键交互(规则法没有):碳青霉烯耐药通路
    if carba or ((esbl or ampc) and porin_loss):
        feats.add("mech=carbapenem_R_pathway")
    # 3GC 耐药通路
    if esbl or ampc:
        feats.add("mech=3gc_R_pathway")
    return feats


def augmented_features(genotype_str: str) -> set[str]:
    """现有 gene=/mut= 特征 ∪ 机制聚合 token(叠加,不替换)。"""
    return parse_genotypes(genotype_str) | mechanism_tokens(genotype_str)
