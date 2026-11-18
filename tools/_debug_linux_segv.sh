#!/usr/bin/env bash
# 临时诊断脚本（不并入主线）：复现 test_R159_L218_ContentLength口径 A/B 的 rc=-11，
# 并用 ASAN 复跑拿栈。用法：REPO=<仓库根> bash tools/_debug_linux_segv.sh
set -u
REPO="${REPO:-$(pwd)}"
export PYTHONPATH="$REPO/src:$REPO/tests/unit"
cd "$REPO"

echo "===== env ====="
uname -a
clang --version || true
python --version

WIN=/tmp/segvdbg2
rm -rf "$WIN"; mkdir -p "$WIN"
cd "$WIN"

echo "===== ① O0 真跑（用例自带严格 master）====="
REPO="$REPO" python "$REPO/tools/_debug_218.py" 2>&1 | tail -30

echo "===== ② ASAN 复跑 ====="
REPO="$REPO" python "$REPO/tools/_debug_218.py" --asan 2>&1 | tail -60
