# PRAXIS-VirtualCell

面向抗菌候选分子的分析平台基础：复用 LLM 工具运行框架、直接 MIC/药敏预测器和可追溯的机制证据。2026-10-06 将 PRAXIS-MDR-GNB 与 Ab-虚拟细胞世界模型的可用资产整合到本仓库，历史工程归档到同级 `PRAXIS-virtualcell-old/`。

## 当前可用能力

- `praxis2/`：LLM 工具调用循环、记忆、任务执行以及 PubMed/UniProt/PDB/PubChem 等检索和对接工具接口。
- `praxis_virtualcell/mdr_gnb/`：已知药物 AMR 分类、大肠杆菌 SMILES→MIC/肽活性预测、规则/OOD/报告和单药 API。
- `components/abaumannii_mic/`：独立的鲍曼不动杆菌直接 MIC 工具；显式选择数据和模型目录，不依赖世界模型训练。
- `integrations/synthemol/`、`candidates/`：SyntheMol 的恢复/验证脚本和已生成候选。作者生成器及其外部资产需按来源说明另行恢复。
- `reports/antibacterial/`：保留已有模型表现、失败与适用边界；原始科学结果不因目录整合而升级。

目标流程是：候选生成 → 活性工具评分 → 菌株背景/机制证据检索 → LLM 汇总 → 实验验证。当前各工具已归入同一工程，但批量智能体闭环、菌株条件化的新化合物预测及新靶点预测仍需后续开发。

MIC 与生长抑制是当前主要终点；没有相应数据时不输出杀伤率、MBC 或时间杀菌曲线。LLM 的机制推断应标为假说并关联证据。

## 安装与使用

在仓库根目录创建环境并安装：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[api,chemistry,dev]'
.venv/bin/praxis-mdr --help
.venv/bin/praxis-mdr run --request examples/ecoli_activity.json
.venv/bin/praxis-mdr serve --host 127.0.0.1 --port 8000
```

`praxis-vc` 是同一 MDR CLI 的兼容入口。鲍曼 MIC 组件单独安装与调用，详见 [组件说明](components/abaumannii_mic/README.md)。

上述真实预测使用本地 `data/mdr_gnb/` 或 `models/abaumannii/` 的工件。GitHub 保存代码、配置、来源说明和小型结果；大型权重、原始数据及服务器恢复资料仅留本地。缺少工件时会报告不可用或弃权。

## 导航

- [安装与环境](docs/INSTALL.md)
- [项目结构](docs/REPOSITORY-LAYOUT.md)
- [数据及模型清单](docs/DATA-ASSETS.md)
- [迁移与恢复](docs/CONSOLIDATION.md)
- [验证范围](docs/TESTING.md)
- [第三方数据来源与许可](docs/DATA-LICENSES.md)

代码许可为 MIT。第三方实验数据与模型资产遵循各自来源许可。
