# 数据质量核查(EC+KP,阶段 2.3)

## escherichia_coli
- 总行数 132095 · 唯一基因组 8008
- **冲突标签(同 genome×药 有 R 又有 S):49 组**
- 精确重复行:8577
- 缺基因型:0
- 物种名不含 genus:0
- 非标准 phenotype 值:无

## klebsiella_pneumoniae
- 总行数 28472 · 唯一基因组 1721
- **冲突标签(同 genome×药 有 R 又有 S):40 组**
- 精确重复行:11236
- 缺基因型:0
- 物种名不含 genus:0
- 非标准 phenotype 值:无

## 诚实结论
- **训练数据基本干净**:冲突标签仅 0.1–0.2%(_combo_rows keep-first 静默消解,微小噪声,
  不推翻 G2R strong 结论);精确重复行按 genome_id 去重已处理;缺基因型/非标准值/物种名错误全 0。
- 冲突 isolate 清单见 conflicting_labels.csv(如需更严格可 drop,但 <0.2% 不影响结果)。
