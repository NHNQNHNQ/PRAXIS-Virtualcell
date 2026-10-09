# 菌株上下文中的细胞结构

2026-10-08 接入版：结构由平台维护为有来源的事实，LLM 负责条件化分析。53 上八卡 Qwen3-32B 的 12 步 LoRA 工程测试已通过，包括最长样本反向、断点恢复与适配器保存/重载。试训适配器位于 `outputs/qwen3_32b_joint_lora_v4_guarded_20261008/adapter`，仅供工程验证；独立 MIC 预测评估尚未执行，正式全量训练继续暂停。

设计参考 [Towards the construction of a virtual yeast](https://www.nature.com/articles/s41586-026-10574-9) 将机制知识、亚细胞结构、动态状态分别组织的思路。本平台当前实现有来源的结构上下文与条件化推理，尚无动态细胞状态模拟或实验闭环。

## 已接入的行为

默认规划—分析—审核—修订流程先读取当前档案对应的结构上下文。分析阶段可调用 `cell_structure_overview`、`query_cell_structure`，查询区室、邻接关系或有原始来源的蛋白定位。结构事实不提供 MIC、通透性预测或药物结合分数。

`Assessment.structure_analysis` 包含区室假说、可达性与屏障假说、限制。开启结构分析时，该字段必须提供；有结构条目时至少引用一个真实区室。每条结构假说必须引用实际返回的 `/structures/N/compartment`，保留 `structure_id`、`evidence_scope`、`evidence_type`。RNA、蛋白丰度等证据分别放在组学的结构化 observations 中，不能冒充定位记录。数值 MIC 的原组学证据要求继续执行。

当前小型事实库 [catalog.json](../data/cell_structure/catalog.json) 有 36 条事实，覆盖鲍曼不动杆菌、大肠杆菌、铜绿假单胞菌、肺炎克雷伯菌，各五个区室节点与四条邻接关系。原始论文、图表定位、来源株和条件见 [来源说明](../data/cell_structure/README.md)。这四种菌的基础拓扑均为革兰阴性菌包膜；该版本尚不能展示所有细菌类别的结构差异。

当前全部为 `species_prior/reference_knowledge`。**菌株结构实测证据、原始蛋白定位记录均为 0**。平台支持加载这类记录，但没有用参考知识或基因存在填充数量。尚未覆盖的物种返回空结构与缺口，不自动套用一个细菌模板。

## 事实的身份与范围

每条事实有区室或蛋白原生 ID、来源 URL/定位、物种与菌株范围、证据类型、独立来源条件。物种背景和菌株证据分别标记 `species_prior`、`strain_evidence`。

菌株事实要求精确物种、菌株、命名空间和来源基因型范围匹配。同名的 study-local 菌株不能跨研究借用；未知基因型不等于野生型。来源结构与参考组学可来自不同条件，不表示当前 MIC 培养物中的细胞。基因存在、RNA 表达、蛋白丰度均不能单独证明蛋白定位。

区室拓扑不等于三维细胞坐标，也不等于蛋白三维结构。膜屏障支持可达性讨论；实际通透、胞内浓度、结合与杀伤仍需各自证据。所有药物候选公开输入继续仅使用校验后的 SMILES。

## 查看与调用

不用调用 LLM 即可查看当前档案的结构事实：

```bash
.venv/bin/praxis-vc inspect --profile AB5075-STRAIN-REFERENCE --cell-structure
```

自定义结构库用全局 `--structure-catalog PATH`。默认平台分析开启结构；`analyze/batch --without-cell-structure` 用于有意比较。历史单分析 Python 接口 `analyze_candidate` 可用 `include_cell_structure=True` 开启；旧 v3 数据保持兼容。

Web 提供 `GET /api/profiles/{profile_id}/cell-structure`，报告展示区室来源、菌株证据范围、蛋白定位与可达性未知项。`POST /api/analyze` 的 `include_cell_structure` 默认 true，可显式 false 进行对照。

## 监督数据

结构监督从封版 v3 衍生，保留 7,193 组件、7,372 原始 MIC、104 联合机制记录及原组学观察。其中 1,950 条有菌株组学的记录加入真实结构工具观察和有范围的弱监督；5,243 条无 profile 辅助记录保持原行。候选分子仅为 SMILES。

v4 共享 v3 的 MIC/机制私有来源索引、留出答案索引与隔离索引；原始组学、论文、MIC 与基座继续单份保存。新增结构索引记录原行和衍生行指纹，组学索引的字节定位随新训练文件重新构建。验证/测试保持原分配及原有公开组学工具轨迹，仅增加结构工具定义与系统说明，不把实测答案加入输入。

七个菌株各一条真实衍生样例保存在本地 `local/joint_dataset_20261008/qwen_joint_inspection_v4_compact/structure_samples.json` 和 53 的 `data/processed/qwen_joint_inspection_v4_compact/structure_samples.json`。样例中的 MIC 是训练监督答案，不是新预测。

结构目标是可追溯的弱监督：候选特异可达性明确 unknown，不编造新的 MIC 或机制金标。当前物种模板与教师查询尚不证明结构提高准确率；后续需同药物—菌株—条件的结构消融和独立留出评估。

完整九条结构视图 `qwen_joint_sft_v4` 有 45 条超过 32,768，上限检查失败记录保留。独立候选 `qwen_joint_sft_v4_compact` 通过真实查询选择全部五个区室节点，运行时仍提供完整邻接图。7,193 条全量预检通过，最长 31,740，最长最终回答 10,890，未截断数据。非锁页 CPU 转存已通过 222 项梯度比较与真实八卡工程测试；checkpoint1→6→12 正确恢复 Adam、scheduler 和各 rank RNG，896 个 LoRA 张量及扰动后参数/输出重载检查通过。训练期间全机最低可用内存的观测值为 292.07 GiB，无 OOM 或 swap，结束后显存和进程已释放。完整阶段结果及旧失败记录见 [试训验证报告](../reports/llm_platform/qwen_v4_compact_trial_verification_20261008.json)，结构来源检查见 [接入验证报告](../reports/llm_platform/cell_structure_verification_20261008.json)。

训练运行使用训练 cgroup 外的独立 supervisor；真实限额为硬上限 300 GiB、high 260 GiB、swap 0、`memory.oom.group=1`，训练入口在权重加载前要求有效硬限制。主机可用内存低于 160 GiB 时停止整个本次训练组；guard 的 observed peak 来自 1 秒采样。NCCL heartbeat 为 120 秒、DDP timeout 为 600 秒，cold 烟测最长 900 秒。已通过的 stop1 及两段恢复工程测试均使用非锁页 CPU 转存，具体入口见 [QWEN-MIC-SFT](QWEN-MIC-SFT.md)。

## 实际接入验证

690 项针对平台、结构、数据和微调准备的 CPU 测试通过，4 项跳过；Ruff 与 diff 检查通过。一次真实 DeepSeek 分析通过数值引用，但科学审核识别了未核验的基因—蛋白桥接和过度通透性解释。审核引用提示修复后，12,288 token 的修订仍被截断，平台拒绝发布；保留原运行记录。

最后复用原真实规划、分析和已校验初审，仅把修订及复审再调用一次，输出预算为 24,576；两次真实 API 调用后通过，最终 activity=uncertain、MIC=null、confidence.calibrated=false。没有手工改答案、引用或来源数据。该结果验证录制分析的修订与复审接线；没有一条重新全程调用的单次成功运行，也不是药效准确率评估。思考 token 占供应商输出预算，不能把 Qwen 禁用 thinking 的 12,288 预算直接视为 DeepSeek 同等有效答案容量。

## 后续数据补充

下一批应优先补当前七个训练菌株的官方定位注释、膜/细胞壁组成及有条件记录的结构测量。已有 PAO1 原始显微研究和 NCBI 原生 OprF 定位线索，但 PAO1 不是本批 ATCC 27853；完成原生身份与证据审核后才可加入新事实版本。跨菌株迁移保留为物种背景，不能替代本株证据。
