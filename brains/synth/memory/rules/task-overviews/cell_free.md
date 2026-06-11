---
rule_id: task-overview-cell_free
schema_version: 1
rule_type: landscape
applies_to:
  synth_tasks: [cell_free]
  host_organisms: [cell_free]
  scale: [test_tube, shake_flask]
last_updated: 2026-04-29
---

## Cell-free 景观

**两大体系**：
- **TX-TL (E. coli extract)**：mg/mL 输出，便宜，含 native chaperone / membrane scaffolding；不能做 mammalian PTM
- **PURE (recombinant)**：μg/mL 输出，纯净（无内源 protease），可 minimal-component 研究

**关键参数**：
- Mg²⁺ 8-15 mM optimal
- K-glutamate 100-200 mM 优于 KCl
- ATP / GTP / NTP 5 mM 总
- Reaction time 4-8 h（>8 h energy 衰竭）

**适用 target**：
- Soluble proteins → TX-TL OK
- Membrane proteins → 加 nanodiscs / liposomes / detergent
- Antibodies / disulfide → 加 DsbC + glutathione redox
- 高度 PTM 蛋白（glycosylation 等）→ 受限，需要 mammalian system

**常见失败**：
- Extract 批次效应（不同 lot 输出可差 5×）
- Energy regen 不足
- 复杂 substrate / mRNA structure 影响 translation

**Rule references**：rule 02（codon opt for cell-free），rule 07（flow cytometry not applicable to bulk cell-free）。
