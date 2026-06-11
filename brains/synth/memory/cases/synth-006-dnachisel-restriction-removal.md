---
case_id: synth-006-dnachisel-restriction-removal
task: dna_constraint_optimization
input_protein: GFP variant for cloning
constraints: [no_BsaI, no_BsmBI, no_NotI, GC_balance, no_homopolymer]
tools: [DNAchisel, GenScript, IDT optimizer]
key_paper_doi: 10.1093/bioinformatics/btaa558
status: validated
---

# DNAchisel：在保持氨基酸序列下移除 forbidden site

## Background
合成基因经常需要满足多 constraint：specific restriction sites 不可在内（用于 cloning）、GC balance、避免 homopolymer、避免 splice site etc. **DNAchisel 是开源 constraint solver**，simulated annealing 在 silent codon space 搜索。

## What I actually did
1. **Input**：GFP cDNA 720 bp
2. **Constraints declared**:
   - `AvoidPattern("BsaI_site")` (×2 strands)
   - `AvoidPattern("BsmBI_site")`
   - `AvoidPattern("NotI_site")`
   - `EnforceGCContent(mini=0.4, maxi=0.6, window=80)`
   - `AvoidPattern(homopolymer_5plus)`
   - `AvoidChanges()` for protein sequence (silent codon only)
3. **Optimization**：DNAchisel simulated annealing + repair
4. **Output**：original 含 1 BsaI + 2 BsmBI → optimized 0 forbidden site
5. **GC profile check**：sliding window GC 维持 40-60%
6. **Verify**：sequence translate back → identical protein
7. **Multi-constraint conflict resolution**：DNAchisel reports 不能完全满足时哪 constraint 放弃

## ★ 排除/不做的事
- **Manual silent mutation**：人工耗时 + 易遗漏；用 solver
- **Single strand check**：restriction site 双链 palindrome 必须 both strand 查
- **Single window GC**：100 nt window vs 30 nt window 给 different signal
- **Constraint conflict 不报**：constraint 太多无 solution，必须 declared
- **Forget polyA / cryptic splice in mammalian host**：mammalian context 还需 splice avoid
- **不 verify protein 一致**：optimization bug 偶 introduce missense

## ★ 失败模式
- **Highly constrained sequence**：multi-constraint 让 search space 几乎为空
- **Local minima**：simulated annealing 偶 stuck，需 multi-restart
- **Long sequence (> 5 kb)**：runtime 长，可能不收敛
- **Forbidden pattern in essential codon stretch**：某些 protein 区域 codon 选择极少，can't avoid
- **Hidden constraints**：未声明的 promoter / poly-A signal 偶被 introduce
- **Compiler 误报**：DNAchisel report no constraint violation 但下游 cloning 失败 → 通常是 host-specific feature 未模型化

## Lessons → seeds for rules
1. **Solver-based optimization** > manual
2. **Both strand restriction site check**
3. **Multi-window GC profile**
4. **Constraint conflict 必报** if no full solution
5. **Verify protein sequence preserve** post-optimization
6. **Mammalian context** add splice / polyA avoidance
7. **Multi-restart** simulated annealing 避 local minima
