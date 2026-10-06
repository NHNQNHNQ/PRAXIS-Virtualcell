# G2R 证据面 sweep(5 物种 EC/KP/PA/AB/salmonella,2026-07-07)

> OOF ST-CV 全功效 + 机制特征 + rule-first 融合 + 预注册运行点(min per-ST VME s.t. ME≤规则ME+0.05)。
> rule-first 保证 per-ST VME≤规则 → 最差 practical(不劣于规则);strong=统计显著优于冻结 AMRFinderPlus。
> 注:sweep 用 OOF(单集选运行点,轻微乐观);锚点已嵌套 CV 确认偏差<0.01。
> EC/KP 本地评估;**PA/AB/salmonella 在 53 评估**(zkyd@10.102.106.53,PRAXIS-article env sklearn 1.9.0,数据+ST 均在 53)。

## 汇总:strong=26 · practical=24 · no_baseline=67 · error=0

## strong 组合(显著优于冻结 AMRFinderPlus 的 VME)

| species | drug | n | R-ST | 融合 VME | 规则 VME | ΔVME | p | ME 融合/规则 |
|---|---|---|---|---|---|---|---|---|
| pseudomonas_aeruginosa | levofloxacin | 415 | 76 | 0.2621 | 0.8728 | -0.6107 | 0.0001 | 0.0745/0.0373 |
| pseudomonas_aeruginosa | ciprofloxacin | 645 | 79 | 0.3402 | 0.8672 | -0.527 | 0.0001 | 0.0734/0.0321 |
| acinetobacter_baumannii | amikacin | 944 | 36 | 0.353 | 0.8512 | -0.4982 | 0.0001 | 0.0508/0.015 |
| acinetobacter_baumannii | ceftriaxone | 807 | 40 | 0.5041 | 0.8067 | -0.3026 | 0.0001 | 0.0226/0.0 |
| acinetobacter_baumannii | ciprofloxacin | 987 | 44 | 0.722 | 0.9995 | -0.2775 | 0.0001 | 0.043/0.0 |
| acinetobacter_baumannii | levofloxacin | 800 | 38 | 0.7782 | 1.0 | -0.2218 | 0.0006 | 0.0373/0.0034 |
| klebsiella_pneumoniae | meropenem | 768 | 68 | 0.1063 | 0.2662 | -0.1598 | 0.0001 | 0.1858/0.1374 |
| escherichia_coli | tobramycin | 2972 | 47 | 0.2427 | 0.3912 | -0.1485 | 0.0005 | 0.0616/0.0144 |
| acinetobacter_baumannii | cefepime | 319 | 32 | 0.5857 | 0.728 | -0.1424 | 0.0159 | 0.036/0.0 |
| escherichia_coli | cefepime | 3525 | 158 | 0.0418 | 0.1671 | -0.1253 | 0.0001 | 0.2202/0.175 |
| klebsiella_pneumoniae | ceftriaxone | 1024 | 145 | 0.1445 | 0.2615 | -0.117 | 0.0001 | 0.0703/0.0216 |
| acinetobacter_baumannii | gentamicin | 982 | 53 | 0.1839 | 0.2887 | -0.1048 | 0.0043 | 0.3602/0.3218 |
| escherichia_coli | ampicillin | 7609 | 531 | 0.0258 | 0.1223 | -0.0965 | 0.0001 | 0.057/0.0182 |
| pseudomonas_aeruginosa | aztreonam | 180 | 56 | 0.8217 | 0.9169 | -0.0952 | 0.0063 | 0.038/0.0127 |
| pseudomonas_aeruginosa | meropenem | 351 | 83 | 0.6024 | 0.6931 | -0.0907 | 0.0012 | 0.2941/0.2521 |
| klebsiella_pneumoniae | amikacin | 730 | 36 | 0.0017 | 0.082 | -0.0803 | 0.0087 | 0.5536/0.5057 |
| salmonella_enterica | gentamicin | 9588 | 36 | 0.0439 | 0.123 | -0.0791 | 0.008 | 0.0611/0.0201 |
| acinetobacter_baumannii | tetracycline | 797 | 34 | 0.3765 | 0.4319 | -0.0554 | 0.0336 | 0.0627/0.0148 |
| klebsiella_pneumoniae | gentamicin | 719 | 89 | 0.09 | 0.1264 | -0.0364 | 0.029 | 0.1246/0.0895 |
| escherichia_coli | gentamicin | 7445 | 212 | 0.0346 | 0.068 | -0.0334 | 0.0001 | 0.0637/0.0179 |
| klebsiella_pneumoniae | tobramycin | 604 | 76 | 0.037 | 0.0683 | -0.0313 | 0.0036 | 0.204/0.16 |
| klebsiella_pneumoniae | cefepime | 627 | 86 | 0.0286 | 0.0591 | -0.0305 | 0.0146 | 0.4706/0.4244 |
| salmonella_enterica | ampicillin | 9611 | 43 | 0.0461 | 0.0587 | -0.0126 | 0.009 | 0.0442/0.0049 |
| escherichia_coli | trimethoprim-sulfamethoxazole | 7040 | 199 | 0.0162 | 0.0198 | -0.0036 | 0.0165 | 0.2855/0.2409 |
| escherichia_coli | ceftriaxone | 6852 | 246 | 0.0269 | 0.0297 | -0.0028 | 0.001 | 0.0463/0.0089 |
| escherichia_coli | tetracycline | 7247 | 541 | 0.0211 | 0.0225 | -0.0014 | 0.0164 | 0.0626/0.0183 |

## practical 组合(不劣于规则,未显著优于)

| species | drug | R-ST | ΔVME | p |
|---|---|---|---|---|
| acinetobacter_baumannii | ampicillin | 53 | -0.2966 | 0.0001 |
| acinetobacter_baumannii | aztreonam | 48 | -0.5289 | 0.0001 |
| acinetobacter_baumannii | meropenem | 35 | -0.0007 | 0.5035 |
| acinetobacter_baumannii | tobramycin | 37 | -0.0191 | 0.5054 |
| acinetobacter_baumannii | trimethoprim-sulfamethoxazole | 51 | 0.0 | 1.0 |
| escherichia_coli | amikacin | 30 | 0.0 | 1.0 |
| escherichia_coli | aztreonam | 55 | -0.0285 | 0.0601 |
| escherichia_coli | chloramphenicol | 174 | -0.0064 | 0.1258 |
| escherichia_coli | ciprofloxacin | 196 | -0.0097 | 0.0632 |
| escherichia_coli | levofloxacin | 85 | -0.0118 | 0.4986 |
| escherichia_coli | meropenem | 32 | -0.0182 | 0.2475 |
| klebsiella_pneumoniae | ampicillin | 159 | -0.0063 | 0.5052 |
| klebsiella_pneumoniae | aztreonam | 71 | -0.0198 | 0.0591 |
| klebsiella_pneumoniae | chloramphenicol | 15 | -0.0667 | 0.5079 |
| klebsiella_pneumoniae | ciprofloxacin | 93 | 0.0 | 1.0 |
| klebsiella_pneumoniae | levofloxacin | 61 | 0.0 | 1.0 |
| klebsiella_pneumoniae | tetracycline | 85 | -0.004 | 0.2585 |
| klebsiella_pneumoniae | trimethoprim-sulfamethoxazole | 113 | 0.0 | 1.0 |
| pseudomonas_aeruginosa | amikacin | 24 | -0.1088 | 0.0639 |
| pseudomonas_aeruginosa | cefepime | 71 | 0.0 | 1.0 |
| pseudomonas_aeruginosa | gentamicin | 37 | -0.0736 | 0.0615 |
| pseudomonas_aeruginosa | tobramycin | 34 | -0.002 | 0.4957 |
| salmonella_enterica | ceftriaxone | 26 | -0.0385 | 0.4958 |
| salmonella_enterica | tetracycline | 56 | 0.0 | 1.0 |

## no_baseline(67):冻结规则表未收录,无对照不可评

ES×amoxicillin-clavulanic acid, ES×ampicillin-sulbactam, ES×azithromycin, ES×cefazolin, ES×cefotaxime, ES×cefotaxime-clavulanic acid, ES×cefoxitin, ES×cefpodoxime, ES×ceftazidime, ES×ceftazidime-clavulanic acid, ES×ceftiofur, ES×cephalothin, ES×colistin, ES×ertapenem, ES×imipenem, ES×kanamycin, ES×moxifloxacin, ES×nalidixic acid, ES×nitrofurantoin, ES×piperacillin-tazobactam, ES×streptomycin, ES×sulfamethoxazole, ES×sulfisoxazole, ES×trimethoprim, KL×amoxicillin-clavulanic acid, KL×ampicillin-sulbactam, KL×cefazolin, KL×cefotaxime, KL×cefotetan, KL×cefoxitin, KL×cefpodoxime, KL×ceftazidime, KL×ceftazidime-avibactam, KL×ceftolozane-tazobactam, KL×cefuroxime, KL×cephalothin, KL×colistin, KL×doripenem, KL×ertapenem, KL×imipenem, KL×moxifloxacin, KL×nalidixic acid, KL×nitrofurantoin, KL×piperacillin-tazobactam, KL×polymyxin b, KL×tigecycline, PS×ceftazidime, PS×ceftazidime-avibactam, PS×imipenem, PS×piperacillin-tazobactam, AC×ampicillin-sulbactam, AC×cefazolin, AC×cefotaxime, AC×cefotetan, AC×cefoxitin, AC×ceftazidime, AC×doripenem, AC×imipenem, AC×nitrofurantoin, AC×piperacillin-tazobactam, SA×amoxicillin-clavulanic acid, SA×cefoxitin, SA×ceftiofur, SA×kanamycin, SA×streptomycin, SA×sulfamethoxazole, SA×sulfisoxazole
