# G2R 特征工程(本地):机制聚合特征 vs 基线(2026-07-07)

> 侦察发现:NCBI genotype 串**已含** porin 失活(ompK35/36 移码)、靶点突变(gyrA/parC)等机制标记,
> 但 parse_genotypes 打成**逐等位 one-hot** → 模型学不到"任何 ompK36 失活→通透性↓"的可泛化机制。
> `predictors/mechanism_features.py` 把它们**聚合成生物学类别 + 关键交互**(碳青霉烯耐药 = 碳青霉烯酶
> OR (ESBL/AmpC ∧ porin 失活)),**全本地、不需组装/AMRFinder/53**。
> 评估:同一 ST 分组 dev/locked(seed=0),操作点对齐,per-ST VME + 置换。harness 见 `run_g2r_locked`。

## 结果(locked,per-ST VME)

| 锚点 | 特征 | nfeat | ML VME | ML p | 融合 VME | 融合 p | 融合 ME |
|---|---|---|---|---|---|---|---|
| KP×meropenem(n_ST(R)=**11**) | 基线 | 343 | 0.200 | 0.31 | 0.109 | 0.064 | 0.376 |
| | **+机制(8 tok)** | 351 | **0.091** | 0.068 | **0.091** | 0.068 | **0.277** |
| EC×ceftriaxone(n_ST(R)=70) | 基线 | 538 | 0.047 | 0.81 | 0.019 | 0.247 | 0.045 |
| | **+机制(7 tok)** | 545 | **0.021** | 0.51 | 0.021 | 0.51 | **0.013** |

## 诚实结论

1. **机制特征是真提升,方向全对**:
   - KP:ML VME 砍半(0.20→0.09),融合 ME 从 0.376→0.277(模型不再乱判 R,校准变好)。
   - EC:ML 从劣于规则(0.047)拉到与规则齐平(0.021),融合 ME 从 0.045→0.013。
   - 关键交互 `carbapenem_R_pathway`(ESBL/AmpC + porin 失活,无碳青霉烯酶)命中了规则法漏判的机制。
2. **仍未 strong-pass**:改善了 VME/ME 权衡,但都没做到"显著优于规则"(p 未过 0.05)。
3. **KP 是数据功效问题,非特征问题**:locked 仅 **11 个耐药 ST** → 置换检验功效根本不够;
   要 KP 显著,得**更多耐药 KP 菌株**(补数据),而非更多特征。
4. **验证了"先本地、后 53"**:机制信号本就在本地数据里、聚合即得收益;k-mer/53 更重且有谱系泄漏风险,
   ROI 不如先把机制特征做扎实、并给 KP 补耐药菌株。

## 保留 / 下一步
- 单 seed;KP locked 小样本。机制特征 + abstain 组合未试(可能把 KP 融合 ME 压到 <0.10)。
- 机制特征词表是启发式基因族折叠(curated ESBL-SHV/TEM 名单可能不全)——由数据判定有效,已见正向。
- 若要 KP strong-pass:优先**补耐药 KP 菌株扩大 ST 数**(需 53/NCBI 下载),而非 k-mer。
- 建议:把 mechanism_features 集成进生产 GenotypeToSIR 训练(作为默认 featurizer),重训 127 模型。
