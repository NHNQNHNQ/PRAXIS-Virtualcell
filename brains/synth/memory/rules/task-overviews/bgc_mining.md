---
rule_id: task-overview-bgc_mining
schema_version: 1
rule_type: landscape
applies_to:
  synth_tasks: [bgc_mining]
  host_organisms: [ALL]
  scale: [ALL]
last_updated: 2026-04-29
---

## BGC mining 景观

**主流工具**（rule 09 强制 ≥2 consensus）：
- **antiSMASH 7**（Blin 2020-2023）：rule-based，主流；输出 cluster + product class prediction
- **PRISM 4**（Skinnider 2020）：rule + statistical
- **DeepBGC**：deep-learning，捕捉 antiSMASH miss 的 cluster
- **GECCO**：light-weight
- **BiG-SCAPE**：cluster family network
- **MIBiG database**：known BGC reference，rule 09 cross-check

**典型 metrics**：
- BGC 在 genome 占比：5-10%（Streptomyces / actinomycetes / cyanobacteria 高产 host）
- 重发现率：80%（vs MIBiG）
- Cluster 长度：5-150 kb（NRPS / PKS 大 cluster）

**常见失败**：
- antiSMASH false positive（rule-only 不足）→ DeepBGC 校验
- Cluster boundaries 错（split / merge）
- Silent cluster（regulator 抑制 → 无表达）
- 大 BGC 难 heterologous express（>50 kb 需要 specialized vector / yeast assembly）

**Reactivation strategies**（如发现 silent cluster）：
- Reporter-guided mutagenesis
- Heterologous expression in Streptomyces coelicolor M1146 / M1152
- OSMAC（One Strain Many Compounds）培养条件 sweep
