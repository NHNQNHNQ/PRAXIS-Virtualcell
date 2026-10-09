# 数据迁移说明：data1 → data2

**日期：** 2026-06-10  
**执行人：** mzy  
**原因：** `.53` 服务器 `data1`（`/dev/nvme0n1`，7.0T）长期满载，影响 PRAXIS-2 部署和数据库写入

---

## 背景

迁移前 `data1` 磁盘状态：

| 盘 | 总量 | 已用 | 可用 | 占用 |
|---|---|---|---|---|
| data1 `/dev/nvme0n1` | 7.0T | 6.6T | 2.4M | **100%** |
| data2 `/dev/nvme1n1` | 7.0T | 3.5T | 3.2T | 53% |

`data1` 主要占用分布：

| 目录 | 大小 | 说明 |
|---|---|---|
| `data1/mzy/conformation` | 3.8T | 构象生成研究数据（conformation_data 3.7T） |
| `data1/mzy/PRAXIS-work-omic` | 425G | 多组学分析工作目录 |
| `data1/ycy/` | 139G | 他人数据，未动 |
| 其余 | <1G | praxis2 运行文件等 |

---

## 迁移操作

### 迁移目标

将 `PRAXIS-work-omic`（425G）从 `data1` 迁移至 `data2`，并在原位置建软链接保持路径透明。

`conformation`（3.8T）因超过 data2 剩余空间（3.2T），本次**未迁移**。

### 执行命令

```bash
# 1. rsync 复制（后台运行）
rsync -a /home/zkyd/data1/mzy/PRAXIS-work-omic/ \
         /home/zkyd/data2/mzy/PRAXIS-work-omic/

# 2. 验证目标完整性（to-chk=0/24138 表示全部传完）
tail -2 /tmp/rsync_omic.log

# 3. 删除源目录
rm -rf /home/zkyd/data1/mzy/PRAXIS-work-omic

# 4. 建软链接
ln -s /home/zkyd/data2/mzy/PRAXIS-work-omic \
      /home/zkyd/data1/mzy/PRAXIS-work-omic
```

### 迁移后磁盘状态

| 盘 | 总量 | 已用 | 可用 | 占用 |
|---|---|---|---|---|
| data1 `/dev/nvme0n1` | 7.0T | 6.2T | **425G** | 94% |
| data2 `/dev/nvme1n1` | 7.0T | ~4.0T | ~2.8T | ~57% |

---

## 路径说明

迁移后 `data1/mzy/PRAXIS-work-omic` 是软链接，指向 `data2/mzy/PRAXIS-work-omic`：

```
/home/zkyd/data1/mzy/PRAXIS-work-omic -> /home/zkyd/data2/mzy/PRAXIS-work-omic
```

**对所有已有脚本、路径引用完全透明，无需修改任何代码或配置。**

---

## 后续建议

- `conformation/conformation_data`（3.7T）是当前 data1 最大占用，暂无空间迁移
- 若后续扩容 data2 或挂载新盘，可继续迁移 conformation
- data1 当前 94% 占用，有 ~425G 余量，够近期使用
