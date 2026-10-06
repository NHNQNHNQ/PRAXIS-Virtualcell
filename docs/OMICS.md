# 菌株组学输入与来源

当前平台向 LLM 提供有来源的、给药前的菌株表达背景。组学加载层负责读文件、检查身份和数值、返回基因注释与来源定位；药物活性、杀伤和作用机制的判断由 LLM 生成。加载层没有恢复旧 MIC/AMR 模型、实测 MIC 查表、扰动预测或世界模型，也不把旧八维状态向量作为实测组学。

## 已有 AB5075 profile 的含义

默认本地输入位于 `data/organisms/AB5075-AZI000/`，由 `manifest.json`、`baseline.npz` 和 `annotations.csv` 组成。

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
| `praxis_virtualcell.omics.load_profile` | 加载已准备好的 JSON manifest、NPZ 基线向量和注释 CSV；返回概览、原生基因表达、注释和来源定位 | 当前模态为 `bulk_RNA_seq`，每个 profile 是一个基线向量；AB5075 准备器针对指定的六个历史源文件 |
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

Pack 根需有符合契约的 `manifest.yaml` 和声明的 H5AD/H5MU 资产，文件后缀本身不足以导入。当前 CLI/Web 没有“上传任意 H5AD/H5MU 后自动生成菌株 profile”的入口，也没有通用表达 CSV 导入器。准备器使用 CSV 的能力限于声明的 pair、元数据、参考注释和映射表，不能据此声称已支持任意用户表格。

## 准备新的菌株 profile

可以在自定义数据根手工准备一个新 profile 目录，交由 loader 验证。当前接口要求：

1. 目录名与 manifest 的 `profile_id` 相同，使用安全的字母、数字、`_`、`.`、`-` ID；不能使用路径穿越或绝对路径。`AB5075-AZI000` 的身份与尺度被冻结，别的菌株应使用新的 ID。
2. `manifest.json` 使用严格 `praxis.organism-profile.v1` schema，声明菌种、taxon、菌株、条件、单位、尺度、观测单位、来源样本与 provenance；未知字段写 `null`。当前条件角色只接受 `untreated_reference` 或 `pre_treatment_baseline`。
3. NPZ 只包含一维 `genes` 与一维数值 `expression`，长度一致，基因 ID 为唯一非空且无首尾空白的字符串，表达为有限数值。资产路径、大小和 SHA-256 必须与 manifest 一致。
4. 注释 CSV 至少含 `gene_id,gene_symbol,product,protein_id,contig,reference_key,mapping_evidence,reference_row,mapping_row`；注释 ID 唯一且属于表达基因集合，来源行号为数字。注释可以覆盖部分基因，概览分别报告表达和注释数量。
5. 声明实测输入与来源，保留原生 ID 和单位。不得将候选药物给药后表达、响应差值、MIC 或旧状态向量塞入基线 NPZ/provenance；额外 schema 字段会被拒绝。

可参照准备器生成的 manifest，但手工准备不是自动适配任意实验的承诺。当前 schema 没有蛋白组、代谢组或单细胞菌株 profile 类型；没有 FASTQ/BAM/FASTA 处理、自动注释、跨 assembly/跨菌株映射或从测序文件推断耐药基因型。新增这些输入需要独立、可核验的适配步骤。

## 定向验证

```bash
.venv/bin/python -m pytest tests/omics -p no:cacheprovider -o addopts='' -q
.venv/bin/ruff check tests/omics praxis_virtualcell/omics praxis_virtualcell/data_packs
```

测试包括真实本地 AB5075 的 3895 基因、`dnaA` 数值/单位/源数组位置核对，以及小型真实 NPZ/CSV/H5AD 的哈希、形状、ID、空值和只读边界。合成源文件把给药后、delta、MIC 键设为不可按安全 NPZ 方式读取的对象，以确认准备器不访问这些键；另用隔离进程阻止历史预测模块导入，验证 profile 读取闭包。

真实 AB5075 资产未随 Git 再分发，缺少本地 manifest 时该真实数据用例明确跳过，其余合成文件用例仍可运行。H5AD 用例需要 `omics` 安装依赖；测试不会把 fixture 值作为生物学证据，也不会调用付费 API 或训练模型。
