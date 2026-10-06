# S4:colistin 标签质量核查(rare_combo QC)

colistin 表型标签噪声高(见 failure_modes)。本表诚实量化:冲突标签率、缺基因型率、unknown-ST 率。

| species | drug | 原始行 | 唯一基因组 | 建模行 | 冲突标签 | 冲突率 | 缺基因型 | 缺基因型率 | unknown-ST | unknown-ST率 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| klebsiella_pneumoniae | colistin | 265 | 237 | 238 | 0 | 0.0 | 0 | 0.0 | 11 | 0.0462 |
| escherichia_coli | colistin | 621 | 526 | 541 | 0 | 0.0 | 0 | 0.0 | 8 | 0.0148 |
| pseudomonas_aeruginosa | colistin | 267 | 142 | 144 | 1 | 0.007 | 0 | 0.0 | 9 | 0.0625 |
| acinetobacter_baumannii | colistin | 342 | 298 | 303 | 1 | 0.0034 | 0 | 0.0 | 3 | 0.0099 |

**读法**:冲突标签率反映同一菌株重复测定的 R/S 分歧(折点/测定噪声的直接体现);unknown-ST 株不进 ST 分组 OOF(被剔除),故建模评估的有效样本 < 原始。

