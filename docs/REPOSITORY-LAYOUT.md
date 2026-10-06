# 项目结构

```text
praxis2/                         LLM 与工具运行框架
praxis_virtualcell/omics/        菌株身份、组学输入包和真实表达查询
praxis_virtualcell/data_packs/   原平台 AnnData/MuData 读取与特征对齐
praxis_virtualcell/llm_prediction/ 纯 LLM 分析、事实引用校验和报告
praxis_virtualcell/web/          本地菌株/候选分析页面与 API
praxis_virtualcell/cli.py        当前 praxis-vc 入口
praxis_virtualcell/mdr_gnb/       AMR、EC MIC、规则、报告和 API
praxis_virtualcell/{core,...}/   MDR 使用的最小共享兼容模块
components/abaumannii_mic/       AB 直接 MIC 独立组件
integrations/synthemol/          生成器恢复/验证脚本与来源
candidates/                     保存的生成候选
brains/_common/                 通用检索/对接工具规则
brains/virtualcell/             默认抗菌分析规则与资料卡
data/organisms/                 当前 LLM 可读取的组学包与单份原始资料（本地）
examples/organisms/             可追溯输入包清单示例
data/mdr_gnb/                   MDR 数据及工件（本地）
data/antibacterial/abaumannii/   AB 实验数据与冻结划分（本地）
models/abaumannii/              AB 直接 MIC 权重（本地）
reports/antibacterial/           已有模型和生成器的验证依据
reports/llm_live/                实时 LLM 输出和工具调用轨迹（本地）
research/mdr_gnb/               菌株/MIC 关联研究脚本及探索数据
tests/                          保留能力的回归测试
local/server_recovery/          服务器资产恢复资料（本地）
docs/                           当前说明
```

当前入口是 `praxis-vc`，由所选组学包和 LLM 直接生成分析。原 Python 命名空间保持不变，以兼容已序列化 MDR 工件；历史 `praxis-mdr` 和独立 AB 组件不进入新预测链路。

旧 VC API/React/Streamlit、K562 与哺乳类扰动、未接入的多阶段合同、世界模型训练工程、论文和历史输出集中到同级 `PRAXIS-virtualcell-old/`。旧 Git 工作树通过 Git 正式移动，保留其未提交内容。
