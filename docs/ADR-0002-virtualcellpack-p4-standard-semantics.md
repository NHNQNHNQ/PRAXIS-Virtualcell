# ADR-0002：VirtualCellPack P4 标准语义层

- 状态：Accepted（P4）
- 日期：2026-07-27
- 唯一起始基线：`ac0fea48c6e8b0fdf27eff9c0852ee43035ff97a`
- 范围：Pack 内物种、细胞、特征、条件、扰动和 named split 的离线确定性语义验证。
- 明确不做：在线 ontology 查询、ontology 自动补全、ortholog projection、随机划分、数据归一、模型接入、权重或大数据入 Git、UI 修改。

## 决策

P4 新增 `vc.pack.v0.2`，保留 `vc.pack.v0.1` 的解析、序列化和 fingerprint 语义。两个版本不混用字段：v0.1 继续使用旧 `condition`；v0.2 必须使用 `feature_semantics`、`cell_semantics`、`conditions`、`perturbations` 和带名称及 leakage guard 的 `split`。未知字段与不完整版本仍 fail-closed。

### 物种与特征

- 物种必须使用 `NCBITaxon:<digits>`；v0.2 assembly 必须是带版本号的 `GCA_` 或 `GCF_` accession。
- v0.2 的 `identity.feature_key` 和 `feature_semantics.id_source` 都固定为 `var_names`。
- `var_names` 是模型和外键使用的 canonical feature ID。当前离线支持 `ensembl_gene` 与 `ncbi_gene_curie` 两种显式格式。
- `symbol_field` 只产生显示标签；symbol 可重复，不能替代、改写或补齐 feature ID。
- perturbation target 必须逐字命中同一 Pack 的 `var_names`。不存在跨物种映射、symbol lookup 或 ortholog fallback。

### 细胞 identity、state 与 context

`cell_semantics` 用互不相同的列分别声明：

- `identity`：细胞类型或细胞系身份；
- `state`：处理前生物状态；
- `context`：组织、培养基或其他实验语境。

列值必须是 `CL:`、`UBERON:` CURIE、Cellosaurus 的 `cellosaurus:XXXX` CURIE/`CVCL_XXXX` accession，或在 manifest `local_terms` 中以 `id`、`label`、`definition` 完整声明的本地 CURIE。Runtime 只做语法、前缀和本地定义校验，不访问网络，也不声称验证了外部 ontology 当前版本中的术语存在性。

### conditions、perturbations 与 control

- observation 的 condition 和 perturbation 值分别是 manifest catalog 的外键。
- perturbation target 是 canonical feature ID 外键；control 不得有 target，非 control 必须显式声明 target。
- condition 的 dose/time 分别由数值列与单位列组成。数值必须有限且非负；单位只接受离线白名单，不做隐式换算。
- `matched_control` 必须指向 Pack 中存在的 condition。control condition 必须自匹配；非 control 必须匹配到 control perturbation。
- matched control 与实验 condition 必须具有相同 identity、state、context、time 和 split。dose 不自动改写，也不作为相等前提，以允许显式的零剂量或 vehicle control。
- 同一 condition ID 的上述语义必须完全一致。

### named split 与 leakage guard

v0.2 split 必须是 `predefined`、有非空 `name`、列出全部 partition，并声明至少一个 `leakage_guard`。普通 guard 名称指向 observation 列；保留键 `target_ids` 从 perturbation 的 target 外键展开，防止不同 perturbation ID 把同一 feature 放入多个 partition。每个 guard 值只能出现于一个 partition；所有声明 partition 都必须在数据中出现。验证器不生成 split、不随机分配，也不去重。

## 验证顺序与真相边界

1. manifest strict schema；
2. Pack 相对路径、size、SHA-256；
3. H5AD read-only backed open 与 shape/X 映射；
4. canonical feature、cell semantics、condition/perturbation/target 外键；
5. control matching、dose/time 与 leakage guard；
6. 仅在全部通过后返回 `CanonicalOmicsView`。

该层只证明 `pack_valid` 的结构与语义部分，不推导 `model_compatible` 或 `scientifically_validated`。LLM 不参与任何验证或裁决。

## 验证 fixture

仓库只保存三份小型 YAML fixture source：

- human：NCBITaxon + GRCh38 + Cellosaurus/UBERON + Ensembl gene；
- mouse：NCBITaxon + GRCm39 + CL/UBERON + Ensembl gene；
- bacteria：NCBITaxon + ASM584v2 + 有定义的本地 cell/state/context CURIE + NCBIGene CURIE。

测试在临时目录生成 tiny H5AD 并写入实际 size/hash；二进制 fixture、大数据和权重不进入 Git。
