# VirtualCellPack Phase 5 → Phase 6 交接

- 收口日期：2026-07-27（Asia/Shanghai）
- P5 唯一起始基线：`a229699deac1e791252739df71f4e4202cc72bac`
- 分支：`codex/p5`
- 状态：`P5_COMPLETE_LOCAL_CANDIDATE — PHASE6_AUTHORIZATION_PENDING`
- 完成提交：由提交后的阶段报告给出；Git commit 不能可靠地自嵌其 SHA。

## 1. 结论

P5 已实现 VirtualCellPack 的 H5MU 多组学基座和严格模型特征输入合同：

- `vc.pack.v0.3`；
- backed/read-only MuData loader；
- paired / partially-paired observation；
- `vc.model-feature-contract.v1`；
- `vc.feature-mapping.v1`；
- 只经显式授权的 alias/aggregate/drop/fill/reorder；
- `vc.alignment-report.v1` 完整 provenance；
- 一份测试时生成的 tiny human RNA+protein Pack。

`pack_valid`、`model_compatible`、`scientifically_validated` 仍是独立状态。没有新增
模型、没有运行模型、没有修改 UI、没有 LLM 数据裁决、没有自动补零/归一/去重/
随机划分/ortholog 转换，也没有把 H5MU、真实大数据或权重提交到 Git。

## 2. v0.3 H5MU Pack

v0.3 manifest 在一个 H5MU asset 上按顺序声明至少两个 modality，每个 modality
有独立的 ontology、feature namespace/version、ID format 和 shape。v0.1/v0.2
的单 modality/matrix 字段与 v0.3 严格隔离，v0.1 frozen fingerprint 保持
`5973dc852f8d7d0cb73ce333d3f99beb2f94c66b7cdf4e6d2e7fc4c422651192`。

loader 使用公开 `mudata.read_h5mu(path, backed="r")`，并显式设置
`pull_on_update=False`。它验证：

- asset media type、modality 顺序与精确 shape；
- global observation 等于各 modality observation 并集；
- paired 必须全部 observation 同序相同；
- partially-paired 必须同时有真实 overlap 和真实 missingness；
- canonical Ensembl/NCBI Gene/UniProtKB feature ID；
- P4 cell/condition/perturbation/control/split/leakage 语义；
- `perturbations.target_modality` 及其 canonical target 外键。

全局 observation selection 不为缺失 modality 造行。RNA 没有 cell-4、protein
没有 cell-1 时，选中 cell-1/cell-4 后两个 modality 各只返回一个真实行。
`PackRegistry` 对 v0.3 走同一完整 loader；缺少 MuData 直接拒绝。

## 3. 模型特征合同与显式对齐

`ModelFeatureContract` 固定 model/taxon/assembly/modality/namespace/version/ID
format 和有序 feature ID。默认必须精确匹配；转换授权只有：

- mapping asset 的显式 alias；
- mapping asset 的显式 `sum`/`mean` aggregate；
- contract 的显式 drop；
- contract 的显式有限常数 fill；
- contract 的 `reorder=true`。

mapping 必须是 Pack manifest 中声明的 `application/json` asset，且 asset
ID/path/size/SHA-256、mapping ID/version 与合同引用全部一致。mapping bytes 或
version 改变后，Pack 与 contract fingerprint 都改变；文件在声明 hash 后被修改
会 fail-closed。

成功转换返回 `AlignmentReport`，包含 contract fingerprint、mapping asset、
source/target feature 顺序和 shape，以及每个实际 alias/aggregate/drop/fill/
reorder step。无转换的精确匹配返回空 steps。不存在 version-strip、symbol lookup、
自动 zero-fill、自动 aggregate、同源转换或 mock fallback。

## 4. 审计中额外关闭的边界

- ModelFeatureContract、drop、fill 和 mapping 中的 feature ID 都必须符合声明的
  canonical ID format；
- UniProtKB 校验覆盖官方 6/10 位 accession 三种格式，不再误收 `A00000`；
- 超大整数 fill 在 `float()` 溢出时转换成稳定 `FeatureAlignmentError`；
- base-only `praxis_virtualcell.data_packs` import 不导入或要求
  anndata/MuData/NumPy/SciPy；数值依赖只在实际 alignment 时按 `omics` extra
  fail-closed；
- fixture 构造和生产 loader 都关闭 MuData annotation pull。

## 5. fixture、lock 与分发

Git 中只有：

- `tests/fixtures/mudata/rna_protein.yaml`；
- `tests/fixtures/mudata/rna_mapping.json`；
- 生成时计算 size/hash 的测试代码；
- ADR、能力矩阵和复现 runbook。

测试在 pytest 临时目录生成 CSR H5MU；仓库内没有 `.h5mu`。`mudata` 只加入
`omics` extra；重生成的 dev lock 为：

```text
anndata 0.12.19
mudata 0.3.10
scverse-misc 0.1.1
```

lean runtime lock 不含 MuData 或 scverse-misc，base import 也不 fallback。

## 6. 测试证据

测试先行红阶段：

```text
初始 API collection error
首轮 P5：20 failed / 5 passed
canonical ID / UniProt：5 failed
超大 fill integer：1 failed
undeclared mapping asset：1 failed
base-only optional import：1 failed
```

全新 Python 3.13.12 strict hash-lock 环境最终结果：

```text
pip check：No broken requirements found.
P5：32 passed / 0 failed
P1–P5 Pack/request/baseline 定向：187 passed / 0 failed
ruff check . --no-cache：All checks passed
VirtualCell core：1144 passed / 35 skipped / 9 deselected / 0 failed
legacy：1146 passed / 59 skipped / 105 deselected / 0 failed
```

P0 代表性 structured report 与 9-section Markdown hash 保持不变：

```text
27a16eef2493bf953c4e572f3480d9c80e4013b5f92ebca4b8bfe0f59722228b
ed4b03d12e9618a7685a19106609f2ec0b0461ccf533c6beec20e7318ec7898a
```

未运行真实 LLM、remote/GPU、Docker、前端或 `.53` 测试；它们不属于 P5 完成
声明。

## 7. 文件范围

实现：

- `praxis_virtualcell/data_packs/__init__.py`
- `praxis_virtualcell/data_packs/anndata_adapter.py`
- `praxis_virtualcell/data_packs/errors.py`
- `praxis_virtualcell/data_packs/feature_alignment.py`
- `praxis_virtualcell/data_packs/manifest.py`
- `praxis_virtualcell/data_packs/mudata_adapter.py`
- `praxis_virtualcell/data_packs/registry.py`
- `praxis_virtualcell/data_packs/schema.py`
- `pyproject.toml`
- `requirements/dev-py313.lock`

测试与 fixture：

- `praxis_virtualcell/tests/test_mudata_alignment.py`
- `praxis_virtualcell/tests/test_anndata_adapter.py`
- `praxis_virtualcell/tests/fixtures/mudata/rna_protein.yaml`
- `praxis_virtualcell/tests/fixtures/mudata/rna_mapping.json`

文档：

- `README.md`
- `docs/ADR-0003-virtualcellpack-p5-multiomics-alignment.md`
- `docs/VIRTUALCELLPACK-CAPABILITY-MATRIX.md`
- `docs/VERSIONING.md`
- `docs/TESTING.md`
- `docs/INDEX.md`
- `docs/P0-BASELINE.md`
- `docs/runbooks/VIRTUALCELLPACK-MULTIOMICS.md`
- `requirements/README.md`
- 本交接文件

## 8. 已知限制

- v0.3 当前每个 Pack 只声明一个 H5MU asset；
- matrix 只读 `X`，支持 CSR/CSC/dense，不解释 layer/raw/obsm；
- partially-paired 只表达 membership，不做任何 imputation；
- 对齐会物化所选 modality matrix，尚无流式超大矩阵转换；
- mapping 只有 alias 和 `sum`/`mean` aggregate；
- UniProt/ontology 只做离线格式验证，不证明 accession/term 在线存在；
- registry 是进程内快照，不是签名系统或跨进程事务；
- 没有 model zoo 模型被升级为 available；对齐成功不证明模型运行或有效；
- MuData 0.3.10 import 产生 2 条上游 namespace 注册 DeprecationWarning；
- 本地 Git 仍有既存 AppleDouble pack-index 警告，未授权修改 `.git`。

## 9. 三端边界

P5 开始时与提交前复核一致：

- 本地 P5 基线：`a229699deac1e791252739df71f4e4202cc72bac`；
- GitHub `HEAD/main`：`8e0d06348ebdf22e076037e6d661094ae877c5d1`；
- `.53` `codex/deploy-v1.6.0`：`8e0d063...`，既存 `?? vc_api.log`；
- 旧 dirty T7 工作树：`24475f2eb14c27c7cfbb82b016b881e88e98b17c`。

本阶段没有 push，没有修改 main/tag，没有同步或写入 `.53`，没有修改旧 T7 用户
文件。

## 10. Phase 6 授权模板

提交后的阶段报告会把占位符替换为精确 SHA：

```text
授权以 <P5 完成 SHA> 作为 Phase 6 唯一起始基线，开始实施 Phase 6。
```

精确迁移关系：

```text
expected_old_sha=a229699deac1e791252739df71f4e4202cc72bac
→ new_sha=<P5 完成提交 SHA>
```
