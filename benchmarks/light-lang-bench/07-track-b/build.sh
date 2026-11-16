#!/bin/sh
# MiniBridge · 一键构建（规格 §5 / DoD D6：必须幂等，连跑两次结果一致）
#
# 产物（全部落在本目录内，绝不写到仓外）：
#   handlers/h_go_len/h_go_len   Go handler 可执行文件
#   handlers/h_c_hash             C handler 的 **CLI 形态**（B1 进程编排用，-DMB_HASH_CLI）
#   handlers/libh_c_hash.so       C handler 的 **共享库形态**（B2 FFI 用；供自测/交叉对拍加载）
#   .build/minibridge.launcher    光明侧入口包装（固定 PYTHONPATH 与 --stdlib-dir）
#
# 幂等策略：每个产物都先删后建；Go 用固定 -trimpath + 不写 buildid，避免二次构建
# 的二进制差异（本脚本不比对二进制 hash，只保证「连跑两次所有 verify 都过」）。
#
# 退出码：0 = 全部成功；1 = 必需件失败。B2 缺 C 编译器属**允许降级**（规格 §4.2(b)），
# 此时打印 B2_status=blocked_no_c_compiler 但仍返回 0 —— 因为 B1 才是本卡核心交付。

set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$HERE" || exit 1

BUILD_DIR="$HERE/.build"
mkdir -p "$BUILD_DIR"

LIGHT_REPO=${LIGHT_REPO:-}
if [ -z "$LIGHT_REPO" ]; then
    # 本卡在 light 仓内：07-track-b → 06 → light 根（benchmarks/light-lang-bench/07-track-b）
    LIGHT_REPO=$(CDPATH= cd -- "$HERE/../../.." && pwd)
fi

say() { printf '%s\n' "$*"; }
fail() { printf 'BUILD FAIL: %s\n' "$*" >&2; }

# ---------------------------------------------------------------- #
# 1. Python handler：只做语法自检（无需构建，run_b1.sh 用 python3 直接跑）
# ---------------------------------------------------------------- #
if python3 -c "import ast,sys; ast.parse(open('handlers/h_py_append.py',encoding='utf-8').read())" 2>/dev/null; then
    say "OK   handlers/h_py_append.py（语法自检通过，无需编译）"
else
    fail "handlers/h_py_append.py 语法错误"
    exit 1
fi

# ---------------------------------------------------------------- #
# 2. Go handler
# ---------------------------------------------------------------- #
if command -v go >/dev/null 2>&1; then
    rm -f handlers/h_go_len/h_go_len
    if ( cd handlers/h_go_len && GOFLAGS=-mod=mod \
            go build -trimpath -buildvcs=false -o h_go_len . ) >"$BUILD_DIR/go_build.log" 2>&1; then
        say "OK   handlers/h_go_len/h_go_len（$(go version | cut -d' ' -f3)）"
    else
        fail "Go handler 构建失败，日志见 .build/go_build.log"
        exit 1
    fi
else
    fail "找不到 go 工具链；B1 需要 Go handler"
    exit 1
fi

# ---------------------------------------------------------------- #
# 3. C handler：CLI 形态（B1）+ .so 形态（B2）
# ---------------------------------------------------------------- #
CC_BIN=""
for cand in cc gcc clang; do
    if command -v "$cand" >/dev/null 2>&1; then
        CC_BIN=$cand
        break
    fi
done

B2_STATUS="ok"
if [ -n "$CC_BIN" ]; then
    rm -f handlers/h_c_hash handlers/libh_c_hash.so
    if "$CC_BIN" -O2 -DMB_HASH_CLI -o handlers/h_c_hash handlers/h_c_hash.c \
            >"$BUILD_DIR/c_cli.log" 2>&1; then
        say "OK   handlers/h_c_hash（C CLI 形态，$CC_BIN；B1 进程编排用）"
    else
        fail "C CLI 构建失败，日志见 .build/c_cli.log"
        exit 1
    fi
    if "$CC_BIN" -shared -fPIC -O2 -o handlers/libh_c_hash.so handlers/h_c_hash.c \
            >"$BUILD_DIR/c_so.log" 2>&1; then
        say "OK   handlers/libh_c_hash.so（共享库形态，$CC_BIN；供自测交叉对拍）"
    else
        # .so 只是自测用件，缺了不影响 B2（B2 走光明 `引 C:` 自己编译）。
        say "WARN handlers/libh_c_hash.so 未编出（不影响 B2：B2 由光明侧 引 C: 自行编译）"
    fi
else
    # 规格 §4.2(b)：无编译器是允许的降级形态，不是本卡失败。
    B2_STATUS="blocked_no_c_compiler"
    say "SKIP handlers/h_c_hash（找不到 cc/gcc/clang）"
    say "     B2_status=blocked_no_c_compiler —— B2 的 FFI 直调在本机未被实测验证，"
    say "     结论只能用于 B1（规格 §4.2(b) / §6）。"
fi
printf '%s\n' "$B2_STATUS" > "$BUILD_DIR/b2_status"

# ---------------------------------------------------------------- #
# 4. 光明侧入口包装器
#    为什么要有它：`light run` 的地板（_light_builtin）依赖 --stdlib-dir 或 cwd 探测，
#    而本卡要求在 07-track-b 目录下跑（cwd 不是 light 仓根）。包装器把这两件事固定死，
#    让 run_b1.sh / run_b2.sh 只关心「跑哪个 .light」。
# ---------------------------------------------------------------- #
if [ ! -f "$LIGHT_REPO/cli/light.py" ]; then
    fail "找不到 light 仓（期望 $LIGHT_REPO/cli/light.py）；可用 LIGHT_REPO=... 覆盖"
    exit 1
fi
if [ ! -d "$LIGHT_REPO/stdlib" ]; then
    fail "找不到 light stdlib（期望 $LIGHT_REPO/stdlib）"
    exit 1
fi

# 用带引号的 heredoc 再 sed 替换占位符：不带引号时，注释里的反引号会被 shell
# 当命令替换执行（实测踩到：注释里写 `light run` 导致 "light: not found"）。
cat > "$BUILD_DIR/minibridge.launcher" <<'LAUNCHER'
#!/bin/sh
# 自动生成，勿手改（由 ../build.sh 产出）。固定 PYTHONPATH 与 --stdlib-dir，
# 使光明侧入口在任意 cwd 下都能加载地板与本地模块。
LIGHT_REPO='__LIGHT_REPO__'
HERE='__HERE__'
PYTHONPATH="$LIGHT_REPO${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
exec python3 -m cli.light run --stdlib-dir "$LIGHT_REPO/stdlib" "$HERE/$1" -- "$2"
LAUNCHER
sed -e "s|__LIGHT_REPO__|$LIGHT_REPO|" -e "s|__HERE__|$HERE|" \
    "$BUILD_DIR/minibridge.launcher" > "$BUILD_DIR/minibridge.launcher.tmp" \
    && mv "$BUILD_DIR/minibridge.launcher.tmp" "$BUILD_DIR/minibridge.launcher"
chmod +x "$BUILD_DIR/minibridge.launcher"
say "OK   .build/minibridge.launcher（light 仓：$LIGHT_REPO）"

# ---------------------------------------------------------------- #
# 5. handler 自测：三向交叉对拍（C CLI / C .so / 参照实现）—— 只在有 .so 时做
# ---------------------------------------------------------------- #
if [ -x handlers/h_c_hash ] && [ -f handlers/libh_c_hash.so ]; then
    if sh tests/selfcheck_handlers.sh >"$BUILD_DIR/selfcheck.log" 2>&1; then
        say "OK   handler 交叉对拍通过（详见 .build/selfcheck.log）"
    else
        fail "handler 交叉对拍失败，日志见 .build/selfcheck.log"
        exit 1
    fi
fi

say ""
say "构建完成。B2_status=$B2_STATUS"
say "自测：sh run_b1.sh tests/case_basic.ndjson | diff - tests/expected_b1.txt"
if [ "$B2_STATUS" = "ok" ]; then
    say "      sh run_b2.sh tests/case_basic.ndjson | diff - tests/expected_b1.txt"
else
    say "      sh run_b2.sh  （将打印 SKIP: no C compiler 并返回 0）"
fi
exit 0
