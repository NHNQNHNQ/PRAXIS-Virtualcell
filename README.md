# PRAXIS-VirtualCell

加载具体菌株的真实组学数据，由 LLM 直接预测候选分子的抗菌活性、MIC，并提出有数据依据的靶点与机制假说。默认使用 DeepSeek；组学查询与结构处理工具不承担药效预测。

## 当前入口

- `praxis_virtualcell/data_packs/`：从原平台恢复的 AnnData/MuData 校验、只读矩阵读取与显式特征对齐。
- `praxis_virtualcell/omics/`：菌株/样本输入包与 NPZ 转录组适配；首包是 AB5075 历史未给药参考 `AB5075-AZI000`。
- `praxis_virtualcell/llm_prediction/`：组学与结构工具调用、LLM 预测、事实引用校验、JSON/Markdown 报告。
- `praxis2/llm/`：复用原平台客户端，支持 DeepSeek 思考模式与连续工具调用。
- `praxis_virtualcell/web/`：选择菌株样本、输入候选结构、查看组学概览与分析报告的本地页面。

旧 MIC、AMR、QSAR、扰动和世界模型不进入新预测入口。实测 MIC 记录不作为推理输入或查表答案。历史工具保留在 `praxis-mdr` 和独立组件中，已有结果保持原科学范围。

## 启动

安装见 [INSTALL](docs/INSTALL.md)。本地 `.env` 保存凭据并被 Git 忽略：

```text
DEEPSEEK_API_KEY=自己的本地凭据
PRAXIS_ANTHROPIC_BASE_URL=https://api.deepseek.com
PRAXIS_MODEL=deepseek-v4-pro
```

`PRAXIS_ANTHROPIC_BASE_URL` 是原框架兼容配置名，实际使用 OpenAI-compatible Chat Completions。凭据只在服务端读取。

```bash
.venv/bin/praxis-vc profiles
.venv/bin/praxis-vc inspect --profile AB5075-AZI000
.venv/bin/praxis-vc serve --port 8787
```

打开 `http://127.0.0.1:8787`。页面显示实际输入包的身份与数据覆盖；分析后可查看报告、工具轨迹以及 JSON/Markdown。

```bash
.venv/bin/praxis-vc batch --profile AB5075-AZI000 --input candidates/synthemol_20260923/repeat_1/molecules.csv --limit 1 --output reports/llm_live/first-candidate
```

批量导入只读取 SMILES 和候选编号，忽略 CSV 的历史 score/Q_value 与终点字段。去掉 `--limit` 可处理完整候选集；每个候选都会调用配置的 LLM。

## 数据与结果语义

首包含真实转录组参考与参考注释，不宣称拥有实测蛋白组、代谢组或新分离株当前状态。未知时间、温度、基因型和生长期保持未知。处理后表达、实际 delta 和 MIC 标签不进入新候选工具结果。

MIC 是未经校准的 LLM 估计，可以为未知；它表示生长抑制，不等于杀伤率。靶点与机制保留假说身份。引用校验只证明观察值与工具返回一致，不证明药效正确或靶点因果关系。无实际组学查询或事实引用校验失败时返回 `unsupported`，不调用其他预测器补数值。

大型数据只存本地 `data/organisms/`，对应归档路径保留引用。数据准备与复现见 [OMICS](docs/OMICS.md)。本地 `.env` 与完整实时报告不进入 GitHub。

## 验证与后续

离线测试覆盖实际文件读取、样本/特征对应、未来数据隔离、多轮工具历史与事实引用。真实 API 运行验证工程链路，尚不构成独立药效准确率评估。当前使用基础 API 模型，尚未训练专用微调模型。

作者药物生成器及外部资产仍需恢复。现有 24 个候选结构可进入同一接口；重复记录不计为 48 个不同分子。

历史整合与来源见 [CONSOLIDATION](docs/CONSOLIDATION.md)、[DATA-ASSETS](docs/DATA-ASSETS.md)、[DATA-LICENSES](docs/DATA-LICENSES.md)。代码许可 MIT；第三方数据遵循原来源许可。
