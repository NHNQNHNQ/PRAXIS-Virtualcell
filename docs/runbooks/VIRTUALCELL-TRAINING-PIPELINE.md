# Virtual Cell Training Pipeline 本地合同运行手册

本 runbook 只用于 P20 repository-local contract tests 和 pytest `tmp_path` tiny dry-run。它不授权
手工选择 output root，不运行真实训练，不读取真实 test/external 数据，不访问 network、GPU、
remote 或 `.53`，不生成 benchmark/scientific evidence/promotion，也不 push、release 或 deploy。

## 1. 固定身份与当前状态

从仓库根只读检查：

~~~bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git branch --show-current
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git status --short
~~~

P20 frozen identity：

~~~text
starting SHA          f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a
completion code SHA   a4003704b70f06eb65297ddd32e0695ae8ee146b
completion tree       d12d64a7c8d013d8d299272eea88a4ce0431ccab
source date epoch     1786040663
branch                codex/p20-training-pipeline
engineering status    COMPLETE — CONTRACT_ONLY
science               NOT_RUN
policy                NO_NEW_DECISION
~~~

这些 identity 只证明 completion code 上的 contract-only work；中间 SHA、临时输出和测试预期值都
不是独立 completion evidence。

## 2. 唯一允许链路

~~~text
exact P19 factory-registered Pack
→ frozen vc.training-job.v1
→ pre-label vc.training-leakage-audit.v1
→ fixed repository tiny deterministic worker
→ staged safe-JSON candidate checkpoint
→ no-overwrite atomic publish
→ vc.training-result.v1
→ vc.training-candidate-model.v1 (`candidate_cataloged_contract_only` only)
~~~

不存在从裸 Pack path、legacy index、caller-authored registration JSON、unverified store 或 uploaded
trainer code 进入 runner 的旁路。

## 3. P19 resolver 审计

传给 `bind_training_job()` 和 `run_training_job()` 的 `PackIndex` 必须使用 explicit absolute index
path。Resolver 必须依次确认：

1. `vc.pack-index.v2` entry 绑定 exact Pack ID/version/fingerprint；
2. entry 同时具有 registration fingerprint 和 canonical absolute factory store root；
3. `PackFactoryStore.open()` 通过 exact `.factory-store.json` marker 检查；
4. `verify_registration()` 可重建完整 receipt/candidate/review/validation/decision chain；
5. registration、index 与当前 exact manifest 双向一致，并保留 stored P19 full-tree identity 作为
   历史 provenance；
6. live-open split metadata 以完成 leakage audit；audit 通过后才打开冻结的 train-consumed
   feature/label bytes，并逐项复核其 identity；
7. record 为 committed/valid，而不是 index 已写但 store registration 缺失的 pending state。

任一步失败即停止。不得把 P19 registration fingerprint 作为绕过实时验证的 bearer token。
P20 不递归枚举当前 Pack root，也不 live-open test/external、未消费 asset 或 uploaded-code-looking
bytes；因此这些当前 bytes 的漂移不属于 P20 live verification claim。

## 4. 冻结 job

Library authoring surface：

~~~python
from praxis_virtualcell.model_zoo.training.pipeline import bind_training_job

job = bind_training_job(
    index=explicit_pack_index,
    pack_id=exact_pack_id,
    pack_version=exact_pack_version,
    registration_fingerprint=exact_registration_fingerprint,
    feature_contract=exact_feature_contract,
    alignment_report=exact_alignment_report,
    split_asset_id=exact_split_asset_id,
    train_feature_asset_ids=exact_ordered_feature_asset_ids,
    train_label_asset_ids=exact_ordered_label_asset_ids,
    trainer_revision=exact_builtin_trainer_revision,
    trainer_source_sha256=exact_builtin_trainer_source_sha256,
    code_sha256=exact_repository_code_sha256,
    environment=exact_training_environment,
    seed=exact_seed,
    hyperparameters=exact_hyperparameters,
    resource_limits=exact_resource_limits,
    model_id=exact_candidate_model_id,
    model_version=exact_candidate_model_version,
)
~~~

这些变量是 API 形状说明，不是可执行占位授权。`TrainingEnvironmentV1`、`TrainingSplitV1`、
`TrainingLeakageAuditV1`、`TrainingJobV1`、`CandidateCheckpointV1`、`TrainingResultV1`、
`CandidateModelArtifactV1`、`CandidateModelCardV1` 和 `TrainingCandidateModelV1` 都必须按 strict
canonical form 重新构造；不要手工编辑 fingerprint 或派生 pass/status 字段。

`TrainingEnvironmentV1` 的 `declared_dependency_lock_sha256` 是调用者冻结的声明，
`installed_distributions_sha256` 是实际观察到的安装分布摘要；不要把前者写成经过外部 registry、
lock file 或供应链认证。Training code SHA-256 是显式 curated security-critical source set，也不是
整个 Python package 的自动 dependency closure。

持久化 job 后只使用 `load_training_job(path)` duplicate-key-safe 地加载和重验。改变 Pack、split、
feature/alignment、trainer、code、environment、seed、hyperparameters、resource limits 或 model
identity 必须产生新 job identity，不能就地修改旧 job。

## 5. Audit-before-label 和 read allowlist

Runner 只先读取 Pack-declared split asset，核对每个 partition 的 ordered sample IDs、leakage group
fields 和 label-asset binding，并生成 `vc.training-leakage-audit.v1`。Audit 通过之前不得打开任何
label asset；失败时立刻退出。

Audit 通过后只允许读取 job 冻结的 train feature/label asset IDs。Validation、test 和 external
label assets 仍在 P20 read denylist；未消费 feature/label 和 Pack 中的
Python/shell/notebook/plugin bytes 也不会被打开或执行。
不得递归枚举 Pack、跟随 symlink、解析 path traversal、读取 environment secret 或回退到用户
提供的 trainer path。

## 6. Tiny runner 与 output root

同步 API：

~~~text
run_training_job(job, *, index, output_root, cancelled=False,
                 timeout_seconds=None) -> TrainingRunBundle
~~~

自动化测试只把 pytest `tmp_path` 下一个不存在的新目录传给 `output_root`。Runner 使用固定单 worker
和内置 deterministic trainer：先核对 worker source SHA-256，复制到 private temporary directory，
再用 scrubbed environment 和 `[sys.executable, "-I", "-S", worker]` 启动；stdout/stderr 写入
file-backed outputs，stdout 在成功退出后按 checkpoint byte ceiling 读取并作 strict semantic
validation。这里不声称 stderr 独立 size cap，也不声称 OS syscall sandbox。相同输入和 seed 应
得到相同 job/checkpoint/result/model identities。

手工 CLI 形状为：

~~~text
praxis-vc training dry-run --job JOB.json \
  --index /absolute/pack-index.json \
  --output-root /absolute/write-new-root
~~~

**不要运行上述占位命令。** 手工 CLI 必须先另行记录并批准一个 exact absolute、canonical、
当时不存在的 write-new output root；不得用当前目录、home、workspace root、已有目录、symlink、
环境变量默认或推断路径代替。本 P20 工作单没有这样的外部 root 授权。

## 7. Staging、发布与结果检查

Runner 只写 canonical safe JSON，不写 pickle/torch 任意对象。预期顺序是：

1. 在 output parent 下创建 sibling exclusive staging directory，并从创建时持有其 dirfd/inode；
2. 经 held staging dirfd 写入 checkpoint payload/manifest，fsync，重读并核对 size/hash；
3. 构造绑定 job/checkpoint/log/resources/contract-only metrics 的 result；
4. 构造双向绑定 Pack/checkpoint/trainer/environment 的 candidate artifact/card/model；
5. 在 publish 前经同一 held dirfd 重载四个 staged artifacts，重算 hash，并完整重验 bundle；
6. 核对 held/named staging inode 仍为创建 identity，再相对 held parent fd 以 no-replace atomic rename
   发布完整目录并返回已验证的 `TrainingRunBundle`。

`bundle.to_dict()` 只用于重验后的完整 bundle。成功精确标为
`candidate_cataloged_contract_only`；不得写 model production registry、evidence ledger 或 promotion
state。完成 identity 见 P20 completion report 中的 frozen values。失败时仅经 held staging dirfd
删除本次四个 artifact basename 并 fsync；源路径被替换时不得触碰 replacement，竞争 destination
必须保留。

## 8. Failure、cancel、timeout

下列情况必须 fail closed、清理本次 staging，且不发布 checkpoint/result/card/model：

- P19 index/store/registration/Pack 任一 identity 漂移或 pending；
- split overlap、leakage group 缺失、partition 或 asset binding 错误；
- label 在 audit 之前被读，或尝试读取 test/external/secret/undeclared asset；
- arbitrary uploaded code、trainer revision/source mismatch 或 worker count 漂移；
- relative/existing/symlink output、path escape、destination overwrite 或 unsafe serialization；
- cancel、timeout、resource limit、trainer exception、partial write、hash/manifest mismatch；
- unknown/duplicate JSON fields、NaN/Infinity 或重签名后的 nested identity mismatch。

不得删除或覆盖先前成功 candidate。失败状态不能伪装成
`candidate_cataloged_contract_only`。

## 9. 本地 contract-only gates

以下命令只运行 repository tiny fixtures；frozen 结果为：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_training_pipeline.py

python -m ruff check \
  praxis_virtualcell/model_zoo/training/pipeline.py \
  praxis_virtualcell/cli.py \
  praxis_virtualcell/tests/test_training_pipeline.py

python -m ruff format --check \
  praxis_virtualcell/model_zoo/training/pipeline.py \
  praxis_virtualcell/model_zoo/training/tiny_worker.py \
  praxis_virtualcell/tests/test_training_pipeline.py

python -m py_compile \
  praxis_virtualcell/model_zoo/training/pipeline.py \
  praxis_virtualcell/cli.py

git diff --check
~~~

~~~text
focused result       56 passed in 158.74s
P19 + P20 adjacent   99 passed, 1 skipped in 180.33s (optional mudata absent)
safe result          1,610 passed, 49 skipped, 387 deselected in 290.17s
legacy result        1,147 passed, 58 skipped, 105 deselected in 62.44s
static checks        Ruff lint / targeted format, py_compile, git diff --check passed
wheel evidence       1,178,805 bytes; SHA-256 2273ee71fb58fef543eae358d3df2aefccec42e80fe72a23380200718c223d79;
                     370 entries / React 14 / tests 0 / AppleDouble 0; byte-identical x2; ZIP passed
~~~

Wheel 内 `pipeline.py` SHA-256 与 source 同为
`dd7dbe480c3f000e5345b35fc6358fe2cc1b4377b035c31809d584ce3c869134`，`tiny_worker.py` 同为
`4de1ba3b67a67ea24c16b7664058939ae3a634e06cf11601a528aca4c465f02b`。构建使用本机已有
Node/npm cache 和 build frontend，显式 offline/no-isolation/skip-dependency-check；它证明 exact local
bytes 的可复现打包和内容完整性，不证明 pinned dependency closure 或 clean install。

这些 gates 不读取真实数据、test/external outputs 或 checkpoint，不调用 Golden/GEM/Norman science。
不得把 tiny metric 写成预测质量、benchmark 或 scientific evidence。

## 10. 停止条件与 P21A

如观察到真实训练、GPU/remote/network、test/external read、evidence write、model registry promotion、
`scientifically_validated=true`、`promotion_eligible=true` 或 `production_promoted=true`，立即停止并
保留 false/NOT_RUN 状态。

P20 完成后的下一 gate 仅为 P21A benchmark system/protocol freeze。P21B real candidate run 和 P21C
operator policy decision 均需独立 exact authorization，不能从本 runbook 或 P20 candidate identity
自动获得。

完整边界见 [ADR-0017](../ADR-0017-virtual-cell-training-pipeline.md)、
[P20 completion report](../../reports/phase20/PHASE20_COMPLETION.md) 和
[Phase 12–30 execution plan](../PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)。
