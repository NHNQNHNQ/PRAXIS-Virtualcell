# 菌株参考组学输入

当前平台向 LLM 提供有来源的、给药前的菌株组学背景。组学加载层负责读文件、检查身份和数值、返回特征注释与来源定位；药物活性、杀伤和作用机制的判断由 LLM 生成。原有 v1 RNA profile 保持兼容；v2 声明接口支持基因组、转录组、蛋白组单独输入或组合。加载层没有恢复旧 MIC/AMR 模型、实测 MIC 查表、扰动预测或世界模型，也不把旧八维状态向量作为实测组学。

当前默认使用 `praxis.strain-reference.v1`：每个具体菌株的每个模态只引用一个 native v1/v2 profile，校验完全一致的 species、strain、genotype。允许同菌株各模态来自不同样本或培养条件，分别保留条件和 native source IDs；关系为 `same_strain_reference`，不声明实验配对。未知基因型不代表已验证野生型，别名与突变株不会自动合并。单模态和组合使用同一加载入口，集合仅存指针。旧物种集合保留兼容读取，但 CLI/Web 默认和训练索引已改为菌株。配置见 [STRAIN-TRAINING](STRAIN-TRAINING.md)。

本地默认 `AB5075-STRAIN-REFERENCE` 引用 AB5075 基因组、下述历史 RNA 与实测蛋白组；MG1655、PAO1 也各有三模态。K. pneumoniae 的 HS11286、K26、NCTC418 是三个不同菌株，分别保留单模态档案。另有 18 个 E. coli 基因组参考。加载不会把 HS11286 的参考映射命名空间误认为 K26 RNA 的来源菌株。

## 已有 AB5075 profile 的含义

历史 RNA 原生输入位于 `data/organisms/AB5075-AZI000/`，由 `manifest.json`、`baseline.npz` 和 `annotations.csv` 组成。默认菌株集合引用它，不复制这些文件。

| 字段 | 当前值或含义 |
| --- | --- |
| 菌种 | *Acinetobacter baumannii*，`NCBITaxon:470` |
| 菌株 | `AB5075` |
| 研究来源 | `PRJNA658638`，AbaumPRECISE 作者表达与元数据 |
| 原始样本 ID | `Abaum_0017`、`Abaum_0023` |
| 条件 | `AZI_000`，未暴露参考条件，培养基 `CA-MHB` |
| 模态 | `bulk_RNA_seq` |
| 观测单位 | `historical_condition_mean`：两个声明的未处理源样本的历史条件均值 |
| 基因命名空间 | `ABUW native locus tags` |
| 覆盖 | 3895 个表达特征，3895 个有参考注释的特征 |
| 单位 | `author_log2_TPM_QC` |
| 尺度 | `author_log2_tpm_qc_unscaled_ABUW_namespace` |
| 未知字段 | 采样时间、温度、生长阶段、详细基因型均为 `null` |

数值保持作者 QC 表达的原始尺度，没有再做标准化。不能把这个单位改称 TPM、计数或 `log2(TPM+1)`；对数偏移量尚未独立确认。源表中的时间、温度、生长阶段和基因型占位 `0` 不代表实测生物学零值，因此 manifest 保持 `null`，概览会列出 `unknown_fields`。

这个 profile 是特定培养基中的历史未处理参考背景。它不代表新分离株，也不是候选药物给药后的状态。蛋白 ID、产物描述和 contig 来自 `AB5075_original` 参考注释，表示参考翻译/注释，不表示该样本实测了蛋白丰度、靶点结合或药物效能。

注释按同一参考中的明确 locus tag 精确关联，保留参考表与映射表的行号。表达仍使用原生 `ABUW_*` ID，不通过同源基因把别的菌株表达值替换进来。

## 查看概览与查询基因

安装环境见 [INSTALL.md](INSTALL.md)。查看本地数据不需要调用 LLM，也不需要 API key：

```bash
.venv/bin/praxis-vc profiles
.venv/bin/praxis-vc inspect --profile AB5075-AZI000
```

自定义数据根是全局参数，放在子命令之前：

```bash
.venv/bin/praxis-vc --data-root /private/tmp/praxis-organism-rebuild profiles
.venv/bin/praxis-vc --data-root /private/tmp/praxis-organism-rebuild inspect --profile AB5075-AZI000
```

Python 接口直接返回可追溯字典：

```python
from praxis_virtualcell.omics import load_profile

profile = load_profile("AB5075-AZI000", data_root="data/organisms")
overview = profile.overview()
hits = profile.search_annotations("dnaA")
evidence = profile.query_genes(["ABUW_0001"])
```

本地真实数据中的 `ABUW_0001` 注释为 `dnaA`，表达值为 `5.837963104248047`，单位和尺度如上；蛋白 ID 为 `AKA29801.1`，contig 为 `CP008706.1`。其 `source_id` 为 `omics:AB5075-AZI000:gene:ABUW_0001`，表达来源可定位到原始 `control[0, 16]`；参考 CSV 第 2 行和映射 CSV 第 18 行提供注释依据。数值是源 `float32` 转为 Python 浮点数后的表示。

`query_genes` 按原生基因 ID 精确查询。传入 `dnaA` 会出现在 `missing_gene_ids` 中；先用注释搜索找到 `ABUW_0001`，再查表达。`search_annotations` 对 ID、基因符号、产物和蛋白 ID 做大小写不敏感的子串搜索，`dnaA` 还会匹配 `ABUW_0983` 的 `DnaA family protein` 描述，所以搜索命中不等于确认了药物靶点。

查询接口的边界如下：

- 未找到的 ID 明确列入 `missing_gene_ids`，不会补值或猜测同义名；重复请求的 ID 按首次出现顺序去重。
- `query_genes([])` 返回空结果。非列表、空字符串或非字符串元素报 `ValueError`；空白字符串查询 ID 会作为未找到的 ID 返回。
- 注释搜索的空字符串、纯空白或非字符串输入报 `ValueError`；有效搜索无命中时返回空列表。
- `limit` 只接受 1–100 的整数；布尔值不作为整数接受。超过上限的有效命中标记 `truncated`，不会把它们误标为缺失。
- 实测 `0.0` 保持数值零；空的注释字段返回 `None`。缺失表达、`NaN` 和无穷值不作为正常表达输入接受。

## 从六个本地源文件重建

准备器是 `praxis_virtualcell.omics.prepare_ab5075`。默认源根为 `data/organisms/_sources`，需要以下六个文件：

```text
abwm/delta_response_v1/ab5075/arrays.npz
abwm/delta_response_v1/ab5075/pairs.csv
abwm/ortholog_response_v1/orthology/reference_features.csv
abwm/ortholog_response_v1/expression_ortholog_mapping.csv
abaumprecise/raw_data/metadata.csv
abaumprecise/interim/metadata_qc.csv
```

将结果写到一个没有同名 profile 的新数据根：

```bash
.venv/bin/python -m praxis_virtualcell.omics.prepare_ab5075 \
  --source-root data/organisms/_sources \
  --data-root /private/tmp/praxis-organism-rebuild
```

准备器选择唯一的 `AZI:AZI_003` pair，核对声明的未处理样本、AB5075 身份、`CA-MHB` 培养基和 `AZI_000` 条件，再读取历史冻结文件中的 `control[0]`。它保留这两个源样本的均值语义；当前脚本没有从两个单样本原始矩阵重新计算均值，也不做新的归一化或训练。

历史数组文件名含 `delta_response_v1`，只是原始资产的来源位置。准备器只访问 `genes` 和 `control`，不会读取 `treated`、`delta` 或 MIC 数组；生成的 NPZ 仅有 `genes` 和 `expression` 两个键。注释来自明确的 `AB5075_original` 参考关联。

准备时生成资产哈希和来源记录，写入临时目录后调用正式 loader 验证，再移入目标 profile 目录。六个源文件不会被改写；已有同名输出拒绝覆盖。脚本不下载数据、不调用 LLM，也不执行生物效能推理。

运行时每次 `load_profile` 检查派生 `baseline.npz` 和 `annotations.csv` 的路径、字节大小与 SHA-256，然后解析内容。原始来源哈希保存在 provenance 中供核对，运行时不会重新遍历和校验全部原始六个文件；因此来源记录与当前派生资产校验是两个不同层次。

源数据与派生数据的再分发许可尚未核实，当前保留为本地研究副本，manifest 标记 `redistribution_approved: false`。Git 保存读取和重建代码，不携带完整数据资产；新克隆需要自行准备声明的源文件。

## 文件导入接口与旧 loader 的复用范围

目前有两个独立的数据接口。当前 LLM 流程使用 `OrganismProfile`；恢复的旧 `data_packs` 提供底层 H5AD/H5MU 读取，尚未自动转换成前者。

| 接口 | 当前实际能力 | 主要限制 |
| --- | --- | --- |
| `praxis_virtualcell.omics.load_profile` | v1 读取 NPZ RNA 基线和注释 CSV；v2 读取显式声明的基因组、转录组、蛋白组 CSV/JSON 特征表，支持七种模态组合及选择视图 | 需要事先整理原生特征与验证样本身份；不会自动融合菌株、条件或推断组学数据 |
| `data_packs.load_anndata_view` | 验证 Pack manifest 与资产，使用公开 AnnData API 以只读 backed 模式打开真实 H5AD，选择观察和特征 | 从 `X` 读取；支持 dense/CSR/CSC，不自动预处理、补值、归一化或重排用户请求 |
| `data_packs.load_mudata_view` | 读取 `vc.pack.v0.3` H5MU；验证模态、形状、观察 ID、共享/联合观察及配对关系 | 保留各模态原有观察，不把缺失模态填成零；严格语义 ID 规则需要数据事先满足 |
| `data_packs.align_features` | 按显式特征契约做数据对齐与报告 | 契约类型仍叫 `ModelFeatureContract`；该函数不加载或调用旧预测模型，也不自动建立菌株同源关系 |

这些恢复组件复用了真实文件解析、schema 校验、安全路径解析、资产大小/哈希检查、观察/特征身份校验和选择读取。未恢复旧 `CellState` 预测 workflow、模型注册器或多组学模型编译器。通用 Pack schema 保留了历史部分声明，但独立 validator 会拒绝 `vc.pack.v0.4` selected-content 执行包。

H5AD 的 `vc.pack.v0.1` 基础契约支持声明的原生特征命名空间；定向测试使用真实小型 H5AD 和 `ABUW_*` ID 验证。`vc.pack.v0.2` H5AD 与 `vc.pack.v0.3` H5MU 的严格特征语义仅接受 `ensembl_gene`、`ncbi_gene_curie`、`uniprot_protein` 三种 ID 格式。因此不能把 `ABUW_0001` 直接填入这些严格格式；需要明确新增原生细菌 ID 契约或经验证的映射。样本 ID、taxon 和 assembly 声明也不会自动推断成完整分离株身份、基因型或采样条件。

底层读取可单独使用，不调用模型：

```python
from praxis_virtualcell.data_packs import load_anndata_view

with load_anndata_view("path/to/pack") as view:
    print(view.observation_ids, view.feature_ids, view.shape)
    matrix = view.matrix
```

Pack 根需有符合契约的 `manifest.yaml` 和声明的 H5AD/H5MU 资产，文件后缀本身不足以导入。H5AD/H5MU 尚未自动转换成 organism profile。v2 可以导入符合下述严格字段契约的 CSV/JSON 特征表，不能据此声称已支持任意用户表格或未经处理的测序文件。

## 准备 v1 RNA profile

可以在自定义数据根手工准备一个新 profile 目录，交由 loader 验证。当前接口要求：

1. 目录名与 manifest 的 `profile_id` 相同，使用安全的字母、数字、`_`、`.`、`-` ID；不能使用路径穿越或绝对路径。`AB5075-AZI000` 的身份与尺度被冻结，别的菌株应使用新的 ID。
2. `manifest.json` 使用严格 `praxis.organism-profile.v1` schema，声明菌种、taxon、菌株、条件、单位、尺度、观测单位、来源样本与 provenance；未知字段写 `null`。当前条件角色只接受 `untreated_reference` 或 `pre_treatment_baseline`。
3. NPZ 只包含一维 `genes` 与一维数值 `expression`，长度一致，基因 ID 为唯一非空且无首尾空白的字符串，表达为有限数值。资产路径、大小和 SHA-256 必须与 manifest 一致。
4. 注释 CSV 至少含 `gene_id,gene_symbol,product,protein_id,contig,reference_key,mapping_evidence,reference_row,mapping_row`；注释 ID 唯一且属于表达基因集合，来源行号为数字。注释可以覆盖部分基因，概览分别报告表达和注释数量。
5. 声明实测输入与来源，保留原生 ID 和单位。不得将候选药物给药后表达、响应差值、MIC 或旧状态向量塞入基线 NPZ/provenance；额外 schema 字段会被拒绝。

可参照准备器生成的 manifest。v1 只表示 RNA，其他模态使用 v2；原有 `AB5075-AZI000` 身份和尺度被冻结，不能用同名 v2 替换。

## v2 多组学导入契约

目录结构为 `<data_root>/<profile_id>/manifest.json`，每个模态的派生特征资产放在同一 profile 内，原始资产仍只存一份。manifest 用 `features.path` 引用相对路径，并声明 `format`（`csv` 或 `json`）、字节大小和 SHA-256。loader 复用现有安全路径与哈希校验，不打开 provenance 中的原始定位路径，不复制原始数据，也不做归一化。

[v2 RNA manifest 模板](../examples/organisms/v2_transcriptome_manifest.template.json) 包含完整单模态声明。它只有占位字段，没有生物学数据；必须替换身份、样本、单位、来源、资产大小和哈希后才可使用。未知实验条件保持 `null`，不能根据一般培养流程猜测。

顶层需要 `schema_version: praxis.organism-profile.v2`、`profile_id`、`species`、`strain`、`genotype`、`condition`、`pairing` 和 `modalities`。`modalities` 是字典，键只接受 `genome`、`transcriptome`、`proteome`。每个模态都要独立声明菌种、菌株、基因型、条件、`sample_id`、`pairing_id`、`assay`、原生特征命名空间、单位、尺度、值语义、观测单位、特征资产和 provenance。

身份和配对规则如下：

- 每个模态的菌种、菌株、基因型和完整条件必须与顶层一致。不同菌株、不同采样条件的表不能自动融合；未知与已知条件也不能假装相同。
- 每个 `sample_id` 必须存在于该模态的 `provenance.source_samples`，源样本 ID 非空且唯一。
- 单模态可以使用 `pairing: null`、`pairing_id: null`。多模态必须提供 `{pairing_id, relation, evidence}`，各模态 `pairing_id` 必须一致。
- `relation: same_sample` 要求所有模态使用同一个明确 sample ID。不同 assay/aliquot ID 只能通过 `matched_samples` 和明确的配对依据声明；loader 检查声明一致性，原始实验配对依据仍需数据整理者核验。
- 转录组和蛋白组必须声明 `input_role: measured_pre_treatment`；基因组可用 `sequenced_reference`。v2 另接受 `condition.role: sequenced_reference`，严格限定 genome-only 并要求 reference provenance，未知培养/暴露条件保持 null；v1 仍仅接受原两种角色。药物处理后的响应表不进入此输入接口。

测量类型有独立校验：基因组支持 `whole_genome_sequencing`、`targeted_sequencing`、`assembly_annotation`；转录组支持 `RNA_seq`、`microarray`、`measured_transcriptomics`；蛋白组支持 `LC_MS_MS`、`SWATH_MS`、`targeted_MS`、`measured_proteomics`。参考序列的翻译产物、蛋白 ID 和基因产物注释不会因为存在而成为实测蛋白组。

三个特征表的字段如下：

| 模态 | 必需字段（值可明确为空的字段另标） | 可选观测字段 |
| --- | --- | --- |
| genome | `feature_id`、`presence`（布尔或 null）、原始来源定位 | `gene_id`、`protein_id`、`variant`、`copy_number` |
| transcriptome | `feature_id`、非空 `gene_id`、`expression_value`（有限数值或 null）、原始来源定位 | `protein_id` |
| proteome | `feature_id`、非空 `protein_id`、`abundance_value`（有限数值或 null）、原始来源定位 | `gene_id` |

所有模态可额外提供 `gene_symbol`、`product`、`contig`。ID 必须非空、无首尾空白，`feature_id` 在同一模态内唯一。`gene_id` 或 `protein_id` 必须来自明确映射，不能根据名称猜测。多个蛋白 feature 可以对应同一 gene，查询会保留多条观测，不自动求平均。

CSV 使用严格表头：转录组最小例子为 `feature_id,gene_id,expression_value,source_path,source_row`。`source_path` 与 `source_row` 定位到原始表；也可以提供 `source_accession` 或 `source_record_id`。JSON 是记录列表，每条记录使用 `source_locator: {path, row, accession, record_id}`，四个键都需要存在，不适用的项为 `null`。每条 feature 至少需要源路径或 accession，以及行号、记录 ID 或 accession。行号从 1 开始，CSV 的首个数据行为第 2 行。

CSV 空单元格解析为 `null`；JSON 使用原生 `null`。`presence` 在 CSV 中只接受 `true`、`false` 或空，JSON 使用布尔或 null。实测 `0.0` 保持零值；缺失丰度保持 null，不补零。数值字符串仅在 CSV 导入时解析，JSON 必须使用数字，`NaN`、无穷和负 copy number 被拒绝。其他字段及 MIC/处理后响应字段不在严格 schema 内，不能混入特征表或 provenance。

计算本地特征资产大小与哈希可使用标准库：

```python
import hashlib
from pathlib import Path

asset = Path("transcriptome.csv")
print(asset.stat().st_size)
print(hashlib.sha256(asset.read_bytes()).hexdigest())
```

声明完成后按现有入口验证和注册，无需调用 LLM：

```python
from praxis_virtualcell.omics import load_profile

profile = load_profile("YOUR-PROFILE-ID", data_root="/path/to/organisms")
view = profile.select_modalities(["genome", "proteome"])
print(view.overview())
print(view.query_features("proteome", ["YOUR-NATIVE-PROTEIN-FEATURE"]))
print(view.search_features("genome", "efflux"))
```

`select_modalities(None)` 选择全部可用模态，传列表支持七种组合，顺序统一为 genome、transcriptome、proteome。空列表、未知模态和不可用模态明确报错。v1 只接受 transcriptome；其蛋白注释不会新增可选模态。

选择视图的 `overview` 返回 `available_modalities` 和 `selected_modalities`，但模态描述、样本来源和 provenance 只包含所选模态。未选特征不能通过 `query_features` 或 `search_features` 读取；`query_genes`、`search_annotations` 也只在所选模态内检索。单模态视图不会暴露跨模态配对 provenance，子集组合不会带出未选模态的配对依据文本。

`query_features` 按该模态的原生 `feature_id` 查询，返回 `features`、`missing_feature_ids` 和 `truncated`。v2 每条观测的 source ID 为 `omics:<profile_id>:<modality>:feature:<feature_id>`，包含模态单位、尺度、观测字段及派生资产记录索引/原始行定位。v1 的通用 feature 查询保留原有 gene source ID 和真实 AB5075 来源位置。`query_genes` 在 v2 返回所选模态中所有明确关联该 `gene_id` 的记录，蛋白未映射到基因时需按 protein feature 查询。

这个版本不包含 FASTQ/BAM 自动处理、自动注释、跨 assembly/跨菌株同源映射、代谢组或单细胞适配。`prepare_genome.py` 只读取已冻结、已注释的本地 NCBI FASTA/GFF，验证字节、assembly、taxon、contig、原生 feature 与坐标，导出参考注释存在性，不作新注释或阴性基因调用。已接入 19 个 E. coli genome-only 原生参考；当前菌株集合还引用后来接入的真实 RNA 和实测蛋白丰度。完整库存见 [DATA-READINESS](DATA-READINESS.md)。

`prepare_baseline_samples.py` 从服务器作者原始 QC 矩阵导出 Abaum_0017/0023 实际两列，不拆均值、不复制原矩阵。每个新 profile 的收据保留原矩阵/metadata 行、QC、Run、BioSample 与来源 hash；两列共用一个 BioSample，独立生物重复未证实。

## 定向验证

```bash
.venv/bin/python -m pytest tests/omics -p no:cacheprovider -o addopts='' -q
.venv/bin/ruff check tests/omics praxis_virtualcell/omics praxis_virtualcell/data_packs
```

测试包括真实本地 AB5075 的 3895 基因、`dnaA` 数值/单位/源数组位置核对，以及小型 NPZ/CSV/JSON/H5AD 的哈希、形状、ID、空值和只读边界。v2 合成 fixture 覆盖七种导入组合、七种所选视图、未选数据隔离、样本配对和跨菌株/条件拒绝，明确只用于软件测试。合成源文件把给药后、delta、MIC 键设为不可按安全 NPZ 方式读取的对象，以确认准备器不访问这些键；另用隔离进程阻止历史预测模块导入，验证 profile 读取闭包。

真实 AB5075 资产未随 Git 再分发，缺少本地 manifest 时该真实数据用例明确跳过，其余合成文件用例仍可运行。H5AD 用例需要 `omics` 安装依赖；测试不会把 fixture 值作为生物学证据，也不会调用付费 API 或训练模型。
