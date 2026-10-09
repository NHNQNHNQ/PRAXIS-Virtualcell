# Finding W4b — 多 predictor 锚定(M1 Task 1)

> 6 个 donor predictor 在 Norman test 复现各 anchor。⚠ **修正**:Week 4b 规划期早期 recon 的 base 分数(latent 0.6922 / cpa 0.5673 等)有误(heredoc 被 SSH 引号串行 + 行错位);以下为 `build_predictor_from_ckpt` 直读 ckpt json `meta.delta_pearson` 的**权威值**(linear 0.663859 与 Week 4a 一致,证明读取正确)。

## 锚定结果(远端 virtualcell GPU,max_cells=200 / seed=1)
| predictor | S0(ckpt meta) | S_eval(复算) | diff |
|---|---|---|---|
| cpa_style | 0.671581 | 0.670821 | 7.6e-4 |
| decoder_only | 0.670949 | 0.672399 | 1.5e-3 |
| gnn_pert | 0.667487 | 0.668478 | 9.9e-4 |
| linear_additive | 0.663859 | 0.663859 | 0(逐位) |
| latent_additive | 0.636536 | 0.635952 | 5.8e-4 |
| pretrained_backbone | 0.618345 | 0.618499 | 1.5e-4 |

- 全部复现成功(diff < 1.5e-3;linear deterministic 逐位,其余 trained 模型容差内)。
- `test_ml_multi_bridge.py` **6 passed**(参数化 build_predictor_from_ckpt)。
- **pretrained_backbone 用 mock_backbone**(identity-projection;ckpt kwargs 只 `{pert_dim, n_genes}`,`backbone_name` 默认 `"mock_backbone"`)→ **非真 scGPT**。真 scGPT(backbone_name="scgpt" + scGPT ckpt)归 Task 4 外部 audit。

## 对 spec/plan 的修正
- 权威强→弱:**cpa 0.672 > decoder 0.671 > gnn 0.667 > linear 0.664 > latent 0.637 > pretrained(mock) 0.618**。
- latent **不是**最强(早期 recon 误为 0.6922);cpa **不是**最弱(早期误为 0.5673)。
- Coordinator 目标分数:Task 3 **实测** donor Coordinator 真值,不预设 0.70。
