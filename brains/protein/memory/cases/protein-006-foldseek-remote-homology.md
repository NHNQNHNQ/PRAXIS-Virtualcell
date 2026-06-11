---
case_id: protein-006-foldseek-remote-homology
design_task: structure_search_homology
target_pdb: 7K9I
fold_class: any
tools: [Foldseek, MMseqs2, DALI, TM-align, FATCAT]
key_paper_doi: 10.1038/s41587-023-01773-0
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# Foldseek 远源同源检索：sequence-level 找不到的怎么找

## Background
Sequence identity < 25%（"twilight zone"）时 BLAST/MMseqs2 几乎找不到同源；但折叠保守的 fold（Rossmann、TIM barrel、Greek key 等）通过 structure 仍可识别——Foldseek 把结构编码成 3Di 字母表，结构搜索快到秒级。Foldseek 论文 case：把 AlphaFoldDB 200M 结构索引化。

## What I actually did
1. **Query 准备**：拿一个新预测的 ESMFold 结构（PDB 格式）
2. **Foldseek easy-search**：`foldseek easy-search query.pdb db_pdb tmp/` 输出 hits ranked by TM-score / E-value
3. **关键参数**：
   - `--tmscore-threshold 0.5`：< 0.5 不算同 fold
   - `--alignment-type 1`：3Di+aa profile（不是单 3Di），更准
4. **DB 选择**：PDB100、AlphaFoldDB（small 100k subset）、UniRef-AFDB（巨大但慢）
5. **Sanity 比对**：top hits 在 PyMOL/ChimeraX align 看 TM-score 是否真 > 0.5
6. **混合搜索**：Foldseek + MMseqs2（序列）取并集——两个互补，纯结构会漏 close homolog（fold OK 但表面残基差异大），纯序列会漏 distant homolog
7. **跨 organism / 功能注释 transfer**：找到 50% TM-score 的同 fold 蛋白后，**功能 transfer 谨慎**——同 fold 不等于同功能（如 TIM barrel 容纳 60+ 种酶活性）

## ★ 排除/不做的事
- **TM-score < 0.5 当同 fold**：< 0.5 可能只是局部相似，不可信
- **直接 transfer 功能 from top fold hit**：同 fold 不等于同功能；要看 active site 残基保守性才能 transfer
- **不做 sequence parallel search**：纯结构会漏 high-seq-id 同源（结构 noise 让 TM-score 略低）
- **使用 single-chain prediction 但 query 是 multimer**：每条链分别搜
- **AlphaFoldDB 拿到的 hit 当 experimental**：predicted structure 也可能错——后续 binding site 比较要慎
- **忽略 Foldseek E-value**：除了 TM-score，E-value < 1e-5 才是可靠 hit

## ★ 失败模式
- **Membrane protein**：lipid 在结构里没有，alpha-helix bundle 都长得像；Foldseek 会给大量假同源
- **Coiled coil / IDR**：周期性 + 无规结构区段 3Di encoding 不稳，hit 不可信
- **Small protein (< 50 aa)**：3Di 字母太少，区分度低
- **Heavy disorder region**：predicted structure 中 disordered 段会被 encode 但 noise
- **Structure prediction error**：ESMFold/AF 结构如果错了，Foldseek 把"错结构"找的同类也是错的——要看 query pLDDT
- **Apo vs holo 形态差异**：底物结合改变 conformation，apo PDB 找到的 hit 可能在 holo 状态下不是同 fold

## Lessons → seeds for rules
1. **结构搜 + 序列搜并跑**，取并集；任一单方法都漏
2. **TM-score ≥ 0.5 + E-value ≤ 1e-5** 才进 top hits
3. **同 fold ≠ 同功能**：功能 transfer 必须验证 active site 残基保守
4. **Membrane / IDR / 小蛋白 query 标 caveat**——Foldseek 这些 case 不可信
5. **Query 结构质量必须报告**：predicted query 的 pLDDT mean 必须报，影响 search precision
6. **Database 选择 task-aware**：精挑 PDB100 高质量 vs AFDB 全覆盖
