---
name: seq_toolkit
description: BioPython 通用序列工具 — DNA/蛋白裸序列的翻译、反向互补、GC 含量、ORF 查找、分子量/等电点、氨基酸组成、pairwise 全局比对。通用计算工具(非领域分析链)，跨 protein/enzyme/crispr/microbiome/immuno 高频复用。
host_env: praxis-protein
schema_version: 1
domains: [protein]
inputs_schema:
  sequence: {type: string, required: true, desc: "DNA 或蛋白裸序列(单条)"}
  seq_type: {type: string, required: false, desc: "dna|protein|auto(默认 auto，按碱基比例自动检测)"}
  operations: {type: array, required: false, desc: "操作列表;不传则按 seq_type 给默认分析"}
  sequence2: {type: string, required: false, desc: "第二序列(pairwise_align 用)"}
status: real
references: []
---

# seq_toolkit — BioPython 通用序列工具

## When to use

需要对 DNA/蛋白序列做**通用、原子级**操作时（不是某学科的完整分析链）：

- **DNA**：翻译成蛋白、反向互补、GC 含量、ORF 查找
- **蛋白**：分子量、等电点(pI)、氨基酸组成
- **两序列**：pairwise 全局比对 + identity%

领域分析链（MSA 共进化 / igblast / 结构预测 / 饱和突变）仍走各学科专用 skill；
本 skill 只补"裸序列计算"的通用工具缺口，跨多学科复用。

## Operations

| operation | seq_type | 输出 |
| --- | --- | --- |
| `translate` | dna | 蛋白序列(标准遗传密码,含 `*` 终止) |
| `reverse_complement` | dna | 反向互补 DNA |
| `gc_content` | dna | GC 百分比 |
| `orf` | dna | ORF 列表 `[{start,end,length,protein}]`(3 个正向 frame) |
| `composition` | both | 残基计数 dict |
| `molecular_weight` | protein | 分子量 (Da) |
| `isoelectric_point` | protein | 等电点 pI |
| `pairwise_align` | both(+sequence2) | `{identity, score, alignment_length, matches}` |

不传 `operations` 时：DNA 默认 `[translate, reverse_complement, gc_content]`，
蛋白默认 `[molecular_weight, isoelectric_point, composition]`。

## I/O

- 输入：`--inputs '{"sequence":"ATGGCC...","operations":["translate"]}'`(JSON 文件路径或 inline 字符串)
- 输出：stdout JSON `{"ok":true,"seq_type_detected":"dna","length":N,"results":{...}}`
- 失败(空序列/非法残基)：`{"ok":false,"error":"..."}`

## 示例

```bash
python run.py --inputs '{"sequence":"ATGGCCTGTTAA","operations":["translate","gc_content"]}'
# → {"ok":true,"seq_type_detected":"dna","length":12,"results":{"translate":"MAC*","gc_content":50.0}}

python run.py --inputs '{"sequence":"MKLVWWQEFH","sequence2":"MKLVWWQEFA","operations":["pairwise_align"]}'
# → results.pairwise_align.identity == 90.0
```

## host_env

`praxis-protein`(biopython 1.84 已装；与现有 6 个 protein skill 同 env)。纯计算，无外部网络/GPU 依赖。

## 测试

同目录 `test_run.py`(不依赖 pytest，`python test_run.py` 直接跑)覆盖 11 个用例，
praxis-protein env 真跑 biopython 全 PASS。Oracle 出处标注于测试注释(遗传密码表/Watson-Crick/数学)。
