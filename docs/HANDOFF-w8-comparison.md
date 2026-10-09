# 续接提示词 —— PRAXIS-VirtualCell 系统全面对比(S2 起)+ 论文 v0.2 收口

> 新对话直接粘贴下面整段即可继续。用简体中文沟通,论文正文英文。

---

继续 PRAXIS-virtualcell。项目 `/Volumes/T7/PRAXIS-virtualcell`(remote `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git`)。PRAXIS-2 派生的大脑引导可通讯虚拟细胞多智能体系统,方向 iii-lite(LLM 辅助但不依赖)。

## 已完成(本阶段)
- **代码 v0.1.0**(Week 1–7,Mac **75 passed + 23 skipped**,已 tag/push)。核心数字:Coordinator Norman **ΔPearson 0.7039**(n=18874)/ 6 base 0.6716→0.6183 / scGPT frozen 0.4407 / GEARS 原生 pearson_de 0.8392(**不可比**)/ ablation A↔D 五指标 0→1 / cross-species 路由 / 等价性 atol 1e-6。详见 `docs/RELEASE-v0.1.0.md`、`docs/findings/`。
- **论文 v0.2**(`docs/paper/v0.2/PRAXIS-VirtualCell-v0.2-manuscript.md`):ARS academic-paper full 从头重写完整初稿,英文正文 + 中英双语摘要,四问四节(理解输入/真多智能体/保持性能/提高可靠性),Limitations 诚实边界齐全。**22 篇引用全部逐条按 DOI 直查 CrossRef 规范记录(或 arXiv/JMLR 官方页)核验通过,无伪造**(语料 `docs/paper/v0.2/phase1_literature.md`)。5 图在 `docs/paper/figures/`(Fig1–5,4 格式)。v0.1 旧稿 `docs/paper/PRAXIS-VirtualCell-v0.1-manuscript.md` 保留。
- **系统对比计划** `docs/paper/v0.2/04_systems_comparison_plan.md`(三表:A 准确性 same-protocol / B 治理能力矩阵 / C abstain_gain risk-coverage)。
- **W8 S1 治理能力矩阵(表 B)完成** `docs/findings/finding_w8_systems_comparison.md`:据实核查 GEARS/CPA/scGPT/scGen/STATE 公开论文+repo,7 项治理能力中 6 项(OOD拒绝/applicability/abstain/provenance/message-bus/retrieve-gate)**全 ✗**,仅"离线可复现"为"部分";PRAXIS 全 ✓,每格附代码路径/论文出处依据。关键证据:CPA 论文承认"will fail if test data very different"、STATE GitHub 搜 abstain/uncertainty/seed 返回 0 文件、GEARS uncertainty 过滤在用户侧、scGPT OOV 基因静默映射 padding。

## 下一步(按计划 04 优先级)
- **S2** mean-perturbation naive baseline(满足项目 ≥3 baseline 不变量)+ 统一准确性表骨架(表 A)— 远端
- **S4** `data/manifests/norman_2019.yaml` + held-out OOD-pert split → abstain_gain / risk-coverage 数值(表 C,补 02_review R9)— 远端
- **S3** GEARS 适配 donor norman split + ΔPearson(解"不可比")/ scGen 接入 — 远端
- **S5** STATE 接入同协议(工程量最大,可最后做或单独立项)— 远端
- **S6** 汇总三表 → manuscript Results §3.3–3.4 + Related Work + 新增 Fig 6(治理矩阵)
- 或转向**论文收口**:v0.2 转 LaTeX/DOCX(pandoc)、英文润色、AI disclosure、再过一轮 ars-reviewer。

## 远端 + 约定
- 远端 `zkyd@10.102.106.53`(8×A100;conda init `source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh`)。env:`virtualcell`(torch 2.6+donor+GEARS/PyG)、`vc-scgpt`(torch 2.3+scgpt)、`vcell`(donor 原 env)。donor 只读 `/home/zkyd/data1/mzy/'Virtual cell'`(**含空格,SSH 务必引号**);ckpt `runs/full_bench_20260521_060815/checkpoints/norman_2019`。**Mac commit+push → 远端 git pull**。
- **铁律**:同 split 同 metric(donor norman split, per-cell ΔPearson, 同 EvalAgent)才进准确性表;跨 metric 数字(GEARS 原生 0.8392)**永不混入**。PRAXIS 准确性**不声称赢 SOTA**(卖点是治理层)。治理矩阵每格必须有代码/论文依据。abstain_gain 需**真 held-out OOD-pert split manifest** 才报数值。数字一律**实跑不臆造**。诚实标注**声明式 vs 运行时**。
- 每 task 单独 commit(末尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`);commit 前 `find docs praxis_virtualcell -name '._*' -delete`;pytest 退出码别用 `|tail` 吞。

## 先复核
`cd /Volumes/T7/PRAXIS-virtualcell && git log --oneline -4 && sed -n '1,20p' docs/findings/finding_w8_systems_comparison.md`(看进度勾选)。然后按 S2 推进,或转论文收口。
