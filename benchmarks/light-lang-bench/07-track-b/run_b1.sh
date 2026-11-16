#!/bin/sh
# MiniBridge · B1 端到端（进程编排）
#
# 用法： sh run_b1.sh tests/case_basic.ndjson
#        sh run_b1.sh              （从 stdin 读）
#
# 判据（任务卡 §3）：
#   sh run_b1.sh tests/case_basic.ndjson | diff - tests/expected_b1.txt   # 必须无差异
#
# 本脚本只做「把参数原样交给光明侧入口」这一件事：路由决策、handler 调用、
# 错误处理全部在 minibridge.light（+ mb_路由/mb_进程）里完成。
# 若还没构建，先跑一次 build.sh（幂等）。

set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$HERE" || exit 1

LAUNCHER=".build/minibridge.launcher"
if [ ! -x "$LAUNCHER" ]; then
    # 没构建过就自动构建一次：判据里 build.sh 与 run_b1.sh 虽是分开的两条命令，
    # 但让 run_b1.sh 单独也能跑起来更稳（首次使用/清场后直接跑）。
    # **构建日志必须走 stderr** —— 本脚本的 stdout 是要被 diff 逐字节比对的，
    # 一旦让构建日志混进 stdout，判据会以最误导的方式失败。
    printf 'run_b1: 缺少 %s，自动执行 build.sh...\n' "$LAUNCHER" >&2
    if ! sh build.sh >&2; then
        printf 'run_b1: build.sh 失败\n' >&2
        exit 1
    fi
fi

# 每次运行从干净状态起步：h_py_append 的累计计数是「out.log 现有行数」，
# 不清掉的话同一输入第二次跑就会得到 OK 2 —— 判据要求可复现，所以这里负责清场。
# 注意：清的是**每次运行前**，运行**内部**的多条记录仍然正常累计（那才是考点）。
rm -f out.log

if [ "$#" -ge 1 ]; then
    exec sh "$LAUNCHER" minibridge.light "$1"
fi
# 无参数：从 stdin 读（launcher 约定第二个参数为空串表示「不传文件」）
exec sh "$LAUNCHER" minibridge.light ""
