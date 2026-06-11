---
name: conservation-msa-analyzer
description: 基于 MSA 的保守性 + co-evolution 分析。整合 ConSurf 风格保守性评分、GREMLIN/CCMpred co-evolution、JSD/Shannon entropy 多 metric, 配合 Jäckel 2010 phylogenetic balance 检查 (anti-rule 6). 输出每个残基的 conservation score + 是否 candidate-mutable 标签. Hard Rule 9 强制分析门控的核心 skill 之一.
---

# Conservation & MSA Analyzer Skill

## 一句话原则
**Mutation 候选必须落在保守性低 + co-evolution 弱的位点**, 否则极易破坏功能. naive consensus 不查 phylogenetic balance 直接被 anti-rule 6 vetoed.

## 适用阶段
Design Agent 在生成 mutation 候选**之前**必须调用. 输出的 conservation 标签会写入 design_artifact 的 evidence_chain.

## 先检查环境
```bash
which mmseqs hhblits jackhmmer    # 至少需要其中之一做 MSA
which gremlin_cpp ccmpred 2>/dev/null  # co-evolution (可选)
python -c "from Bio import AlignIO; print('OK')"
```

## 输入契约
```json
{
  "uniprot_accession": "P62694",
  "sequence": "MKVLLAPVA...",
  "msa_method": "mmseqs2",            // mmseqs2 / hhblits / jackhmmer
  "msa_database": "uniref30",          // uniref30 / uniref90 / bfd
  "msa_max_seqs": 1000,
  "msa_min_seq_id": 0.30,
  "do_phylogenetic_weighting": true,  // ★ 必须 true; false 触发 anti-rule 6
  "do_coevolution": true,              // GREMLIN/CCMpred
  "metrics": ["consurf", "shannon", "jsd"]
}
```

## 输出契约
```json
{
  "skill_id": "conservation-msa-analyzer",
  "msa_path": "",
  "n_sequences": 0,
  "conservation_csv": "",
  "diagnostics": {
    "brain": "enzyme",
    "archetype": "msa_conservation"
  }
}
```

## 评分阈值
- **ConSurf 1-3**: variable, 工程化候选区
- **ConSurf 4-6**: moderately conserved, 改动需要其它证据 (PyRosetta OK + ESM > 0)
- **ConSurf 7-9**: highly conserved, 强烈不推荐除非有特定 case 证据

## 关键检查 (★ 强制)
1. **Phylogenetic balance check (Jäckel 2010, anti-rule 6)**:
   - 单一 clade 占比 > 50% → naive consensus 不可信 → 强制 weighted MSA
   - 触发 warning, design agent 必须 acknowledge
2. **Strong co-evolution pair check**:
   - 若候选位 r 与某 r' 强耦合 (GREMLIN/CCMpred score > 阈值), 单独 mutate r 风险高
   - 标记进 design_artifact, 推荐配套设计 r' 的 compensating mutation
3. **Consensus consistency check**:
   - weighted vs naive consensus 不一致的位置 → 标 "MSA-bias-suspect", 降权

## 与上下游的衔接
- **上游可选**:
  - `uniprot-fetcher` → 拿序列
  - `cazy-crawler` → CAZy 家族框架内的 MSA
- **本 skill 输出供后续使用**:
  - `esm-mutation-scan` → 在 candidate mutation 列表上跑 ESM
  - `pyrosetta-stability-scan` → 仅在 conservation 允许的位点跑
  - `catalytic-site-annotator` → 高保守位通常对应催化或辅因子, 双向交叉验证

## 失败模式与排查
| 现象 | 根因 | 解法 |
|---|---|---|
| MSA 太小 (< 50 seqs) | 蛋白罕见 / 数据库小 | 切大库 (bfd) 或降低 min_seq_id |
| 单 clade 占比 > 50% | 临床 / 病原微生物过表示 | 强制 weighted MSA + 报警 |
| Co-evolution 没强对 | MSA 太小, 信号差 | 标 "coevolution_unavailable", 不阻断 |
| ConSurf score 在边界 | metric 不一致 | 多 metric 取 majority vote |
| jackhmmer 跑太慢 | 数据库大 + 多 iter | 降到 mmseqs2 (快 10×) |

## 与 Anti-rule 的关联
- **Anti-rule 6 (naive consensus 不查 phylogenetic balance)**: 本 skill 强制 phylogenetic weighting 并报告 clade balance 数值. 不通过则 design agent 不允许用 consensus mutation 路线.
- **Anti-rule 2 (multi-mutation stacking 加性)**: 本 skill 输出的 strong co-evolution pair 警告 design agent multi-mutation 必须考虑耦合.

## 引用与出处
- Ashkenazy H et al. "ConSurf 2016: an improved methodology to estimate and visualize evolutionary conservation in macromolecules." Nucleic Acids Res 2016;44:W344-W350.
- Kamisetty H, Ovchinnikov S, Baker D. "Assessing the utility of coevolution-based residue-residue contact predictions in a sequence- and structure-rich era." PNAS 2013;110:15674-15679. (GREMLIN)
- Seemayer S, Gruber M, Söding J. "CCMpred—fast and precise prediction of protein residue-residue contacts from correlated mutations." Bioinformatics 2014;30:3128-3130.
- Jäckel C, Bloom JD, Kast P, Arnold FH, Hilvert D. "Consensus protein design without phylogenetic bias." J Mol Biol 2010;399:541-546. (与 NEG-CONSENSUS-jackel-2010-jmb 一致)

## Skill 版本
v1.0, 2026-04-29.
