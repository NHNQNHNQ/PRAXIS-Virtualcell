# SyntheMol 候选生成与评估接口

这里保留原项目对 **SyntheMol-MCTS v1.0.3** 的运行、筛选表提取、来源重叠分析和评估脚本。默认外部资产目录是 `integrations/synthemol/external/SyntheMol-MCTS`，也可以显式传入 `--generator-root`。

**外部代码与权重没有迁入本地。** 原服务器曾完成下载和运行；本地只有下载验证、脚本、24 个候选和历史评估结果。`download_verification.json` 记录的是 2026-09-22 服务器获取状态，不表示当前电脑已经拥有这些资产。生成脚本在外部资产缺失时明确报错；本次没有下载大型生成资产，也没有重新生成或训练模型。

来源是 [作者仓库 v1.0.3](https://github.com/swansonk14/SyntheMol/tree/v_1.0.3)，固定 commit `7444ee4762244cf53d316822609e288505c51457`。作者公开资产见 [Zenodo DOI 10.5281/zenodo.13932150](https://doi.org/10.5281/zenodo.13932150)。既有获取记录标明：代码 **MIT**，数据与权重资产 **CC BY 4.0**。引用作者与原论文，保留上述资产许可；主仓库代码许可不覆盖外部资产。

完整原始包的校验记录：Data.zip 885,192,166B、MD5 `fd5cce7c87c82da07ed8f138f1fcfad0`；Models.zip 197,528,579B、MD5 `4cbb05926cebc0584b4093b5e94a8daa`。`verify_download.py --generator-root PATH` 只校验已有代码提交、归档及 CRC，不执行模型 pickle。

## 迁入资产

- `candidates/synthemol_20260923/`：两次固定种子运行各 24 个候选、协议与结果。它们是生成候选，尚无这些候选的生物验证。
- `reports/antibacterial/synthemol/`：2026-09-23 历史评分验证报告、覆盖、指标、预测和推理回放记录。
- `data/antibacterial/abaumannii/`：ChEMBL MIC 和本地 Abaucin 实测生长表。原始 XLSX 和生长表许可尚未本地确认，因此 Git 忽略。
- `local/server_recovery/ab_world_model/`：原始服务器路径文档和未脱敏运行记录，只保留本地。

历史评估曾使用服务器 direct MIC seeds **17/42/314159**。目前本地导入的是 2026-09-13 direct MIC seeds **17/42/2026**，两套版本不能混称。评估脚本默认保留原三种子；若做旧本地版本的独立回放，显式传 `--seeds 17 42 2026` 并使用新的输出目录。

## 使用已有生成环境

原生成器运行环境是 Python 3.11、SyntheMol 1.0.3、Chemprop 1.6.1、PyTorch 2.0.1+cpu、RDKit 2022.9.5、scikit-learn 1.2.2。保留与主平台科学环境的隔离；旧 scikit-learn pickle 不应在新的 sklearn 环境里静默加载。

```bash
python integrations/synthemol/scripts/run_generation_check.py \
  --generator-root /path/to/verified/SyntheMol-MCTS \
  --output /tmp/synthemol_new_generation
python integrations/synthemol/scripts/test_evaluation.py
```

完整评估依次运行 `evaluate_synthemol.py prepare/predict/report`，各阶段都需要显式 `--output`；用 `--data-root`、`--prediction-root`、`--generator-root` 指定迁移后的输入。`prepare` 创建新目录，不覆盖历史结果。评分阶段需要原作者代码和资产；当前本地没有完整 `evaluation_records.csv` 与逐成员数组，本次只运行了不依赖它们的 5 项评估单元测试。

抑菌筛选标签使用实测 Mean/Mean_Growth，保留 50 µM、ATCC 17978、LB、工作表及行号；旧模型 Activity 列不作真值。MIC 与固定浓度生长抑制分别评价，作者分类分数不转换为 MIC。论文数据来源与许可说明见 `components/abaumannii_mic/README.md`。
