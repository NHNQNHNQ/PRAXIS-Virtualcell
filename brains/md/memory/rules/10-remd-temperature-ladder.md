# 10 REMD 温度梯度设计

## 核心规则

REMD 的接受率要保持在 20–30%；温度梯度设计决定接受率，交换太频或太稀都浪费计算资源。

## 温度梯度公式

近似公式（假设恒压热容 Cp 为常数）：

```
T_{i+1} = T_i × exp(sqrt(2 / (N_dof × (ΔT_target/T_i))))
```

实用近似：相邻温度比约为 T_{i+1}/T_i ≈ 1.02–1.04（小体系取大值，大体系取小值）。

例：300 K → 450 K，可取 [300, 310, 320, 330, 345, 360, 375, 392, 409, 428, 447]（~11 replica）。

## 检查接受率

```bash
grep "Repl ex" md0.log | awk '{sum+=$NF; n++} END {print sum/n}'
```
目标接受率：0.20–0.30。

## 启动命令

```bash
# 每个温度一个子目录
for T in 300 310 320 ...; do
  mkdir -p T_${T}
  # 修改 mdp 中 ref_t = T
  gmx grompp -f md_T${T}.mdp -c confout.gro -p topol.top -o T_${T}/tpr.tpr
done

# gmx_mpi 运行(需 praxis-md-plumed env 或带 MPI 的 gmx)
mpirun -np N_REPLICAS gmx_mpi mdrun \
  -multidir T_300 T_310 T_320 ... \
  -replex EXCHANGE_INTERVAL \
  -ntmpi 1 -ntomp 18

# 无 gmx_mpi 时可用 thread-MPI(replica 数受限于 CPU 核数)：
gmx mdrun -multidir T_300 T_310 T_320 ... -replex 1000 \
  -ntmpi N_REPLICAS -ntomp 2
```

## gmx vs gmx_mpi 选择

| 情况 | 命令 |
|---|---|
| replica ≤ 8，单节点 | `gmx mdrun -multidir ... -ntmpi N` |
| replica > 8，多节点 | `mpirun gmx_mpi mdrun -multidir ...` |
| .53 A100 单节点 | `gmx mdrun -multidir` 足够，无需 gmx_mpi |

`.53` 当前 `praxis-md-cuda` 只有 `gmx`（无 `gmx_mpi`），用 `-ntmpi N_REPLICAS` 即可。

## exchange_interval 建议

- 1000–2000 steps（2–4 ps）；太频繁加大 I/O 开销，太稀疏接受率统计不稳定。

## 分析

```bash
# 提取最低温度 replica 的轨迹
gmx trjcat -f T_300/traj.xtc -o combined.xtc
# 观察各温度的遍历
grep "Repl ex" T_300/md.log | head -20
```

## 适用

- 蛋白折叠/构象转变采样
- 自由能计算的初构象生成
- 克服高能垒体系

## 为什么

- 接受率 < 10% 说明温度间距太大，replica 间交换几乎不发生，相当于各自独立跑。
- 接受率 > 50% 说明温度间距太小，replica 间差异不够，混合效率低。
