# G2R 数据功效诊断(2026-07-07)

> 脚本:`workflows/run_g2r_power_diagnosis.py`。诚实要点:**per-ST 置换检验的功效由「不同耐药 ST 数」
> 决定,不是原始菌株数**。这决定了"补耐药菌株"该补什么。

## 现有数据(单个 NCBI PDG 快照)

| 组合 | n | R | **R-ST(功效上限)** | R无ST(可捞回) | top5-ST 占 R |
|---|---|---|---|---|---|
| KP × meropenem | 768 | 339 | **68** | 15 | 50% |
| KP × ceftriaxone | 1024 | 578 | 145 | 44 | 32% |
| EC × ceftriaxone | 6852 | 1386 | 246 | 15 | 40% |
| EC × meropenem | 6232 | **69** | **32** | 0 | 46% |
| KP × colistin | 238 | 77 | 26 | 6 | 56% |
| KP × amikacin | 730 | 165 | 36 | 6 | 49% |

## 三个诚实结论

1. **功效瓶颈 = 不同耐药克隆数,不是菌株数。** KP meropenem 有 339 个耐药株但只在 68 个 ST 上,top-5 克隆占一半 →
   **再下 ST258/ST11 那几个主流克隆的菌株,对 per-ST 置换检验毫无帮助**。要提功效只能补**新耐药谱系(新 R-ST)**。
2. **碳青霉烯耐药高度克隆化,新谱系可能不多。** EC meropenem 全库才 69 个耐药株、32 个 R-ST(碳青霉烯耐药 EC 真稀有)。
   下载新快照能加多少新 R-ST 未知 → runbook 必须**测 R-ST 增量并设停止判据**(loop-until-dry),否则白烧算力。
3. **KP meropenem"不显著"部分是我方法学选择的代价,不是数据的错。** 原始门用**全量 ST 分组 CV(68 R-ST)** 时
   KP×mero 就是 p=0.0001 显著;是本轮**严格 25% locked holdout** 把它降到 11 R-ST 才不显著。
   → **先试更省的本地杠杆 A,再决定要不要上 53。**

## 两条杠杆(runbook 详见 `docs/G2R-data-scaleup-runbook-53.md`)

- **杠杆 A(本地,先试,零下载)**:对稀有 R 组合用**嵌套 ST 分组 CV**(operating point 逐折内选,全 R-ST 参与显著性检验),
  把 25% holdout 损失的功效捞回来。KP meropenem + 机制特征很可能这一步就够 strong-pass。
- **杠杆 B(53)**:**定向**下载新耐药株——拉最新 PDG 快照、按 目标药×phenotype=R 过滤、去重现有 genome_id、
  只对新耐药株下 FASTA + 跑 MLST → 新 R-ST。**目标是 R-ST 多样性**,测增量、见干就停。
