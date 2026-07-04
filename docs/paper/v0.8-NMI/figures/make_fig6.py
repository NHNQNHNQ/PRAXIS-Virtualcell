#!/usr/bin/env python3
"""Fig 6 — Learned reliability governance (Result 3). Faithful renderer:每个数值硬编码自已核实 finding
(docs/ANALYSIS-SUMMARY.md §2 / RESULTS-CONSOLIDATED §R3 / finding_g2_percell_w45),绘图时不计算不臆造。

面板:(a) bad-pert AUROC 对比 + per-cell 复算;(b) risk–coverage(真 donor 保留准度随覆盖率);
(c) 接回 runtime 前后 wrong-accept / risk-coverage。输出 SVG(主)/PDF/PNG(600dpi 预览)。
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── 已核实数值(硬编码,来源见 docstring)──────────────────────────────
AUROC = {"Learned": 0.907, "Disagreement": 0.774, "OOD flag": 0.788, "Random": 0.479}
AUROC_PERCELL_LEARNED = 0.869                       # per-cell 复算(finding_g2_percell_w45)
RC_COVERAGE = [1.00, 0.96, 0.88, 0.82, 0.74]        # 覆盖率
RC_RETAINED = [0.672, 0.683, 0.707, 0.732, 0.754]   # 保留集 delta-Pearson(真 donor)
RC_AUC, RC_AUC_PERCELL = 0.746, 0.736
WA_RULE, WA_LEARNED = 0.974, 0.211                  # wrong-accept 接回前后
RCV_RULE, RCV_LEARNED = 0.026, 0.789                # risk-coverage 接回前后

TEAL, AMBER, GRAY, RED = "#2a9d8f", "#e9a13b", "#9aa0a6", "#d1495b"
plt.rcParams.update({"font.size": 7, "font.family": "sans-serif", "svg.fonttype": "none",
                     "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6})


def _tidy(ax):
    ax.tick_params(width=0.6, length=2.5)


fig, (axa, axb, axc) = plt.subplots(1, 3, figsize=(7.2, 2.35))

# (a) AUROC 对比
names = list(AUROC)
vals = [AUROC[n] for n in names]
colors = [TEAL, GRAY, GRAY, GRAY]
bars = axa.bar(range(len(names)), vals, color=colors, width=0.66, zorder=3)
axa.axhline(0.5, color="#bbbbbb", lw=0.6, ls="--", zorder=1)              # chance
axa.plot([0], [AUROC_PERCELL_LEARNED], marker="D", ms=4, color="#146c60",
         zorder=5, label="learned, per-cell (0.869)")
for i, v in enumerate(vals):
    axa.text(i, v + 0.015, f"{v:.3f}", ha="center", va="bottom", fontsize=6.3)
axa.set_xticks(range(len(names)))
axa.set_xticklabels(names, rotation=20, ha="right")
axa.set_ylim(0, 1.0)
axa.set_ylabel("Bad-perturbation AUROC")
axa.set_title("a  Error detection (leave-pert-out)", fontsize=7.3, loc="left", fontweight="bold")
axa.legend(frameon=False, fontsize=5.8, loc="upper right")
_tidy(axa)

# (b) risk–coverage
axb.plot([c * 100 for c in RC_COVERAGE], RC_RETAINED, marker="o", ms=4, lw=1.4,
         color=TEAL, zorder=3)
for c, r in zip(RC_COVERAGE, RC_RETAINED):
    axb.annotate(f"{r:.3f}", (c * 100, r), textcoords="offset points", xytext=(0, 5),
                 ha="center", fontsize=5.8)
axb.invert_xaxis()
axb.set_xlabel("Coverage (%)")
axb.set_ylabel("Retained delta-Pearson")
axb.set_ylim(0.66, 0.77)
axb.set_title("b  Risk–coverage (real donors)", fontsize=7.3, loc="left", fontweight="bold")
axb.text(0.02, 0.02, f"risk–cov AUC {RC_AUC} (per-cell {RC_AUC_PERCELL})",
         transform=axb.transAxes, fontsize=5.8, color="#555555")
_tidy(axb)

# (c) 接回 runtime 前后
groups = ["Wrong-accept\nrate", "Risk-coverage"]
rule = [WA_RULE, RCV_RULE]
learned = [WA_LEARNED, RCV_LEARNED]
x = range(len(groups))
axc.bar([i - 0.2 for i in x], rule, width=0.36, color=RED, label="rule policy", zorder=3)
axc.bar([i + 0.2 for i in x], learned, width=0.36, color=TEAL, label="learned_with_rule_fallback", zorder=3)
for i, (r, l) in enumerate(zip(rule, learned)):
    axc.text(i - 0.2, r + 0.015, f"{r:.3f}", ha="center", va="bottom", fontsize=6.0)
    axc.text(i + 0.2, l + 0.015, f"{l:.3f}", ha="center", va="bottom", fontsize=6.0)
axc.set_xticks(list(x))
axc.set_xticklabels(groups)
axc.set_ylim(0, 1.05)
axc.set_ylabel("Rate")
axc.set_title("c  Wired into runtime", fontsize=7.3, loc="left", fontweight="bold")
axc.text(0.98, 0.55, "hard-override = 0", transform=axc.transAxes, ha="right",
         fontsize=5.8, color="#555555")
axc.legend(frameon=False, fontsize=5.8, loc="upper center")
_tidy(axc)

fig.tight_layout(w_pad=1.4)
_STEM = __file__.rsplit("/", 1)[0] + "/Fig6_learned_governance"
fig.savefig(f"{_STEM}.svg")
fig.savefig(f"{_STEM}.pdf")
fig.savefig(f"{_STEM}.png", dpi=600)
print("wrote Fig6_learned_governance .svg/.pdf/.png")
