#!/usr/bin/env bash
# 临时诊断脚本（不并入主线）：在 Linux runner 上复现「原生腿 rc=-11」并取三份证据
#   ① 直跑（确认 rc 与输出）
#   ② gdb 栈回溯
#   ③ AddressSanitizer 报告（定位越界/悬空/双重释放）
# 用法：REPO=<仓库根> bash tools/_debug_linux_segv.sh
set -u
REPO="${REPO:-$(pwd)}"
export PYTHONPATH="$REPO/src"
echo "===== env ====="
uname -a
clang --version || true
python --version
ulimit -a

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

echo "===== ① 按测试同口径编译（optimize_level=2）====="
python - <<'PY'
import subprocess
from llvm.compiler import compile_light_typed
exe = compile_light_typed('主.light', '产物', optimize_level=2, verbose=True)
print('EXE =', exe)
r = subprocess.run([exe], capture_output=True, text=True)
print('RC  =', r.returncode)
print('OUT =', repr(r.stdout))
print('ERR =', repr(r.stderr))
PY

echo "===== ② gdb 栈回溯（O2，无 -g，靠符号名即可定位）====="
if command -v gdb >/dev/null 2>&1; then
  gdb -batch -ex 'set pagination off' -ex 'run' -ex 'bt 40' -ex 'info registers rip' --args ./产物 2>&1 | tail -60
else
  echo "no gdb"
fi

echo "===== ③ ASAN 构建并运行 ====="
clang -c -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer 产物.ll -o 主.o 2>&1 | tail -20
clang -c -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer "$REPO/src/llvm/runtime_typed.c" -o rt.o 2>&1 | tail -20
clang -fsanitize=address,undefined -g 主.o rt.o -o 产物_asan -lm -pthread 2>&1 | tail -20
if [ -x ./产物_asan ]; then
  ASAN_OPTIONS="detect_leaks=0:abort_on_error=0:symbolize=1" UBSAN_OPTIONS="print_stacktrace=1" ./产物_asan 2>&1 | head -80
  echo "ASAN RC = $?"
else
  echo "ASAN 构建失败"
fi

echo "===== ④ O0 对照（排除 -O2 优化放大 UB）====="
python - <<'PY'
import subprocess
from llvm.compiler import compile_light_typed
exe = compile_light_typed('主.light', '产物_o0', optimize_level=0)
r = subprocess.run([exe], capture_output=True, text=True)
print('O0 RC  =', r.returncode)
print('O0 OUT =', repr(r.stdout))
print('O0 ERR =', repr(r.stderr))
PY
