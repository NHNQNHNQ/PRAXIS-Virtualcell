---
rule_id: task-overview-strain_engineering
schema_version: 1
rule_type: landscape
applies_to:
  synth_tasks: [strain_engineering]
  host_organisms: [ALL]
  scale: [shake_flask, fermenter, industrial]
last_updated: 2026-04-29
---

## Strain engineering 景观

**核心 algorithms**：
- **OptKnock**（Burgard 2003）：bilevel programming，max product s.t. max biomass
- **OptStoic**：化学计量驱动，不需要 thermodynamic constraint
- **OptForce / OptGene / OptReg**：扩展集合
- **MOMA / ROOM**：post-perturbation flux distribution

**典型 KO 数量**：3-5（工业菌） vs 10+（极端 high-yield）；越多 fitness penalty 越高。

**Wet-lab 路径**：
- λRed recombineering（E. coli）
- CRISPR-Cas9 multiplex（rule: 跨 agent envelope → CRISPR）
- Allelic exchange（slow but reliable for non-model）

**Validation**：
- GC-MS / HPLC titer（必须）
- Continuous fermentation 30-50 generation 测稳定性
- Compensatory mutation 监控（whole-genome seq）

**常见失败**：
- OptKnock 推荐含 essential gene → rule 08 必须 audit
- 30-50% in silico vs in vivo gap（synth-009 evidence）
- 长 cultivation 后 strain instability（plasmid loss / suppressor mutation）
