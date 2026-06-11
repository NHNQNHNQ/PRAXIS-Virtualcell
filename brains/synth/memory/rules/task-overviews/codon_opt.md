---
rule_id: task-overview-codon_opt
schema_version: 1
rule_type: landscape
applies_to:
  synth_tasks: [codon_opt]
  host_organisms: [ALL]
  scale: [ALL]
last_updated: 2026-04-29
---

## Codon 优化 / DNA constraint solving 景观

**目标**：在保持氨基酸序列前提下，针对 host 重写 codon 以最大化 expression，同时满足约束（restriction sites / GC / homopolymer）。

**主流工具**：DNAchisel (Python, multi-constraint solver), JCAT (web), CodonW (CLI), GeneOptimizer (commercial), IDT codon optimizer (web).

**关键 metrics**：
- **CAI** (Codon Adaptation Index)：host-specific，0.65+ 优秀，0.5- 风险
- **GC%**：35-55% 安全区
- **5' UTR ΔG**（首 50 nt）：> -10 kcal/mol（避免强发卡）
- **Forbidden sites**：BsaI, BsmBI, SapI, NotI（看下游 cloning）

**约束 trade-off**：
- 过度优化（CAI=0.95）→ 折叠失败，因 ribosome 不停顿（rare codon 提供 cotranslational folding 时间）
- 推荐 ~5% rare codon 保留

**适配场景**：rule 02（heterologous 强制 codon opt），synth-006 GFP 案例（restriction site removal），synth-004 IL-2（host = yeast）。
