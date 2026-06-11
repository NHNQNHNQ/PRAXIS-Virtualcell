---
rule_id: task-overview-plasmid_assembly
schema_version: 1
rule_type: landscape
applies_to:
  synth_tasks: [plasmid_assembly]
  host_organisms: [ALL]
  scale: [ALL]
last_updated: 2026-04-29
---

## Plasmid 装配景观

**主流方法**：
- **Golden Gate / MoClo**：Type-IIs（BsaI / BsmBI / SapI），4-bp overhang，标准化 part library；多 fragment 可一锅
- **Gibson Assembly**：长 overlap (15-40 bp)，T5 exo + Phusion + Taq lig；不需 type-IIs
- **Yeast assembly (TAR)**：20+ fragments 可能，需 yeast host
- **NEBuilder HiFi**：Gibson 商业版本

**适用矩阵**：
| 方法 | 单 reaction frags | DNA 长度 | 内部 site 限制 |
|---|---|---|---|
| Golden Gate | ≤10 | 200 bp - 50 kb | 必须 destroy |
| Gibson | ≤5 | 200 bp - 100 kb | 无 |
| Yeast TAR | ≤20+ | up to 100 kb | 无 |

**核心规则**：rule 03（overhang collision）+ rule 04（destroy internal sites）+ rule 05（≥3 colony pick）+ 全质粒 sanger / Plasmidsaurus / Nanopore 验证。

**常用工具**：Benchling / SnapGene / j5/DeviceEditor / NEBuilder online / Pydna (Python)。
