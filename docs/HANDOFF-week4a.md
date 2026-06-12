# 续接提示词 —— PRAXIS-virtualcell Week 4a 执行(inline)

> 新对话直接粘贴下面整段即可继续。

---

继续 PRAXIS-virtualcell 的 Week 4a,**inline 执行**(用 superpowers:executing-plans)。

**项目**:PRAXIS-virtualcell,位于 `/Volumes/T7/PRAXIS-virtualcell`(新仓,push 到 `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git`)。PRAXIS-2 派生的多物种虚拟细胞多智能体框架,方向 **iii-lite**(LLM-assisted but not -dependent)。

**已完成(均已 push)**:
- Week 1 bootstrap:复制 PRAXIS-2,去 13 学科脑→单 `virtualcell` 脑。
- Week 2:communicative agent runtime(`praxis_virtualcell/` 包:core/agents/predictors/agents_llm/workflows,offline,35 tests 绿)。
- Week 3:LLM-assisted(纯 DeepSeek via httpx,4 个 LLM agent + runtime `llm_assisted` seam,48 tests 含真 DeepSeek;DeepSeek key 在 gitignored `.env`)。

**现在要做**:Week 4a(远端迁 `linear_additive` predictor)。spec + plan 已写好并 push:
- plan(6 task):`docs/superpowers/plans/2026-06-12-week4a-remote-linear-migration.md`
- spec:`docs/superpowers/specs/2026-06-12-week4a-remote-linear-migration-design.md`
→ **直接 invoke superpowers:executing-plans,inline 执行这个 plan,从 Task 1 开始。**

**关键事实**:
- 远端 GPU:`zkyd@10.102.106.53`(6× A100 40GB,SSH 已验证可连,免密)。conda init:`source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh`。
- conda 环境 **`virtualcell` 不存在,Task 1 要新建**:python 3.11 + `torch(匹配 A100 CUDA)` + lightning/numpy/scipy/pint/pyyaml/jsonschema。**这是最高风险步**(P2-B env 坑),gate = `torch.cuda.is_available()` True;装不通就停下报告,别硬凑。
- donor(**只读复用,勿改**):`/home/zkyd/data1/mzy/Virtual cell`(**路径含空格,SSH 命令务必加引号**)。已含 predictors/bench/coordinator/data/runs。
- 远端 praxis 仓:Task 1 `git clone` 到 `/home/zkyd/data1/mzy/PRAXIS-virtualcell`;之后每次改码:Mac `commit+push` → 远端 `git pull`。
- linear ckpt:`/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260521_060815/checkpoints/norman_2019/linear_additive.{pt,json}`。json `kwargs={pert_dim:5120,n_genes:2000}`,**anchor ΔPearson≈0.5886**(json meta)。Task 1 recon 确认实际路径/anchor。
- donor 真实 API(已读源码确认):`LinearAdditivePredictor(pert_dim,n_genes)`(predict 需 `ctx.control` + `pert.meta['pert_emb']`);`load_vcbench_split("norman_2019",split,rng_seed=,max_perts=,max_cells_per_pert=)`;`EvalAgent(batch_size,device).evaluate(model,ds)` → `.metrics.delta_pearson/.cosine`、`.n_samples`;ckpt `.pt` 是 state_dict。
- **torch 只在远端 `predictors/ml/`**;Mac `.venv` 无 torch → ml 测试标 `@pytest.mark.remote`,Mac 自动 skip(Task 6 conftest)。Mac 端 Week 2/3 的 48 测试必须零回归。

**约定**:
- 每 task TDD + 单独 commit;milestone push。pytest 退出码**别用 `| tail` 吞掉**(用 `rc=$?; if [ "$rc" -eq 0 ]; then ... commit`)。
- 每次 commit 前 `find praxis_virtualcell -name '._*' -delete`(macOS 在 T7 exFAT 卷生成 AppleDouble;已 gitignore 但清掉防 yaml/glob 误读)。
- commit message 末尾:`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- 偏好「靠重写」(迁移破坏旧测试→重写到新事实,不 skip/xfail);**prototype-first**:本期只 linear,latent/cpa/gnn/decoder + Coordinator + 复现 ~0.70 留 **Week 4b**。
- 用简体中文回复;简洁、不寒暄、不 trailing summary。

**先复核现状**(Mac):`cd /Volumes/T7/PRAXIS-virtualcell && git log --oneline -6 && .venv/bin/python -m pytest praxis_virtualcell/tests -q`(应 48 passed)。然后开始 Week 4a Task 1。
