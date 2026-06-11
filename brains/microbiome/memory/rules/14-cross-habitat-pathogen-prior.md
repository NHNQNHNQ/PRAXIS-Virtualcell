---
rule_id: 14-cross-habitat-pathogen-prior
rule_type: case_distilled
applies_to: {microbiome_task: [cross_habitat_analysis, network, keystone_identification, hypothesis_generation], sample_type: [any]}
confidence: high
evidence_cases: [microbiome-015-cross-habitat-generalists, microbiome-017-keystone-dichotomy]
schema_version: 2
---

# Rule 14:跨 ≥4 生境 named species 优先标记 opportunistic-pathogen prior

## Statement

凡是带 GTDB `s__` 命名(`gtdb_s != ""`)且在分析覆盖的生境集中出现于 **≥4 个生境** 的 species,在 Phase 3 hypothesis generation / tournament reranker / cross_feeding 边推断时:

1. 自动 attach label `opportunistic_pathogen_candidate`
2. tournament reranker 中该 species 的 hypothesis 权重 × 1.5
3. 自动并跑 **strain_tracking_real**(看是否是同 strain 散布,而非物种水平 convergent generalist)
4. 自动并跑 **CARD**(抗药基因) + **VFDB**(毒力基因) + **antismash/MIBiG**(BGC content)三联注释
5. 在最终图谱中分到 **Type B(chemical-warfare keystone)** 名单(case-017 §20)

## Why

case-015 跨 9 生境 / 20 catalog ingestion 发现:
- 跨 ≥6 生境的 5 个 named species **全部是临床机会致病菌**(K. pneumoniae, P. aeruginosa, C. acnes, A. johnsonii, E. coli)
- 跨 5 生境 13 species 中机会致病(S. aureus, A. baumannii, S. epidermidis, K. variicola, P. agglomerans)与 probiotic(L. plantarum, L. crispatus)两极分布
- 跨 4 生境 40 个 species 中大部分有 PubMed 临床或多 niche 文献

case-017 用**完全独立的第二条数据轴**(MIBiG BGC content homology)在 gut_human 358 species 图谱里验证:
- BGC content top 5 = K. pneumoniae(1598)/ E. coli(1477)/ Enterocloster bolteae(1315)/ Eggerthella lenta(1283)/ Bilophila wadsworthia(1253)
- 与 case-015 跨生境顶级名单 K. pneumoniae + E. coli 在 top 2 完全重合
- BGC top 10 / weighted_degree top 10 **完全 mutually exclusive** → 化学武器 keystone vs 代谢 keystone 是两个生态策略

→ "**多生境适应 ≈ BGC 化学武器 ≈ 机会致病潜力**" 假说被两条独立证据轴共同支持

## Exceptions(false-positive 风险)

- **probiotic Lactobacillus / Lactiplantibacillus**:跨多生境但不致病(产 SCFA / bacteriocin 但 spectrum 窄)。处理:加 secondary check —— 若 BGC 主要是 RiPP-narrow-spectrum + 无 CARD 抗药基因 → 重标 `probiotic_candidate` 而非 pathogen
- **Cutibacterium acnes**:跨 7 生境但绝大多数是皮肤共生,仅少数 acne / 心内膜炎情境致病 → 标 `commensal_with_pathogenic_potential` 而非纯 pathogen
- **NaN / GTDB unnamed sp**:此规则不适用(GTDB 未命名意味着 MAG-only,无文献支持);跨多生境的 unnamed species 不打 pathogen 标记

## How to apply

```python
# in hypothesis generation pipeline
def apply_rule_14(species_row, n_habitats):
    if n_habitats >= 4 and species_row.gtdb_s and species_row.gtdb_s.strip():
        priors = ["opportunistic_pathogen_candidate"]
        # secondary checks
        if species_row.has_RiPP_narrow and not species_row.has_CARD:
            priors.append("probiotic_candidate")
            priors.remove("opportunistic_pathogen_candidate")
        return {"reranker_weight": 1.5, "priors": priors,
                "auto_skills": ["strain_tracking_real", "cross_feeding_gem",
                                "bgc_antagonism", "card_annotate", "vfdb_annotate"]}
    return {}
```

## Validation

- case-015 名单(habitat-based)与 case-017 图谱(BGC-based)在 top 2 species 完全重合(K.pneumoniae + E.coli)
- 两条数据轴是操作上完全独立的(habitat detection vs BGC protein homology)
- 共同 species 都有强 PubMed 临床证据

## Linked rules
- 与 §07(multiomics-triangulation)互补:§07 要求 ≥2 证据,本规则给出"哪些 species 优先做 ≥3 证据深挖"
- 与 §13(isolate-vs-MAG)互补:本规则不依赖 isolate vs MAG,只看 GTDB s__ 是否命名 + 生境数
- 与候选 §20(case-017 提)互锁:Type B keystone = 本规则识别出的 species 子集

## Anti-rule(NEG)候选

如果将来分析发现跨 ≥4 生境的某 named species 是纯 probiotic 或环境 specialist(非致病),记录为 NEG case + 收紧 exceptions 条件。
