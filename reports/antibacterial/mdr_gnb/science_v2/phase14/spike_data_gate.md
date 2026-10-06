# P14 spike:KP 小分子活性 QSAR 数据门(受阻:ChEMBL API 故障)

> 2026-07-17 · /loop 第 4 轮 · 只读探针 · **数据门未过(未验证),不写 TDD**

## 结论(一句话)

**P14 数据门本轮受阻于 ChEMBL/EBI API 外部故障,无法真拉 KP MIC 数据核实清洗后唯一化合物/scaffold 数。** 本地锚定的**估计**强烈提示 KP 数据充足(≈9400 唯一 / ≈3000 scaffold),但**这是估计不是门通过**——KP 的去盐/去重留存率可能与 EC 不同,必须待 ChEMBL 恢复后真拉真清才能定门。**不据估计写 TDD。**

## ChEMBL API 故障实证

- `https://www.ebi.ac.uk/chembl/api/data/status.json` → **HTTP 500**
- `activity.json?target_organism=Klebsiella pneumoniae&standard_type=MIC&limit=1` → **HTTP 500**(返回 EBI 网站 HTML 错误页,非 JSON)
- 重试(含加浏览器 User-Agent)→ 500 与连接错误交替 → 是 **EBI 服务端故障**,非本地网络/UA/查询问题(DNS/TCP/TLS 均通,拿到的是服务端 500)。

## 本地锚定的估计(真实数字,但仅供参考,非门通过)

从**本地 EC 数据**实测留存率外推 KP(B0 已记 KP raw MIC=31130):

| 指标 | EC(本地实测) | KP(B0 记 + 按 EC 留存外推) |
|---|---|---|
| 原始拉取测量数 | 90099 | **31130**(B0 探针记录) |
| 清洗后唯一化合物 | 27175 | 估计 ≈ **9389** |
| Bemis-Murcko scaffold | 8724 | 估计 ≈ **3014** |
| 留存率(唯一/原始) | 0.302 | 假设同 EC |
| scaffold/化合物 | 0.321 | 假设同 EC |

- EC 数字全部本地真跑(`escherichia_coli_mic_clean.parquet` + `_mic_raw.jsonl` + RDKit MurckoScaffold,parse 失败 0)。
- KP 估计 = 31130 × (27175/90099) 及 scaffold 同比外推。**假设 KP 留存率 ≈ EC**——这是外推,KP 实际关系/单位/重复分布可能不同,估计可上下浮动。
- 即便如此,~9400 唯一 / ~3000 scaffold 约为 EC 的 1/3,**量级上足以训一个 scaffold-GroupKFold QSAR**(远高于"几千化合物+上千 scaffold"的合理下限)。

## 预注册数据门判据(待真拉后判)

真拉真清 KP 后,数据门**通过**当:清洗后唯一化合物 ≥ 5000 **且** Bemis-Murcko scaffold ≥ 1500(约 EC 的 1/5;确保 scaffold GroupKFold 每折有足够独立骨架,防泄漏切分有意义)。低于此 → 诚实结论"KP 数据不足、不训"。**门槛此处预注册,真拉后不看结果再改。**

## 下一步

- ChEMBL 恢复后:`python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.chembl_pull --species klebsiella_pneumoniae`(pull_raw 游标分页 → clean 去盐去重取中位)→ 读清洗后唯一/scaffold 真数 → 判门。
- 门过 → 用 writing-plans 写 P14 TDD(KP artifact + registry `_SM_ACTIVITY_SPECIES` 加 KP + 证据分层按物种 gate + golden_compounds 加 KP)。
- 门未过 → 诚实记"KP 数据不足",转 P19/P12。
- **本轮不写 TDD、不据估计推进**(铁律:数据门未过就写 TDD = 编造)。
