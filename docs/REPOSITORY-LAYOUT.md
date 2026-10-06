# 项目结构

```text
praxis2/                         LLM 与工具运行框架
praxis_virtualcell/mdr_gnb/       AMR、EC MIC、规则、报告和 API
praxis_virtualcell/{core,...}/   MDR 使用的最小共享兼容模块
components/abaumannii_mic/       AB 直接 MIC 独立组件
integrations/synthemol/          生成器恢复/验证脚本与来源
candidates/                     保存的生成候选
brains/_common/                 通用检索/对接工具规则
brains/virtualcell/             默认抗菌分析规则与资料卡
data/mdr_gnb/                   MDR 数据及工件（本地）
data/antibacterial/abaumannii/   AB 实验数据与冻结划分（本地）
models/abaumannii/              AB 直接 MIC 权重（本地）
reports/antibacterial/           已有模型和生成器的验证依据
research/mdr_gnb/               菌株/MIC 关联研究脚本及探索数据
tests/                          保留能力的回归测试
local/server_recovery/          服务器资产恢复资料（本地）
docs/                           当前说明
```

原 Python 命名空间保持不变，以兼容已序列化 MDR 工件。AB 组件独立安装，避免改变已有模型架构或让主入口隐式训练世界模型。

旧 VC API/React/Streamlit、K562 与哺乳类扰动、未接入的多阶段合同、世界模型训练工程、论文和历史输出集中到同级 `PRAXIS-virtualcell-old/`。旧 Git 工作树通过 Git 正式移动，保留其未提交内容。
