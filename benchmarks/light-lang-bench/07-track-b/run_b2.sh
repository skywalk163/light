#!/bin/sh
# MiniBridge · B2 端到端（C FFI 直调）
#
# 用法： sh run_b2.sh tests/case_basic.ndjson
#        sh run_b2.sh              （从 stdin 读）
#
# 判据（任务卡 §3）：
#   sh run_b2.sh tests/case_basic.ndjson | diff - tests/expected_b1.txt   # 必须与 B1 完全相同
#
# 与 B1 的唯一差别（规格 §4.3）：`h_c_hash` 不再起外部进程，而是走光明侧
# `引 C:` 的 C FFI 直调（mb_cffi.light）。`h_py_append` / `h_go_len` 仍走进程，
# 路由与错误处理完全共用。
#
# 降级路径（规格 §4.2(b)，允许）：若本机确实没有 C 编译器，
# 打印 `SKIP: no C compiler` 与 `B2_status=blocked_no_c_compiler` 并返回 0 ——
# 不算失败，但必须在规格.md 记录「FFI 直调未被实测验证，结论只能用于 B1」。
# 绝不为了「让 B2 看起来通过」而用 Python/Go 冒充 C（规格 §4.2 第 3 条）。

set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$HERE" || exit 1

LAUNCHER=".build/minibridge.launcher"
if [ ! -x "$LAUNCHER" ]; then
    # 同 run_b1.sh：自动补构建，日志走 stderr 以免污染被比对的 stdout。
    printf 'run_b2: 缺少 %s，自动执行 build.sh...\n' "$LAUNCHER" >&2
    if ! sh build.sh >&2; then
        printf 'run_b2: build.sh 失败\n' >&2
        exit 1
    fi
fi

STATUS_FILE=".build/b2_status"
if [ -f "$STATUS_FILE" ] && [ "$(cat "$STATUS_FILE")" = "blocked_no_c_compiler" ]; then
    printf 'SKIP: no C compiler\n'
    printf 'B2_status=blocked_no_c_compiler\n'
    exit 0
fi

# 运行前再确认一次编译器在场：.so 由光明侧 `引 C:` 在运行期现场编译，
# 光有 build 记录不算数。
CC_FOUND=""
for cand in cc gcc clang; do
    if command -v "$cand" >/dev/null 2>&1; then
        CC_FOUND=$cand
        break
    fi
done
if [ -z "$CC_FOUND" ]; then
    printf 'SKIP: no C compiler\n'
    printf 'B2_status=blocked_no_c_compiler\n'
    exit 0
fi

# 与 run_b1.sh 同样清场，保证两次运行的输出可复现（理由见 run_b1.sh）。
rm -f out.log

if [ "$#" -ge 1 ]; then
    MB_MODE=b2; export MB_MODE
    exec sh "$LAUNCHER" minibridge.light "$1"
fi
MB_MODE=b2; export MB_MODE
exec sh "$LAUNCHER" minibridge.light ""
