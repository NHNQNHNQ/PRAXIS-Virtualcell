# ADR-0003：VirtualCellPack P5 多组学与显式特征对齐

- 状态：Accepted（P5）
- 日期：2026-07-27
- P5 唯一起始基线：`a229699deac1e791252739df71f4e4202cc72bac`
- 范围：MuData/H5MU 多组学 Pack、配对/部分配对 observation、模型特征合同和可审计对齐。
- 明确不做：新增模型、模型执行、数值预测、数据归一、自动补零、自动去重、随机划分、在线 ontology、ortholog/同源转换、UI 修改。

## 决策

### `vc.pack.v0.3` 多组学合同

P5 新增 `vc.pack.v0.3`，不修改 `vc.pack.v0.1` 和 `vc.pack.v0.2` 的序列化或
fingerprint。v0.3 使用一个声明并经过 size/SHA-256 验证的 H5MU asset，并在
`multiomics.modalities` 中按顺序声明至少两个 modality。每个 modality 独立声明：

- H5MU key；
- modality 名称与 ontology CURIE；
- feature namespace 名称与版本；
- `var_names` feature ID 格式与可选 display-only symbol 列；
- 精确 observation×feature shape。

v0.3 不得同时出现 v0.1/v0.2 的单 modality、单 matrix 或顶层
feature-semantics 字段。全局 observation identity 固定为 `obs_names`，每个 modality
的 feature identity 固定为 `var_names`。RNA/基因特征沿用 Ensembl/NCBI Gene
合同；蛋白特征支持带 `UniProtKB:` 前缀的
[官方 6 位或 10 位 accession 格式](https://www.uniprot.org/help/accession_numbers)。
格式验证不查询网络，也不证明 accession 当前存在。

`perturbations.target_modality` 必须显式指向一个已声明 modality。扰动 target
只在该 modality 的 canonical feature ID 空间中解析；不得从 symbol、其他 modality
或其他物种猜测 target。

### observation 配对语义

`observation_pairing` 只有两个合法值：

- `paired`：所有 modality 的 observation 必须与全局 observation 完全相同且顺序
  相同；
- `partially_paired`：全局 observation 必须等于各 modality observation 的并集，
  必须存在真实跨 modality 重叠，也必须存在真实缺测。

loader 不为 modality 中不存在的 observation 造行或补零。选择全局 observation
后，每个 modality 只返回其中真实存在的 observation；`shared_observation_ids`
只记录所选 observation 中所有 modality 共同拥有的 ID。

H5MU 通过公开 `mudata.read_h5mu(..., backed="r")` 只读打开，并显式设置
`pull_on_update=False`，不让 MuData 隐式拉取或合并 annotation。shape、modality
顺序、global/modality observation 关系、matrix format、feature ID、P4
condition/control/split/leakage 语义全部通过后，才返回 `CanonicalMuDataView`。
`PackRegistry` 对 v0.3 必须走同一完整 loader；缺少 `omics` extra 时 fail-closed，
不得降级成只验证 manifest/hash。

### `ModelFeatureContract`

模型输入通过独立的 `vc.model-feature-contract.v1` 声明：

- model ID/version；
- taxonomy 与 versioned assembly；
- modality key；
- feature namespace 名称/版本和 ID 格式；
- 模型要求的精确、有序 feature ID；
- 是否显式允许 reorder；
- 显式 drop 集；
- 带有限常数的显式 fill 规则；
- 可选 mapping asset 的 ID、相对路径、版本和 SHA-256。

合同未知字段、重复 feature、非 canonical ID、非有限 fill、布尔伪数值和无法转换
成有限浮点数的超大整数都 fail-closed。合同 canonical JSON 的 SHA-256 是
`contract_fingerprint`；mapping asset 的版本或 hash 改变会改变该 fingerprint。

### 对齐操作与 provenance

默认模式是严格逐字相等：taxonomy、assembly、modality、namespace 名称/版本、
ID 格式、feature 集和顺序任何一项不匹配都拒绝。只允许下列显式操作：

| 操作 | 唯一授权来源 | 禁止的隐式行为 |
|---|---|---|
| alias | hash/version 绑定的 `vc.feature-mapping.v1` 规则 | 不剥 Ensembl version，不查 symbol |
| aggregate | mapping asset 中的 sources、target 与 `sum`/`mean` | 不因重复或多对一自行聚合 |
| drop | `ModelFeatureContract.drop` | 不静默丢弃额外 feature |
| fill | `ModelFeatureContract.fill` 的 feature ID 与有限常数 | 不自动补零、不从均值或邻近 feature 猜值 |
| reorder | `ModelFeatureContract.reorder=true` | 不静默排序 |

mapping JSON 拒绝重复 key、重复 source、alias/aggregate source 重叠、重复 target、
未知 source、非 canonical ID、ID/version/hash 不一致和越出 root 的路径。不存在
ortholog、同源转换或跨 namespace fallback。

成功后返回 `vc.alignment-report.v1`，记录合同 fingerprint、mapping asset 身份、
source/target feature 顺序与 shape，以及按执行顺序记录每个 alias、aggregate、
drop、fill、reorder。无变换的严格匹配报告保留空 steps。

## 三层状态

三层状态仍相互独立，不得向上自动升级：

1. `pack_valid`：v0.3 manifest、资产 bytes 和完整 H5MU/科学语义验证通过；
2. `model_compatible`：指定 modality 对指定 `ModelFeatureContract` 严格匹配或仅经
   合同显式授权的操作成功，并产生 `AlignmentReport`；
3. `scientifically_validated`：必须由独立、版本和口径匹配的实验/benchmark
   evidence 给出，本阶段不授予。

Pack 可 valid 但没有任何兼容模型；成功对齐也只证明输入合同兼容，不证明模型
预测有效。LLM 不参与三层状态、数据真相、数值变换或最终裁决。

## fixture、依赖与分发

仓库保存一份 tiny human RNA+protein YAML source 和一份小型 mapping JSON。测试
在临时目录生成 CSR H5MU，计算真实 size/hash 并写 manifest；二进制 H5MU、真实
数据集和模型权重不进入 Git。复现步骤见
[`runbooks/VIRTUALCELLPACK-MULTIOMICS.md`](runbooks/VIRTUALCELLPACK-MULTIOMICS.md)。

`mudata>=0.3.10,<0.4` 只加入 `omics` extra 和完整 dev lock，不进入精简 runtime
lock。当前锁解析为 MuData 0.3.10，并按其兼容范围使用 `scverse-misc` 0.1.1。

## 已知限制

- 当前 v0.3 每个 Pack 只声明一个 H5MU asset；
- 当前实现支持 CSR、CSC 和 dense `X`，不解释 layer/raw/obsm；
- 部分配对只表达 observation membership，不做跨 modality imputation；
- feature mapping 只支持显式 alias、`sum`/`mean` aggregate，不提供 ontology 或
  sequence-based mapping；
- 对齐会物化所选 modality matrix；本阶段未实现流式超大矩阵变换；
- registry 是进程内验证快照，不提供 Pack 签名或跨进程文件系统事务；
- 本阶段没有把任何 model zoo 条目升级为 available，也没有运行或验证模型。
