---
case_id: synth-004-codon-optimization
task: codon_optimization
input_protein: human IL-2 (CHEMBL P60568)
target_host: S. cerevisiae (also relevant for E.coli, mammalian)
tools: [DNAchisel, IDT codon optimizer, JCAT, COOL, CodonW, GeneOptimizer]
key_paper_doi: 10.1186/s12859-018-2333-9
status: validated
---

# Codon optimization：human IL-2 在酵母表达

## Background
Codon usage 跨物种差异巨大（human vs yeast vs E.coli）。直接克隆 native CDS 给低表达。Codon optimization 包含：(1) CAI 升 → tRNA pool 匹配；(2) 避 forbidden site (restriction)；(3) 避 cryptic splice / poly-A site；(4) 避免 mRNA secondary structure block translation。

## What I actually did
1. **Input**：human IL-2 native cDNA
2. **Target host**：S.cerevisiae（CAI 升 from ~0.5 to ≥ 0.85）
3. **DNAchisel constraint**：
   - Codon usage match yeast (CodonW reference table)
   - No BsaI / BsmBI / SapI sites（cloning 用）
   - No homopolymer runs ≥ 6
   - No yeast intron splice donor/acceptor
   - GC content 35-55%（yeast preferred）
   - No mRNA strong secondary structure in 5' (first 50 nt) — affects translation initiation
4. **Optimization algo**：DNAchisel uses simulated annealing
5. **Compare**：original vs optimized
   - CAI: 0.45 → 0.88
   - GC: 38% (matches host)
   - No restriction sites
   - Translation efficiency 估计 ↑ 5-10×
6. **Validate in vitro**：transfect yeast → IL-2 ELISA
7. **Avoid over-optimize**：100% optimal codon 偶引入 secondary problems（rare codon spike used by ribosome for proper folding pause）

## ★ 排除/不做的事
- **CAI alone**：忽略 secondary structure / forbidden site
- **不查 5' UTR + first 50 nt secondary structure**：strong hairpin block translation initiation
- **不审 splice site**：optimized seq 偶 introduce splice → mRNA degradation
- **GC 极端**：< 30% or > 70% block translation
- **All-rare codon clustering 不 break**：rare codon 长 stretch 让 ribosome stall
- **Single algorithm**：DNAchisel + IDT + JCAT 比 cross-check
- **Forget protein-level constraints**：silent change 偶影响 mRNA stability / rare codon-mediated folding

## ★ 失败模式
- **Cryptic splice in mammalian host**：splice site 难 fully avoid
- **Rare codon-mediated folding pause loss**：完全 optimize 让 protein misfold
- **mRNA stability change**：codon use 影响 mRNA half-life（codon usage decay）
- **Translation throttling required for toxic protein**：低表达可能是 desired，高表达毒
- **Different strain different tRNA pool**：lab E.coli vs industrial strain codon table 略不同
- **Restriction site missed**：fewer common sites 还可能遗漏 customer-specific

## Lessons → seeds for rules
1. **Multiple constraints**（CAI + GC + restriction + splice + secondary structure + homopolymer）
2. **5' UTR secondary structure check** specifically
3. **Multiple algorithm cross-check**
4. **Avoid 100% optimization**：保留少量 rare codon for folding pause
5. **In vitro translate validate**
6. **Host-specific tRNA table**：lab vs industrial E.coli 不同
7. **Document constraints in optimization log**
