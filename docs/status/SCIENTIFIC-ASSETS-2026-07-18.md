# PRAXIS-VirtualCell 科学资产与分发边界 — 2026-07-18

> 状态：`C5_ASSET_CLASSIFICATION_LOCAL`
>
> 证据基线：Phase 10 gate + C4 固定发行证据 HEAD `8ce42fe5d167bc4f41bbee596cdc9ab255591056` + C5 Gate A 实现证据 HEAD `038e7476a2b8c05ef30722eb9947363b0cbca11d`
>
> 本轮范围：检查本地 APFS 仓库并验证 C5 本地 provenance seam；未下载任何数据或权重，未访问或修改 `.53`，未修改 GitHub。

本文回答的是“一个科学资产现在位于哪一层、能否随 wheel/container 分发、还缺什么证据”，不是重新评价数据集、模型或科学结论。科学能力与论文措辞仍以 `reports/phase10/PHASE10_GATE.md` 为最高权威；本表中的状态不得用于把 Phase 10 的 `narrowed`、`unsupported` 或 `needs_new` 项改绿。

## 1. 状态口径与当前发布拓扑

本文的状态只描述**资产交付与复现证据**：

- `met`：当前声明范围内，来源/许可边界、包路径及本地发布产物可用性已有直接证据。
- `narrowed`：资产或历史运行证据存在，但只覆盖源码 checkout、可选依赖或特定远端环境；不能推广为默认 wheel/container 可用。
- `unsupported`：当前发布契约明确不包含该资产，或缺少可据以再分发的许可/产品路径；这不等于否定资产的科学价值。
- `pending`：所需文件、位置、授权或端到端结果尚未在本轮得到证据。

当前发布拓扑是：

```text
praxis_virtualcell/data/module_gene_sets/*
        -> setuptools package-data -> wheel -> container /opt/venv       [随包]

仓库根 data/*
        -> 不属于 Python package + .dockerignore 排除 data              [源码研究层]

registry 中 remote:/self_trained: 权重
        -> manual fetch + ~/.cache/praxis_virtualcell/model_zoo/* + SHA  [私有/远端层]
```

C4 的两次 clean build 产出字节一致的 `1.6.0` wheel（922,334 bytes，SHA-256 `78e5287a5dd61478b041fd1a28783732cb75a250de02eec306d3803b3128fd4f`）。安装验证明确枚举了三份默认 gene-set；release container 最终阶段只复制安装后的 `/opt/venv`。根 `data/` 既不在 setuptools 包发现范围内，又被 `.dockerignore` 的 `data` 规则排除，因此“文件被 Git 跟踪”不等于“已进入 wheel/container”。

## 2. 默认随包资产

| 资产 | 状态 | 来源与许可 | 本地源码 | C4 wheel | C4 container | 当前允许的声明 | 所需下一证据 |
|---|---|---|---:|---:|---:|---|---|
| `praxis_virtualcell/data/module_gene_sets/membrane_system.json`（M1） | **met** | 项目自编定性映射；文件与同目录 README 明确为 MIT，仅借鉴公开 GO/Reactome 概念而非数据库导出 | 是 | **是，已枚举验证** | **是，经 wheel 进入镜像** | 只用于 `rule_based` / `evidence_limited` advisory；不含测量、效应量或数值 delta | 当前声明无需新证据；若要做数值预测，须另建模型、数据与独立评估，不能升级本映射的含义 |
| `praxis_virtualcell/data/module_gene_sets/biosynthetic_network.json`（M5） | **met** | 同上；MIT 仅覆盖该定性映射 | 是 | **是，已枚举验证** | **是，经 wheel 进入镜像** | 同上 | 同上 |
| `praxis_virtualcell/data/module_gene_sets/degradation_machinery.json`（M8） | **met** | 同上；MIT 仅覆盖该定性映射 | 是 | **是，已枚举验证** | **是，经 wheel 进入镜像** | 同上 | 同上 |
| `praxis_virtualcell/model_zoo/registry.yaml`（注册元数据，不含权重） | **narrowed** | 项目注册表随代码按 MIT 管理；各模型/权重仍受各自 `license` 与 `distributable` 字段约束 | 是 | 配置规则会包含 `*.yaml`；C4 installed verifier 未单独枚举该文件 | 经 wheel 进入镜像的配置路径；不等于权重存在 | 可声明 fail-closed 的模型目录与版本/SHA 契约；不可声明五个注册模型均可运行 | 在 checkout 外对 installed wheel 直接构造 `ModelZooRegistry()` 并枚举条目；这仍只验证元数据，不验证权重 |

三份 gene-set 是当前唯一经 C4 gate **直接点名确认**的默认科学数据文件。`module_gene_sets.py` 使用 `importlib.resources` 从已安装包读取，避免依赖仓库父目录；这也是它们与下节源码研究数据的关键区别。

## 3. 源码研究数据：Git 跟踪，但不随发布产物分发

下表中的 predictor 默认路径均从源码文件向上定位仓库根 `data/`。在 editable/source checkout 中可用，但 installed wheel 位于 `site-packages` 后该根数据树不存在；基础 runtime lock 也不含 `cobra`。因此这些能力不能由 C4 的普通 offline wheel/API smoke 推导为安装包全覆盖。

### 3.1 策展子集、机制模型与 manifest

| 资产 | 状态 | 本地证据 | 分发/许可边界 | wheel / container | 所需下一证据 |
|---|---|---|---|---|---|
| `data/cellstate/kang_isg_subset.json` | **narrowed** | Git tracked；564,154 B；provenance 记录 Kang 2018、GSE96583、确定性抽样，SHA-256 `792588…77c8` | 来源与重建配方已记；本地 provenance 未明确给出该派生子集的再分发许可 | **否 / 否** | 要么正式声明 source-only；要么先补资产级许可审查，再迁入 package resources，并做 installed-wheel/container 的 cell-state case |
| `data/cellstate/kang_metabolic_subset.json` | **narrowed** | Git tracked；561,016 B；provenance SHA-256 `19cb56…e8eb` | 同上 | **否 / 否** | 同上，并保持 Phase 10 对 pathway-scoring 适用场景的现有窄门 |
| `data/cellstate/kang_lr_subset.json` | **narrowed** | Git tracked；333,568 B；provenance SHA-256 `7ca02e…26a1` | 同上 | **否 / 否** | 同上；需 installed communication case，而非只验证文件存在 |
| `data/cellstate/imc_niche_subset.json` | **narrowed** | Git tracked；346,120 B；provenance 记录 Squidpy IMC 来源、预计算 niche，SHA-256 `43e77a…861b` | 来源/构建事实已记；未见资产级再分发许可声明 | **否 / 否** | 许可审查 + package-resource 路径 + installed spatial case；不得由此扩大 M6 能力结论 |
| `data/cellstate/mcfarland_emt_subset.json` | **narrowed** | Git tracked；173,073 B；provenance 记录 McFarland 2020、seed=1，SHA-256 `40b5fa…068f` | 同上 | **否 / 否** | 许可审查 + installed EMT case；Phase 10 的 `emt` limitation 保持不变 |
| `data/cellstate/paul15_fate_subset.json` | **narrowed** | Git tracked；118,776 B；provenance 记录 Paul 2015、seed=1，SHA-256 `f897bf…9207` | 同上 | **否 / 否** | 许可审查 + installed fate case；Phase 10 的 `fate` limitation 保持不变 |
| `data/drug_signatures/curated_subset.json` | **narrowed** | Git tracked；15,213 B；由 Enrichr LINCS L1000 原库形成六药 top-100 共识子集 | provenance 有源 URL/原库 SHA；未见该派生子集的资产级再分发许可声明 | **否 / 否** | 明确 Enrichr/LINCS 条款与派生物许可，随后决定 source-only 或 package-resource；若随包，补 installed drug-signature case |
| `data/drug_signatures/dose_response_subset.json` | **narrowed** | Git tracked；22,650 B；provenance SHA-256 `663ee1…ac44`，三药每剂量 top-150 | 同上 | **否 / 否** | 同上，并补 installed dose-response case |
| `data/gems/iML1515.xml.gz` | **narrowed** | Git tracked；620,180 B；代码标为 BiGG iML1515，源码环境可由可选 COBRApy 路径真跑 | 仓库未给该二进制资产附独立许可文件；不能仅凭项目 MIT 推断第三方模型的再分发权 | **否 / 否**；基础 runtime lock 不含 `cobra` | 补模型来源版本/下载 URL/原始 SHA/许可文件；若要随包，再补 mechanistic release profile 与 installed FBA smoke |
| `data/gems/iMM904.xml.gz` | **narrowed** | Git tracked；310,805 B；代码标为 BiGG iMM904，源码环境由可选 COBRApy 路径真跑 | 同上 | **否 / 否**；基础 runtime lock 不含 `cobra` | 同上，并运行 installed yeast GEM case |
| `data/manifests/norman_2019.yaml` | **narrowed** | Git tracked；记录远端 processed file 的路径、937,614,888 B、SHA-256 `e3d116…17de`、shape 与 split 配方 | manifest 明确“PRAXIS 只读复用，不重新分发数据”；manifest 可分发不代表 Norman 数据可分发 | manifest 本身不随 wheel / container；数据也不随包 | 在另行授权的只读远端窗口复核文件 SHA、loader 与 split；若只做论文复现，应继续保持“manifest + 用户自行取得数据”模式 |

### 3.2 本地存在但 Git 忽略的完整源数据

这些文件本轮只做了路径与大小盘点，没有重新下载、解析或改写。它们由 `.gitignore` 排除，也被 `.dockerignore` 的根 `data` 规则整体排除。

| 本地文件 | 状态 | 本轮观察 | provenance / 许可现状 | wheel / container | 所需下一证据 |
|---|---|---|---|---|---|
| `data/kang_2018.h5ad` | **unsupported**（发布层） | 本地 38,356,412 B | 已有 Kang provenance 与公开来源信息；未建立发布许可/包契约 | **否 / 否** | 保留为受保护的本地研究资产；需要时做恢复副本 checksum 与来源许可审计，不默认纳入发布 |
| `data/mcfarland_2020.h5ad` | **unsupported**（发布层） | 本地 1,459,410,830 B | 已有来源与 shape 描述；未建立发布许可/包契约 | **否 / 否** | 同上；大文件应继续与代码发布解耦 |
| `data/anndata/imc.h5ad` | **unsupported**（发布层） | 本地 1,574,836 B | provenance 指向 Squidpy dataset；未建立发布许可/包契约 | **否 / 否** | 同上 |
| `data/paul15/paul15.h5` | **unsupported**（发布层） | 本地 10,297,693 B | provenance 有 Scanpy loader 与来源描述；未建立发布许可/包契约 | **否 / 否** | 同上 |
| `data/drug_signatures/LINCS_L1000_Chem_Pert_up.txt` | **unsupported**（发布层） | 本地 16,214,812 B；provenance SHA-256 `324647…a4a2` | Enrichr URL 与 hash 已记；再分发条款未在仓库内明确 | **否 / 否** | 保持 gitignored；先完成条款审查，通常优先让用户从权威源重建 |
| `data/drug_signatures/LINCS_L1000_Chem_Pert_down.txt` | **unsupported**（发布层） | 本地 14,045,684 B；provenance SHA-256 `25c0db…c83a` | 同上 | **否 / 否** | 同上 |

“unsupported（发布层）”只表示这些完整源数据不属于当前安装包/镜像契约。它不推翻基于其生成、且已在 Phase 10 中诚实标界的源码研究证据。

## 4. 模型注册表、私有 checkpoint 与远端数据

`ModelCache` 的默认位置是 `~/.cache/praxis_virtualcell/model_zoo/<model_name>/<asset>`，并在存在期望 SHA 时 fail-closed 校验。`resolve_source()` 对 `remote:` 与 `self_trained:` 只返回 `requires_manual_fetch`，不会自动下载权重。该安全契约是已实现的；但它不能替代文件存在、分发许可、依赖环境与真实推理证据。

| 资产/条目 | registry 状态 | C5 状态 | 已有证据 | 分发/许可 | 本地 wheel / container | 所需下一证据 |
|---|---|---|---|---|---|---|
| `ecoli_gem` / COBRApy bundled `e_coli_core` | `available` | **narrowed** | registry 可解析为 `fetch=none`；Phase 10 本地 M3/M4 FBA 范围有真实引擎证据 | registry 标 `cobrapy-bundled`；资产由可选第三方依赖提供 | 基础 wheel 只声明可选 `mechanistic`；C4 runtime/container 未安装 `cobra` | 若把它列为默认安装能力，需加入明确 release profile、锁定 COBRApy 并在 installed wheel/container 真跑；否则文档明确“可选源码/extra 能力” |
| `gears`: `model.pt` + `config.pkl` | `planned` | **narrowed** | registry 有两个 SHA；Phase 10 记录 2026-07-17 `.53` GEARS 真 delta remote test 通过 | registry 的代码许可字段为 MIT，但 `provenance.distributable=false`；checkpoint 不得随包 | **无 / 无**；还需 torch、GPU 与 `.53` 特定环境 | 经用户授权只读核对远端文件 SHA；明确 checkpoint 权属/再分发禁令；在手动填充 cache 后复跑其 CaseRunner/wrapper 远端路径，不复制进 wheel/container；该路径不替代 W4B Gate A 验证 |
| `scgpt`: `pretrained_backbone.pt` + `.json` | `planned` | **narrowed** | registry 有两个 SHA；Phase 10 记录 `.53` `vc-scgpt` 环境与 donor 对齐测试通过 | registry 标 MIT，但 `distributable=false`，约 196 MiB 权重仍是手工远端资产 | **无 / 无**；还需 torch、GPU 与专用环境 | 授权后只读复核 SHA/环境；手动 cache 注入 + 独立 installed/remote e2e；不因代码许可推导权重可再分发 |
| `norman_mean_baseline`: `mean_delta.pt` | `planned` | **narrowed** | registry 有 SHA `306f0b…41d5`；Phase 10 记录 `.53` 两个 gated test 通过 | `license=internal`、`distributable=false` | **无 / 无**；基础 runtime 无 torch | 授权后只读复核 SHA；明确内部资产保管/获取流程；手动 cache 后做 installed entry + run_query，不随公开包分发 |
| `yeast_deletion_fitness` | `planned` | **pending** | training card 明确数据、架构、指标和权重均未就绪 | `license=internal`、`distributable=false` | **无 / 无** | 取得可用且许可清晰的 SGD deletion 数据，建立 split/基线/训练与权重 SHA；完成前继续 broker fail-closed |
| donor `W4B_CKPT_DIR` 多预测器 checkpoint | 注册表外的 remote test 输入 | **pending（当前候选）** | 历史 finding 记录 repo `390b67b` 时 `/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260521_060815/checkpoints/norman_2019/` 曾存在并重验 6 个 base/Coordinator；Phase 10 的 2026-07-17 候选窗口未重新定位，`test_ml_workflow_e2e` 未完成 | 私有 donor 路径；仓库无可分发授权；现有 bridge 以 `weights_only=False` 加载 PT，属于可执行信任边界 | **无 / 无** | 先只读定位并登记六文件 size/SHA，再由可信资产负责人批准精确 digest 集；同时批准 clean donor Git SHA/remote。两道门都满足后才能 import donor/反序列化并真跑；找不到或未批准就保持 pending。长期迁移 `weights_only=True` 或安全格式 |
| Norman 2019 processed dataset | manifest 指认的远端只读输入 | **pending**（本轮实时性） | manifest 有远端路径、size、SHA 与 split；Phase 10 使用过历史远端证据 | manifest 明确不重新分发 | **无 / 无** | 授权后只读复核当前 `.53` 文件与 manifest 一致；不把数据复制到 Git、wheel 或 container |
| MLBackedPredictor Gate A 不误伤真 ML | 非资产；依赖上述 donor/remote 资产的验收项 | **narrowed（本地 seam met）/ pending（真 ML）** | C5 在本地实际 runtime 中验证三 adapter success 不触发 Gate A、缺版本精确 fail-closed，并把 W4B per-call version 绑定 `.json + .pt` 内容；本机无 torch，真 donor 两条 remote 用例均 skip | 不改变任何 checkpoint 分发边界；内容身份不是 checked-in integrity pin | 未完成真 ML | 先取得批准候选 SHA、clean donor SHA/remote 与可信 W4B digest 集，再经 `build_runtime_ml(...).run_workflow(...)` 取得 `2 passed / 0 skipped / 0 failed`；普通 `run_query()` 不装载该 runtime，单独 wrapper/seam pass 也不足以关闭真 ML 项；见远端 runbook |

历史 `.53` 亲验可以支撑“特定 commit、特定环境、特定路径曾经通过”，不能支撑以下任一推论：权重已经进入本地 package、checkpoint 可公开再分发、当前 `.53` 状态未变化、或默认 container 具备 GPU/torch 推理能力。

## 5. C5 结论与下一证据顺序

1. **默认发行层已闭合但很窄**：三份 MIT gene-set 可随 wheel/container 使用，且只承担 M1/M5/M8 定性 advisory。注册表元数据可随包，但模型权重不随包。
2. **源码研究层尚未形成安装包契约**：六份 cell-state 子集、两份药物子集、两份 GEM 和 Norman manifest 都是 Git 跟踪研究资产；它们被 release wheel/container 排除。若产品选择继续 source-only，应在用户文档明确；若选择随包，必须先做逐资产许可审查、迁移到 `importlib.resources` 路径、锁定相应 extra，并从 checkout 外做真实 case smoke。
3. **完整数据继续留在本地研究层**：约 1.4 GiB 根 `data/` 不应因“整理项目”被删除或因“完整 wheel”被误纳入镜像。恢复/迁移应沿用独立 asset manifest 与 checksum 流程。
4. **远端资产继续 manual + fail-closed**：GEARS、scGPT、Norman mean baseline 有历史 `.53` 证据但不可分发；yeast deletion、W4B donor、Gate A 真 ML e2e 仍 pending。本地 adapter seam 不等于远端推理。关闭 W4B 项必须按 `docs/runbooks/REMOTE-SCIENCE-VALIDATION.md` 在批准候选 SHA、批准 donor Git SHA 和可信六文件 digest 集上取得 `2 passed / 0 skipped / 0 failed`；不能用下载、复制或“只打印 hash”绕过代码/反序列化信任边界。
5. **科学结论不升级**：真实引擎级覆盖仍仅四族（M2/M3/M4/M7）；M1/M5/M8 仍是 advisory；M6/emt/fate 仍按 Phase 10 limitation 表述；项目仍不是 SOTA 预测模型。“独立结果冲突检测”和“LLM unsupported claim=0”仍 unsupported，资产盘点不提供改变它们状态的新证据。

因此，本轮资产分类完成的准确结论是：`LOCAL_ASSET_MATRIX_COMPLETE`；C5 本地 seam 已收窄风险，但科学远端 backlog 尚未全部关闭，三端状态不能据此从 `KNOWN_DIVERGENCE` 提升为 `READY_TO_SYNC`。
