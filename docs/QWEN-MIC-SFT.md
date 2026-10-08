# Qwen MIC 工具对话微调准备

当前训练数据为 **2026-10-08 v4_compact**，从封版 v3 独立衍生。53 工作区为 `/home/zkyd/data1/mzy/qwen-PRAXIS-MIC`，数据在 `data/processed/qwen_joint_sft_v4_compact`，结构样例在 `data/processed/qwen_joint_inspection_v4_compact`。v3 保留；下文 v2/v1 为历史记录。用户已授权首轮正式训练。12 步工程试训已完成最长样本反向、完整保存、checkpoint1→6→12 恢复及适配器扰动重载；它不代表正式模型或 MIC 准确率。结果见 [试训验证报告](../reports/llm_platform/qwen_v4_compact_trial_verification_20261008.json)。

## 首轮基线、正式微调与配对验证

2026-10-08 20:23（北京时间）已在 53 启动 `praxis-qwen-first-formal-contract-20261008.service`，启动时 8 张 GPU 均空闲、主机可用内存 492.47 GiB。当前首先运行原始 Qwen3-32B 的 64 条验证基线；基线全部尝试并独立评分后，才开始全量正式训练。最终训练和准确率结果仍待运行完成。

固定 pilot 在 `data/processed/evaluation_pilot_v4_contract_20261008`：四物种各 8 条有组学、8 条无组学，共 64 条，覆盖 7 个参考菌株。两项消融各保留相同 32 条参考记录的 SMILES、菌株、条件和 ID，分别去掉组学或结构证据。211 次现成工具调用已用真实平台重放，公共结果全部一致；结构 bootstrap 明确为物种背景知识。官方 tokenizer 的最长公共输入为 25,199 token，不截断。公开请求包含平台真实 Assessment JSON schema，推理只读公共输入，MIC 仅在预测文件完整后由独立评分器读取；评分沿用原封版 v3 和已审阅的 v3 assay audit。

[流程控制器](../scripts/finetuning/run_qwen_pipeline.py) 顺序执行原始模型基线 → [正式训练控制器](../scripts/finetuning/run_qwen_formal.py) → 同组微调模型验证 → 两项配对消融 → 比较报告。正式模型从原始基座创建全新 LoRA，使用全部 7,193 条数据、BF16、r=16、八卡 FSDP，225 个优化步；分布式尾部补齐 7 个槽位。75 个三步段始终保留同一个完整学习率调度，恢复 Adam、scheduler、RNG 和 Trainer 状态，三份完整检查点滚动保留。正式输出为 `outputs/qwen3_32b_joint_lora_v4_compact_formal_20261008/adapter`；旧 trial adapter 保留。

每个 GPU 段在加载权重前核验真实 `memory.max=300 GiB/high=260 GiB/swap=0/oom.group=1`，外部监控保留至少 160 GiB 主机可用内存，单段硬限 40 分钟。控制器自身限 512 MiB，SSH 断开后继续运行。资源越界、GPU OOM、失败或不完整断点会停止流程，不自动重试。预测逐条落盘，恢复时核对输入、模型资产和生成设置；失败、超时和截断均计入覆盖率。无组学消融的合法数值报告可独立评分，但原平台缺组学拒绝原因全部保留，`platform_eligible=false`，不能把验证门槛造成的缺失误称为组学收益。

进展和结果在 `reports/first_formal_contract_pipeline_20261008`：`pipeline.json` 为阶段状态；`training/runner.json` 为实际完成步数；`*.predictions.jsonl`、`*.score.json` 和 `comparison.json` 分别为原始生成、独立分数和配对比较。当前没有机制人工金标，因此不会产生机制准确率。

查看阶段与日志：

```bash
cd /home/zkyd/data1/mzy/qwen-PRAXIS-MIC
cat reports/first_formal_contract_pipeline_20261008/pipeline.json
journalctl --user -u praxis-qwen-first-formal-contract-20261008.service --no-pager -n 30
```

如需停止本次流程，执行 `systemctl --user stop praxis-qwen-first-formal-contract-20261008.service`，控制器会向正在运行的 guard 传递停止信号。

## v4_compact：与智能体一致的结构监督

平台先维护有来源的细胞结构，再让模型学习使用查询结果。实现与覆盖见 [CELL-STRUCTURE](CELL-STRUCTURE.md)。7,193 个组件、7,372 次 MIC、104 个机制报告保持原值；1,950 条组学报告增加真实 `query_cell_structure` 返回和结构弱监督，5,243 条无组学辅助行保持原字节。

完整九条结构视图保留在 `qwen_joint_sft_v4`：45 条超出 32,768，最长 33,701，未截断。独立 `v4_compact` 查询全部五个区室节点，运行时仍可检索完整邻接图。最新全量官方 tokenizer/TRL collator 预检通过：7,193 条、最长 **31,740**、最长最终回答 **10,890**，system/user/tool 的 loss token 为 0；共 33,159,672 输入 token、13,084,824 监督 token。原生 MIC、文献与 380 段引用来源核验通过。这些数据、tokenizer 与来源检查仅用 CPU。

v4 使用 manifest 的相对路径共享 v3 原始来源索引、隔离索引和留出答案，新增字节索引指向衍生训练文件。验证/测试保持原划分与公开组学轨迹，不加入实测答案或教师结构答案。目录复制到别处时需一起保留 v3、结构 catalog 及相对路径。

配置 `qwen3_32b_joint_lora_v4_compact.yaml` 已用于首轮正式流程；以下工程试训使用独立短试训配置。投影＋CE 分块与二维连续投影输入已部署。此前 CPU 数值验证完成原生、分块、offload＋gradient checkpointing 各 4 个案例，共 222 项梯度比较，最大 loss 差异 4.77e-7、最大梯度差异 2.98e-8。第一次 GPU 尝试在 RMSNorm 重计算申请 620 MiB 时 OOM，第二次三维输出头发生 checkpoint 元数据不匹配，均为 0 步。第三次使用 `pin_memory=True` 完成最长样本反向与 3 个 optimizer 步后，断点保存挂起；锁页缓存按尺寸取整并保留多组缓冲，主机可用内存降至约 9 GiB、swap 仅余 4 KiB，随后 SSH 连接超时，用户重启服务器。该次 checkpoint 目录为空，没有可恢复断点。

当前部署使用 `save_on_cpu(pin_memory=False)`；非锁页 CPU 转存的 222 项梯度比较通过，真实 cold checkpoint 保存与扰动后重载通过。cold 烟测未执行 backward 或 optimizer 更新。随后 guarded stop1 返回 `stopped_at_checkpoint`、`optimizer_steps=1`：每 rank 完成 4 个 backward microbatch，8 个 rank 均覆盖最长 31,740 token；梯度有限、LoRA 更新量为 4.99994e-5。checkpoint-1 完整包含 LoRA、Adam、scheduler、8 rank RNG 与 manifest；推理适配器的 896 个 LoRA 张量精确一致且有限，扰动被检出，重载参数与 forward 精确恢复。训练 cgroup 的 1 秒采样最高观察值为 187.47 GiB，全机最低可用内存为 304.18 GiB，OOM/high/max 事件均为 0，swap 为 0。stop1 结束后的 GPU 释放已核实。

checkpoint1→6 恢复测试已通过：恢复了 896 份 optimizer 状态，恢复时 step 的最小值和最大值均为 1，moments 有限且非零，scheduler 与 8 rank RNG 恢复通过。该段新增 5 个 optimizer 步、每 rank 20 个 backward microbatch，8 rank 均覆盖最长 31,740 token。checkpoint-6 完整，896 个推理适配器张量有限且精确一致，扰动后参数与 forward 精确恢复。该阶段 GPU 分配峰值每 rank 最高 28.755 GiB；训练 cgroup 的 1 秒采样最高观察值为 196.39 GiB，全机最低可用内存为 295.26 GiB，high/max/OOM 事件及 swap 均为 0。step6 结束后全部 GPU 已释放。

最终 checkpoint6→12 恢复测试通过，返回 `status=trained`、`optimizer_steps=12`，指本次短工程配方完成。本段恢复了 896 份 Adam 状态，恢复时 step 最小值和最大值均为 6，moments 有限且非零，scheduler 与 8 rank RNG 恢复通过；新增 6 个 optimizer 步、每 rank 24 个 backward microbatch，8 rank 均覆盖最长 31,740 token。推理适配器的 896 个 LoRA 张量有限且精确一致，扰动被检出，重载后 shard 与 forward 精确恢复，误差为 0。该阶段 GPU 分配峰值每 rank 最高 28.755 GiB，cgroup 的 1 秒采样最高观察值为 199.225 GiB，全机最低可用内存为 292.069 GiB，high/max/OOM 事件均为 0、swap 为 0。结束后所有 GPU 与服务 MainPID 均为 0，SSH 正常，主机可用内存约 492 GiB。trial adapter 位于 53 的 `outputs/qwen3_32b_joint_lora_v4_guarded_20261008/adapter`，仅供工程验证；工程测试结束时尚未做独立 MIC 预测评估。首轮正式流程见前节。

当前 36 条结构事实全为 `species_prior`；没有新菌株结构、蛋白定位金标或候选通透性标签。机制人工金标仍为 0。工程验证不证明结构或组学已经提高药效准确率，后续需结构消融及独立留出评估。

当前训练命令必须经 [guard_qwen_trial.py](../scripts/finetuning/guard_qwen_trial.py) 启动：独立 supervisor 位于训练 cgroup 外，训练 worker 在 gate 前等待。真实 cgroup 已核验 `memory.max=300 GiB`、`memory.high=260 GiB`、`memory.swap.max=0`、`memory.oom.group=1`；训练入口在加载权重前也要求有效硬限制。supervisor 每 1 秒采样，主机 `MemAvailable <160 GiB` 时停止整个本次训练组。guard 的 observed peak 是 1 秒采样观察值，不能当作连续测量的真实瞬时峰值。NCCL heartbeat 为 120 秒，DDP timeout 为 600 秒；cold 烟测的最长运行时间为 900 秒。已通过的 guarded stop1、checkpoint1→6 和 checkpoint6→12 工程测试均使用这些保护并保持 `pin_memory=False`。

以下 cold smoke 示例可在 GPU 资源空闲时复用。每次生成唯一的 supervisor/训练服务名和全新输出目录；不要复用旧 `pin_memory=True` 的空 checkpoint 目录，也不要覆盖已完成 12 步工程测试的 `outputs/qwen3_32b_joint_lora_v4_guarded_20261008`。53 已启用用户服务 linger，后台 supervisor 由 systemd 管理，SSH 断开后继续运行；supervisor 自身限额为 512 MiB、swap 0，最长 960 秒，训练 guard 最长 900 秒。

```bash
qwen_cold_root=/home/zkyd/data1/mzy/qwen-PRAXIS-MIC
qwen_cold_tag="cold-$("$qwen_cold_root/.venv/bin/python" -c 'import uuid; print(uuid.uuid4().hex[:12])')"
qwen_cold_unit="praxis-qwen-$qwen_cold_tag"
qwen_cold_watch="praxis-qwen-watch-$qwen_cold_tag"
qwen_cold_output="$qwen_cold_root/outputs/qwen3_32b_joint_lora_v4_$qwen_cold_tag"
qwen_cold_guard_report="$qwen_cold_root/reports/$qwen_cold_tag.guard.json"
qwen_cold_model_report="$qwen_cold_root/reports/$qwen_cold_tag.checkpoint_smoke.json"

systemd-run --user --unit="$qwen_cold_watch" --service-type=exec \
  --property=MemoryMax=512M --property=MemorySwapMax=0 \
  --property=OOMPolicy=kill --property=KillMode=control-group \
  --property=TimeoutStopSec=10s --property=RuntimeMaxSec=960s \
  --property=WorkingDirectory="$qwen_cold_root" -- \
  "$qwen_cold_root/.venv/bin/python" \
  "$qwen_cold_root/scripts/finetuning/guard_qwen_trial.py" \
  --report "$qwen_cold_guard_report" --unit "$qwen_cold_unit" \
  --working-directory "$qwen_cold_root" --max-seconds 900 \
  --max-memory-gib 300 --high-memory-gib 260 --min-host-available-gib 160 -- \
  "$qwen_cold_root/.venv/bin/accelerate" launch \
  --config_file "$qwen_cold_root/configs/finetuning/fsdp_a100_8gpu.yaml" \
  "$qwen_cold_root/scripts/finetuning/train_qwen_lora.py" \
  --config "$qwen_cold_root/configs/finetuning/qwen3_32b_joint_lora_v4_compact_trial.yaml" \
  --checkpoint-smoke --output-dir "$qwen_cold_output" --report "$qwen_cold_model_report"
```

查看同一次运行的日志和两个报告；重新 SSH 登录后，用启动时服务名中的同一标签恢复上述变量，不重新生成 UUID。模型报告中的 `checkpoint_smoke.status` 应为 `checkpoint_smoke_passed`，optimizer/backward 均为 0；guard 报告需确认限额校验、服务结果及清理结果。

```bash
journalctl --user -u "$qwen_cold_watch.service" -u "$qwen_cold_unit.service" --no-pager -n 200
cat "$qwen_cold_guard_report"
cat "$qwen_cold_model_report"
```

下面 v3 的训练/服务命令记录预定接口，真实运行仍须使用上述保护入口。cold 断点只验证未更新权重的保存与重载；当前已生成 12 步工程试训的 trial adapter，工程测试结束时尚未做独立 MIC 预测评估；现已获得首轮正式授权，采用前节的受保护流程。

## v3：SMILES、完整报告与可恢复训练

公开候选分子只有经过 RDKit 校验的 `candidate.smiles`，保留键连接、手性和源结构的盐形式。化合物名字、ChEMBL 分子编号、论文内编号只作私有溯源，不替代结构或进入候选特征。菌株身份、基因 ID 和事实引用 ID 有独立用途。

六项 MIC 条件 `medium/medium_supplements/temperature_c/exposure_hours/method/inoculum` 从 Web/CLI 贯穿实际推理各阶段，未知为 `null`；不与参考组学采样条件相互填补。

| 项目 | 数量 |
|---|---:|
| 训练组件 / 原始 MIC 测量 | 7,193 / 7,372 |
| 通过实际组学引用检查的报告 / 菌株 | 1,950 / 7 |
| 无组学辅助报告 | 5,243 |
| 联合机制报告 / 机制声明 | 104 / 128 |
| 新增背景待核隔离组件 / 测量 | 11 / 22 |
| 合计隔离原始测量 | 402 |
| 独立机制人工待标注候选 / 已完成人工金标 | 32 / 0 |

全部答案统一 `praxis.assessment-supervision.v1`，对应平台 Assessment，保留 `mic_observations`、机制证据等级/范围及实际工具引用。只有全部精确且同值的观测提供点值；异质或删失观测保留原值与开闭边界，点估计为 null。报告是来源核验后保守构建的**弱监督**，不是专家推理金标。无组学辅助报告明确无组学证据，不能声称通过平台组学校验。

检索词依据 SMILES 粗结构线索及训练时来源审核的机制选择，只引用实际命中的 feature。留出输入只用结构线索，不读取机制答案。当前有 41 种 profile+query 视图；确定性教师轨迹尚不证明模型学会自适应选择特征或组学提高准确率。未注明质粒不推定为野生型，相关背景冲突来源已隔离待原文复核。

`train.jsonl` 是唯一混合训练来源。`joint.train.jsonl` 是其中 104 条的替代子集，不能再次合并。`omics.train.index.jsonl` 定位 1,950 条 canonical 记录，不复制长轨迹。原始 MIC、组学、论文、基座继续复用单份资产。

检查包中 `inspection_samples.json` 有 7 条实际报告，`human_mechanism_annotation.queue.jsonl` 有 32 条冻结 validation 候选（四物种各 8 条，其中 8 条 source_unseen，标签空、pending），`training_mechanism_review.queue.jsonl` 独立保存 104 条训练审阅。

训练沿用 Qwen3-32B BF16、LoRA r=16/alpha=32、八卡 FSDP，assistant-only，不 packing、不截断。序列上限 **32,768**；官方 tokenizer 全量预检最长 **27,342** token，最长最终答案 **9,150** token。监督 token 份额为辅助 18.23%、组学报告 74.94%、联合机制 6.83%，初版每条每轮一次，根据验证结果决定后续混采。

正式配置 `configs/finetuning/qwen3_32b_joint_lora.yaml` 每 25 步保存断点，保留三份，包含 LoRA、optimizer、scheduler、RNG、Trainer 状态；不重复落盘基座。最终推理适配器为 `output_dir/adapter`，只有 adapter 不是完整可恢复断点。短试训配置为 `qwen3_32b_joint_lora_trial.yaml`，12 步、warmup=0、显式覆盖最长样本；第 6 步暂停，再恢复到 12。短试训只验证工程链路，不能当作完成正式微调。

```bash
cd /home/zkyd/data1/mzy/qwen-PRAXIS-MIC
PYTHONPATH=runtime .venv/bin/python scripts/datasets/verify_joint_sources.py \
  --dataset-dir data/processed/qwen_joint_sft_v3 \
  --source-path-map data/source_refs/joint_literature_20261008/source_path_map.json \
  --report reports/joint_v3_native_sources_20261008.json
.venv/bin/python scripts/finetuning/preflight_qwen.py \
  --config configs/finetuning/qwen3_32b_joint_lora.yaml \
  --report reports/joint_v3_qwen_preflight_20261008.json
```

原 scaffold 分配保持冻结：validation 1,419、test 2,382 组件。保守扫描原生 assay 元数据后，暂不评分未编码组合、衍生背景或动物来源；分别保留 **1,343 / 2,324** 组件。隔离名单为 `reports/v3_validation_assay_audit.json` 和 `reports/v3_test_assay_audit.json`。扫描不是人工机制金标。

独立生成器 `scripts/finetuning/predict_qwen.py` 只接受 `.inputs.jsonl`，不读答案索引或实测标签；实际组学工具仍受精确 profile 与事实引用校验。基线和适配器使用同一 `serve_qwen_adapter.py`，省略 `--adapter-dir` 即为未微调基线。服务从本地读取权重，禁用 thinking，不下载、不默默截断；Qwen 分析输出预算 **12,288**。

```bash
PYTHONPATH=runtime .venv/bin/python scripts/finetuning/serve_qwen_adapter.py \
  --base-dir models/Qwen3-32B --model-name qwen3-praxis-joint --port 8790 \
  --adapter-dir outputs/qwen3_32b_joint_lora_v3_trial/adapter
PYTHONPATH=runtime .venv/bin/python scripts/finetuning/predict_qwen.py \
  --inputs data/processed/qwen_joint_sft_v3/validation.inputs.jsonl \
  --output reports/adapter.validation.predictions.jsonl \
  --base-url http://127.0.0.1:8790 --model qwen3-praxis-joint
PYTHONPATH=runtime .venv/bin/python scripts/datasets/score_qwen.py \
  --dataset-dir data/processed/qwen_joint_sft_v3 --split validation \
  --predictions reports/adapter.validation.predictions.jsonl \
  --source-path-map data/source_refs/joint_literature_20261008/source_path_map.json \
  --audit reports/v3_validation_assay_audit.json --report reports/adapter.validation.metrics.json
```

少量输入试运行可用评分 `--pilot-subset`，输出明确标为 pilot；正式默认覆盖整个冻结集合，缺失/失败计入覆盖率。精确 MIC 用 log2 及稀释误差，删失保留边界不取中点，多观测顺序无关比较并报告数量/关系匹配。经验列表不是校准分布；机制准确率仍为 null，须完成独立人工标签。

平台分析/修订可单独接 Qwen，规划/审阅保留现有基础服务：

```text
PRAXIS_ANALYSIS_MODEL=qwen3-praxis-joint
PRAXIS_ANALYSIS_BASE_URL=http://127.0.0.1:8790
PRAXIS_ANALYSIS_PROVIDER=qwen
PRAXIS_ANALYSIS_MAX_OUTPUT_TOKENS=12288
```

## v2 历史准备记录

## 联合版本 v2：药物—菌株—组学—MIC—文献机制

| 范围 | 当前数量 |
|---|---:|
| 混合训练组件 / 原始 MIC 测量 | 7,204 / 7,394 |
| 有同菌株参考组学的组件 / 菌株 | 1,950 / 7 |
| 五项齐全的联合组件 / MIC 测量 | 104 / 110 |
| 联合样本的菌株 / 论文 / 机制声明 | 4 / 7 / 128 |
| 联合样本的单基因组 / 三种参考组学输入 | 69 / 35 |
| 因实验上下文或身份疑点暂不入训的源测量 | 380 |
| 补充来源明确实验条件的源记录 | 332 |

联合样本为 AB5075 35 个、ATCC 19606 43 个、ATCC 17978 18 个、AYE 8 个，目前均为鲍曼不动杆菌。混合训练中的另外三个有组学菌株是大肠杆菌 ATCC 25922、铜绿假单胞菌 ATCC 27853、肺炎克雷伯菌 ATCC 10031；它们目前提供 MIC 与参考基因组监督，还没有本批逐化合物核验的文献机制目标。AB5075 使用基因组、转录组、蛋白组参考，其余六株只有基因组参考。新增基因组视图记录 CDS 注释与明确的注释假基因，不等同于完整变异检测、基因功能实验或确定的耐药表型。

128 条机制声明分为实验支持 37、遗传证据 20、作者提出 15、类别背景 6、靶点未确定 50。来源证据的实验物种和条件保留在声明及限制中；其他物种的酶实验或突变实验不改写为目标菌株的直接证据。声明另有 `mechanism_role`，区分药物靶点、耐药机制、活性调节及未确定机制。耐药酶水解证据不能冒充药物杀伤靶点，联用增敏实验也不能替代单药 MIC。

这些是智能体依据原文核对后编写的机制弱监督，**人工金标为 0**。同株参考组学来自独立采集的样本或条件，没有声称与 MIC 培养物配对。工具轨迹复用实际平台的 overview/search/query 返回，但目前是固定查询模板，不能证明模型已学会自适应选择组学特征。这套目标是条件化 MIC 分布及有等级的机制声明，仍不是完整平台 `Assessment`，也没有模型性能或组学有效性结果。

| 文件 | 使用方法 |
|---|---|
| `train.jsonl` | 7,204 个混合工具对话；104 个联合目标替换对应数值目标 |
| `joint.train.jsonl` | 104 个联合目标的替代子集，**不要与 train.jsonl 一起加载** |
| `source_refs.jsonl` | 私有 MIC 定位、药物与文献绑定、原文证据跨度 |
| `quarantined_measurements.index.jsonl` | 380 条逐测量隔离原因与来源定位；同组正常测量保留 |
| `manifest.json` | 数量、文件指纹、证据等级、限制与冻结评估子集 |
| `qwen_joint_inspection_v2/joint_index.sqlite` | 药物、菌株、组学档案、论文与联合记录的关系索引 |
| `qwen_joint_inspection_v2/inspection_samples.json` | 10 个可直接检查的结构化样例 |

原始 MIC 文件复用已有单份标签；新文献和化合物映射按内容哈希存于 `data/source_refs/joint_literature_20261008`。新增 NCBI 原件仅下载到 53 的 `data/source_refs/joint_strain_omics_20261008`，平台读取的规范组学资产通过硬链接共享文件。SQLite 只保存小型摘要及 JSONL 的字节定位，不复制完整组学和论文。原始路径保留用于证据身份，53 的实际物理路径由 `source_path_map.json` 映射；来源路径、实测 MIC 和论文原文均不会作为推理答案输入模型。

监督仍仅计算 assistant 工具调用和最终目标的损失，未知实验条件保留为空；原文明确的培养补充、培养基和剂量才补入输入。相同公开输入下的正常重复 MIC 保留为多条实测观测，不取平均、不制造预测置信区间。联用、撤药后培养、其他药物 MIC、动物终点、未编码构建体以及待核菌株歧义均暂不进入混合训练。验证/测试保留原 scaffold 分配及无答案输入，尚未完成全部留出记录的原生实验上下文审阅，正式评分前仍需做这一轮审阅；当前没有独立机制金标测试集。

在 53 工作区运行独立来源核验及全量 tokenizer 预检：

```bash
cd /home/zkyd/data1/mzy/qwen-PRAXIS-MIC

PYTHONPATH=runtime .venv/bin/python scripts/datasets/verify_joint_sources.py \
  --dataset-dir data/processed/qwen_joint_sft_v2 \
  --source-path-map data/source_refs/joint_literature_20261008/source_path_map.json \
  --report reports/joint_native_sources_20261008.json

.venv/bin/python scripts/finetuning/preflight_qwen.py \
  --config configs/finetuning/qwen3_32b_joint_lora.yaml \
  --report reports/joint_qwen_preflight_20261008.json
```

联合配置沿用官方 Qwen3-32B BF16、LoRA r=16、八卡 FSDP、assistant-only 损失及不截断的 24,576 token 上限；数据和输出路径与 v1 分开，基座共享。上述命令不会启动 32B 训练。正式微调前先抽查联合机制样例，确认监督范围与证据等级；工具模板与完整智能体报告监督还需要后续扩充。

53 实际来源核验通过全部 7,204 个训练组件、7,394 次 MIC、104 个联合组件和 128 条机制声明，逐一检查原文件、字节定位、化合物、菌株及原文跨度。全量官方 tokenizer 与 assistant mask 预检通过，最长 **22,227 token**，没有截断；system/user/tool 的监督 token 为 0。相关本地测试 **169 passed**，Ruff 通过。没有加载或训练原始 32B 模型；之前 v1 的八卡前向结果不能替代当前最长样本的反向传播显存验证。汇总结果见 [实际验证报告](../reports/llm_platform/joint_training_verification_20261008.json)。

## 原数值版本 v1

2026-10-07 导出的是数值组件：分子结构、明确菌株身份、已知条件、实际可用的同株参考组学 → 条件化 MIC 观测分布。它不是完整的活性、杀菌、靶点与机制 `Assessment`，尚未训练模型，也不证明组学改善药效准确率。

下面的重新导出命令在保留原始 `local/strain_training_20261007` 的本机工程中运行。53 已有独立导出的训练文件，使用后文的预检与训练命令，不依赖复制整套原始工程数据。

```bash
.venv/bin/python -m praxis_virtualcell.finetuning.prepare \
  --supervision-dir local/strain_training_20261007/supervision/v1 \
  --joint-dir local/strain_training_20261007/joint/v1 \
  --output-dir local/qwen_praxis_mic_20261007

.venv/bin/python -m praxis_virtualcell.finetuning.prepare \
  --output-dir local/qwen_praxis_mic_20261007 --validate-only
```

已有输出目录非空时拒绝覆盖。导出先验证冻结的 scaffold 切分、源文件及组件指纹，再逐条将训练答案与规范实测标签比对。它不连接服务器、下载数据、调用 LLM 或启动训练。

## 文件与训练边界

| 文件 | 用途 | 是否进入模型输入 |
|---|---|---|
| `train.jsonl` | `messages`、`tools`、`record_id`、`source_record_id`、任务范围和目标契约 | 只有 `messages`、`tools` 进入 tokenizer |
| `source_refs.jsonl` | 原案例、私有答案 byte-offset 定位、药物/菌株/文献/scaffold 分组 | 否 |
| `validation.inputs.jsonl`、`test.inputs.jsonl` | 无答案的推理消息与明确的评估子集 | 仅 `messages`、`tools` |
| `validation.answers.index.jsonl`、`test.answers.index.jsonl` | 私有实测标签指针，仅独立评分读取 | 否 |
| `mechanism_review.index.jsonl` | 3 条目前未人工审查的机制组件定位 | 否，首轮排除 |
| `manifest.json` | 文件完整性、数量、删失关系、数据限制 | 否 |

原始组学与实验资产没有复制。`source_refs` 与答案索引保留本机规范路径及 SHA-256；部署到其他机器时由评分器的路径映射定位对应文件，不能把路径替换进模型消息。输入只显示结构、菌株及可用条件，不给模型实验 MIC、原文答案、旧小模型分数或私有标签文件。目标中的实测值仅用于监督损失。

Qwen 工具调用采用 `function.arguments` 对象；已有 OpenAI 风格 JSON 字符串会被解析，保留工具名、调用 ID 和实际工具返回。不导出 `reasoning_content` 或隐藏推理。只对 assistant 的工具调用与最终答案计算损失；system/user/tool 全部屏蔽。训练前必须用实际官方 tokenizer 检查 assistant mask、工具格式和 token 长度，不能默认普通 chat 模板支持该损失掩码。

## 实际数据范围（2026-10-07）

当前有 7,227 个训练组件、7,774 次源记录支持的 MIC 测量。其中 7,179 个无组学的菌株辅助组件，48 个同株参考组学组件使用同一个参考视图；同株跨来源数据的培养条件分别保留，没有声称与 MIC 实验同样本、同条件。工具视图只查询少量原生特征，不能称为全细胞状态编码。

目标保留 `=`、`>`、`>=`、`<`、`<=` 与区间及边界开闭，单位为 `ug/mL`。具有相同公开条件的重复测量共同构成一个经验观测列表，不取均值、删失中点或伪造校准区间。条件缺失保持 `null`。仅有生长抑制、S/I/R 或模型预测的记录不能冒充该 MIC 标签。

原有 scaffold 训练/验证/测试分配不变。验证集 1,419 个组件／1,540 次测量，测试集 2,383 个组件／2,659 次测量；只收录明确菌株身份，未知菌株评估案例分别排除 1,481 和 3,559 条。

每个评估记录包含 `cohorts`：`frozen_scaffold`、`compound_unseen`、`strain_unseen`、`source_unseen`、`compound_strain_source_unseen`。化合物分组采用与原评估一致的盐/电荷归一化，仅用于切分，测试结构保持原值；菌株使用规范的 strain ID，文献同时按 DOI 与数据库文档 ID 对比。验证子集相对训练检查；测试子集相对训练及全部明确菌株验证记录检查。测试的三类共同未见子集只有 234 个组件，验证为 176 个；不能将所有 scaffold 测试都称为菌株或来源未见测试，也不能称命名菌株未见为基因组谱系未见。

## 53 服务器工作区与官方基座

工作区为 `zkyd@10.102.106.53:/home/zkyd/data1/mzy/qwen-PRAXIS-MIC`。运行命令前进入该工作区；模型、数据、配置及输出分别使用以下路径：

| 内容 | 工作区内路径 |
|---|---|
| 官方基座 | `models/Qwen3-32B` |
| 已准备的对话与私有索引 | `data/processed/qwen_sft_v1` |
| LoRA 配置 | `configs/finetuning/qwen3_32b_lora.yaml` |
| 八卡 FSDP 配置 | `configs/finetuning/fsdp_a100_8gpu.yaml` |
| 适配器输出 | `outputs/qwen3_32b_lora_v1` |

基座固定为 [官方 Qwen/Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B/tree/9216db5781bf21249d130ec9da846c4624c16137)，revision 为 `9216db5781bf21249d130ec9da846c4624c16137`。下载的是原始 BF16 权重，共 17 个分片，权重张量合计 **65,524,246,528 字节**，含 safetensors 文件头的分片合计 **65,524,328,560 字节**。镜像仅用作文件传输；文件名、大小及 SHA-256 必须与固定官方 revision 的元数据对应后才能使用，不能把“下载完成”视为完整性验证通过。

工作区 `.venv` 继承 `/home/zkyd/data1/mzy/envs/praxis-gears-linux-a100-v1` 中的 Torch CUDA。该基础环境仍被其他任务使用，应保留；新任务依赖装在工作区环境中，不删除或重建基础环境。配置锁定 Torch 2.6.0、transformers 4.57.6、PEFT 0.18.1、TRL 0.28.0、Accelerate 1.12.0、datasets 4.5.0，预检核对实际版本。

## 算法与损失

首轮采用 **BF16 LoRA SFT**，基础权重冻结。LoRA `r=16`、`alpha=32`、`dropout=0.05`，适配 `q_proj/k_proj/v_proj/o_proj/gate_proj/up_proj/down_proj` 七类线性层。八张 A100 40 GB 使用 FSDP `FULL_SHARD`，启用 SDPA 注意力和梯度检查点。state dict 配置使用 `FULL_STATE_DICT`：固定版本 Trainer 拒绝 `save_only_model` 与 sharded state dict 的组合，因此保存时使用完整 state dict 路径；这不改变训练时的 `FULL_SHARD` 分片。

实际全量 token census 的最长训练记录为 **19,762 token**；48 个同株组学工具样本都超过 16,384 token，其余 7,179 个样本的长度第 99 百分位为 782。因此默认上下文上限改为 **24,576 token**，全部样本保留，关闭 packing；超过限制时预检直接失败，不截断对话。每卡微批次 1，梯度累积 4，八卡有效批次 32；学习率 `5e-5`，先用 1 epoch 作为起点。配置使用 cosine 调度和 0.03 warmup ratio。这些是首轮配置，不是已验证的最优参数或性能结果。

**assistant-only 损失通过真实 tokenizer offset 构建，保留官方 chat template。** TRL 0.28.0 没有针对 Qwen 自动修补 assistant mask 的路径，脚本不依赖这种行为：先按官方模板串行化，再使用 fast tokenizer 的字符 offset 找到 assistant 工具调用与最终答案，给它们保留 label；system、user、tool 及空的 thinking 框架 label 为 `-100`。配置中的 `assistant_only_loss=False` 表示不采用 TRL 内置生成标签机制，不表示对所有 token 计算损失；准备好的 `labels/assistant_masks` 会交给 collator，并检查实际 batch 标签与原 mask 一致。

脚本核对“官方模板 tokenize”与“串行化文本再 tokenize”的 token 序列完全一致，并用角色哨兵验证工具结果和用户消息没有监督 token。不开启隐藏思维训练，不修改官方模板，不插入自定义角色 token。

长工具对话的 decoder 仍读取完整输入和上下文。输出层使用原生 Qwen3 的 `logits_to_keep` 与 `shift_labels`，仅在需要监督 assistant 下一 token 的位置计算 `lm_head` 和交叉熵，减少无损失位置的大词表 logits 内存；它不删减 decoder 输入、不改变目标 token，也没有引入新的依赖。代码提供 tiny 随机 CPU Qwen3 的数值等价自检，分别比较 dense 模型与 PEFT 模型在完整 logits 和选取监督位置两条路径上的 loss 与梯度。53 固定环境已通过 4 种情况及 74 个参数梯度比较：loss 最大绝对差为 `4.77e-7`，梯度最大绝对差为 0；没有对原始 32B 模型进行微调。

## 无训练预检与显式训练

默认命令验证文件、消息、包版本、官方 tokenizer、角色 mask 和全训练集长度，不加载完整模型，不对原始 32B 模型反向传播或优化。随机 CPU 小模型的 loss／梯度单元检查会执行反向传播，以确认优化后的损失与普通损失数值等价：

```bash
cd /home/zkyd/data1/mzy/qwen-PRAXIS-MIC

.venv/bin/python scripts/finetuning/preflight_qwen.py \
  --config configs/finetuning/qwen3_32b_lora.yaml \
  --report outputs/preflight_qwen.json
```

不加 `--train` 运行训练入口也只做预检。只检查 JSON、不导入训练库时，可给预检入口增加 `--schema-only`，但这不能代替真实 tokenizer 和 mask 验证。

需要显式检查 BF16/FSDP 模型前向时，使用独立开关；该命令加载完整模型，但不反向传播、进行优化或保存适配器：

```bash
.venv/bin/accelerate launch \
  --config_file configs/finetuning/fsdp_a100_8gpu.yaml \
  scripts/finetuning/preflight_qwen.py \
  --config configs/finetuning/qwen3_32b_lora.yaml \
  --gpu-forward --report outputs/preflight_qwen_gpu.json
```

真正训练必须在预检通过后显式使用 `--train`：

```bash
.venv/bin/accelerate launch \
  --config_file configs/finetuning/fsdp_a100_8gpu.yaml \
  scripts/finetuning/train_qwen_lora.py \
  --config configs/finetuning/qwen3_32b_lora.yaml \
  --train --report outputs/training_qwen.json
```

训练关闭在线上报与中间完整检查点，最终仅保存 LoRA 适配器及 tokenizer；不合并、复制或覆盖基座权重。验证／测试只有无答案输入，不能直接交给 SFT Trainer 求验证损失，配置因此设置 `eval_strategy=no`。独立评估先生成答案，之后由评分器读取私有 MIC 定位指针，分别报告删失关系及各留出子集表现。

当前数值分布契约输出还需要与平台完整 `Assessment` 接口明确区分；不要把这一适配器当已训练好的完整机制智能体。缺少完整报告监督时保持机制未知，不能通过脚本补造靶点或杀菌标签。远端模型校验、实际 token 长度、mask 自测、GPU 前向和训练结果应以工作区生成的验证报告为准；本执行说明不代替这些实际结果。

## 53 实际准备结果（2026-10-07）

官方原始权重的 17 个分片全部完成 SHA-256 核验。全量 7,227 个训练记录通过真实 tokenizer、工具协议、角色 mask 和长度检查；全部上下文保留。最长 19,762-token 样本已通过八卡 BF16/FSDP 前向，仅 493 个监督位置计算输出层，每卡峰值已分配显存约 16.415 GiB，损失有限；优化步数及原始大模型反向传播次数均为 0，没有保存训练适配器。这个前向结果不代表正式训练的反向传播显存已验证，也不代表 MIC 预测准确率。

服务器实际资产检查通过：59 个原生/参考档案中有 24 个菌株参考集合，各自的可用单模态选择保持菌株身份；11,973 个私有答案定位均经过源文件 SHA 与 byte offset 回读检查。原始大数据在 `data/source_refs` 中以软链接引用，规范标签保存在 `canonical_labels`，私有评估映射保存在 `source_path_map.json`；`data/omics` 指向单份处理后的菌株档案。只读机制目录当前仅有 7 条 AB5075 基因功能注释，尚无经核验的候选化合物—蛋白相互作用金标。

平台 CI 同选择集加微调预检测试本地为 1,045 passed／2 skipped；53 上的相关测试为 363 passed／1 skipped，完整预检另已实际执行 CPU 数值自检。全仓另有 5 项旧 MDR 可选 FBA 依赖或旧目录路径测试失败，新智能体入口不导入这些旧预测模块。GitHub 登录缺少 workflow scope，原 CI 配置保持不变，新增微调预检在两端单独验证。

工作区 `reports/` 保存模型校验、实际资产、包版本冻结、token census、mask 与数值自检、GPU 前向及代码版本报告；`README.md` 为本说明。当前材料是可复核的首轮准备，下一步应补充多菌株组学监督和审核合格的完整智能体报告，再进行小规模试训及独立评估。
