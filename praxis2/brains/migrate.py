"""brains 三层结构契约迁移(总纲 §6② + v1 §2.1 忠实,D3 不增不改语义)。

12 学科 slug 对齐真盘 `/Volumes/T7/PRAXIS-Brains/_brains/` lowercase 目录
(B.3 校准,reviewer M5 C1+C2:Synth v1.0.2 carry,真盘无目录;总纲 §6②
已回写 13→12;旧 TitleCase 入口经 resolve_agent 内部 .lower() 标准化兼容)。
真实 brains_snapshot 不在本机:M5 落结构契约 + 最小 fixture 大脑;
migrate_dir_tree 是运维拿到 brains_snapshot 后灌入的纯函数(非占位)。"""

from pathlib import Path

from praxis2.brains.store import BrainDoc

# B.3+ v2.0.2 单源:真盘 13 个 lowercase 目录(Synth v1.0.2 carry 落地 → 13);
# 4 源(本表 + _SLUG_CASE_HINTS + loader._SLUG_KEYWORDS + server.app._AGENT_META)
# 对齐由 tests/test_correctness_slug_canonical.py 不变式锁住。
# Synth 大脑真盘路径:/home/zkyd/data1/mzy/PRAXIS-Brains/_brains/synth/,
# 已 rsync 到 brains/synth/(22 cases / 44 rules / 13 workflows / prompts 完整)。
DISCIPLINE_SLUGS: list[str] = [
    "cell", "crispr", "cryo", "dock", "drug", "enzyme",
    "immuno", "md", "microbiome", "omics", "pharma", "protein", "synth",
]

# v1 §2.1 固定结构对应的四合并接口 kind
THREE_LAYER_DIRS = ("cases", "neg_cases", "rules", "skills")

# 各学科 cases/c1 嵌入关键词,供 BM25-lite 检索命中(T11 端到端需;
# 与 T8 _SLUG_KEYWORDS 同口径,系 T5↔T11 跨任务一致性校准,见 plan T11 carry)。
# B.3 校准:key lowercase 对齐 DISCIPLINE_SLUGS;模块顶层定义便于不变式 import。
_SLUG_CASE_HINTS: dict[str, str] = {
    "cell":       "细胞 培养 凋亡 标准流程",
    "crispr":     "CRISPR cas9 基因编辑 脱靶 标准流程",
    "cryo":       "冷冻电镜 cryo 三维重构 颗粒 标准流程",
    "dock":       "对接 docking 结合位点 标准流程",
    "drug":       "药物 成药 先导 标准流程",
    "enzyme":     "酶 enzyme 催化 米氏 动力学 标准流程",
    "immuno":     "免疫 抗体 抗原 标准流程",
    "md":         "分子动力学 MD 模拟 force forcefield 标准流程",
    "microbiome": "微生物 菌群 16S 标准流程",
    "omics":      "组学 转录组 测序 标准流程",
    "pharma":     "药代 PK 代谢 标准流程",
    "protein":    "蛋白 折叠 结构预测 标准流程",
    "synth":      "合成 异源表达 BGC 生物传感器 cell-free FBA 标准流程",
}


def build_fixture_brain(slug: str) -> list[BrainDoc]:
    """最小 fixture 大脑(M5 测试用;真实学科内容批量灌入是运维步骤)。
    _common 纯规则(S11);其余 slug 含四类最小文档。
    cases/c1 文本含学科关键词(BM25-lite 可检索,T11 端到端检索需)。"""
    if slug == "_common":
        return [
            BrainDoc(slug, "rules", "rmcp",
                     "RMCP 硬规则:行动前必检索 → 反向过滤 → 计划 → 执行;"
                     "显式列依据;DOI 强制;API only,禁 web scraping"),
            BrainDoc(slug, "rules", "safety",
                     "安全规则:不杜撰 DOI/引用;2-of-3 工具一致性"),
        ]
    # B.3:hint key lowercase;旧 TitleCase 入口(如测试传 "Cryo")用 .lower()
    # 兼容查表,fixture text 仍保留原 slug 字符串以便老测试断言文字命中。
    hint = _SLUG_CASE_HINTS.get(slug.lower(), "标准流程与依据")
    return [
        BrainDoc(slug, "cases", "c1",
                 f"{slug} 领域正例:{hint}(doi:10.0/{slug})"),
        BrainDoc(slug, "neg_cases", "NEG-1",
                 f"{slug} 反例:常见误用与排除方法"),
        BrainDoc(slug, "rules", "r1",
                 f"{slug} 学科硬规则:方法学约束"),
        BrainDoc(slug, "skills", "wf1",
                 f"{slug} 技能 wf1:可复用工作流"),
    ]


def migrate_dir_tree(root: Path, slug: str) -> list[BrainDoc]:
    """从 v1 单 agent 目录树(v1 §2.1/§10)抽出四类文档为 BrainDoc。
    运维步骤:拿到真实 brains_snapshot 后对每个 slug 跑本函数 → put_brain_doc
    灌入 store。正例排除 _ 前缀(v1 Brain.cases() 语义)。
    skills 取 workflows/<dir>/SKILL.md 正文;无 SKILL.md 时退化为目录名。
    三层目录→kind 契约即下方显式分支(THREE_LAYER_DIRS 为权威键集,
    不另设映射函数避免静默语义分叉)。"""
    root = Path(root)
    out: list[BrainDoc] = []
    for kind in ("cases", "neg_cases", "rules"):
        if kind == "cases":
            base, pat = root / "memory" / "cases", "*.md"
        elif kind == "neg_cases":
            base, pat = root / "memory" / "cases" / "_neg", "NEG-*.md"
        else:
            base, pat = root / "memory" / "rules", "*.md"
        if not base.is_dir():
            continue
        for f in sorted(base.glob(pat)):
            if f.name.startswith("._"):
                continue  # M8 修补:跳过 macOS AppleDouble resource fork(.__*)
            if kind == "cases" and f.stem.startswith("_"):
                continue  # v1:Brain.cases() 跳过 _ 前缀
            out.append(BrainDoc(slug, kind, f.stem, f.read_text()))
    wf = root / "skills" / "workflows"
    if wf.is_dir():
        for d in sorted(p for p in wf.iterdir() if p.is_dir()):
            if d.name.startswith("._"):
                continue  # M8 修补:跳过 macOS AppleDouble resource fork
            sk = d / "SKILL.md"
            text = sk.read_text() if sk.is_file() else d.name
            out.append(BrainDoc(slug, "skills", d.name, text))
    return out
