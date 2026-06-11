---
rule_id: 15-hyaluronidase-engineering-landscape
schema_version: 1
rule_type: landscape
applies_to:
  cazy_families: [PL8, GH56]            # PL8 lyase 与 GH56 hydrolase 两 fold/机制
  property: substrate_specificity        # HA 分子量控制 / GAG 选择性 / 临床蛋白稳定性
  enzyme_classes: [lyase, hydrolase]
evidence_cases:
  - PL8-jedrzejas-2002-jbc               # 机制 + substrate 复合物结构
  - GH56-bookbinder-2006-jcontrolrel     # 临床蛋白工程化 (rHuPH20)
confidence: cold_start                   # 仅 2 evidence cases, 等 evidence 累积升级
last_updated: 2026-04-28
---

## 规则

透明质酸 / GAG 降解酶工程化按以下优先级:

1. **首先识别 fold + 机制**: PL8 lyase (β-elimination, α/α toroid fold) vs GH56 hydrolase ((β/α)8 TIM barrel + EGF-like domain) — 工程化 mask 与策略不同
2. **PL8 lyase 工程化主线 = cleft 表面 aromatic patch tuning**: HA 分子量控制 / processive vs endo 模式切换通过 surface Trp/Phe/Tyr 数量调
3. **GH56 hydrolase 工程化主线 = truncation 而非 mutagenesis**: 临床 PH-20 / 哺乳动物 hyaluronidase 的 GPI-anchor signal 截除是首要工程化, 非定点突变
4. **CS / HA / chondroitin substrate 选择性 = cleft 内 positive patch (Lys/Arg) 位置**: PL8 对 sulfate group 选择由 cleft 内正电荷 cluster 决定
5. **临床应用必选 source**: human PH-20 (GH56) > bacterial PL8 (免疫原性, 不适合体内); 工业 application 反之 (PL8 来源稳定 / 高活)

**强制排除区**:
- **PL8**: catalytic Asn-Tyr-His 三联体 + α/α toroid 内壁 + processive cleft 全表面 aromatic patch (改 endo/exo 模式时部分可调, 但 catalytic core 锁定)
- **GH56**: catalytic Glu (general acid) + Substrate-binding cleft aromatic + 多 disulfide (含 EGF-like domain) + N-glycosylation site (临床 application 必需)

## 依据

| evidence_case | 关键观察 |
|---------------|---------|
| `PL8-jedrzejas-2002-jbc` | Sm SpnHL substrate-bound 结构揭示 processive 机制 + Asn-Tyr-His 三联体催化几何 + cleft 内 Trp 主 sliding ramp |
| `GH56-bookbinder-2006-jcontrolrel` | rHuPH20 truncation engineering (去 GPI signal + N-端 + C-端) 是临床应用关键; 单点突变多失败, truncation 是 dominant 策略 |

## 边界

- 仅 PL8 + GH56 两个家族; 其他 hyaluronidase / GAG 酶 (PL16 chondroitinase ABC, GH84 等) 单独 landscape
- PL8 → GH56 mutation 转移**不可信** (fold 与机制不同, β-elimination vs hydrolysis)
- HA 分子量精确控制需配合 product 长度筛选 (不只 single mutation 即可)
- **临床应用** vs **工业应用** 工程化路线分歧 (人源 vs 微生物源, truncation vs mutagenesis)

## How to apply

- **Scoping Agent**: 识别用户目标是 'industrial GAG processing' 还是 'biopharmaceutical' — 路线分歧
- **Design Agent**: 按 PL8 / GH56 fold 选 mask, 应用 cleft engineering vs truncation 策略
- **Reviewer**: 检 临床场景是否选 human source + 是否含 truncation; 工业场景检是否考虑 fold-specific mask

## 升级路径

升 `confidence: low` 需要再增 ≥1 evidence case (建议补 PL16 chondroitinase 或 GH84 类 GAG 酶); 升 `medium` 需 ≥3 evidence cases 跨 ≥2 工程化策略 + 至少 1 个反例.
