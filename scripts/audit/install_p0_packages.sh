#!/usr/bin/env bash
# install_p0_packages.sh
# 在 .53(staging)上跑,补齐 SOFTWARE-GAP-REPORT.md 列出的 P0 缺口。
#
# 用法:
#   bash install_p0_packages.sh dry-run    # 仅打印命令,不执行
#   bash install_p0_packages.sh run        # 真跑
#
# 范围(已剔除 foldx,改走 pyrosetta @ antibody env):
#   1. gnina        → praxis-dock           (dock 5 个 skill 解锁)
#   2. mkdssp/dssp  → praxis-protein        (enzyme 3 个 skill + RSA 标注)
#   3. mmseqs2      → PRAXIS-Enzyme         (conservation MSA)
#   4. praxis-pharma env 新建(PBPK / 异速度量)
#   5. 不做:foldx 安装。所有 ΔΔG 走 pyrosetta-stability-scan(antibody env)。

set -uo pipefail   # 故意不开 -e:单节失败不阻塞后续

MODE="${1:-dry-run}"

if [[ "$MODE" != "dry-run" && "$MODE" != "run" ]]; then
  echo "Usage: $0 {dry-run|run}" >&2
  exit 2
fi

run() {
  echo "$ $*"
  if [[ "$MODE" == "run" ]]; then
    eval "$@"
  fi
}

echo "=== P0 install · mode=$MODE ==="
echo "host: $(hostname)  date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 0. conda 必须可用(非交互式 shell 不会自动 source ~/.bashrc,显式找)
for candidate in \
  "/home/zkyd/software/miniconda3/etc/profile.d/conda.sh" \
  "$HOME/miniconda3/etc/profile.d/conda.sh" \
  "$HOME/anaconda3/etc/profile.d/conda.sh" \
  "/opt/miniconda3/etc/profile.d/conda.sh"
do
  if [[ -f "$candidate" ]]; then
    # shellcheck disable=SC1090
    source "$candidate"
    break
  fi
done

if ! command -v conda >/dev/null 2>&1; then
  echo "[error] conda not found · 请在脚本顶部加你的 conda init 路径" >&2
  exit 1
fi

# ---------------- 1. gnina -> praxis-dock ----------------
# gnina 已不在 bioconda;走 GitHub 预编译二进制 (linux-x64)。CUDA 版需源码,这里只装 CPU 版。
echo
echo "--- [1/4] gnina -> praxis-dock (GitHub release CPU binary) ---"
if conda env list | awk '{print $1}' | grep -qx 'praxis-dock'; then
  GNINA_BIN="$(conda info --envs | awk '/^praxis-dock /{print $NF}')/bin/gnina"
  GNINA_URL="https://github.com/gnina/gnina/releases/latest/download/gnina"
  if [[ "$MODE" == "run" ]]; then
    echo "$ wget -q -O $GNINA_BIN $GNINA_URL"
    if wget -q -O "$GNINA_BIN" "$GNINA_URL"; then
      chmod +x "$GNINA_BIN"
      echo "[ok] gnina downloaded → $GNINA_BIN"
    else
      rm -f "$GNINA_BIN"
      echo "[fail] gnina 下载失败 · 跳过(需手工:从 https://github.com/gnina/gnina/releases 下载放入 $GNINA_BIN)"
    fi
  else
    echo "$ wget -O $GNINA_BIN $GNINA_URL  # dry-run"
  fi
else
  echo "[warn] praxis-dock env not found · skipping."
fi

# 校验
run "conda run -n praxis-dock which gnina 2>/dev/null || echo '[verify-fail] gnina not on PATH'"

# ---------------- 2. mkdssp/dssp -> praxis-protein ----------------
echo
echo "--- [2/4] mkdssp -> praxis-protein ---"
if conda env list | awk '{print $1}' | grep -qx 'praxis-protein'; then
  run "conda install -n praxis-protein -y -c bioconda dssp mkdssp"
  run "conda run -n praxis-protein bash -c 'ln -sf \$(which mkdssp) \$CONDA_PREFIX/bin/dssp || true'"
else
  echo "[warn] praxis-protein env not found · skipping."
fi

# ---------------- 3. mmseqs2 -> PRAXIS-Enzyme ----------------
echo
echo "--- [3/4] mmseqs2 -> PRAXIS-Enzyme ---"
if conda env list | awk '{print $1}' | grep -qx 'PRAXIS-Enzyme'; then
  run "conda install -n PRAXIS-Enzyme -y -c bioconda mmseqs2"
else
  echo "[warn] PRAXIS-Enzyme env not found · skipping。"
fi
run "conda run -n PRAXIS-Enzyme which mmseqs || echo '[verify-fail] mmseqs not on PATH'"

# ---------------- 4. praxis-pharma env 新建 ----------------
echo
echo "--- [4/4] praxis-pharma env 新建 ---"
if conda env list | awk '{print $1}' | grep -qx 'praxis-pharma'; then
  echo "[skip] praxis-pharma already exists."
else
  run "conda create -n praxis-pharma -y -c conda-forge -c bioconda \\
        python=3.11 numpy scipy pandas lifelines openpyxl matplotlib scikit-learn"
  run "conda run -n praxis-pharma pip install pkpdsim PKPDsim || true"
fi

# ---------------- 总结 ----------------
echo
echo "=== Done. ==="
echo "next steps:"
echo "  - 在本机(Mac canonical) 重跑 host inventory:"
echo "    ssh zkyd@10.102.106.53 'bash -s' < scripts/audit/collect_host.sh > _audit/host_raw.txt"
echo "    python scripts/audit/parse_host.py _audit/host_raw.txt _audit/host_inventory.json"
echo "    python scripts/audit/parity.py"
echo "  - 主路径 skill 数应从 26 → ~35"
echo ""
echo "foldx NOTE:"
echo "  本脚本 *故意不装* foldx。所有 ΔΔG 已统一走 brains/enzyme/skills/workflows/pyrosetta-stability-scan,"
echo "  使用 staging 上已装的 antibody env(pyrosetta cartesian_ddg)。"
