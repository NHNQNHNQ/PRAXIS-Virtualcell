---
case_id: crispr-001-spcas9-knockout-tp53
schema_version: 1
edit_type: knockout_indel
target_gene: TP53
target_organism: hg38
cell_context: HeLa
editing_system: SpCas9
delivery_method: lentivirus
tools:
- CRISPOR
- CHOPCHOP
- GuideScan2
- CRISPResso2
- Doench Rule Set 3
key_paper_doi: 10.1038/nbt.3026
status: validated
provenance:
  source_type: literature
  doi: 10.1038/nbt.3026
  citation: Doench JG et al. (2016) Nat Biotechnol 34:184-191 — Optimized sgRNA design
    (Rule Set 2)
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- knockout_indel
- HeLa
- SpCas9
- TP53
- polyploid
- tumor_suppressor
---

# TP53 KO with SpCas9：guide design 经典 case

## Background
TP53 KO 在癌症 cell line 是高频实验。HeLa 本身含 HPV E6（degrade p53），但完全 KO 仍是 standard control。关键挑战：(1) p53 有 splice variants，guide 必须 hit 所有 isoform 共有 exon；(2) HeLa 多倍体，需多 allele KO 才生效。

## What I actually did
1. **Target exon 选择**：取 NM_000546（canonical isoform）early common exon——exon 4（DNA-binding domain N 端）。**避开 last exon**（NMD escape） + **避开 alternatively spliced 外显子**（如 exon 9 omitted in p53β）
2. **Guide 候选生成**：CRISPOR 输入 exon 4 序列 + genome=hg38 → 输出 ~30 个 NGG PAM guide
3. **Ranking**：
   - **Doench Rule Set 3 score** ≥ 0.6（高 cleavage activity）
   - **CFD off-target score**：每个 guide 全基因组扫描，cumulative CFD ≤ 0.2 是低风险
   - **Mismatch position weight**：seed region（PAM-proximal 12 nt）零 mismatch 的 off-target 是大问题
   - **GC% 40-60%**
   - **No restriction sites**（BsmBI/BbsI for cloning）
4. **Top 5 选择 + cloning**：lentiCRISPR v2 backbone，BsmBI overhangs：5'-CACCG[20mer]-3' + 5'-AAAC[20mer-rc]C-3'
5. **HeLa 多倍体考虑**：单 guide 可能 KO 部分 allele；推荐双 guide（不同 exon）或 single-cell clone screening
6. **Validation primer**：amplicon-seq with ~200 bp around cut site；Sanger as backup

## ★ 排除/不做的事
- **Last exon (exon 11) cut**：NMD 不降解，可能 truncated p53 仍有部分功能
- **First exon (exon 1)**：UTR 多，开始密码子可能下游 reinit 给截短蛋白
- **Alternatively spliced exon**：guide 命中部分 isoform 错过其他
- **CFD cumulative > 0.5 的 guide**：off-target 风险高
- **Single guide for polyploid cell line**（HeLa 三倍体）：KO efficiency < 50%
- **GC% > 70% / < 30%**：cleavage 活性显著下降

## ★ 失败模式
- **HeLa HPV E6 background**：p53 已被 E6 degrade，KO phenotype 难解读——必须用 wt p53 cell line（A549, MCF7）做对照
- **Off-target in tumor suppressor**：~5% guide 命中其他 TS gene（PTEN, RB1）造成 confounding
- **Indel signature 偏 in-frame**：3 nt 倍数 indel 不破坏 frame，蛋白仍有功能；选 guide 倾向 -1/+1 frameshift signature（DeepHF predict）
- **Splice site disruption**：cut site 距 splice junction < 20 nt 可能引入 cryptic splicing 而非 KO
- **Polyclonal vs monoclonal**：bulk pop 是 mosaic，需 single-cell sort 验证
- **Compensatory upregulation**：p53 KO 后 p63/p73 upregulate 部分 compensate

## Lessons → seeds for rules
1. **Target exon 选择规则**：early constitutive exon（in 所有 isoform）+ functional domain + 非 last exon
2. **Composite guide score**：Doench RS3 + CFD + GC + mismatch position weight
3. **多倍体 cell line 用双 guide**或 single-cell clone
4. **Cell context matters**：HPV+ cell line 不适合 p53 KO 研究
5. **Validation 三件套**：amplicon-seq + Western + functional readout（p21 induction by Nutlin）
6. **Frameshift bias**：选 -1/+1 indel-favoring guide
