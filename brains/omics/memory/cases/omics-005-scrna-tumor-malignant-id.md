---
case_id: omics-005-scrna-tumor-malignant-id
modality: scRNA_seq
study: Kim et al 2020, Lung cancer scRNA-seq
public_accession: GSE131907
doi: 10.1038/s41467-020-16164-1
organism: Homo sapiens
tissue: NSCLC primary + LN met + brain met
tools:
- Scanpy
- inferCNV 1.18
- CopyKAT 1.1.0
- scVI
status: validated
validated: true
source: praxis_seed
study_design: case_control_tumor_normal
assay_subtype: 10x_chromium_v2
cell_type_focus:
- tumor_epithelial
- malignant_id
method_choice:
- infercnv
- copykat
- harmony
case_class: success
---

# Kim 2020 NSCLC：肿瘤恶性细胞识别（不能只靠 marker）

## Background
NSCLC scRNA-seq atlas 含原发灶/淋巴结/脑转移三个解剖位点，~200k cells。**肿瘤上皮 vs 正常上皮**是肿瘤单细胞研究的核心难题——marker（EPCAM/KRT19）两边都阳，必须靠 CNV inference 区分。

## What I actually did
1. 标准 scRNA pipeline（同 case-001）→ initial annotation（epithelial/immune/stromal 大类）
2. **Subset 出 EPCAM+ epithelial 子群**做 CNV inference
3. **inferCNV**：用 immune cells（T/B）作 reference（已知 diploid），window=100 genes，cutoff=0.1。输出每个 epithelial cell 的 CNV score 矩阵 + heatmap
4. **CopyKAT** 平行跑：用 GMM 二分类 aneuploid vs diploid。**两个工具结果做交集 + 投票**——单一工具假阳率 5-15%
5. **决策规则**：inferCNV CNV burden 高 + CopyKAT aneuploid + 来自 tumor sample（非 normal adjacent）= malignant；任一失败标 ambiguous
6. Malignant cells subset 后做 inter-patient 整合用 **Harmony with patient as batch**——肿瘤间异质性极大，naive concat 会按 patient 分群
7. Subclone 分析：在每个 patient 内 hierarchical cluster CNV score → 确认 clone 数

## ★ 排除/不做的事
- **靠 EPCAM/KRT19 等"epithelial marker"判恶性**：normal alveolar type 2 同样高表达，假阳一塌糊涂
- **不用 reference 跑 inferCNV**：noise level 不可校准
- **跨 patient 整合恶性细胞**：肿瘤间生物学差异 > 共性，整合后看到的是 patient effect 不是 tumor biology
- **依赖单一 CNV 工具**：inferCNV 假阳在高度增殖正常细胞（regenerating epithelium）；CopyKAT 假阴在低 CNV burden 肿瘤
- **CNV 当唯一判据**：早期/低突变负荷肿瘤 CNV 可能轻；要结合 sample origin + driver mutation expression

## ★ 失败模式
- **Reference contamination**：用 NK 当 reference 时若混入 NKT，CNV 估计偏
- **Aneuploid normal cells**：肝再生肝细胞、衰老组织部分细胞 CNV 异常但非肿瘤——靠 sample origin 区分
- **Mixed malignancy**：腺癌+鳞癌共存的肿瘤会有两个 CNV pattern，hierarchical 聚类后才看得出
- **Brain met vs primary CNV**：metastasis 经历 bottleneck，subclone 收窄；不能假设 met 的 CNV pattern == primary

## ★ QC sanity check (known answer)
- Anchor (Kim 2020 NSCLC GSE131907)：
  - **Tumor sample** 内 epithelial subset 中 malignant fraction (inferCNV ∩ CopyKAT 共识) 在 30-60%
  - **Normal-adjacent sample** 内同 epithelial subset 中 malignant fraction < 10%
  - inferCNV 与 CopyKAT 共识率 > 70%（disagreement 标 ambiguous）
  - Per-patient subclone 数（hierarchical cluster CNV）通常 2-5 个
- Pass criterion：tumor 30-60% malignant + 共识率 > 70%
- Fail criterion：tumor < 20% malignant → reference cell 选错（NK + NKT 混入？）；共识率 < 50% → tool 选择不互补

## Lessons → seeds for rules
1. **肿瘤恶性识别 ≥ 2 工具交集**（inferCNV + CopyKAT 或 + Numbat），单一工具不接受
2. **Reference 必须是已知 diploid 免疫细胞**（最好 T cell，丰度高、CNV 干净）
3. **Malignant subset 跨 patient 用 Harmony with patient batch**，期望保留 inter-tumor 异质性
4. **CNV + sample origin + driver expression 三角验证**——任一缺失置 confidence: ambiguous
5. **Subclone 分析在 patient 内做**，不跨 patient
