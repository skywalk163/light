#!/usr/bin/env sh
# 光明（Light）冒烟测试：10 秒回答「装好了没有」。
#
# 用法（任意目录均可）：
#   ./scripts/smoke.sh
#   LIGHT_BIN=/path/to/light ./scripts/smoke.sh   # 指定非 PATH 里的可执行文件
#
# 判据（与 quye.com/start.html 的「成功时你会看到什么」逐字一致）：
#   1. `light --version` 输出含 v0.4.x；
#   2. `light run` 一个 hello.light 输出「你好，世界！」，退出码 0；
#   3. 两条都过才打印「✅ 装好了」，脚本退出码 0。
#
# 任一失败：原因写到 stderr，退出码 1。
# 只依赖 POSIX sh；不调用 grep / head / awk（Windows worker 上会 255 假失败）。

set -u

LIGHT_BIN=${LIGHT_BIN:-light}

fail() {
    printf '❌ 没装好：%s\n' "$1" >&2
    exit 1
}

if ! command -v "$LIGHT_BIN" >/dev/null 2>&1; then
    fail "找不到命令 $LIGHT_BIN，请先安装：pip install guangming"
fi

# ── 判据 1：版本 0.4.x ──────────────────────────────────────────────
version=$("$LIGHT_BIN" --version 2>&1) || fail "light --version 执行失败：$version"
case "$version" in
    *v0.4.*) ;;
    *) fail "版本不是 0.4.x：$version" ;;
esac

# ── 判据 2：跑通最小 hello.light ────────────────────────────────────
tmpdir=$(mktemp -d 2>/dev/null) || fail "无法创建临时目录（mktemp 不可用）"
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM

cat >"$tmpdir/hello.light" <<'LIGHT'
打印("你好，世界！")
LIGHT

output=$("$LIGHT_BIN" run "$tmpdir/hello.light")
rc=$?
[ "$rc" -eq 0 ] || fail "light run 退出码 $rc（预期 0）"
[ "$output" = "你好，世界！" ] || fail "light run 输出与预期不一致：$output"

# ── 判据 3：成功时只吐这三行 ────────────────────────────────────────
printf '%s\n' "$version"
printf '%s\n' "$output"
printf '✅ 装好了\n'
