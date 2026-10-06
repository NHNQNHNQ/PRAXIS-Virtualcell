"""Summarize the measured runtime and frozen retrospective evaluation."""
import argparse
import json
from pathlib import Path
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--evaluation-root", type=Path, required=True)
parser.add_argument("--generation-root", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
ev = args.evaluation_root
generation = json.loads((args.generation_root / "result.json").read_text())
coverage = json.loads((ev / "coverage.json").read_text())
metrics = pd.read_csv(ev / "metrics.csv")
comparison = pd.read_csv(ev / "baseline_comparison.csv")
studies = pd.read_csv(ev / "within_study_metrics.csv")
records = pd.read_csv(ev / "evaluation_records.csv", low_memory=False)
status = json.loads((ev / "status.json").read_text())
assert generation["completed"] and status["completed"]
names = {"antibiotic_chemprop": "Chemprop", "antibiotic_chemprop_rdkit": "Chemprop＋RDKit",
         "antibiotic_random_forest": "随机森林", "knn5_score": "5近邻基线",
         "direct_mic_score": "项目直接 MIC（三种子均值）"}
main = metrics[(metrics.cohort == "MIC") & (metrics.subset == "all_unseen_parents")]
novel = metrics[(metrics.cohort == "MIC") & (metrics.subset == "unseen_scaffolds")]
far = metrics[(metrics.cohort == "MIC") & (metrics.subset == "nearest_training_tanimoto_le_0.4")]
within = studies.groupby("score").agg(studies=("study", "nunique"), median_auc=("roc_auc", "median"))
default_main = main.set_index("score").loc["antibiotic_chemprop"]
default_far = far.set_index("score").loc["antibiotic_chemprop"]
direct = comparison[comparison.score.eq("direct_mic_score")].set_index("split")
screen = records[records.cohort == "screen_50uM"]
screen_eligible = int(screen.eligibility.eq("eligible").sum())
parts = ["# SyntheMol：运行检查与未见分子评分验证\n",
         "日期：2026-09-23。范围仅为运行生成器和检验评分，不接入 V1，不重新训练或按测试集挑选权重。\n",
         "## 结论\n",
         f"生成器已经实际跑通。固定 seed=17，独立启动两次，每次 20 次搜索，均得到 {generation['unique_smiles']} 个不同、可解析的候选结构。两次结构及评分逐项一致。这里只验证运行与复现，不表示候选已具备抗菌活性。\n",
         f"原始筛选表的 {len(screen):,} 条实验记录经过结构查重后，只有 {screen_eligible:,} 条符合本轮保守的独立性条件。训练来源重叠 {screen.eligibility.eq('author_seen').sum():,} 条，另有无效或非有机结构 {screen.eligibility.eq('invalid_or_nonorganic_structure').sum():,} 条。因此不能利用这些表给出同条件、未见分子的独立验证通过结论。\n",
         f"MIC 主表共有 {coverage['project_mic_rows']:,} 条记录。排除作者训练来源的结构重叠后，保留 {coverage['eligible_rows']:,} 条测量、{coverage['eligible_parents']:,} 个归组后的独立化合物。它们支持下面的跨终点评分检验，但不是作者原来的固定浓度抑制率任务。\n",
         f"**人话结论：能生成，不等于能选准。** 默认 Chemprop 评分器对未见化合物的 MIC 排序 AUC 为 {default_main.roc_auc:.3f}；在与训练分子相似度更低的子集上只有 {default_far.roc_auc:.3f}，接近随机。不能凭它生成时的高分就断言有抗菌效果。\n",
         f"现有直接 MIC 模型在共同的新化合物、新骨架测试记录上 AUC 分别为 {direct.loc['compound', 'roc_auc']:.3f}、{direct.loc['scaffold', 'roc_auc']:.3f}，比三套作者评分器的点估计更好；但跨研究降至 {direct.loc['study', 'roc_auc']:.3f}。这说明数据条件变化仍是短板，不是现在把生成数量放大就能解决的问题。上述结论只针对这次回顾性 MIC 检验，不否定原模型在作者任务上的效果。\n",
         "## 第 1 步：环境与实际生成\n",
         "独立环境：`external_models/SyntheMol-MCTS/.venv`，不继承系统或 V1 的 site-packages。Python 3.11.15、PyTorch 2.0.1+cpu、SyntheMol 1.0.3、Chemprop 1.6.1、RDKit 2022.9.5、scikit-learn 1.2.2。`pip check` 通过；完整依赖版本保存于 `generation/requirements.freeze.txt`。\n",
         f"使用作者的十成员 Chemprop 活性集成及原论文构件/反应对应关系。两次运行各耗时 {generation['seconds'][0]:.1f} 和 {generation['seconds'][1]:.1f} 秒。保留两次日志、候选、运行参数。未修改作者源码。\n",
         "## 第 2 步：如何防止假验证\n",
         "- 作者用于建模的 antibiotics.csv 有 13,524 行。为了保守排除来源泄漏，同时纳入原始 library_1/2/3 的结构，不能把被作者某一步过滤的同源记录称作全新独立数据。十折模型组成的完整集成不能直接拿作者训练池当外部测试。\n",
         "- 按去盐母体、去电荷后的非立体结构键，以及 InChI 连接层查重；再沿项目化合物组传播排除标记。立体异构体保守归为同组。预测输入保留原被测结构，不把归组结构冒充被测化学形式。\n",
         "- 原始筛选表使用 Mean/Mean_Growth 作为实验结果；Activity 及 Activity_model_* 是先前模型的预测，不能当真值。SD1 与经过旧模型挑选的 SD3 分开记录。标签为原论文的 50 µM 下生长抑制 >80%，即相对生长 <0.2。[原论文](https://www.nature.com/articles/s41589-023-01349-8)\n",
         "- MIC 采用预先固定的研究性界限 ≤8 µg/mL，并报告 4、16 的敏感性分析。这不是临床药敏折点。删失区间跨越界限的测量不强行贴标签，未知不当阴性。作者分类分数不转换成预测 MIC。\n",
         "- 指标按化合物等权，同一化合物的多次测量不会因数量多而支配汇总；不同菌株和实验的 MIC 不取最低值或随意平均。另报告研究内表现。区间由 200 次化合物/研究分组重采样估计，是探索性区间。\n",
         "- 三套作者评分器均使用全部十个已公开模型。5近邻基线只读取作者训练标签。直接 MIC 对照使用现存三个种子（17、42、314159）的测试集预测；9 个权重对应的冻结划分及测试记录已核对，见 baseline_split_check.json。\n",
         "## 未见化合物的 MIC 排序结果\n",
         "分数越高表示预测活性越强。ROC-AUC 越接近 1 越好，0.5 接近随机排序。平均精确率（AP）须与同表阳性比例比较，不能脱离数据分布解读。\n",
         f"在 ≤8 µg/mL 的主要界限下，有 {int(default_main.rows):,} 条记录、{int(default_main.parents):,} 个化合物可明确贴标签；另外 {coverage['eligible_rows'] - int(default_main.rows)} 条区间测量不能确定属于哪一边，仍保留在逐行结果中，但不计入二分类指标。所有去重排除与不可定标签记录都保留原因，没有从源数据删除。\n",
         "| 模型 | ROC-AUC | 按研究重采样的 95% 区间 | AP | 阳性比例 | 可定标签的测量/化合物 |",
         "|---|---:|---|---:|---:|---:|"]
for _, r in main.iterrows():
    parts.append(f"| {names[r.score]} | {r.roc_auc:.3f} | {r.study_bootstrap_auc_low:.3f}–{r.study_bootstrap_auc_high:.3f} | {r.average_precision:.3f} | {r.positive_prevalence:.3f} | {int(r.rows)}/{int(r.parents)} |")
parts += ["\n## 连骨架也没在作者训练来源出现过的子集\n",
          "| 模型 | ROC-AUC | AP | 阳性比例 | 测量/化合物 |", "|---|---:|---:|---:|---:|"]
for _, r in novel.iterrows():
    parts.append(f"| {names[r.score]} | {r.roc_auc:.3f} | {r.average_precision:.3f} | {r.positive_prevalence:.3f} | {int(r.rows)}/{int(r.parents)} |")
parts += ["\n## 与作者训练分子差异更大的子集\n",
          "使用预先固定的 Morgan 指纹最大 Tanimoto 相似度 ≤0.4。这里只是本次结构表示下的差异标准，不是绝对的新颖性证明。\n",
          "| 模型 | ROC-AUC | 按研究重采样的 95% 区间 | AP | 阳性比例 | 测量/化合物 |",
          "|---|---:|---|---:|---:|---:|"]
for _, r in far.iterrows():
    parts.append(f"| {names[r.score]} | {r.roc_auc:.3f} | {r.study_bootstrap_auc_low:.3f}–{r.study_bootstrap_auc_high:.3f} | {r.average_precision:.3f} | {r.positive_prevalence:.3f} | {int(r.rows)}/{int(r.parents)} |")
parts += ["\n## 同一研究内部的排序\n",
          "只统计至少有 10 个化合物、且两类标签均存在的研究，各研究等权汇总 AUC 中位数。研究往往较小，不能把中位数当作另一种总 AUC；它用于提醒混合不同研究后看起来不错的分数不一定能在单项实验里挑准。\n",
          "| 模型 | 可评估研究数 | 研究内 AUC 中位数 |", "|---|---:|---:|"]
for name, r in within.iterrows():
    parts.append(f"| {names[name]} | {int(r.studies)} | {r.median_auc:.3f} |")
parts += ["\n## 与项目现有模型公平比较\n",
          "下表各划分内使用完全相同的记录，且都排除了作者已见结构。项目的 compound、scaffold、study 是三种不同问题的冻结测试集，不能混称一种验证。study 留出本身不保证项目模型没见过相同化合物。\n",
          "| 项目测试划分 | 模型 | ROC-AUC | AP | 测量/化合物 |", "|---|---|---:|---:|---:|"]
for _, r in comparison.iterrows():
    parts.append(f"| {r.split} | {names[r.score]} | {r.roc_auc:.3f} | {r.average_precision:.3f} | {int(r.rows)}/{int(r.parents)} |")
parts += ["\n以上是描述性比较，没有据此重新训练、调参或宣布某个模型显著优于其他模型。原有项目测试集此前已被查看，因此这里是回顾性诊断，不是新设盲测。\n",
          "## 结果应如何使用\n",
          "生成器可以作为候选提出工具，但还不能作为可信的自动筛选闭环。随机森林在混合研究的总体数据上比两种 Chemprop 的 AUC 更高，但研究内 AUC 中位数仅约 0.56，不能据此直接换成唯一的生成奖励。既有直接 MIC 模型也有跨研究退化，暂时只适合作为参考评分之一。\n",
          "本轮没有剩余的同条件独立筛选标签可用于验证。下一步若要确证新分子抑菌筛选能力，需要补充与作者训练来源不重叠的固定条件实验数据，或开展预先规定、盲法留出的实验验证；不要把本轮跨 MIC 终点的结果冒充该结论。V1 暂时不作生成奖励。\n",
          "## 复现\n",
          "从整合仓库根执行，显式指定已验证的 --generator-root。生成与评估均写入新目录；使用 data/antibacterial/abaumannii 下的实测生长表并保留原始 Excel、工作表和行号。\n",
          "```bash\npython integrations/synthemol/scripts/run_generation_check.py --project . --output /tmp/synthemol_replay/generation\npython integrations/synthemol/scripts/test_evaluation.py\npython integrations/synthemol/scripts/evaluate_synthemol.py prepare --output /tmp/synthemol_replay/evaluation\nOMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 python integrations/synthemol/scripts/evaluate_synthemol.py predict --output /tmp/synthemol_replay/evaluation\npython integrations/synthemol/scripts/evaluate_synthemol.py report --output /tmp/synthemol_replay/evaluation\n```\n",
          "逐行查重清单、冻结协议、逐模型/逐成员预测、汇总指标、共同测试子集和研究内指标都保存在 evaluation/。所有原始训练数据、V1 权重与训练环境均未修改。"]
args.output.write_text("\n".join(parts) + "\n")
dump_status = dict(generation_runtime_verified=True, fixed_seed_repeat_identical=True,
    author_unseen_mic_evaluation_completed=True, same_endpoint_independent_screen_available=screen_eligible > 0,
    integrated_with_v1=False, v1_modified=False, author_source_code_modified=False)
(args.output.parent / "status.json").write_text(json.dumps(dump_status, indent=2))
print(json.dumps(dump_status, indent=2))
