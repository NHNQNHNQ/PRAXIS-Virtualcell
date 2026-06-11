---
case_id: synth-002-pathway-artemisinin
task: heterologous_pathway_design
target_compound: artemisinic acid (precursor of artemisinin antimalarial)
host_organism: Saccharomyces cerevisiae
tools: [RetroPath2.0, Cameo, KEGG, BioCyc, OptStoic]
key_paper_doi: 10.1038/nature12051
status: validated
---

# Artemisinic acid 在酵母异源表达：Amyris 经典 case

## Background
Amyris/UC Berkeley (Keasling lab) 2013 把 Artemisia annua 植物 artemisinic acid 通路移植到酵母，工业化生产。10+ year effort，是合成生物学 heterologous pathway 教科书。**关键 lesson**：单纯把酶 cloning 进 host 不够，需 strain engineering（precursor pool、cofactor、toxicity mitigation）。

## What I actually did（设计层面复盘）
1. **Pathway**：Acetyl-CoA → mevalonate → IPP/DMAPP → FPP → amorpha-4,11-diene → artemisinic alcohol → aldehyde → artemisinic acid
2. **Heterologous enzymes**：
   - ADS (amorphadiene synthase, plant)
   - CYP71AV1 (P450, plant) + CPR (cytochrome P450 reductase)
   - ADH1 / ALDH1 (plant alcohol/aldehyde dehydrogenase)
3. **Precursor flux up-regulation**：endogenous mevalonate pathway 上调（HMG-CoA reductase truncated form, ERG20 modified for FPP accumulation）
4. **Co-factor balance**：CYP71AV1 需 NADPH，过度引导 reductase 流动
5. **Toxicity mitigation**：amorphadiene + artemisinic acid 对 yeast toxic at high concentration → secretion / extraction strategy
6. **Codon optimize**：plant gene → S.cerevisiae codon
7. **Validation**：HPLC / GC-MS 量化 artemisinic acid titer，achieve 25 g/L industrial scale

## ★ 排除/不做的事
- **直接 clone enzyme 不调 precursor**：endogenous FPP 池太小，pathway 限速
- **不验证 P450 functional in yeast**：plant P450 在 yeast 经常失活；CPR partner 必备
- **不评估 toxicity**：高浓度 product 杀 host，yield drop
- **Codon 不 optimize**：plant codon 在 yeast 表达低 5-10×
- **Single gene cassette**：多 enzyme 各自 promoter，防止 metabolic flux imbalance
- **不监控 cofactor**：NADPH 耗尽时整个 pathway 崩

## ★ 失败模式
- **Flux imbalance**：上游过量 → 中间体堆积 toxic；下游过量 → 不必要 metabolic burden
- **P450 misfolding in heterologous host**：plant P450 需 specific membrane context，yeast ER 不全 compatible
- **Glycosylation difference**：plant vs yeast post-translational mod 差，活性可能损
- **Strain instability**：长时间 cultivation 中 plasmid loss / mutation 累积
- **Scale-up issue**：lab scale 50 mL works，industrial 100k L 完全不同 mass transfer
- **Regulatory feedback**：endogenous regulation 抑制 over-expression，需 deregulated promoter

## Lessons → seeds for rules
1. **Precursor flux engineering** along with heterologous enzyme cloning
2. **Codon optimization for host** 必步
3. **P450 + CPR pair** for plant P450 in yeast
4. **Toxicity assessment + mitigation** strategy
5. **Co-factor balance** monitor
6. **Multiple promoter (not operon-style)** for each gene
7. **Strain stability** over generations 验证
