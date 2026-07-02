#!/usr/bin/env python3
"""
PRAXIS-VirtualCell v0.1 — 出版级图 (Nature Methods 风格, Python/matplotlib)
所有数字硬编码自 docs/findings/*,注释标注来源 finding。
输出: 每图 SVG(主, editable text) + PDF + 600dpi TIFF,放本目录。
运行: python3 make_figures.py
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch, Rectangle

# ── MANDATORY: editable SVG text (nature-figure 不变量) ───────────────────────
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["font.size"] = 7
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["legend.frameon"] = False

OUT = os.path.dirname(os.path.abspath(__file__))

# ── palette (一族中性 + 一族信号 + 方向色) ────────────────────────────────────
C = {
    "blue":      "#0F4D92",  # base predictor family
    "blue_soft": "#3775BA",
    "green":     "#2E9E44",  # applicable / gain
    "green_soft":"#8BCF8B",
    "amber":     "#E28E2C",  # caution / abstain branch
    "red":       "#C0392B",  # reject / gate
    "red_soft":  "#E9A6A1",
    "teal":      "#33B5A5",  # coordinator / hero
    "violet":    "#7C6CCF",
    "n_light":   "#E3E3E3",
    "n_mid":     "#9A9A9A",
    "n_dark":    "#4D4D4D",
    "ink":       "#272727",
    "bus":       "#484878",  # message bus
    "llm":       "#9A4D8E",  # optional LLM agents
}


def save_pub(fig, name, dpi=600):
    base = os.path.join(OUT, name)
    fig.savefig(base + ".svg", bbox_inches="tight")
    fig.savefig(base + ".pdf", bbox_inches="tight")
    fig.savefig(base + ".tiff", dpi=dpi, bbox_inches="tight", pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(base + ".png", dpi=200, bbox_inches="tight")  # QA 预览, 非投稿用
    plt.close(fig)
    print(f"  saved {name}.svg/.pdf/.tiff (+png preview)")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ Fig 1 — 架构 / 数据流 (schematic-led composite)                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def box(ax, cx, cy, w, h, text, fc, ec=C["ink"], tc=None, fs=6.6, lw=1.0,
        ls="-", rounded=0.02, fw="normal"):
    """画一个圆角框,文字居中,返回 (cx, cy, w, h)。"""
    if tc is None:
        tc = "white" if fc in (C["blue"], C["bus"], C["red"], C["teal"], C["llm"], C["n_dark"]) else C["ink"]
    p = FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                       boxstyle=f"round,pad=0.0,rounding_size={rounded}",
                       linewidth=lw, edgecolor=ec, facecolor=fc, linestyle=ls,
                       mutation_aspect=1.0, zorder=3)
    ax.add_patch(p)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=tc,
            zorder=4, fontweight=fw, linespacing=1.15)
    return (cx, cy, w, h)


def arrow(ax, p1, p2, color=C["n_dark"], lw=1.1, ls="-", rad=0.0,
          style="-|>", ms=7, z=2, alpha=1.0):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=ms,
                        linewidth=lw, color=color, linestyle=ls,
                        connectionstyle=f"arc3,rad={rad}", zorder=z, alpha=alpha,
                        shrinkA=2, shrinkB=2)
    ax.add_patch(a)


def edge(b, side):
    cx, cy, w, h = b
    return {"r": (cx + w / 2, cy), "l": (cx - w / 2, cy),
            "t": (cx, cy + h / 2), "b": (cx, cy - h / 2)}[side]


def fig1():
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    # ── Row 1: intake + brain ────────────────────────────────────────────────
    y1 = 86
    req = box(ax, 9, y1, 15, 9, "Virtual-cell\ntask (free text\nor structured)", C["n_light"], fs=6.0)
    ii  = box(ax, 29, y1, 15, 9, "Input\nInterpreter", C["blue"], fw="bold")
    nm  = box(ax, 48, y1, 15, 9, "BioObject\nNormalizer", C["blue"], fw="bold")
    sb  = box(ax, 67, y1, 15, 9, "Species\nBrain", C["teal"], fw="bold")
    ma  = box(ax, 87, y1, 17, 9, "Model\nApplicability", C["teal"], fw="bold")
    for a, b in [(req, ii), (ii, nm), (nm, sb), (sb, ma)]:
        arrow(ax, edge(a, "r"), edge(b, "l"))
    ax.text(9, y1 - 6.2, "VirtualCellRequest\n(typed, validated)", ha="center", va="top",
            fontsize=5.3, color=C["n_mid"], style="italic")
    ax.text(77, y1 + 6.6, "retrieve applicability +\nnegative-transfer rules", ha="center",
            va="bottom", fontsize=5.3, color=C["teal"])

    # ── retrieve-before-predict GATE ─────────────────────────────────────────
    gate = box(ax, 86, 68, 21, 7.0, "retrieve-before-\npredict GATE",
               C["red"], ec=C["red"], fs=6.0, fw="bold")
    arrow(ax, edge(ma, "b"), edge(gate, "t"), color=C["red"], lw=1.3)

    # ── Row 2: predictor fan-out ─────────────────────────────────────────────
    y2 = 54
    p_lin = box(ax, 57, y2, 16, 8, "MockLinear\nagent", C["blue_soft"], fs=6.0)
    p_cpa = box(ax, 75, y2, 16, 8, "MockCPA\nagent", C["blue_soft"], fs=6.0)
    p_gea = box(ax, 90, y2 - 12, 16, 8, "MockGEARS\nagent  (OOV→reject)", C["red_soft"], fs=5.6)
    # fan-out from gate
    for p in (p_lin, p_cpa):
        arrow(ax, edge(gate, "b"), edge(p, "t"), color=C["n_dark"], lw=1.0, rad=-0.05)
    arrow(ax, edge(gate, "b"), edge(p_gea, "t"), color=C["n_mid"], lw=1.0, ls=(0, (4, 2)), rad=0.0)
    ax.text(60, y2 + 6.6, "heterogeneous predictor-agents  ·  independent reject / abstain",
            ha="center", va="bottom", fontsize=5.3, color=C["n_mid"])
    ax.text(90, y2 - 18.4, "status: success /\nrejected / failed", ha="center", va="top",
            fontsize=5.0, color=C["n_mid"], style="italic")

    # ── Row 3: aggregate + reliability + audit ───────────────────────────────
    y3 = 33
    ens = box(ax, 12, y3, 17, 8.5, "Ensemble\nCoordinator", C["blue"], fw="bold", fs=6.2)
    rel = box(ax, 33, y3, 16, 8.5, "Reliability", C["blue"], fw="bold")
    cri = box(ax, 52, y3, 14, 8.5, "Critic\n(7 invariants)", C["blue"], fw="bold", fs=6.0)
    prov= box(ax, 70, y3, 15, 8.5, "Provenance", C["blue"], fw="bold")
    rep = box(ax, 88, y3, 15, 8.5, "Report", C["blue"], fw="bold")
    # predictors -> ensemble
    for p in (p_lin, p_cpa, p_gea):
        arrow(ax, edge(p, "b"), edge(ens, "t"), color=C["n_mid"], lw=0.9, rad=0.12)
    for a, b in [(ens, rel), (rel, cri), (cri, prov), (prov, rep)]:
        arrow(ax, edge(a, "r"), edge(b, "l"))

    # ── outputs: predict vs abstain ──────────────────────────────────────────
    outp = box(ax, 88, 16, 15, 7.5, "Prediction +\nprovenance + reliability",
               C["green_soft"], fs=5.7)
    arrow(ax, edge(rep, "b"), edge(outp, "t"), color=C["green"], lw=1.2)
    abst = box(ax, 33, 16, 17, 7.5, "ABSTAIN\n(with reasons)", C["amber"], ec=C["amber"],
               tc="white", fs=6.2, fw="bold")
    arrow(ax, edge(rel, "b"), edge(abst, "t"), color=C["amber"], lw=1.4)
    ax.text(43, 16, "reliability\ninsufficient", ha="left", va="center",
            fontsize=5.0, color=C["amber"], style="italic")

    # ── MessageBus spine ─────────────────────────────────────────────────────
    busy = 5.5
    bus = FancyBboxPatch((6, busy - 2.2), 92, 4.4, boxstyle="round,pad=0,rounding_size=0.6",
                         linewidth=1.0, edgecolor=C["bus"], facecolor=C["bus"], zorder=3)
    ax.add_patch(bus)
    ax.text(52, busy, "MessageBus — single auditable channel · every AgentMessage recorded · fully replayable trace",
            ha="center", va="center", fontsize=6.0, color="white", fontweight="bold", zorder=4)
    for bx in (ii, nm, sb, ma, ens, rel, cri, prov, rep):
        cx = bx[0]
        arrow(ax, (cx, busy + 2.4), (cx, busy + 2.4 + 0.1), color=C["bus"], lw=0.0)  # noop spacing
        ax.plot([cx, cx], [busy + 2.2, bx[1] - bx[3] / 2], color=C["bus"], lw=0.5,
                ls=(0, (1, 1.5)), alpha=0.55, zorder=1)

    # ── optional LLM agents (dashed) ─────────────────────────────────────────
    llm = box(ax, 13, 68, 18, 9,
              "Optional LLM agents\nInput · Router · Critic · Report",
              "white", ec=C["llm"], tc=C["llm"], fs=5.6, ls=(0, (3, 2)), lw=1.1)
    ax.text(13, 60.5, "assist only · never in prediction core · offline fallback",
            ha="center", va="top", fontsize=5.0, color=C["llm"], style="italic")
    arrow(ax, (13, 63.5), (24, y1 - 4.5), color=C["llm"], lw=0.8, ls=(0, (3, 2)), rad=0.1)

    # ── legend ───────────────────────────────────────────────────────────────
    leg = [
        Patch(fc=C["teal"], ec=C["ink"], label="brain / routing"),
        Patch(fc=C["blue"], ec=C["ink"], label="deterministic agent"),
        Patch(fc=C["red"], ec=C["red"], label="hard gate"),
        Patch(fc=C["amber"], ec=C["amber"], label="abstain branch"),
        Patch(fc="white", ec=C["llm"], label="optional LLM (dashed)"),
    ]
    lg = ax.legend(handles=leg, loc="center left", bbox_to_anchor=(0.0, 0.44),
                   fontsize=5.3, ncol=2, handlelength=1.1, labelspacing=0.35,
                   columnspacing=0.9, frameon=True)
    lg.get_frame().set_facecolor("white"); lg.get_frame().set_edgecolor("none")
    lg.get_frame().set_alpha(0.92); lg.set_zorder(6)
    ax.text(0, 99, "a", fontsize=11, fontweight="bold", ha="left", va="top")
    save_pub(fig, "Fig1_architecture")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ Fig 2 — Norman ΔPearson: base + Coordinator (quantitative grid)            ║
# ║ data: finding_w4b_multi_anchor, finding_w4b_coordinator, finding_w4a       ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def fig2():
    # (name, ΔPearson, kind)  kind: base / coord
    rows = [
        ("Coordinator · all-5",            0.7039, "coord"),
        ("Coordinator · CPA+Dec+GNN",      0.7020, "coord"),
        ("Coordinator · Latent+GNN",       0.6847, "coord"),
        ("CPA-style (best base)",          0.6716, "best"),
        ("Decoder-only",                   0.6709, "base"),
        ("GNN-pert",                       0.6675, "base"),
        ("Linear-additive",               0.6639, "base"),
        ("Latent-additive",               0.6365, "base"),
        ("Pretrained backbone (mock)",     0.6183, "base"),
    ]
    rows = rows[::-1]  # 自下而上递增显示
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    kinds = [r[2] for r in rows]
    cmap = {"coord": C["teal"], "best": C["blue"], "base": C["blue_soft"]}
    colors = [cmap[k] for k in kinds]

    fig, ax = plt.subplots(figsize=(5.4, 3.5))
    y = np.arange(len(rows))
    ax.barh(y, vals, color=colors, edgecolor=C["ink"], linewidth=0.8, height=0.66, zorder=3)
    for yi, v, k in zip(y, vals, kinds):
        ax.text(v + 0.0015, yi, f"{v:.4f}", va="center", ha="left",
                fontsize=6.2, color=C["ink"], fontweight="bold" if k == "coord" else "normal")
    ax.axvline(0.70, color=C["n_dark"], ls=(0, (4, 2)), lw=1.0, zorder=2)
    ax.text(0.70, len(rows) - 0.3, "0.70", color=C["n_dark"], fontsize=6.0,
            ha="center", va="bottom")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=6.4)
    ax.set_xlim(0.60, 0.715)
    ax.set_xlabel("Norman 2019 per-cell ΔPearson  (test, n = 18,874)", fontsize=6.8)
    ax.tick_params(axis="x", labelsize=6.2)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    # ensemble gain annotation (clear of the bars)
    ax.text(0.7039, len(rows) - 0.42, "all-5 ensemble  +0.032 vs strongest base",
            fontsize=5.8, color=C["teal"], ha="right", va="bottom", fontweight="bold")
    leg = [Patch(fc=C["teal"], ec=C["ink"], label="Coordinator ensemble"),
           Patch(fc=C["blue"], ec=C["ink"], label="strongest single base"),
           Patch(fc=C["blue_soft"], ec=C["ink"], label="single base predictor")]
    ax.legend(handles=leg, loc="lower right", fontsize=5.6, handlelength=1.1)
    ax.text(-0.02, 1.04, "", transform=ax.transAxes)
    save_pub(fig, "Fig2_norman_performance")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ Fig 3 — ablation A↔D, 5 reliability metrics (grouped bar)                  ║
# ║ data: finding_w7                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def fig3():
    metrics = ["OOD\nrejection", "Wrong-model\nuse", "Provenance\ncompleteness",
               "Abstention\ncorrectness", "Trace\ncompleteness"]
    better = ["↑", "↓", "↑", "↑", "↑"]  # desired direction
    A = [0.0, 1.0, 0.0, 0.0, 0.0]   # ML-only Coordinator
    D = [1.0, 0.0, 1.0, 1.0, 1.0]   # Full PRAXIS
    x = np.arange(len(metrics))
    w = 0.38
    fig, ax = plt.subplots(figsize=(5.6, 3.3))
    ba = ax.bar(x - w / 2, A, w, color=C["n_mid"], edgecolor=C["ink"], linewidth=0.8,
                label="A · ML-only Coordinator", zorder=3)
    bd = ax.bar(x + w / 2, D, w, color=C["teal"], edgecolor=C["ink"], linewidth=0.8,
                label="D · Full PRAXIS-VirtualCell", zorder=3)
    for bars in (ba, bd):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02,
                    f"{b.get_height():.1f}", ha="center", va="bottom", fontsize=6.0,
                    color=C["ink"])
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}\n({d} better)" for m, d in zip(metrics, better)], fontsize=6.0)
    ax.set_ylim(0, 1.18)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_ylabel("rate / completeness", fontsize=6.8)
    ax.tick_params(axis="y", labelsize=6.2)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=2, fontsize=5.8,
              columnspacing=1.2, handlelength=1.1)
    ax.text(0.5, -0.30, "same mock-predictor set for A and D · 6 seed requests · offline deterministic   (finding_w7)",
            transform=ax.transAxes, ha="center", va="top", fontsize=5.2, color=C["n_mid"])
    save_pub(fig, "Fig3_ablation")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ Fig 4 — cross-species routing heatmap (categorical)                        ║
# ║ data: finding_w5                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def fig4():
    species = ["Human", "Mouse", "Bacteria", "Yeast", "Unknown\n(martian)"]
    preds = ["MockLinear", "MockCPA", "MockGEARS"]
    # 0=applicable, 1=caution, 2=reject
    M = np.array([
        [0, 0, 0],   # human: all applicable, no caution
        [1, 1, 1],   # mouse: applicable + ortholog caution (real projection)
        [2, 2, 2],   # bacteria: all reject (negative transfer)
        [2, 2, 2],   # yeast: all reject (negative transfer)
        [2, 2, 2],   # unknown: all reject -> abstain, no fake evidence
    ])
    outcome = ["Predict",
               "Predict + ortholog caution",
               "Abstain · negative-transfer",
               "Abstain · negative-transfer",
               "Abstain · species unknown"]
    cmap = {0: C["green_soft"], 1: C["amber"], 2: C["red_soft"]}
    txt = {0: "applicable", 1: "caution", 2: "reject"}
    tcol = {0: C["ink"], 1: "white", 2: C["red"]}

    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.set_xlim(0, 3); ax.set_ylim(0, 5); ax.invert_yaxis(); ax.axis("off")
    for i in range(5):
        for j in range(3):
            v = M[i, j]
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=cmap[v], edgecolor="white",
                                    linewidth=2.0, zorder=2))
            ax.text(j + 0.5, i + 0.5, txt[v], ha="center", va="center",
                    fontsize=5.8, color=tcol[v], fontweight="bold", zorder=3)
    # column headers
    for j, p in enumerate(preds):
        ax.text(j + 0.5, -0.12, p, ha="center", va="bottom", fontsize=6.4, fontweight="bold")
    # row labels
    for i, s in enumerate(species):
        ax.text(-0.08, i + 0.5, s, ha="right", va="center", fontsize=6.4, fontweight="bold")
    # outcome column
    ax.text(3.15, -0.12, "system outcome", ha="left", va="bottom", fontsize=6.2,
            fontweight="bold", color=C["n_dark"])
    for i, o in enumerate(outcome):
        oc = C["green"] if o.startswith("Predict") and "caution" not in o else (
            C["amber"] if "caution" in o else C["red"])
        ax.text(3.15, i + 0.5, o, ha="left", va="center", fontsize=5.8, color=oc)
    # legend
    leg = [Patch(fc=C["green_soft"], ec="white", label="applicable"),
           Patch(fc=C["amber"], ec="white", label="caution (ortholog)"),
           Patch(fc=C["red_soft"], ec="white", label="reject")]
    ax.legend(handles=leg, loc="upper left", bbox_to_anchor=(0.0, -0.04),
              ncol=3, fontsize=5.8, handlelength=1.0, columnspacing=1.0)
    ax.text(0.0, 5.55, "One fixed task routed across species  ·  finding_w5  ·  no fabricated rule references for unknown species",
            ha="left", va="top", fontsize=5.3, color=C["n_mid"])
    save_pub(fig, "Fig4_cross_species")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ Fig 5 — reliability / audit mechanisms (schematic)                         ║
# ║ data: finding_w6                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def fig5():
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    STAR = "*"  # declarative marker (ASCII-safe; Arial 无 ★/⇔ 字形)

    # Stage 1: disagreement
    s1 = box(ax, 14, 78, 24, 20,
             "EnsembleCoordinator\n\nmodel disagreement =\nmean pairwise cosine distance\nzero-vector pairs audited\nthreshold τ = 0.5 (configurable)",
             C["blue"], fs=5.6, fw="bold")
    # Stage 2: reliability (two columns)
    box(ax, 50, 86, 30, 12, "ABSTAIN triggers", C["amber"], ec=C["amber"], tc="white", fs=6.0, fw="bold")
    ax.text(50, 86, "", ha="center")
    ax.text(50, 79.5,
            "all-rejected · species-unsupported\ncore-predictor-failed " + STAR + " · disagreement > τ " + STAR,
            ha="center", va="center", fontsize=5.3, color=C["ink"])
    box(ax, 50, 67, 30, 10, "DOWNGRADE triggers", C["n_mid"], tc="white", fs=6.0, fw="bold")
    ax.text(50, 60.5, "disagreement " + STAR + " · cell-type-unsupported " + STAR,
            ha="center", va="center", fontsize=5.3, color=C["ink"])
    ax.text(50, 95.5, "ReliabilityAgent", ha="center", va="center", fontsize=6.4,
            fontweight="bold", color=C["n_dark"])
    arrow(ax, edge(s1, "r"), (35, 84), color=C["n_dark"], lw=1.0)

    # Stage 3: critic
    cri = box(ax, 84, 78, 28, 30,
              "CriticAgent  ·  7 trace invariants\n\n1  retrieve-before-predict order\n2  no rejected in ensemble\n3  prediction present if not abstain\n4  rules referenced if not abstain\n5  uncertainty reported\n6  species supported in ensemble\n7  abstain iff no surviving prediction",
              "white", ec=C["blue"], tc=C["ink"], fs=5.2)
    arrow(ax, (65, 78), edge(cri, "l"), color=C["n_dark"], lw=1.0)

    # Stage 4: report split
    rA = box(ax, 27, 26, 30, 12, "report.abstain_reasons\n(true refusals only)", C["amber"],
             ec=C["amber"], tc="white", fs=5.6, fw="bold")
    rD = box(ax, 62, 26, 30, 12, "report.downgrade_reasons\n(reliability lowered, still predicts)",
             C["n_mid"], tc="white", fs=5.6, fw="bold")
    rx = box(ax, 89, 26, 18, 12, "caution_flags\nmodel_disagreement\ncritic_violations", C["n_light"], fs=5.0)
    ax.text(50, 40, "ReportAgent — separated so a downgrade is never misread as an abstention",
            ha="center", va="bottom", fontsize=5.8, fontweight="bold", color=C["n_dark"])
    arrow(ax, (50, 60), (40, 33), color=C["amber"], lw=1.0, rad=0.1)
    arrow(ax, (84, 62), (66, 33), color=C["n_mid"], lw=1.0, rad=-0.1)

    # declarative note
    ax.text(2, 6,
            STAR + "  declarative mechanism: proven activatable by hand-written unit tests; "
            "does not fire in the offline mock end-to-end path (finding_w6). "
            "Real activation awaits a real disagreeing / failable predictor.",
            ha="left", va="center", fontsize=5.2, color=C["red"], wrap=True)
    save_pub(fig, "Fig5_reliability")


if __name__ == "__main__":
    print("rendering figures ->", OUT)
    fig1(); fig2(); fig3(); fig4(); fig5()
    print("done.")
