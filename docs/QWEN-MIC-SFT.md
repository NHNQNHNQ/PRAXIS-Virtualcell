# Qwen MIC 工具对话微调准备

本导出训练一个数值组件：分子结构、明确菌株身份、已知条件、实际可用的同株参考组学 → 条件化 MIC 观测分布。它不是完整的活性、杀菌、靶点与机制 `Assessment`，尚未训练模型，也不证明组学改善药效准确率。

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
