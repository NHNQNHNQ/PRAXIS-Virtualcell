# ADR-0017：Virtual Cell Training Pipeline 合同

- 状态：Accepted（P20 `COMPLETE — CONTRACT_ONLY`）
- 日期：2026-08-07
- 唯一起始基线：`f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a`
- Completion code SHA：`a4003704b70f06eb65297ddd32e0695ae8ee146b`
- Completion tree：`d12d64a7c8d013d8d299272eea88a4ce0431ccab`
- Source date epoch：`1786040663`
- 分支：`codex/p20-training-pipeline`
- 前置：ADR-0016
- 工程状态：`COMPLETE — CONTRACT_ONLY`
- Science：`NOT_RUN`
- Policy：`NO_NEW_DECISION`

## 背景

P19 已建立 receipt → candidate → review → validation → registration-only decision →
FactoryRegisteredPack 的受控链，并让 Pack index consumer 回查 factory store 后才信任
registration。此前仍缺少从这个 exact RegisteredPack 出发，冻结训练输入和执行条件、产生安全
candidate checkpoint、记录 training result 并形成 candidate-only model identity 的本地工程合同。

P20 只补齐同步、确定性、固定受信 worker 隔离执行的 training contract 和仓库 tiny fixture
dry-run。测试输出只写入
pytest `tmp_path`，指标只证明合同重放；不读取真实数据、真实 test/external 结果，不进行真实候选
训练、GPU/remote 执行、自动调参、benchmark、scientific evidence 或 promotion。

## 决策

### 1. 只接受 exact P19 factory registration

训练入口不接受裸 Pack path、legacy v1 index provenance、调用者自报的 Pack fingerprint 或单独
传入的 `FactoryRegisteredPackV1`。Resolver 必须完成整条 fail-closed 链：

~~~text
explicit absolute PackIndex
→ exact vc.pack-index.v2 entry
→ factory_registration_fingerprint + canonical factory_store_root
→ PackFactoryStore.open() exact marker verification
→ verify_registration() complete receipt/review/validation/decision chain
→ index registration/Pack identity bidirectional match
→ current exact manifest + split metadata + train-consumed asset validation
→ frozen P20 RegisteredPack binding
~~~

P19 registration 中的完整 Pack tree identity 是不可变历史 provenance；P20 不把它误报为对当前
Pack root 的递归重算。任一 store marker、registration artifact、manifest、split metadata、实际
train-consumed feature/label bytes 或相关 identity 漂移都拒绝 job；P19 pending index→store 状态不能
进入 runner。Test/external、未消费 asset 和 uploaded-code-looking bytes 不会被打开，其当前 bytes
不属于 P20 live verification boundary。

### 2. Job 在执行前冻结全部输入

公开 authoring 入口为：

~~~text
bind_training_job(*, index, pack_id, pack_version, registration_fingerprint,
                  feature_contract, alignment_report, split_asset_id,
                  train_feature_asset_ids, train_label_asset_ids,
                  trainer_revision, trainer_source_sha256, code_sha256,
                  environment, seed, hyperparameters, resource_limits,
                  model_id, model_version) -> TrainingJobV1
~~~

`TrainingJobV1` 使用 `vc.training-job.v1`，并绑定 exact P19 registration、Pack、feature
contract、alignment report、split/leakage contract、trainer revision/source digest、code SHA、
`TrainingEnvironmentV1`（`vc.training-environment.v1`）、seed、hyperparameters、resource
limits 和 candidate model identity。Strict canonical JSON 拒绝 unknown fields、duplicate keys、
非有限数值和调用者补写的派生 identity。

`load_training_job(path)` 只加载并重验冻结 job；它不是 authoring wizard，也不修复或推断缺失
字段。Pack/split/feature/alignment/trainer/code/environment/seed/hyperparameter/resource/model
任一变化都改变 job identity 或 fail closed。

### 3. Leakage audit 必须先于任何 label read

`TrainingSplitV1`（`vc.training-split.v1`）绑定 Pack-declared split asset、partition、ordered
sample IDs、leakage group fields 和 partition-specific label assets。Runner 先读取 split metadata，
生成并验证 `TrainingLeakageAuditV1`（`vc.training-leakage-audit.v1`）；只有 audit 明确通过后，
trainer 才能打开 allowlisted train label assets。

Test/external label assets 在 P20 永远不进入 read allowlist。Audit 失败时，即使 train label bytes
本身 malformed，observable outcome 也必须先是 leakage rejection，证明 label read 没有越过 gate。

### 4. Runner 固定且不执行上传代码

`run_training_job(job, *, index, output_root, cancelled=False,
timeout_seconds=None) -> TrainingRunBundle` 是同步入口。Runner 只调度仓库内置、revision 和 source
SHA-256 均与 job 匹配的 tiny deterministic worker，worker count 固定，不启用 scheduler、subprocess
plugin、GPU queue、distributed runtime 或 autotuning。

Pack 中即使声明 Python、shell 或其他 executable-looking asset，也只是不可执行 bytes，不能成为
trainer、hook、callback 或 import path。Runner 先核对固定 worker source，再把它复制到 private
temporary directory，以 scrubbed environment 和 `[sys.executable, "-I", "-S", worker]` 执行，
并以文件承载 stdout/stderr；stdout 只在 worker 成功退出后按 checkpoint byte ceiling 读取，
随后接受 strict semantic validation。这里不声称 stderr 独立 size cap，也不声称 OS syscall
sandbox。Worker 只能读取冻结 allowlist 中的 train feature/label assets；不得枚举 Pack 后自行
打开 test、external、secret 或未声明路径。

### 5. Checkpoint 只用安全 JSON，先 staging 后无覆盖发布

Candidate checkpoint 使用 `CandidateCheckpointV1` 和 canonical JSON，不使用 pickle、任意对象
反序列化或用户代码。每次 run 要求一个显式 absolute、canonical、write-new output root。Library
在 output parent 下创建 sibling staging directory，并从创建时起持有 staging dirfd 和 inode
identity；写入安全 JSON artifact、fsync 后，经该 held dirfd 重载、重算 size/hash/manifest，且在
publish 前再次完整重验 bundle。随后相对 held parent fd 执行 no-replace atomic rename；既存
destination、staging source swap、symlink、path traversal 或 identity 冲突均拒绝。发布失败时仅经
held staging dirfd 清除本次四个 artifact basename，绝不删除或覆盖竞争者目录。

当前授权只允许测试控制的 `tmp_path`。手工 CLI 不得仅凭命令中的任意路径运行；必须先有一项
独立记录的 exact absolute write-new root 授权，且该 root 当时不存在。P20 没有获得外部 output
root 授权。

### 6. Result 与 model identity 双向绑定但保持 candidate-only

`TrainingResultV1`（`vc.training-result.v1`）绑定 job fingerprint、checkpoint size/hash、log digest、
实际资源摘要和 contract-only metrics。`CandidateModelArtifactV1`、`CandidateModelCardV1` 与
`TrainingCandidateModelV1`（`vc.training-candidate-model.v1`）双向绑定 exact Pack registration、
job、checkpoint、trainer、code 和 environment。

`TrainingRunBundle.to_dict()` 只序列化经过重验的整套 candidate artifacts。成功状态精确为
`candidate_cataloged_contract_only`：它不写 production model registry、evidence ledger 或
product policy，并固定 scientific validation、promotion eligibility 和 production promotion 为
false。

### 7. Failure、cancel、timeout 不留下 candidate

Leakage、identity、path、allowlist、worker、serialization、resource 或 integrity 错误，以及显式
cancel/timeout，必须清理 staging，并且不发布 checkpoint、training result、candidate model/card。
对既存完成目录不覆盖、不删除。失败可以返回/记录最小拒绝状态，但不能把 partial bytes 解释为
candidate。

CLI 固定为：

~~~text
praxis-vc training dry-run --job JOB.json \
  --index /absolute/pack-index.json \
  --output-root /absolute/write-new-root
~~~

上式只描述参数形状，不授权占位路径。CLI 与 library 使用同一 resolver/runner，不提供 HTTP write
route、隐式 index/store/output default 或真实训练开关。

## 验证与完成身份

以下证据全部绑定 completion code，不把临时目录或中间工作树当作 completion：

| Evidence | Frozen value |
|---|---|
| completion code SHA / tree / epoch | `a4003704b70f06eb65297ddd32e0695ae8ee146b` / `d12d64a7c8d013d8d299272eea88a4ce0431ccab` / `1786040663` |
| training job / leakage audit | `e29d5c49059eec0346bd8f199b03602ea1ceb23fd876e90291aa9511c3affd67` / `35ce1eaf7ea540cd05bde6045cff88dc2ea82ce7807ddda09fd60d86902b3733` |
| candidate checkpoint fingerprint | `bdc927e53447402e2b4a3050077ebaf343e752112af11d539d59acdfc70ab47d` |
| checkpoint state bytes / SHA-256 | `377` / `950e44d437a3565320ff1ad00540f53983c785b22e11e30cbaeab72dbf24c1f9` |
| result / artifact / card / candidate fingerprints | `45560256e1320494baefb724d538a6f16a7ac109b8c81e279ea2602b5dc5009c` / `77be408817a9c4000a38b433409cefa37a4dd55c4822f9e2cae08d55b4f2a939` / `2eeacc202b9f2f832bee78ffe963073d628192eb07f48dabe668e54ea2ddee58` / `25c0bafe4d71375e00b3dce069e9b5329e954f2b213484bc411e859fd39be0fe` |
| environment fingerprint | `d37da47364978b187ebfc721c88cc912f4825950c34dd1bc7b7f7f74873b5232` |
| focused / P19-adjacent | `56 passed` / `99 passed, 1 skipped`（optional `mudata` absent） |
| safe / legacy | `1,610 passed, 49 skipped, 387 deselected` / `1,147 passed, 58 skipped, 105 deselected` |
| static checks | Ruff lint / targeted format、py_compile、`git diff --check` passed |
| reproducible wheel | `1,178,805` bytes；SHA-256 `2273ee71fb58fef543eae358d3df2aefccec42e80fe72a23380200718c223d79`；`370` entries / React `14` / tests `0` / AppleDouble `0`；ZIP integrity passed |

`TrainingEnvironmentV1` 分别记录 caller-declared dependency-lock SHA-256 和实际观察到的 installed
distributions digest；前者是声明值而非经 registry 或 lock file authenticate 的事实。Curated
training code digest 为
`99481d3261a24d17e564b9a5e0a7cf30e660a5fe31e8110e518a0fcbf362f397`，表示显式安全关键 source set，
不是整个 Python package 的自动 closure。`pipeline.py` 与 wheel 内 bytes 的 SHA-256 均为
`dd7dbe480c3f000e5345b35fc6358fe2cc1b4377b035c31809d584ce3c869134`；`tiny_worker.py` 均为
`4de1ba3b67a67ea24c16b7664058939ae3a634e06cf11601a528aca4c465f02b`。

## 后果与下一 gate

P20 完成后也只证明 RegisteredPack→candidate model 的工程合同可在 tiny fixture 上确定性重放。
以下事项保持 false/NOT_RUN：real training、真实 test/external read、GPU/remote、network、benchmark、
scientific evidence、`scientifically_validated`、`promotion_eligible`、`production_promoted`、release
和 deploy。

下一 eligible gate 是 P21A：先冻结通用 benchmark protocol/system，且在任何 candidate result 之前
冻结 Pack/split/feature/output/metric/baseline/CI/OOD/external policy。P21B real run 与 P21C operator
policy 均需独立精确授权，不能由 P20 completion 推导。

完整操作边界见 [P20 runbook](runbooks/VIRTUALCELL-TRAINING-PIPELINE.md)、
[P20 completion report](../reports/phase20/PHASE20_COMPLETION.md) 和
[Phase 12–30 execution plan](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)。
