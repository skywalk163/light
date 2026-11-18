#!/usr/bin/env bash
# 临时诊断脚本（不并入主线）：Linux runner 上验证「原生腿 rc=-11」修复效果
#   ① 跑此前崩溃的整簇用例（真判据）
#   ② W4 单例：O2 直跑 + gdb 回溯（若仍崩）
#   ③ W4 的 ASAN 构建（定位残余越界）
# 用法：REPO=<仓库根> bash tools/_debug_linux_segv.sh
set -u
REPO="${REPO:-$(pwd)}"
export PYTHONPATH="$REPO/src"
cd "$REPO"

echo "===== env ====="
uname -a
clang --version || true
python --version

echo "===== ① 崩溃簇用例（-n 0 串行，真判据）====="
pytest tests/unit/test_R146_L204_嵌套dict深拷贝.py \
       tests/unit/test_R142_L187_rethrow.py \
       tests/unit/test_R142_L196_异步方法形参与协程.py \
       tests/unit/test_R131_L186L187_原生腿.py \
       tests/unit/test_R119B_异步等待内存回收.py \
       tests/unit/test_llvm_first_class_fn.py \
       tests/unit/test_R129_DvClosure地基.py \
       tests/unit/test_llvm_builtin_gaps.py \
       "tests/unit/test_原生腿_R11C_数据高级.py::Test图像处理基础" \
       -n 0 -q --no-header --timeout=600 2>&1 | tail -40

WIN=/tmp/segvdbg
rm -rf "$WIN"; mkdir -p "$WIN"; cd "$WIN"

cat > 主.light <<'LIGHT'
类 仓库:
  段落 设置回():
    设 己.回 为 {"错误":{"码":-1,"消息":"连接失败"},"结果":"ok"}
    返回 空

段落 主():
  设 a 为 新建 仓库()
  a.设置回()
  输出("码=" 加上 转字符串(a.回["错误"]["码"]) 加上 " 消息=" 加上 转字符串(a.回["错误"]["消息"]))
LIGHT

echo "===== ② 按测试同口径编译（O2）并直跑 ====="
python - <<'PY'
import os, subprocess
from llvm.compiler import compile_light_typed
exe = compile_light_typed('主.light', '产物', optimize_level=2)
print('EXE =', exe)
r = subprocess.run([os.path.abspath(exe)], capture_output=True, text=True)
print('RC  =', r.returncode)
print('OUT =', repr(r.stdout))
print('ERR =', repr(r.stderr))
PY

if [ -x ./产物 ]; then
  ./产物; echo "直跑 RC = $?"
fi

echo "===== ③ ASAN 构建并运行 ====="
clang -c -O1 -g -fsanitize=address,undefined 产物.ll -o 主.o 2>&1 | tail -5
clang -c -O1 -g -fsanitize=address,undefined "$REPO/src/llvm/runtime_typed.c" -o rt.o 2>&1 | tail -5
clang -fsanitize=address,undefined -g 主.o rt.o -o 产物_asan -lm -pthread 2>&1 | tail -5
if [ -x ./产物_asan ]; then
  ASAN_OPTIONS="detect_leaks=0" UBSAN_OPTIONS="print_stacktrace=1" ./产物_asan 2>&1 | head -60
  echo "ASAN 完成"
fi
