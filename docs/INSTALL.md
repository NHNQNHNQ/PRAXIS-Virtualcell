# 安装

主包使用 Python 3.11 或更新版本；现有 MDR 工件要求 scikit-learn 1.9.0。新建环境后使用 editable 安装，因为 MDR 的外部工件按仓库根定位。

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,api,chemistry]'
.venv/bin/praxis-mdr --help
```

`api` 提供本地 FastAPI 服务，`chemistry` 提供 RDKit 分子特征；`mechanistic` 为可选 FBA 侧车。`server` 为继承的 praxis2 多用户服务依赖，非单药 CLI 的必需安装项。

AB MIC 使用独立组件的安装说明。SyntheMol 也使用独立环境，避免其原始 Chemprop/PyTorch/RDKit 版本与 MDR 的已序列化模型环境混用。

本地已迁入全部 MDR 工件与从 2026-09-13 交付包恢复的 AB direct MIC 权重。GitHub 克隆不包含这些大型工件；请按 [数据清单](DATA-ASSETS.md) 和各组件来源说明恢复。原数据及权重未因本次整合重训。

LLM 凭据放 `.env` 或环境变量，示例见根 `.env.example`；离线数值工具不需要 LLM 凭据。
