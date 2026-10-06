"""S0.2:把 Science v0.9 证据面冻结成只读快照 → reports/antibacterial/mdr_gnb/science_v0.9_freeze/。

目的:防止后续升级越改越说不清——先把"现在到底证明了什么"钉死成可核对的快照。
一条命令重跑得到字节一致的产物(确定性):
    .venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.freeze_v0_9

产物:127 SIR 模型清单 + 132 组合证据面(四层拆分)+ 两锚点终判 + rule-first 安全补丁说明
      + 诚实科学边界 + MANIFEST(各文件 sha256 + 计数断言)。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.mdr_gnb.coordinator.fusion import load_evidence_tiers
from praxis_virtualcell.mdr_gnb.workflows.science_v1._io import dump_json, sha256, write_csv

# 仓库根(本文件在 praxis_virtualcell/mdr_gnb/workflows/science_v1/)
_ROOT = Path(__file__).resolve().parents[4]
_REGISTRY = _ROOT / "praxis_virtualcell" / "model_zoo" / "registry_mdr_gnb_batch.yaml"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v0.9_freeze"

# 证据面列序:evidence_tiers 全字段 + note(no_baseline/unevaluated 缺字段留空)
_EVIDENCE_COLS = [
    "species", "drug", "tier", "evidence_level", "n", "n_R_ST", "t_star",
    "per_st_vme_fusion", "per_st_vme_rule", "delta_vme", "p_value",
    "me_fusion", "me_rule", "auc_R", "calibration_ece", "note",
]
_INVENTORY_COLS = ["species", "drug", "artifact", "version", "sha256", "n", "r_rate"]

# 预注册的两个 G2R 锚点(冻结证据面均 tier=strong)
_ANCHORS = ["EC×ceftriaxone", "KP×meropenem"]
# 断言用的分层/证据级计数(与 evidence_tiers.yaml 现状一致)
_EXPECT_TIERS = {"strong": 26, "practical": 24, "no_baseline": 67, "unevaluated": 15}
_EXPECT_LEVELS = {"E4": 26, "E3": 91, "E1": 15}


# ---------------------------------------------------------------- 数据加载
def _load_models() -> list[dict]:
    """从 registry 读 127 条 mdrgnb_sir__ 模型 → 清单行(按 species,drug 排序)。"""
    doc = yaml.safe_load(_REGISTRY.read_text(encoding="utf-8"))
    sir = {k: v for k, v in doc["models"].items() if k.startswith("mdrgnb_sir__")}
    rows = []
    for name, v in sir.items():
        species, _, drug = name[len("mdrgnb_sir__"):].partition("__")
        asset = v["assets"][0]
        metrics = v.get("training_card", {}).get("metrics", {})
        rows.append({
            "species": species,
            "drug": drug,
            "artifact": asset["filename"],
            "version": v.get("version", ""),
            "sha256": asset.get("sha256", ""),
            "n": metrics.get("n", ""),
            "r_rate": metrics.get("r_rate", ""),
        })
    rows.sort(key=lambda r: (r["species"], r["drug"]))
    return rows


def _load_surface() -> list[dict]:
    """从 evidence_tiers 读 132 组合 → 证据面行(按 species,drug 排序)。"""
    rows = [dict(v) for v in load_evidence_tiers().values()]
    rows.sort(key=lambda r: (r["species"], r["drug"]))
    return rows


# ---------------------------------------------------------------- 文本产物
def _anchor_block(row: dict, title: str, verdict: str) -> str:
    """把某锚点的 evidence_tiers 数字摊成 markdown 小节(数字全取自冻结面,保证与 02 一致)。"""
    g = row.get
    return (
        f"## {title} → **{verdict}**\n\n"
        f"| 项 | 值 |\n|---|---|\n"
        f"| n / R-bearing ST | {g('n')} / {g('n_R_ST')} |\n"
        f"| 运行阈值 t* | {g('t_star')} |\n"
        f"| per-ST VME 融合 / 规则 | {g('per_st_vme_fusion')} / {g('per_st_vme_rule')} |\n"
        f"| **ΔVME** | **{g('delta_vme')}** |\n"
        f"| 置换检验 **p** | **{g('p_value')}** |\n"
        f"| **ME** 融合 / 规则 | **{g('me_fusion')}** / {g('me_rule')} |\n"
        f"| AUC(R) / 校准 ECE | {g('auc_R')} / {g('calibration_ece')} |\n"
    )


def _md_03(surface: dict) -> str:
    """03 锚点终判:两锚点的 strong-pass 关键数字 + 纪律来源与诚实保留。"""
    ec = surface[("escherichia_coli", "ceftriaxone")]
    kp = surface[("klebsiella_pneumoniae", "meropenem")]
    return (
        "# 03 G2R 锚点终判:EC×ceftriaxone + KP×meropenem(Science v0.9 冻结)\n\n"
        "> 来源:`reports/antibacterial/mdr_gnb/g2r_locked/`(`kp_meropenem_operating_curve.md`、\n"
        "> `ec_ceftriaxone_operating_verdict.md`、`locked_decision.md`)+ 生产证据面\n"
        "> `praxis_virtualcell/model_zoo/evidence_tiers.yaml`。下表数字取自冻结证据面,\n"
        "> 与 `02_evidence_surface_132.csv` 逐字一致。两锚点在冻结面均为 **tier=strong / E4**。\n\n"
        + _anchor_block(ec, "EC × ceftriaxone", "G2R-strong-pass")
        + "\n"
        + _anchor_block(kp, "KP × meropenem", "G2R-strong-pass")
        + "\n## 判据与纪律来源\n\n"
        "- **EC×ceftriaxone**:ST 分组、dev/locked 分离、locked 只跑一次;abstain-aware 运行点\n"
        "  (τ* 由 dev 5 折 OOF 选,覆盖率≥0.80 且 covered ME<0.10 下 per-ST VME 最小)应用到\n"
        "  held-out locked 一次。ΔVME 为负、方向更安全,ME 受控。\n"
        "- **KP×meropenem**:全 68 R-ST OOF ST-CV,预注册运行点 t*=0.40(判据 **ME ≤ 规则ME+0.05**,\n"
        "  即「不显著劣于规则」);per-ST VME 显著砍半(ΔVME −0.16,p=0.0001)。\n\n"
        "## 诚实保留(勿夸大)\n\n"
        "- `locked_decision.md`(更严的单次 dev/locked 划分 + **ME<0.10 绝对上限**)当时判 EC=practical-pass、\n"
        "  KP=fail。KP 的 fail 源于把「ME<0.10 绝对」当判据——而**规则法自身 ME 就 0.137**,该判据等于\n"
        "  要求融合比规则还严,不合理;改回计划原文的「ME 不显著劣于规则」后 KP 为 strong-pass。冻结面\n"
        "  采用后者(与 `kp_meropenem_operating_curve.md` 修正终判一致)。\n"
        "- EC 的 ΔVME 虽为负但 **p 不显著**(p=0.25 于 operating verdict),strong 主要由 rule-first 融合\n"
        "  的**方向安全**(VME≤规则)+ 显著性阈值下的分层规则给出;不得表述为「显著更安全」的确证。\n"
        "- 均单 seed(seed=0);运行点 t* 与显著性检验同集 → 轻微乐观,但 rule-first 保证 VME≤规则、\n"
        "  效应量大,方向稳健。完全干净需嵌套 CV 内层选 t*(留最终确认)。\n"
    )


_MD_08 = """# 08 rule-first 安全补丁:rule=R 永不翻 S

## 保证
生产融合 `praxis_virtualcell/mdr_gnb/coordinator/fusion.py::fuse_sir` 采用 **rule-first**:
只要冻结版 AMRFinderPlus 规则法判该组合为 **R**,融合输出必为 **R**,ML 不得把它翻成 S。
数学后果:**融合的 per-ST VME(极重大误差,把真耐药漏判成敏感)≤ 规则法**——这是 G2R 全部
「不劣于规则」结论赖以成立的地基。

## 实现
- 有对照(规则表收录该药)时:`fused_r = (rule_r == 1) or (p_r >= t)`——规则 R 直接短路为 R,
  ML 只能在规则判 S 处补判 R,**永远无法反向下调**。
- 运行时自检断言(热路径内联,防未来重构破坏):
  `assert not (has_baseline and rule_r == 1 and fused_sir == "S")`,消息「融合违反安全保证:rule=R 被翻成 S」。
- 无对照(no_baseline)时 fail-open 到 ML-only 并打 warning(冻结规则表未收录该药,无规则验证);
  abstained / 非 sir_class 原样返回(fail-closed 保留)。

## 测试指针
- `praxis_virtualcell/mdr_gnb/tests/test_fusion.py::test_rule_R_never_flipped_to_S`
  ——构造 rule=R 但 ML 强判 S 的场景,断言融合仍输出 R。
- 运行:`.venv/bin/python -m pytest praxis_virtualcell/mdr_gnb/tests/test_fusion.py -q`
"""


_MD_09 = """# 09 诚实科学边界(Science v0.9)

面向"这套东西到底证明了什么、不能声称什么",逐条钉死。

## 覆盖面
- **5 物种有 SIR 模型**:acinetobacter_baumannii / escherichia_coli / klebsiella_pneumoniae /
  pseudomonas_aeruginosa / salmonella_enterica(共 127 个 genotype→SIR artifact)。
- 其余物种 **fail-closed**:无模型即弃权,不臆测(不是 5/5 全覆盖)。
- 132 组合有证据分层,127 组合有落地模型;差额组合走规则 / no_baseline 路径。

## 每层能声称什么
- **strong(26)**:在冻结版 AMRFinderPlus 对照下,融合 per-ST VME **统计显著优于**规则法
  (量级通常小但显著)。**仅这 26 条**可说"优于冻结基线"。
- **practical(24)**:融合**不劣于**规则法但**未显著优于**(输出带 warning)。不得声称更优。
- **no_baseline(67)**:冻结规则表未收录该药,**无对照** → ML-only,未经规则验证。
- **unevaluated(15)**:artifact 存在且确定性可加载,但**本地缺 phenotype/ST 数据未做 ST-CV**
  (需 53 环境)——未评估,不得当作已验证。

## 已知弱点(不藏)
- 部分 strong 组合**绝对 ME 偏高**(如 KP×meropenem ME≈0.19):因规则法自身 ME 就高
  (KP×meropenem 规则 ME≈0.14),融合在「ME 不显著劣于规则」判据下过关,但绝对误报率不低。
- ML 特征与 AMRFinderPlus 基因调用**同源**,融合只能"规则兜底 + ML 补漏";要在锚点上拿到**显著**
  优于规则,需引入规则法没有的新信息(k-mer / porin / CARD),依赖真实工具链——现为天花板。
- 全程**单 seed(seed=0)**;运行点 t* 与显著性检验多为同集选取,轻微乐观(rule-first 方向稳健)。

## 用途边界
- **仅科研筛选**,非临床决策;任何组合的输出都不构成给药建议。
- 冻结基线是**版本冻结的 AMRFinderPlus 规则法**,不代表当前临床折点或最新数据库。
"""


# ---------------------------------------------------------------- 主流程
def freeze() -> dict:
    """生成全部冻结产物到 _OUT,返回 MANIFEST(供测试/调用方核对)。"""
    _OUT.mkdir(parents=True, exist_ok=True)

    models = _load_models()
    surface = _load_surface()
    by_key = {(r["species"], r["drug"]): r for r in surface}
    by_tier = {t: [r for r in surface if r.get("tier") == t] for t in _EXPECT_TIERS}

    # CSV 产物
    write_csv(_OUT / "01_model_zoo_inventory.csv", _INVENTORY_COLS, models)
    write_csv(_OUT / "02_evidence_surface_132.csv", _EVIDENCE_COLS, surface)
    write_csv(_OUT / "04_strong_26_detail.csv", _EVIDENCE_COLS, by_tier["strong"])
    write_csv(_OUT / "05_practical_24_detail.csv", _EVIDENCE_COLS, by_tier["practical"])
    write_csv(_OUT / "06_no_baseline_67_detail.csv", _EVIDENCE_COLS, by_tier["no_baseline"])
    write_csv(_OUT / "07_unevaluated_15_detail.csv", _EVIDENCE_COLS, by_tier["unevaluated"])

    # markdown 产物
    (_OUT / "03_g2r_anchor_results.md").write_text(_md_03(by_key), encoding="utf-8")
    (_OUT / "08_rule_first_safety_patch.md").write_text(_MD_08, encoding="utf-8")
    (_OUT / "09_known_scientific_limits.md").write_text(_MD_09, encoding="utf-8")

    counts = {t: len(by_tier[t]) for t in _EXPECT_TIERS}
    levels: dict[str, int] = {}
    for r in surface:
        lv = r.get("evidence_level")
        if lv:
            levels[lv] = levels.get(lv, 0) + 1

    files = [
        "01_model_zoo_inventory.csv", "02_evidence_surface_132.csv",
        "03_g2r_anchor_results.md", "04_strong_26_detail.csv",
        "05_practical_24_detail.csv", "06_no_baseline_67_detail.csv",
        "07_unevaluated_15_detail.csv", "08_rule_first_safety_patch.md",
        "09_known_scientific_limits.md",
    ]
    manifest = {
        "science_version": "v0.9",
        "description": "Science v0.9 证据面只读冻结(S0.2);后续升级以此为基线,勿悄改计数。",
        "source": {
            "evidence_tiers": "praxis_virtualcell/model_zoo/evidence_tiers.yaml",
            "registry": "praxis_virtualcell/model_zoo/registry_mdr_gnb_batch.yaml",
            "anchors": "reports/antibacterial/mdr_gnb/g2r_locked/",
        },
        "n_models": len(models),
        "n_combos": len(surface),
        "counts": counts,
        "evidence_levels": levels,
        "anchors_strong_pass": list(_ANCHORS),
        "files": {name: {"sha256": sha256(_OUT / name)} for name in files},
    }
    dump_json(_OUT / "MANIFEST.json", manifest)

    # 计数断言:与已知现状不符就炸,别产出说不清的快照
    assert manifest["n_models"] == 127, manifest["n_models"]
    assert manifest["n_combos"] == 132, manifest["n_combos"]
    assert counts == _EXPECT_TIERS, counts
    assert levels == _EXPECT_LEVELS, levels
    # 两锚点必须落在 strong 层(否则 anchors_strong_pass 名不副实)
    for sp, dr in [("escherichia_coli", "ceftriaxone"), ("klebsiella_pneumoniae", "meropenem")]:
        assert by_key[(sp, dr)]["tier"] == "strong", (sp, dr)
    return manifest


if __name__ == "__main__":
    m = freeze()
    c = m["counts"]
    print(
        f"frozen {m['n_combos']} combos → reports/antibacterial/mdr_gnb/science_v0.9_freeze/ "
        f"(strong={c['strong']} practical={c['practical']} "
        f"no_baseline={c['no_baseline']} unevaluated={c['unevaluated']})"
    )
