# 2026-09-23 生成候选

两次 SyntheMol-MCTS v1.0.3 运行使用 seed=17，每次 20 rollouts，各得到相同的 24 个候选。模型为作者 10 成员 antibiotic_chemprop 集成。`repeat_1/molecules.csv` 和 `repeat_2/molecules.csv` 保留结构、模型分数及反应/原料信息；`result.json` 记录运行与复现检查。

这些是未经生物验证的生成候选。score 是作者分类评分，不能解释为实测 MIC、杀菌率或靶点证据。

代码及资产来源、作者归属和 MIT/CC BY 4.0 许可见 `integrations/synthemol/README.md`。公开 protocol 中的原服务器绝对路径已替换为 `<original-project-root>`；原始协议和完整环境快照仅本地保留在 `local/server_recovery/ab_world_model/synthemol_original/`。完整历史依赖清单不用于安装当前组件。
