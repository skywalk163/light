#!/usr/bin/env bash
# 临时诊断脚本（不并入主线）：复现 test_R159_L218_ContentLength口径 A/B 的 rc=-11，
# 并用 ASAN 复跑拿栈。用法：REPO=<仓库根> bash tools/_debug_linux_segv.sh
REPO="${REPO:-$(pwd)}"
export PYTHONPATH="$REPO/src:$REPO/tests:$REPO/tests/unit"
export PYTHONUNBUFFERED=1
cd "$REPO" || exit 1

echo "===== env ====="
uname -a
clang --version || true
python --version
echo "REPO=$REPO  PWD=$(pwd)"

WIN=/tmp/segvdbg2
rm -rf "$WIN"; mkdir -p "$WIN"
cd "$WIN" || exit 1

echo "===== ① O0 真跑（用例自带严格 master）====="
REPO="$REPO" python "$REPO/tools/segv_218_probe.py"
echo "① exit=$?"

echo "===== ② ASAN 复跑 ====="
REPO="$REPO" python "$REPO/tools/segv_218_probe.py" --asan
echo "② exit=$?"

