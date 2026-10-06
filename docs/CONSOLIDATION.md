# 2026-10-06 项目整合

目标是集中可运行的抗菌分析工具和真实数据，保留可恢复的历史工程。本次整理不训练模型，也不把文档合同或占位模块认作已验证的生物学能力。

归档根目录为同级 `PRAXIS-virtualcell-old/`，按原项目名保留结构：

```text
PRAXIS-virtualcell-old/
  PRAXIS-virtualcell/             主项目移出的历史内容和旧工作树
  PRAXIS-MDR-GNB/                 原项目完整历史副本
  Ab-虚拟细胞世界模型/            原世界模型/交付包及历史研究资料
  records/2026-10-06/             原 Git 状态、未提交补丁和移动清单
```

主项目迁入 MDR 的真实运行包、模型/数据和验证；迁入 AB 的直接 MIC 工具、部分交付包工件、生长筛选与 SyntheMol 结果。来源项目随后整体归档，完整副本用于恢复来源和未迁入历史，不作为当前可执行依赖。

主项目旧未提交内容已经原样保存在归档，并在 records 中保存了迁移前的 tracked patch；没有 reset 或覆盖它们。旧 Git 工作树使用 `git worktree move` 更新登记。

两个来源项目已整体移入归档，MDR 的本地 Git 历史与未提交内容仍随原目录保留。`records/2026-10-06/final-source-moves.json` 记录最终移动，`root-moves.json` 记录主项目历史文件移动。过时测试的迁移副本另存于 `records/2026-10-06/migrated-legacy-tests/`。

AB 新公开组学仍以 09-23 的服务器下载记录为准，未在此次整合中下载或纳入重训。原组学/状态/时序世界模型资料保留在归档，以便今后机制研究需要时恢复。
