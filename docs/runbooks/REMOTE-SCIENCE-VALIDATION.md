# `.53` 真实 ML 科学验证 Runbook

> 状态：`LOCAL_RUNBOOK_READY — REMOTE_NOT_RUN`
>
> 适用目标：在 Phase D 已批准的同一候选 SHA 上，定位 W4B donor checkpoint，并验证 `MLBackedPredictorAgent` 真实推理不会被 Gate A 误伤。

本手册只定义可复现的远端验证窗口，不授权 push、fetch、checkout、部署、服务重启或 `.53` 仓库/资产状态变更。首次 GitHub 写入或 `.53` 状态变更仍须按同步计划取得用户明确授权。Python bytecode 和 pytest cache 均显式关闭，避免测试污染 checkout。成功标准不是命令退出码为零，而是按收集数与 pytest 摘要归一化后明确得到 `2 passed / 0 skipped / 0 failed`。

## 1. 边界与停止条件

- 本地 APFS 仓库是开发真相源，GitHub 是发布真相源，`.53` 只验证 GitHub 已存在且已批准的精确 SHA；禁止 rsync 源码、直接远端开发或产生权威提交。
- 保留 `.53` 的旧 `b9abdbd`、`remote-gears-l4-95dc764` 分支/commit 和任何已登记日志。不得 reset、clean、删除、覆盖或把远端独有历史盲 merge 进候选。
- 不读取 `.env`、API key、token 或环境变量全集；本验证不运行 LLM，不需要网络模型调用。
- 不停止、重启或探测无关服务。测试本身不依赖已运行的 API 服务。
- 以下任一情况立即停止并记 `REMOTE_VALIDATION_PENDING`：候选 SHA 不一致、仓库 dirty 且不在批准台账、checkpoint 未找到、六个 checkpoint 文件（三份 JSON sidecar 与三份 PT 权重）不齐、class 不匹配、Norman 数据不匹配、donor 源码版本/状态或 checkpoint digest 集未获批准、无可用 torch/donor 环境、任何测试 skip/error/fail。CUDA 状态只盘点，不是当前 CPU-loaded 验收的通过前置。
- checkpoint 内容摘要用于记录“本次实际加载了什么”，不是 checked-in 完整性 pin；没有独立批准的期望摘要时，不得写成“未被篡改”。
- `donor_bridge.py` 会把 `/home/zkyd/data1/mzy/Virtual cell` 加入 `sys.path` 并执行其中 predictor/loader 源码，还会以 `torch.load(..., weights_only=False)` 反序列化 PT bundle。PT 因而是可执行信任边界：发现阶段只能计算元数据与摘要；在 donor commit/status/remote 和六文件 digest 集经用户或资产负责人明确批准前，禁止 import donor 模块或运行 pytest。

## 2. 进入窗口前的批准输入

执行者必须从 Phase D 同步台账取得并填入：

```bash
praxis_candidate_sha='<APPROVED_40_HEX_SHA>'
praxis_candidate_ref='<APPROVED_GITHUB_REF>'
praxis_repo='/home/zkyd/data1/mzy/PRAXIS-virtualcell'
donor_repo='/home/zkyd/data1/mzy/Virtual cell'
approved_donor_sha='<APPROVED_DONOR_40_HEX_SHA>'
approved_donor_origin_url='<APPROVED_DONOR_ORIGIN_URL>'
approved_linear_additive_json_sha='<APPROVED_SHA256>'
approved_linear_additive_pt_sha='<APPROVED_SHA256>'
approved_latent_additive_json_sha='<APPROVED_SHA256>'
approved_latent_additive_pt_sha='<APPROVED_SHA256>'
approved_gnn_pert_json_sha='<APPROVED_SHA256>'
approved_gnn_pert_pt_sha='<APPROVED_SHA256>'
```

在任何远端测试前核对：

1. 候选 SHA 已存在于 GitHub，且 GitHub ref 的 live SHA 与台账相同。
2. `.53` 已按另行批准的 D2 方案安全到达该 SHA；本手册不执行该同步。
3. 运行窗口、远端主机和 `virtualcell` conda 环境均已获批准。
4. 台账已说明如何保留已知未跟踪日志；若没有说明，非空 status 即停止。
5. donor 仓库的精确 SHA、remote、clean status 以及三份 JSON/三份 PT 的 size/SHA-256 已先完成只读发现，并作为一组交由用户或资产负责人批准；没有这组批准值时只能执行第 3–6 节的发现命令，不能进入第 7 节。

## 3. 只读核对候选与 Python 来源

在 `.53` 的同一个 Bash 会话中按顺序执行本手册命令并保存原始输出；不要把单个后续代码块脱离前置变量/批准门单独运行：

```bash
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0
cd "$praxis_repo"
pwd
git status --short --branch
git status --ignored --short
git remote -v
git rev-parse HEAD
git show -s --format='%H %P %s' HEAD
test "$(git rev-parse HEAD)" = "$praxis_candidate_sha"

source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh
conda activate virtualcell
export PYTHONDONTWRITEBYTECODE=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
python --version
python -c 'import pathlib,praxis_virtualcell; print(pathlib.Path(praxis_virtualcell.__file__).resolve())'
python -c 'import torch; print("torch",torch.__version__); print("cuda",torch.version.cuda); print("available",torch.cuda.is_available()); print("devices",torch.cuda.device_count())'
python -m pip check
```

`praxis_virtualcell.__file__` 必须解析到 `$praxis_repo` 当前 checkout，而不是旧 site-packages。HEAD 不等于批准 SHA、remote URL 异常、未登记 dirty 状态或 torch 无法导入时停止；不得在本手册内修环境。CUDA available/device count 只记录现场能力：当前 builder 使用 `torch.load(..., map_location="cpu")` 且没有 `.to(cuda)`，所以本验收不证明 GPU 推理，CUDA 不可用也不能被单独写成测试失败或通过。

## 4. 只读核对 donor 执行代码

W4B 不只执行 PRAXIS 候选代码。先在不 import donor Python 模块的前提下核对 donor 仓库：

```bash
test -d "$donor_repo/.git"
git -C "$donor_repo" status --short --branch
git -C "$donor_repo" remote -v
git -C "$donor_repo" rev-parse HEAD
git -C "$donor_repo" show -s --format='%H %P %s' HEAD
git -C "$donor_repo" ls-files --error-unmatch -- \
  predictors/linear_additive.py \
  predictors/latent_additive.py \
  predictors/gnn_pert.py \
  predictors/cpa_style.py \
  predictors/decoder_only.py \
  predictors/pretrained_backbone.py \
  bench/vcbench/loader.py
```

donor 必须是可解释 remote 上的 Git checkout、状态 clean、HEAD 精确等于批准的 `approved_donor_sha`。dirty、非 Git、SHA/remote 未批准或必要模块缺失时停止；不要用未完整覆盖依赖图的少量源文件 hash 冒充 Git commit 身份，也不要在本手册内 checkout、fetch 或修复 donor。实际 import 路径要在第 7 节通过信任门后再核对，因为 import 本身会执行 donor 代码。

## 5. 只读定位 W4B checkpoint

历史证据只说明以下第一个目录在 repo `390b67b` 时曾存在；2026-07-17 的候选窗口没有重新定位成功。按顺序检查两个已记录候选，不做全盘搜索：

```bash
w4b_candidate_one='/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260521_060815/checkpoints/norman_2019'
w4b_candidate_two='/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260525_075729/checkpoints/norman_2019'

for w4b_candidate in "$w4b_candidate_one" "$w4b_candidate_two"; do
  if test -d "$w4b_candidate"; then
    echo "W4B_CANDIDATE=$w4b_candidate"
  fi
done
```

如果没有输出，记录 `W4B_CKPT_DIR_NOT_FOUND` 并停止。若两个都存在，分别记录元数据，按用户批准选择一个；不得凭较新 mtime 自动替换科学资产。

对选定目录设置 `w4b_ckpt_dir`，只读核对三组必需文件：

```bash
w4b_ckpt_dir='<APPROVED_EXISTING_CANDIDATE>'
for w4b_stem in linear_additive latent_additive gnn_pert; do
  for w4b_suffix in json pt; do
    w4b_file="$w4b_ckpt_dir/$w4b_stem.$w4b_suffix"
    test -f "$w4b_file" || exit 2
    stat -c '%n %s bytes %y' "$w4b_file"
    sha256sum "$w4b_file"
  done
done
python - "$w4b_ckpt_dir" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
expected = {
    "linear_additive": "LinearAdditivePredictor",
    "latent_additive": "LatentAdditivePredictor",
    "gnn_pert": "GNNPertPredictor",
}
for stem, expected_class in expected.items():
    actual = json.loads((root / f"{stem}.json").read_text(encoding="utf-8")).get("class_name")
    if actual != expected_class:
        raise SystemExit(f"{stem}: expected {expected_class}, got {actual}")
    print(stem, actual)
PY
```

只输出文件名、size、mtime、SHA-256 和 `class_name`；不要打印完整 JSON 或模型内容。

## 6. 只读核对 Norman 数据

当前 manifest 指定 donor 根下的 processed file：

```bash
norman_file='/home/zkyd/data1/mzy/Virtual cell/data/raw/tasks_data/unseen_perts/norman2019_comb_stack.h5ad'
test -f "$norman_file"
stat -c '%n %s bytes %y' "$norman_file"
sha256sum "$norman_file"
test "$(stat -c %s "$norman_file")" = '937614888'
test "$(sha256sum "$norman_file" | awk '{print $1}')" = \
  'e3d116b4e01baffb154b7b42b4ad9d2c6680b088c2d7aba766d4dd4d8b4317de'
```

必须精确匹配：

- size：`937614888` bytes；
- SHA-256：`e3d116b4e01baffb154b7b42b4ad9d2c6680b088c2d7aba766d4dd4d8b4317de`。

不匹配时停止。不要复制数据到 Git、wheel、container 或新的远端目录。

## 7. 通过信任门后执行唯一的 Gate A 真 ML 验收

保持候选 checkout 与 `virtualcell` 环境不变。先用台账的批准值重新验证 donor SHA/clean status 和六文件 digest；任一不相等都停止，绝不进入 `torch.load`：

```bash
(
  set -euo pipefail
  cd "$praxis_repo"
  export W4B_CKPT_DIR="$w4b_ckpt_dir"

  test "$(git -C "$donor_repo" rev-parse HEAD)" = "$approved_donor_sha"
  test "$(git -C "$donor_repo" config --get remote.origin.url)" = "$approved_donor_origin_url"
  test -z "$(git -C "$donor_repo" status --porcelain)"

  check_approved_sha() {
    approved_sha="$1"
    approved_file="$2"
    actual_sha="$(sha256sum "$approved_file" | awk '{print $1}')"
    test "$actual_sha" = "$approved_sha"
  }
  check_approved_sha "$approved_linear_additive_json_sha" "$w4b_ckpt_dir/linear_additive.json"
  check_approved_sha "$approved_linear_additive_pt_sha" "$w4b_ckpt_dir/linear_additive.pt"
  check_approved_sha "$approved_latent_additive_json_sha" "$w4b_ckpt_dir/latent_additive.json"
  check_approved_sha "$approved_latent_additive_pt_sha" "$w4b_ckpt_dir/latent_additive.pt"
  check_approved_sha "$approved_gnn_pert_json_sha" "$w4b_ckpt_dir/gnn_pert.json"
  check_approved_sha "$approved_gnn_pert_pt_sha" "$w4b_ckpt_dir/gnn_pert.pt"

  test "$(stat -c %s "$norman_file")" = '937614888'
  check_approved_sha \
    'e3d116b4e01baffb154b7b42b4ad9d2c6680b088c2d7aba766d4dd4d8b4317de' \
    "$norman_file"

  python - "$donor_repo" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))

from bench.vcbench import loader
from predictors import (
    cpa_style,
    decoder_only,
    gnn_pert,
    latent_additive,
    linear_additive,
    pretrained_backbone,
)

for module in (
    loader,
    linear_additive,
    latent_additive,
    gnn_pert,
    cpa_style,
    decoder_only,
    pretrained_backbone,
):
    path = pathlib.Path(module.__file__).resolve()
    path.relative_to(root)
    print(module.__name__, path)
PY

  python -m pytest \
    praxis_virtualcell/tests/test_ml_workflow_e2e.py \
    --run-remote -m remote -p no:cacheprovider -o addopts='' -q -ra
)
```

上述 import 只有在两道批准门都满足后才允许执行；每个路径必须解析到批准的 `$donor_repo`。唯一合格结果是 `2 passed / 0 skipped / 0 failed`。它证明批准 donor/checkpoint 的 CPU-loaded 推理与 Gate A 行为，不证明 CUDA/GPU 执行。两条用例分别要求：

- human 真 ML 路径中 `MockLinear`、`MockCPA`、`MockGEARS` 三个 predictor 全部 success；无 rejected/failed；每个 `model_version` 精确绑定对应 `.json + .pt` 内容身份；input/output hash 格式完整，output hash 与实际 predictor result 一致；Gate A 未触发。
- bacteria 路径中三个 predictor 明确 rejected、零 used，workflow 诚实 abstain，Gate A 不因空 `models_used` 误触发。

若输出为 skip，即使退出码为 0 也仍是 pending。不要加入新的 skip、放宽断言或临时改源码让测试通过。

## 8. 证据记录与收口

在本地状态文档记录以下内容，不提交 checkpoint、数据或完整远端环境：

| 证据 | 必需值 |
|---|---|
| GitHub ref / `.53` HEAD | 同一批准 SHA |
| `.53` repo status | 原始输出；任何例外须与同步台账一致 |
| Python / torch / CUDA | 版本与 CUDA available/device count |
| donor 代码 | origin remote、clean status、批准 SHA、七个实际 import path、批准人/时间 |
| checkpoint | 目录、六个 checkpoint filename/size/mtime/SHA-256（三 JSON sidecar、三 PT 权重）、三个 class、可信来源与批准人/时间；不记录秘密 |
| Norman data | size/SHA 与 manifest 一致 |
| pytest | 完整命令、开始/结束时间、`2 passed / 0 skipped / 0 failed` |
| Gate A | human 未触发；bacteria 为空 used 的设计路径 |

通过后只允许把当前候选的 C5 远端项从 `pending` 更新为 `met at <SHA>/<environment>`；不得据此升级 GEARS/scGPT、独立结果冲突检测、LLM unsupported claim、跨设备哈希稳定性或 SOTA 声明。

测试命令通过 `GIT_OPTIONAL_LOCKS=0`、`PYTHONDONTWRITEBYTECODE=1`、`PIP_DISABLE_PIP_VERSION_CHECK=1` 和 `-p no:cacheprovider` 避免常见仓库/cache 写入。离开窗口前再次只读执行 PRAXIS 与 donor 的 `git status --short --branch`、`git rev-parse HEAD`，并复核 PRAXIS 的 `git status --ignored --short`；必须与进入时一致。若测试意外产生文件或状态变化，保留证据并停止，未经新授权不得清理。

长期加固项是先验证现有 bundle 能否在 `weights_only=True` 下加载，不能时迁移为纯 `state_dict`/安全格式并登记新 digest；在迁移完成前，任何新的或未批准 PT 都必须 fail closed。
