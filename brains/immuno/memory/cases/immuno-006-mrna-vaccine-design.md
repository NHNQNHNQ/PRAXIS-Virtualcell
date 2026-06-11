---
case_id: immuno-006-mrna-vaccine-design
schema_version: 1
task: mrna_vaccine_sequence_design
immuno_task: mrna_vaccine_sequence_design
antigen_class: viral
hla_class: population_coverage
hla_alleles: []
peptide_length_bin: n/a
disease_indication: infection_sars_cov_2
target_pathogen: SARS-CoV-2 Spike (Omicron BA.5)
target_protein_uniprot: ["P0DTC2"]
modality: mRNA + LNP
tools: [LinearDesign, mRNA codon optimizer, RNAfold, ARNIE, IDT codon tool, Vaxgen]
key_paper_doi: 10.1038/s41586-023-06127-z
status: validated
source: praxis_seed
---

# mRNA 疫苗序列设计：codon optimization + 二级结构 + UTR

## Background
mRNA 疫苗（Pfizer/Moderna COVID）设计涉及：(1) ORF codon optimization（CAI + GC balance）；(2) 二级结构（folding stability 影响半衰期）；(3) 5'/3' UTR；(4) modified nucleoside（pseudouridine）减 immunogenicity；(5) cap structure。LinearDesign（He et al 2023 Nature）首次形式化"最优 stable + optimal codon" mRNA 设计。

## What I actually did
1. **Antigen 选择**：Omicron BA.5 spike 全长 + 2P prolyl mutations（K986P/V987P 稳定 prefusion 形态）
2. **Codon optimization**:
   - CAI (Codon Adaptation Index) ≥ 0.85 in human
   - GC content 45-65%
   - Avoid restriction sites (BsaI/BsmBI for cloning)
   - Avoid extreme rare codons
3. **Secondary structure (RNAfold)**:
   - MFE (minimum free energy) → low MFE = stable structure = high half-life in cell
   - 但太 stable → translation efficiency 降；balance 是 art
   - LinearDesign: 同时优化 CAI + MFE
4. **5'/3' UTR**：复用 BNT162b2 / mRNA-1273 验证 UTR，OR 设计 strong-translation UTR (HBA1, AES)
5. **Cap structure**：m7G + Cap1 (2'-O-methyl on first nucleotide)
6. **Pseudouridine substitution**：100% U → m1Ψ 减 TLR activation, 提升 translation
7. **PolyA tail**：100-150 nt
8. **Cross-strain coverage**：多 strain consensus epitope OR multivalent (BA.5 + XBB ratio)
9. **In vitro test**：transfect HEK293 → GFP fusion 测 translation；测 IFN-α response

## ★ 排除/不做的事
- **Native CDS sequence 不 codon optimize**：低 CAI = 低 translation
- **MFE only / CAI only**：单目标过度优化损另一
- **U 不 modify**：未修饰 U 强 TLR7/8 → IFN response 灭活 mRNA
- **5'/3' UTR 不优化**：generic UTR 比 strong UTR 表达低 5-10×
- **Cap0 (no 2'-O-methyl)**：触发 RIG-I → IFN
- **Single strain target without coverage analysis**：variant escape 风险
- **不评估 immunogenicity 风险**：parent protein 与人 cross-react peptide 引入 autoimmune

## ★ 失败模式
- **High GC content secondary structure block translation**：> 70% GC 高度 stable hairpin 阻 ribosome
- **Cryptic splice site**：codon optimized 序列偶然 introduce splice site → mRNA degradation
- **CpG dinucleotide**：高 CpG 触发 TLR9 → 免疫 inactivation
- **N-terminal signal peptide bias**：optimized N-term affecting ER targeting
- **In vitro vs in vivo expression discrepancy**：mouse vs human cell different dynamics
- **LNP delivery**：mRNA 设计好但 LNP composition 决定 in vivo distribution

## Lessons → seeds for rules
1. **LinearDesign or similar joint CAI + MFE optimizer**
2. **N1-methylpseudouridine (m1Ψ) substitution**
3. **Cap1 + optimized UTR**
4. **CpG dinucleotide minimization**
5. **Cross-strain consensus 或 multivalent**
6. **In vitro translation + IFN response 测 必步**
7. **2P prolyl 等 conformation-stabilize mutation** for class I fusion proteins
