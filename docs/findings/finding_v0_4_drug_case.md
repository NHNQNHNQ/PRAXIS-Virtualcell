# finding v0.4 W3.1 — Human drug response case:LINCS L1000 签名 MOA 一致性(真跑)

> 目标:证明 PRAXIS 能处理 **gene 以外的扰动**(药物),把 drug 对象规范化 → 路由到 signature 引擎 → 做真实签名分析 → **受治理裁决**(accept/downgrade/abstain),体现 R6"防过度承诺"。证据类型:`[Mac确定性]`(公开数据 + 确定性可复跑)。
> 对应 `docs/PLAN-v0.4-species-applications.md` 步骤 W3.1(C6)。**自主完成**:公开数据自取,无需用户提供。

## 1. 数据(公开,自主获取)

- **来源**:Enrichr `LINCS_L1000_Chem_Pert_up` / `_down`(公开、无凭证)。原始库各 ~15MB / 33132 签名 → **gitignore**;provenance(URL + sha256 + 大小)见 `data/drug_signatures/PROVENANCE.json`。
- **curated 子集**(committed,小):`data/drug_signatures/curated_subset.json` —— 6 药 × consensus top-100 up/down 基因 + MOA 标注。consensus = 每药跨所有 LINCS 条件最频繁的 top-100 基因(抗单条件噪声)。
- **MOA 标注**:curated 教科书药理(HSP90/HDAC/PI3K/mTOR 抑制剂),非本文新发现。

## 2. 分析 + 治理裁决(实跑,7 部分 case)

drug → 签名 → 与**同 MOA** 药物签名相似度[(up Jaccard + down Jaccard)/2] vs **跨 MOA** 均值 → 富集比。富集≥**1.5**(设定默认:同 MOA 须比跨 MOA 高 ≥50%)→ accept;否则 downgrade;无同 MOA 参考→downgrade;不在库→abstain。

| drug | MOA | n_sig | 同MOA伙伴 | 富集 | **裁决** |
|---|---|---|---|---|---|
| geldanamycin | HSP90 | 457 | tanespimycin | **2.65** | **accept**(MOA-consistent) |
| tanespimycin | HSP90 | 24 | geldanamycin | **3.45** | **accept** |
| vorinostat | HDAC | 377 | entinostat | 0.10 | **downgrade**(弱信号) |
| sirolimus | mTOR | 142 | 无 | — | **downgrade**(无同 MOA 参考) |
| notadrug123 | — | — | — | — | **abstain**(不在库) |

## 3. 关键点:治理防过度承诺(R6 硬证据)

- **HSP90 对验证方法有效**:geldanamycin↔tanespimycin 签名富集 **2.6–3.5×**(同 MOA 明显比跨 MOA 更像)→ 真实可检验信号,accept。
- **HDAC 对信号弱 → agent 主动降级**:vorinostat↔entinostat 富集仅 0.10(同 MOA 相似度 0.005 ≈ 跨 MOA)→ 系统**不硬说"MOA 一致"**,downgrade。即使 vorinostat 有 377 条签名(高 n),证据不支持就不 accept。
- **单例药无参考 → downgrade**;**未知药 → abstain 不虚构签名**。
- 这正是**"reliability-governed reporting prevents overclaiming"**:同一分析管线,信号强则 accept、信号弱/无参考则降级弃权,**不为了"跑通"而包装成功**。

## 4. 诚实边界

- LINCS L1000 签名是 **bulk/群体 consensus**(方向级 up/down 基因集),**非** per-cell 表达预测;噪声大。
- 富集阈值 1.5、consensus top-100 为**设定默认**(写明依据,非调优)。
- downgrade 不代表药物无效,仅表"签名证据不足以确证 MOA 一致"(如 HDAC 对受 entinostat 低 n / top-100 严格所限)。
- curated 6 药 × 4 MOA 是**演示子集**,非完备药物库;drug 案例证明的是**"agent 能处理药物扰动并受治理产出",非药物响应的完备刻画**。

## 5. 架构

- `praxis_virtualcell/predictors/embedding/drug_signature.py`:`DrugSignatureDB`(签名库)+ `run_drug_response_case`(7 部分 case)。route_table `(*, drug, *) → embedding`(W3.1 起非 data-gated,caution)。
- 测试 `test_drug_signature_case.py`(7 passed)覆盖 accept/downgrade(弱)/downgrade(无参考)/abstain 四种裁决 + 同 MOA>跨 MOA 可检验断言。**不训练任何模型**。

---

## 6. R2(v0.5)补充 — Drug dose-response(剂量-响应单调性)

- 数据:LINCS 剂量子集(`dose_response_subset.json`,geldanamycin/sirolimus/vorinostat 每剂量 top-150 共识)。
- 指标:参考态 = 信号最多剂量共识;recall(dose)=|dose_top ∩ ref|/|ref|;dose-recall 的 Spearman。
- **治理对照(实跑)**:

| drug | Spearman | max recall | 裁决 |
|---|---|---|---|
| geldanamycin | **0.90** | 0.06 | **accept**(单调剂量依赖) |
| sirolimus | 0.50 | 0.02(近零) | **downgrade**(签名重叠不足,不硬说剂量依赖) |
| vorinostat | 0.50 | 0.75 | **caution**(中等) |

- **幅度守卫**:max recall <0.05(sirolimus)→ 无足够信号评估剂量-响应 → downgrade(Spearman 不可靠时不硬判)。`predictors/embedding/drug_dose.py` + `test_drug_dose_case.py`(4 passed)。
- 诚实:downgrade 表"签名层无足够证据支持剂量依赖",非"药物无剂量效应"。不训练模型。
