# 09 伞形采样 PMF

## 核心规则

做伞形采样时，先做 SMD 拉伸获取构象快照，再按间距切窗口跑约束 MD，最后用 `gmx wham` 重建 PMF；三步缺一不可，顺序不能颠倒。

## 窗口设计

- 窗口间距建议 0.1–0.2 nm；间距过大导致 PMF 不连续，过小浪费计算。
- 推荐 20–50 个窗口；n_windows < 10 通常统计不足。
- 弹簧常数 k 建议 1000–3000 kJ/mol/nm²；太软窗口间采样重叠不足，太硬限制太强。

## SMD → 窗口提取

```bash
# 1. SMD 拉伸
gmx mdrun -deffnm pull -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu

# 2. 提取构象快照(每 window_spacing_nm 取一帧)
gmx trjconv -s pull.tpr -f pull.xtc -o conf_window.gro \
    -b 0 -e TOTAL_TIME -skip SKIP_FRAMES -sep
```

## 约束窗口 MD

- 每个窗口的 `.mdp` 需加：
  ```ini
  pull = yes
  pull-ncoords = 1
  pull-coord1-type = umbrella
  pull-coord1-geometry = distance
  pull-coord1-k = K_VALUE
  pull-coord1-init = WINDOW_CENTER
  ```

## WHAM 分析

```bash
ls tpr_*.tpr > tpr-files.dat
ls pullf_*.xvg > pullf-files.dat
gmx wham -it tpr-files.dat -if pullf-files.dat -o pmf.xvg -hist hist.xvg -unit kJ
```

## 收敛检验

- 检查 `hist.xvg` 各窗口重叠；相邻窗口重叠 < 20% 视为覆盖不足。
- PMF 误差棒 > 2 kJ/mol 需延长窗口模拟时间。

## PBC 注意事项

- 膜体系沿 Z 轴拉伸时需确认 pull-coord 不跨 PBC 盒子边界。
- 使用 `pull-coord1-geometry = distance_from_nearest_image` 可缓解 PBC 问题。

## 适用

- 蛋白-配体解结合自由能
- 膜通道穿越 PMF
- 界面吸附能

## 为什么

- wham 依赖完整的力文件(pullf.xvg)和 tpr 文件，路径错误或文件缺失会导致静默错误。
- 窗口间重叠不足是 PMF 曲线虚假平台的主要来源。
